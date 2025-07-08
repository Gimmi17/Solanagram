#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logging Manager - Gestione container Docker per il logging dei messaggi Telegram
"""

import docker
import logging
import os
import re
import json
import tarfile
import io
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class LoggingManager:
    """Manager per la gestione dei container Docker per il logging dei messaggi"""
    
    # Limiti di risorse di default per i container di logging
    DEFAULT_RESOURCE_LIMITS = {
        'mem_limit': '128m',           # 128MB RAM max (più leggero dei forwarders)
        'memswap_limit': '256m',       # 256MB total (RAM + swap)
        'cpu_quota': 25000,            # 25% di un core CPU
        'cpu_period': 100000,          # Periodo 100ms
        'nano_cpus': 250000000,        # 0.25 CPU (alternativa più moderna)
        'pids_limit': 50               # Max 50 processi per container
    }
    
    # Limiti massimi consentiti per utente
    MAX_USER_LIMITS = {
        'mem_limit': '256m',
        'memswap_limit': '512m',
        'cpu_quota': 50000,            # 50% di un core CPU max
        'nano_cpus': 500000000         # 0.5 CPU max
    }
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.logging_image = "solanagram-logger:latest"
            self.network_name = "solanagram-net"
            self._ensure_network_exists()
            self._ensure_logging_image()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
    
    def _ensure_network_exists(self):
        """Ensure the Solanagram network exists"""
        try:
            self.docker_client.networks.get(self.network_name)
        except docker.errors.NotFound:
            self.docker_client.networks.create(self.network_name, driver="bridge")
            logger.info(f"Created Docker network: {self.network_name}")
    
    def _sanitize_container_name(self, name: str) -> str:
        """Sanitize container name to be Docker-compliant"""
        # Replace non-alphanumeric characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized
    
    def validate_resource_limits(self, requested_limits: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida e normalizza i limiti di risorse richiesti
        
        Args:
            requested_limits: Limiti richiesti dall'utente
            
        Returns:
            Limiti validati e normalizzati
        """
        validated_limits = self.DEFAULT_RESOURCE_LIMITS.copy()
        
        if not requested_limits:
            return validated_limits
        
        # Validazione memoria
        if 'memory_limit' in requested_limits:
            mem_limit = self._parse_memory_string(requested_limits['memory_limit'])
            max_mem = self._parse_memory_string(self.MAX_USER_LIMITS['mem_limit'])
            
            if mem_limit > max_mem:
                logger.warning(f"Requested memory {requested_limits['memory_limit']} exceeds max, using {self.MAX_USER_LIMITS['mem_limit']}")
                validated_limits['mem_limit'] = self.MAX_USER_LIMITS['mem_limit']
            else:
                validated_limits['mem_limit'] = requested_limits['memory_limit']
        
        # Validazione CPU
        if 'cpu_limit' in requested_limits:
            cpu_limit = float(requested_limits['cpu_limit'])
            if cpu_limit > 0.5:
                logger.warning(f"Requested CPU {cpu_limit} exceeds max, using 0.5")
                validated_limits['nano_cpus'] = self.MAX_USER_LIMITS['nano_cpus']
            else:
                validated_limits['nano_cpus'] = int(cpu_limit * 1000000000)
        
        return validated_limits
    
    def _parse_memory_string(self, mem_str: str) -> int:
        """Converte string di memoria (es. '128m') in bytes"""
        units = {'b': 1, 'k': 1024, 'm': 1024**2, 'g': 1024**3}
        
        match = re.match(r'^(\d+)([bkmg])?$', mem_str.lower())
        if not match:
            raise ValueError(f"Invalid memory format: {mem_str}")
        
        value = int(match.group(1))
        unit = match.group(2) or 'b'
        
        return value * units[unit]
    
    def _ensure_logging_image(self) -> bool:
        """Ensure the logging Docker image exists"""
        try:
            # Check if image already exists
            try:
                self.docker_client.images.get(self.logging_image)
                logger.info(f"Logging image {self.logging_image} already exists")
                return True
            except docker.errors.ImageNotFound:
                pass
            
            # Build image if it doesn't exist
            logger.info(f"Building logging image {self.logging_image}...")
            # This would need the actual build process
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure logging image: {e}")
            return False
    
    def _validate_session_file(self, session_file_path: str, api_id: int, api_hash: str) -> bool:
        """
        Validate if a session file is valid and authorized
        
        Args:
            session_file_path: Path to the session file
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            
        Returns:
            True if session is valid and authorized, False otherwise
        """
        try:
            import asyncio
            from telethon import TelegramClient
            
            async def check_session():
                client = TelegramClient(session_file_path, api_id, api_hash)
                try:
                    await client.connect()
                    if await client.is_user_authorized():
                        await client.disconnect()
                        return True
                    else:
                        await client.disconnect()
                        return False
                except Exception as e:
                    logger.warning(f"Session validation failed: {e}")
                    try:
                        await client.disconnect()
                    except:
                        pass
                    return False
            
            return asyncio.run(check_session())
            
        except Exception as e:
            logger.error(f"Error validating session file: {e}")
            return False
    
    def create_logging_container(
        self, 
        user_id: int,
        phone: str,
        api_id: int,
        api_hash: str,
        session_string: str,
        chat_id: str,
        chat_title: str,
        chat_username: str,
        chat_type: str,
        session_file_path: Optional[str] = None,
        resource_limits: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, str]:
        """Create and start a new logging container with resource limits"""
        try:
            # Validate resource limits
            limits = self.validate_resource_limits(resource_limits or {})
            
            # Generate container name
            container_name = self._sanitize_container_name(f"logger_{user_id}_{chat_id}_{int(datetime.now().timestamp())}")
            
            # Check if container already exists
            try:
                existing_container = self.docker_client.containers.get(container_name)
                logger.warning(f"Container {container_name} already exists")
                return False, "Container already exists", container_name
            except docker.errors.NotFound:
                pass
            
            # Prepare environment variables
            env_vars = {
                'USER_ID': str(user_id),
                'PHONE': phone,
                'API_ID': str(api_id),
                'API_HASH': api_hash,
                'SESSION_STRING': session_string,
                'CHAT_ID': str(chat_id),
                'CHAT_TITLE': chat_title,
                'CHAT_USERNAME': chat_username or '',
                'CHAT_TYPE': chat_type,
                'DB_HOST': os.getenv('DB_HOST', 'localhost'),
                'DB_PORT': os.getenv('DB_PORT', '5432'),
                'DB_NAME': os.getenv('DB_NAME', 'chatmanager'),
                'DB_USER': os.getenv('DB_USER', 'solanagram_user'),
                'DB_PASSWORD': os.getenv('DB_PASSWORD', ''),
                'BACKEND_URL': os.getenv('BACKEND_URL', 'http://localhost:8000'),
                'LOG_LEVEL': 'INFO'
            }
            
            # Prepare container configuration
            container_config = {
                'image': self.logging_image,
                'name': container_name,
                'environment': [f"{k}={v}" for k, v in env_vars.items()],
                'network': self.network_name,
                'restart_policy': {'Name': 'unless-stopped'},
                'detach': True,
                'tty': True,
                'stdin_open': True,
                'labels': {
                    'solanagram.type': 'logger',
                    'solanagram.user_id': str(user_id),
                    'solanagram.chat_id': str(chat_id),
                    'solanagram.created_at': datetime.now().isoformat()
                }
            }
            
            # Add resource limits
            container_config.update(limits)
            
            # Create and start container
            logger.info(f"Creating logging container: {container_name}")
            container = self.docker_client.containers.run(**container_config)
            
            # Wait a moment for container to start
            import time
            time.sleep(2)
            
            # Check container status
            container.reload()
            if container.status == 'running':
                logger.info(f"Logging container {container_name} started successfully")
                return True, "Container started successfully", container_name
            else:
                # Get logs for debugging
                logs = container.logs().decode('utf-8')
                logger.error(f"Container {container_name} failed to start. Logs: {logs}")
                return False, f"Container failed to start: {logs}", container_name
                
        except Exception as e:
            logger.error(f"Error creating logging container: {e}")
            return False, str(e), ""
    
    def get_container_status(self, container_name: str) -> Dict[str, Any]:
        """Get detailed status of a logging container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.reload()
            
            # Get container stats
            try:
                stats = container.stats(stream=False)
                memory_usage = stats['memory_stats'].get('usage', 0)
                cpu_usage = stats['cpu_stats'].get('cpu_usage', {}).get('total_usage', 0)
            except:
                memory_usage = 0
                cpu_usage = 0
            
            # Get recent logs
            try:
                logs = container.logs(tail=50).decode('utf-8')
            except:
                logs = ""
            
            return {
                'container_id': container.id,
                'name': container.name,
                'status': container.status,
                'state': container.attrs['State'],
                'created': container.attrs['Created'],
                'image': container.attrs['Config']['Image'],
                'memory_usage': memory_usage,
                'cpu_usage': cpu_usage,
                'logs': logs,
                'labels': container.attrs['Config']['Labels']
            }
            
        except docker.errors.NotFound:
            return {
                'error': 'Container not found',
                'name': container_name
            }
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return {
                'error': str(e),
                'name': container_name
            }
    
    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """Restart a logging container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.restart()
            logger.info(f"Restarted logging container: {container_name}")
            return True, "Container restarted successfully"
        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            logger.error(f"Error restarting container: {e}")
            return False, str(e)
    
    def stop_and_remove_container(self, container_name: str) -> Tuple[bool, str]:
        """Stop and remove a logging container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove()
            logger.info(f"Stopped and removed logging container: {container_name}")
            return True, "Container stopped and removed successfully"
        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False, str(e)
    
    def list_user_containers(self, user_id: int) -> List[Dict[str, Any]]:
        """List all logging containers for a specific user"""
        try:
            containers = self.docker_client.containers.list(
                filters={'label': f'solanagram.user_id={user_id}'}
            )
            
            result = []
            for container in containers:
                try:
                    status = self.get_container_status(container.name)
                    result.append(status)
                except Exception as e:
                    logger.warning(f"Error getting status for container {container.name}: {e}")
                    result.append({
                        'name': container.name,
                        'error': str(e)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing user containers: {e}")
            return []
    
    def cleanup_orphaned_containers(self) -> Dict[str, Any]:
        """Clean up orphaned logging containers"""
        try:
            # Find containers with solanagram.type=logger label
            containers = self.docker_client.containers.list(
                filters={'label': 'solanagram.type=logger'}
            )
            
            cleaned_count = 0
            error_count = 0
            
            for container in containers:
                try:
                    # Check if container is running but has been running for too long without activity
                    container.reload()
                    
                    # Get container creation time
                    created = datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00'))
                    running_time = datetime.now(created.tzinfo) - created
                    
                    # If container has been running for more than 24 hours, consider it orphaned
                    if running_time.total_seconds() > 86400:  # 24 hours
                        logger.info(f"Cleaning up orphaned logging container: {container.name}")
                        container.stop(timeout=10)
                        container.remove()
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.error(f"Error cleaning up container {container.name}: {e}")
                    error_count += 1
            
            return {
                'cleaned_count': cleaned_count,
                'error_count': error_count,
                'total_containers': len(containers)
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {
                'error': str(e),
                'cleaned_count': 0,
                'error_count': 0
            }
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get system resource usage for logging containers"""
        try:
            # Get all logging containers
            containers = self.docker_client.containers.list(
                filters={'label': 'solanagram.type=logger'}
            )
            
            total_memory = 0
            total_cpu = 0
            running_count = 0
            
            for container in containers:
                try:
                    container.reload()
                    if container.status == 'running':
                        running_count += 1
                        
                        # Get container stats
                        stats = container.stats(stream=False)
                        memory_usage = stats['memory_stats'].get('usage', 0)
                        cpu_usage = stats['cpu_stats'].get('cpu_usage', {}).get('total_usage', 0)
                        
                        total_memory += memory_usage
                        total_cpu += cpu_usage
                        
                except Exception as e:
                    logger.warning(f"Error getting stats for container {container.name}: {e}")
            
            return {
                'total_containers': len(containers),
                'running_containers': running_count,
                'total_memory_usage_mb': round(total_memory / (1024 * 1024), 2),
                'total_cpu_usage': total_cpu
            }
            
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {
                'error': str(e)
            }