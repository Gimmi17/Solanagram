#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor Manager - Avvia container che estraggono dati crypto dai gruppi Telegram
Reuse la logica di ForwarderManager ma con naming e immagine diverse.
"""
from typing import Any, Dict, Tuple, Optional
import re
import docker
import logging
from datetime import datetime
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from forwarder_manager import ForwarderManager

logger = logging.getLogger(__name__)

class ExtractorManager(ForwarderManager):
    """Gestisce i container di estrazione crypto"""

    def __init__(self):
        super().__init__()
        self.extractor_image = "solanagram-extractor:latest"
        self.forwarder_image = self.extractor_image  # override image from parent
        self._ensure_extractor_image()

    def _ensure_extractor_image(self) -> bool:
        """Ensure the extractor Docker image exists"""
        try:
            # Check if image already exists
            try:
                self.docker_client.images.get(self.extractor_image)
                logger.info(f"Extractor image {self.extractor_image} already exists")
                return True
            except docker.errors.ImageNotFound:
                logger.info(f"Extractor image not found, attempting to build...")
                
            # Build image if it doesn't exist
            logger.info(f"Building extractor image {self.extractor_image}...")
            
            # Check if Dockerfile exists
            import os
            dockerfile_path = os.path.join(os.path.dirname(__file__), '../../docker/extractor/Dockerfile')
            if not os.path.exists(dockerfile_path):
                logger.error(f"Dockerfile not found at {dockerfile_path}")
                return False
            
            # Build the image
            self.docker_client.images.build(
                path=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                dockerfile='docker/extractor/Dockerfile',
                tag=self.extractor_image,
                rm=True,
                pull=True
            )
            
            logger.info(f"Successfully built extractor image {self.extractor_image}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure extractor image: {e}")
            return False

    # Override for custom container name
    def _generate_container_name(self, user_id: int, source_chat_title: str) -> str:
        # Numero progressivo basato su quanti container extractor esistono già per questo utente
        existing = [c for c in self.docker_client.containers.list(all=True)
                    if c.name.startswith(f'solanagram-elaboratore-{user_id}-')]
        seq = len(existing) + 1
        safe_source = self._sanitize_container_name(source_chat_title)[:30]
        return f"solanagram-elaboratore-{user_id}-{seq}-{safe_source}-to-CryptoExtractor".lower()

    def create_extractor_container(self,
                                   user_id: int,
                                   source_chat_id: str,
                                   source_chat_title: str,
                                   rules: list,
                                   db_url: str,
                                   api_id: int,
                                   api_hash: str,
                                   session_string: str,
                                   session_file_path: Optional[str] = None,
                                   resource_limits: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, str]:
        """Create and start extractor container with resource limits"""
        try:
            # Validate resource limits
            limits = self.validate_resource_limits(resource_limits or {})
            
            container_name = self._generate_container_name(user_id, source_chat_title)
            
            logger.info(f"Creating extractor container: {container_name} with limits: {limits}")

            # Check existing
            try:
                existing = self.docker_client.containers.get(container_name)
                if existing.status == "running":
                    return False, container_name, "Container already running"
                else:
                    existing.remove(force=True)
            except docker.errors.NotFound:
                pass

            env = {
                "SOURCE_CHAT_ID": source_chat_id,
                "RULES_JSON": json.dumps(rules),
                "DATABASE_URL": db_url,
                "TELEGRAM_API_ID": str(api_id),
                "TELEGRAM_API_HASH": api_hash
            }
            
            # Determine whether to use session file or session string
            use_session_file = session_file_path and os.path.exists(session_file_path)
            
            if use_session_file:
                # Read session file and convert to string
                try:
                    from telethon.sessions import SQLiteSession
                    from telethon import TelegramClient
                    import tempfile
                    import os
                    
                    # Create a temporary client to extract the session string
                    temp_client = TelegramClient(SQLiteSession(session_file_path), api_id, api_hash)
                    session_string = temp_client.session.save()
                    temp_client.disconnect()
                    
                    env["TELEGRAM_SESSION"] = session_string
                    logger.info(f"Converted session file to string for container, length: {len(session_string)}")
                except Exception as e:
                    logger.error(f"Failed to convert session file to string: {e}")
                    env["TELEGRAM_SESSION"] = session_string or ""
            else:
                env["TELEGRAM_SESSION"] = session_string or ""
                logger.info(f"Using session string for container creation, length: {len(session_string) if session_string else 0}")

            # Create container with resource limits (similar to forwarder)
            container = self.docker_client.containers.create(
                self.extractor_image,
                name=container_name,
                environment=env,
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
            
            container.start()
            logger.info(f"Extractor container started: {container_name}")
            return True, container_name, "Extractor started successfully"
            
        except Exception as e:
            logger.error(f"Failed to create extractor container: {e}")
            return False, "", str(e)
    
    def list_user_extractors(self, user_id: int) -> list:
        """List all extractor containers for a specific user"""
        try:
            containers = self.docker_client.containers.list(all=True)
            user_containers = []
            
            prefix = f"solanagram-elaboratore-{user_id}-"
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
            logger.error(f"Failed to list user extractors: {e}")
            return [] 