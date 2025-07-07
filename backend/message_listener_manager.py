#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Message Listener Manager - Manages containers that listen to Telegram messages
"""

import os
import sys
import json
import docker
import logging
import io
import tarfile
from typing import Dict, Tuple, Optional, Any, List
from datetime import datetime
import tempfile

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from forwarder_manager import ForwarderManager

logger = logging.getLogger(__name__)

class MessageListenerManager(ForwarderManager):
    """Manages message listener containers"""
    
    def __init__(self):
        super().__init__()
        self.listener_image = "solanagram-listener:latest"
        self.forwarder_image = self.listener_image  # Override parent's image
        self._ensure_listener_image()
    
    def _ensure_listener_image(self) -> bool:
        """Ensure the listener Docker image exists"""
        try:
            # Check if image already exists
            try:
                self.docker_client.images.get(self.listener_image)
                logger.info(f"Listener image {self.listener_image} already exists")
                return True
            except docker.errors.ImageNotFound:
                logger.info(f"Listener image not found, attempting to build...")
            
            # Build image if it doesn't exist
            logger.info(f"Building listener image {self.listener_image}...")
            
            # Check if Dockerfile exists
            dockerfile_path = os.path.join(os.path.dirname(__file__), '../../docker/listener/Dockerfile')
            if not os.path.exists(dockerfile_path):
                logger.warning(f"Dockerfile not found at {dockerfile_path}, using forwarder image as base")
                # Use forwarder image as base for now
                self.listener_image = "solanagram-forwarder:latest"
                return self._ensure_forwarder_image()
            
            # Build the image
            self.docker_client.images.build(
                path=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                dockerfile='docker/listener/Dockerfile',
                tag=self.listener_image,
                rm=True,
                pull=True
            )
            
            logger.info(f"Successfully built listener image {self.listener_image}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure listener image: {e}")
            # Fallback to forwarder image
            logger.info("Falling back to forwarder image")
            self.listener_image = "solanagram-forwarder:latest"
            return self._ensure_forwarder_image()
    
    def create_listener_container(
        self,
        user_id: int,
        phone: str,
        api_id: int,
        api_hash: str,
        session_string: str,
        source_chat_id: str,
        source_chat_title: str,
        source_chat_type: str,
        db_url: str,
        listener_id: int,
        session_file_path: Optional[str] = None,
        resource_limits: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, str]:
        """Create and start a new message listener container"""
        try:
            # Validate resource limits
            limits = self.validate_resource_limits(resource_limits or {})
            
            # Generate container name
            safe_source = self._sanitize_container_name(source_chat_title)[:30]
            container_name = f"solanagram-listener-{user_id}-{listener_id}-{safe_source}".lower()
            
            logger.info(f"Creating listener container: {container_name} with limits: {limits}")
            
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
                "LISTENER_ID": str(listener_id),
                "DATABASE_URL": db_url,
                "MODE": "listener"  # Set mode to listener only
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
                self.listener_image,
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
                "source_chat_type": source_chat_type,
                "listener_id": listener_id,
                "user_id": user_id,
                "phone": phone,
                "api_id": api_id,
                "api_hash": api_hash,
                "mode": "listener"
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
            
            logger.info(f"Created and started listener container: {container_name}")
            return True, container_name, "Container created successfully"
            
        except Exception as e:
            logger.error(f"Failed to create listener container: {e}")
            return False, "", str(e)
    
    def update_listener_elaborations(
        self,
        container_name: str,
        elaborations: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Update elaborations configuration for a running listener container"""
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Create elaborations config
            elaborations_json = json.dumps(elaborations, indent=2)
            
            # Write elaborations.json to container
            exec_result = container.exec_run(
                f"sh -c 'echo {json.dumps(elaborations_json)} > /app/configs/elaborations.json'"
            )
            
            if exec_result.exit_code != 0:
                logger.error(f"Failed to update elaborations: {exec_result.output}")
                return False, "Failed to update elaborations configuration"
            
            # Send signal to reload configuration (if the container supports it)
            container.exec_run("kill -HUP 1")
            
            logger.info(f"Updated elaborations for container: {container_name}")
            return True, "Elaborations updated successfully"
            
        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            logger.error(f"Failed to update elaborations: {e}")
            return False, str(e)
    
    def get_listener_stats(self, container_name: str) -> Dict[str, Any]:
        """Get statistics from a listener container"""
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Get container stats
            base_stats = self.get_container_status(container_name)
            
            # Try to get listener-specific stats
            try:
                # Read stats file if exists
                result = container.exec_run("cat /app/configs/stats.json")
                if result.exit_code == 0:
                    listener_stats = json.loads(result.output.decode())
                    base_stats.update(listener_stats)
            except:
                pass
            
            return base_stats
            
        except docker.errors.NotFound:
            return {
                "status": "not_found",
                "running": False,
                "message_count": 0
            }
        except Exception as e:
            logger.error(f"Error getting listener stats: {e}")
            return {
                "status": "error",
                "running": False,
                "message_count": 0,
                "error": str(e)
            }
    
    def list_user_listeners(self, user_id: int) -> List[Dict[str, Any]]:
        """List all listener containers for a specific user"""
        try:
            containers = self.docker_client.containers.list(all=True)
            user_containers = []
            
            prefix = f"solanagram-listener-{user_id}-"
            for container in containers:
                if container.name.startswith(prefix):
                    stats = self.get_listener_stats(container.name)
                    user_containers.append({
                        'name': container.name,
                        'id': container.id,
                        'status': container.status,
                        'created': container.attrs['Created'],
                        'stats': stats
                    })
            
            return user_containers
        except Exception as e:
            logger.error(f"Failed to list user listeners: {e}")
            return []
    
    def start_container(self, container_name: str) -> Tuple[bool, str]:
        """Start a stopped container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.start()
            logger.info(f"Started container: {container_name}")
            return True, "Container started successfully"
        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            return False, str(e)
    
    def stop_container(self, container_name: str) -> Tuple[bool, str]:
        """Stop a running container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop()
            logger.info(f"Stopped container: {container_name}")
            return True, "Container stopped successfully"
        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            return False, str(e)
    
    def remove_container(self, container_name: str) -> Tuple[bool, str]:
        """Remove a container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.remove(force=True)
            logger.info(f"Removed container: {container_name}")
            return True, "Container removed successfully"
        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            return False, str(e) 