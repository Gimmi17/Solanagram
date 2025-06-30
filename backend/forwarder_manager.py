#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Forwarder Manager - Gestione container Docker con limiti di risorse
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

class ForwarderManager:
    """Manager per la gestione dei container Docker dei forwarders"""
    
    # Limiti di risorse di default per i container
    DEFAULT_RESOURCE_LIMITS = {
        'mem_limit': '256m',           # 256MB RAM max
        'memswap_limit': '512m',       # 512MB total (RAM + swap)
        'cpu_quota': 50000,            # 50% di un core CPU
        'cpu_period': 100000,          # Periodo 100ms
        'nano_cpus': 500000000,        # 0.5 CPU (alternativa più moderna)
        'pids_limit': 100              # Max 100 processi per container
    }
    
    # Limiti massimi consentiti per utente (per evitare abusi)
    MAX_USER_LIMITS = {
        'mem_limit': '512m',
        'memswap_limit': '1g',
        'cpu_quota': 100000,           # 100% di un core CPU max
        'nano_cpus': 1000000000        # 1 CPU max
    }
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.forwarder_image = "solanagram-forwarder:latest"
            self.network_name = "solanagram-net"
            self._ensure_network_exists()
            self._ensure_forwarder_image()
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
            if cpu_limit > 1.0:
                logger.warning(f"Requested CPU {cpu_limit} exceeds max, using 1.0")
                validated_limits['nano_cpus'] = self.MAX_USER_LIMITS['nano_cpus']
            else:
                validated_limits['nano_cpus'] = int(cpu_limit * 1000000000)
        
        return validated_limits
    
    def _parse_memory_string(self, mem_str: str) -> int:
        """Converte string di memoria (es. '256m') in bytes"""
        units = {'b': 1, 'k': 1024, 'm': 1024**2, 'g': 1024**3}
        
        match = re.match(r'^(\d+)([bkmg])?$', mem_str.lower())
        if not match:
            raise ValueError(f"Invalid memory format: {mem_str}")
        
        value = int(match.group(1))
        unit = match.group(2) or 'b'
        
        return value * units[unit]
    
    def _ensure_forwarder_image(self) -> bool:
        """Ensure the forwarder Docker image exists"""
        try:
            # Check if image already exists
            try:
                self.docker_client.images.get(self.forwarder_image)
                logger.info(f"Forwarder image {self.forwarder_image} already exists")
                return True
            except docker.errors.ImageNotFound:
                pass
            
            # Build image if it doesn't exist
            logger.info(f"Building forwarder image {self.forwarder_image}...")
            # This would need the actual build process
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure forwarder image: {e}")
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
    
    def create_forwarder_container(
        self, 
        user_id: int,
        phone: str,
        api_id: int,
        api_hash: str,
        session_string: str,
        source_chat_id: str,
        source_chat_title: str,
        target_type: str,
        target_id: str,
        target_name: str,
        session_file_path: Optional[str] = None,
        resource_limits: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, str]:
        """Create and start a new forwarder container with resource limits"""
        try:
            # Validate resource limits
            limits = self.validate_resource_limits(resource_limits or {})
            
            # Generate container name
            safe_source = self._sanitize_container_name(source_chat_title)[:20]
            safe_target = self._sanitize_container_name(target_name)[:20]
            container_name = f"solanagram-fwd-{user_id}-{safe_source}-to-{safe_target}".lower()
            
            logger.info(f"Creating forwarder container: {container_name} with limits: {limits}")
            
            # Check if container already exists
            try:
                existing_container = self.docker_client.containers.get(container_name)
                if existing_container.status == "running":
                    return False, container_name, "Container already exists and is running"
                else:
                    existing_container.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            # Prepare environment variables
            environment = {
                "TELEGRAM_PHONE": phone,
                "TELEGRAM_API_ID": str(api_id),
                "TELEGRAM_API_HASH": api_hash,
                "CONFIG_FILE": "/app/configs/config.json",
                "SOURCE_CHAT_ID": source_chat_id,
                "TARGET_TYPE": target_type,
                "TARGET_ID": target_id
            }
            
            # Determine whether to use session file or session string
            use_session_file = session_file_path and os.path.exists(session_file_path)
            
            if use_session_file:
                environment["SESSION_FILE"] = "/app/configs/session.session"
                logger.info(f"Using session file for container creation: {session_file_path}")
            else:
                environment["TELEGRAM_SESSION"] = session_string
                logger.info(f"Using session string for container creation, length: {len(session_string) if session_string else 0}")
            
            # Create container with resource limits
            container = self.docker_client.containers.create(
                self.forwarder_image,
                name=container_name,
                environment=environment,
                network=self.network_name,
                detach=True,
                # Resource limits
                mem_limit=limits['mem_limit'],
                memswap_limit=limits['memswap_limit'],
                nano_cpus=limits['nano_cpus'],
                pids_limit=limits['pids_limit'],
                # Security options
                security_opt=['no-new-privileges'],
                # Logging configuration
                log_config={
                    'type': 'json-file',
                    'config': {
                        'max-size': '10m',
                        'max-file': '3'
                    }
                },
                # Restart policy
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Start the container
            container.start()
            
            # Create config.json file in the container
            config_data = {
                "source_chat_id": source_chat_id,
                "source_chat_title": source_chat_title,
                "target_type": target_type,
                "target_id": target_id,
                "target_name": target_name,
                "phone": phone,
                "api_id": api_id,
                "api_hash": api_hash
            }
            
            # Create config directory and file
            container.exec_run("mkdir -p /app/configs")
            config_json = json.dumps(config_data, indent=2)
            
            # Write config.json to container
            exec_result = container.exec_run(
                f"sh -c 'echo {json.dumps(config_json)} > /app/configs/config.json'"
            )
            
            if exec_result.exit_code != 0:
                logger.error(f"Failed to create config.json: {exec_result.output}")
                container.stop()
                container.remove()
                return False, container_name, "Failed to create configuration file"
            
            # If we have a valid session file, copy it to the container
            if use_session_file:
                # Create a tar archive containing the session file
                tar_buffer = io.BytesIO()
                with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                    tar.add(session_file_path, arcname='session.session')
                
                tar_buffer.seek(0)
                # Put tar archive in container
                container.put_archive('/app/configs/', tar_buffer.getvalue())
                logger.info(f"Copied session file {session_file_path} to container")
            
            # Restart container to apply configuration
            container.restart()
            
            logger.info(f"Created and started container: {container_name}")
            return True, container_name, "Container created successfully"
            
        except Exception as e:
            logger.error(f"Failed to create forwarder container: {e}")
            return False, "", str(e)
    
    def get_container_status(self, container_name: str) -> Dict[str, Any]:
        """Get status and metrics of a forwarder container"""
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Get container stats (non-streaming)
            stats = container.stats(stream=False)
            
            # Calculate memory usage
            memory_stats = stats.get('memory_stats', {})
            memory_usage = memory_stats.get('usage', 0)
            memory_limit = memory_stats.get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
            
            # Calculate CPU usage
            cpu_stats = stats.get('cpu_stats', {})
            precpu_stats = stats.get('precpu_stats', {})
            
            cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                       precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
            system_delta = cpu_stats.get('system_cpu_usage', 0) - \
                          precpu_stats.get('system_cpu_usage', 0)
            
            cpu_percent = 0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * 100
            
            # Get message count from container logs or file
            message_count = 0
            try:
                result = container.exec_run("cat /app/configs/count.txt")
                if result.exit_code == 0:
                    message_count = int(result.output.decode().strip())
            except:
                pass
            
            return {
                "status": container.status,
                "running": container.status == "running",
                "message_count": message_count,
                "created": container.attrs['Created'],
                "memory_usage_mb": round(memory_usage / (1024 * 1024), 2),
                "memory_limit_mb": round(memory_limit / (1024 * 1024), 2),
                "memory_percent": round(memory_percent, 2),
                "cpu_percent": round(cpu_percent, 2),
                "restart_count": container.attrs.get('RestartCount', 0)
            }
            
        except docker.errors.NotFound:
            return {
                "status": "not_found",
                "running": False,
                "message_count": 0
            }
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return {
                "status": "error",
                "running": False,
                "message_count": 0,
                "error": str(e)
            }
    
    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """Restart a forwarder container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.restart()
            logger.info(f"Restarted container: {container_name}")
            return True, "Container restarted successfully"
        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            logger.error(f"Failed to restart container: {e}")
            return False, str(e)
    
    def stop_and_remove_container(self, container_name: str) -> Tuple[bool, str]:
        """Stop and remove a forwarder container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove()
            logger.info(f"Stopped and removed container: {container_name}")
            return True, "Container removed successfully"
        except docker.errors.NotFound:
            return True, "Container not found (already removed)"
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            return False, str(e)
    
    def list_user_containers(self, user_id: int) -> List[Dict[str, Any]]:
        """List all containers for a specific user"""
        try:
            containers = self.docker_client.containers.list(all=True)
            user_containers = []
            
            prefix = f"solanagram-fwd-{user_id}-"
            for container in containers:
                if container.name.startswith(prefix):
                    user_containers.append({
                        'name': container.name,
                        'id': container.id,
                        'status': container.status,
                        'created': container.attrs['Created']
                    })
            
            return user_containers
        except Exception as e:
            logger.error(f"Failed to list user containers: {e}")
            return []
    
    def cleanup_orphaned_containers(self) -> Dict[str, Any]:
        """Remove containers that are stopped and older than 24 hours"""
        try:
            removed = 0
            containers = self.docker_client.containers.list(all=True, filters={'status': 'exited'})
            
            for container in containers:
                if container.name.startswith('solanagram-fwd-'):
                    # Check if container is older than 24 hours
                    created = datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00'))
                    age_hours = (datetime.now(created.tzinfo) - created).total_seconds() / 3600
                    
                    if age_hours > 24:
                        container.remove()
                        removed += 1
                        logger.info(f"Removed orphaned container: {container.name}")
            
            return {
                'success': True,
                'removed_count': removed
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up containers: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get overall system resource usage"""
        try:
            info = self.docker_client.info()
            
            return {
                'total_containers': info['Containers'],
                'running_containers': info['ContainersRunning'],
                'cpu_count': info['NCPU'],
                'total_memory_gb': round(info['MemTotal'] / (1024**3), 2),
                'docker_version': info['ServerVersion']
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {} 