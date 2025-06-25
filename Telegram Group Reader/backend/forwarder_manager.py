#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔄 Telegram Forwarder Manager
Manages Docker containers for message forwarding
"""

import os
import json
import docker
import logging
import subprocess
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ForwarderManager:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.forwarder_image = "tcm-forwarder:latest"
        self.network_name = "telegram-chat-manager-dev"
    
    def _sanitize_container_name(self, name: str) -> str:
        """Sanitize string for Docker container name (only [a-zA-Z0-9][a-zA-Z0-9_.-] allowed)"""
        # Remove emojis and special unicode characters
        name = name.encode('ascii', 'ignore').decode('ascii')
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Remove any character that's not alphanumeric, underscore, dot, or hyphen
        name = re.sub(r'[^a-zA-Z0-9_.-]', '', name)
        # Ensure it starts with alphanumeric
        name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
        # Limit length
        name = name[:50]
        # If empty after sanitization, use default
        if not name:
            name = "unnamed"
        return name
        
    def build_forwarder_image(self) -> bool:
        """Build the forwarder Docker image if not exists"""
        try:
            # Check if image already exists
            try:
                self.docker_client.images.get(self.forwarder_image)
                logger.info(f"Forwarder image {self.forwarder_image} already exists")
                return True
            except docker.errors.ImageNotFound:
                pass
            
            # Create Dockerfile content for forwarder
            dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir telethon cryptg python-dotenv

# Copy forwarder script
COPY forwarder.py /app/

# Create directories
RUN mkdir -p /app/sessions /app/configs

ENV PYTHONUNBUFFERED=1

CMD ["python", "forwarder.py"]
"""
            
            # Create temporary directory for build context
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                dockerfile_path = Path(tmpdir) / "Dockerfile"
                dockerfile_path.write_text(dockerfile_content)
                
                # Copy forwarder script
                forwarder_script_path = Path(tmpdir) / "forwarder.py"
                forwarder_script_path.write_text(self._get_forwarder_script())
                
                # Build image
                logger.info(f"Building forwarder image {self.forwarder_image}...")
                image, logs = self.docker_client.images.build(
                    path=tmpdir,
                    tag=self.forwarder_image,
                    rm=True
                )
                
                for log in logs:
                    if 'stream' in log:
                        logger.debug(log['stream'].strip())
                
                logger.info(f"Successfully built forwarder image {self.forwarder_image}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to build forwarder image: {e}")
            return False
    
    def _get_forwarder_script(self) -> str:
        """Get the forwarder Python script content"""
        return '''#!/usr/bin/env python3
import asyncio
import os
import json
import logging
import sys
import time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramForwarder:
    def __init__(self):
        self.config_file = os.environ.get('CONFIG_FILE', '/app/configs/config.json')
        self.phone = os.environ.get('TELEGRAM_PHONE')
        self.api_id = int(os.environ.get('TELEGRAM_API_ID', 0))
        self.api_hash = os.environ.get('TELEGRAM_API_HASH')
        self.session_string = os.environ.get('TELEGRAM_SESSION')
        self.session_file = os.environ.get('SESSION_FILE')
        self.message_count = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Validate environment variables
        logger.info(f"Phone: {self.phone}")
        logger.info(f"API ID: {self.api_id}")
        logger.info(f"API Hash present: {'Yes' if self.api_hash else 'No'}")
        
        if self.session_file:
            logger.info(f"Using session file: {self.session_file}")
            logger.info(f"Session file exists: {os.path.exists(self.session_file)}")
        else:
            logger.info(f"Session string length: {len(self.session_string) if self.session_string else 0}")
        
        if not self.phone or not self.api_id or not self.api_hash:
            logger.error("Missing required environment variables!")
            logger.error(f"TELEGRAM_PHONE: {self.phone}")
            logger.error(f"TELEGRAM_API_ID: {self.api_id}")
            logger.error(f"TELEGRAM_API_HASH: {'SET' if self.api_hash else 'NOT SET'}")
            sys.exit(1)
            
        if not self.session_string and not self.session_file:
            logger.error("Neither TELEGRAM_SESSION nor SESSION_FILE is set!")
            sys.exit(1)
        
    async def run(self):
        """Main forwarding loop with auto-reconnection"""
        # Load config
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        logger.info(f"✓ Configurazione caricata da {self.config_file}")
        
        source_chat_id = int(config['source_chat_id'])
        target_type = config['target_type']
        target_id = config['target_id']
        
        # Create client
        if self.session_file and os.path.exists(self.session_file):
            # Use file session
            client = TelegramClient(
                self.session_file,
                self.api_id,
                self.api_hash
            )
        else:
            # Use string session
            client = TelegramClient(
                StringSession(self.session_string),
                self.api_id,
                self.api_hash
            )
        
        logger.info("Connessione in corso...")
        
        # Connetti prima per verificare lo stato
        await client.connect()
        
        # Verifica se la sessione è autorizzata
        if not await client.is_user_authorized():
            logger.error("ERRORE: La sessione non è autorizzata!")
            logger.error("Il file di sessione esiste ma non contiene una sessione valida.")
            logger.error("Probabilmente il codice di verifica non è stato inserito correttamente.")
            logger.error("Rimuovi questo forwarder e ricrealo inserendo il codice corretto.")
            sys.exit(1)
        
        logger.info(f"✓ Client autenticato!")
        
        # Get target entity
        if target_type == 'user' and target_id.startswith('@'):
            target_entity = await client.get_entity(target_id)
        else:
            target_entity = await client.get_entity(int(target_id))
        
        logger.info(f"✓ Chat di destinazione: {getattr(target_entity, 'title', getattr(target_entity, 'username', target_id))}")
        
        # Message handler with error handling
        @client.on(events.NewMessage(chats=[source_chat_id]))
        async def handler(event):
            try:
                message = event.message
                if not message.text:
                    return
                
                logger.info(f"📨 Nuovo messaggio: {message.text[:50]}...")
                
                # Forward with retry logic
                for attempt in range(3):
                    try:
                        await client.send_message(target_entity, message.text)
                        break
                    except FloodWaitError as e:
                        logger.warning(f"Flood wait, sleeping for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except (ConnectionError, OSError) as e:
                        logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            logger.error(f"Failed to send message after 3 attempts: {e}")
                            return
                    except Exception as e:
                        logger.error(f"Error forwarding message: {e}")
                        return
                
                self.message_count += 1
                logger.info("✅ Messaggio inoltrato")
                
                # Update count file for external monitoring
                try:
                    with open('/app/configs/count.txt', 'w') as f:
                        f.write(str(self.message_count))
                except:
                    pass  # Don't fail if we can't update count
                    
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
        
        logger.info(f"🚀 Forwarding attivo: {config['source_chat_title']} -> {getattr(target_entity, 'title', getattr(target_entity, 'username', target_id))}")
        logger.info("Container in esecuzione... Premi Ctrl+C per fermare")
        
        # Main loop with auto-reconnection
        while True:
            try:
                await client.run_until_disconnected()
                break  # Normal disconnection
            except (ConnectionError, OSError) as e:
                self.reconnect_attempts += 1
                if self.reconnect_attempts > self.max_reconnect_attempts:
                    logger.error(f"Max reconnection attempts reached ({self.max_reconnect_attempts})")
                    break
                
                wait_time = min(60, 5 * self.reconnect_attempts)
                logger.warning(f"Server closed the connection: {e}")
                logger.info(f"Attempting reconnection #{self.reconnect_attempts} in {wait_time} seconds...")
                
                await asyncio.sleep(wait_time)
                
                try:
                    if not client.is_connected():
                        await client.connect()
                    logger.info("✓ Riconnesso al server Telegram")
                    self.reconnect_attempts = 0  # Reset counter on successful reconnection
                except Exception as reconnect_error:
                    logger.error(f"Reconnection failed: {reconnect_error}")
            except KeyboardInterrupt:
                logger.info("\\n⏹️ Forwarding fermato dall'utente")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(10)
        
        # Cleanup
        if client:
            try:
                await client.disconnect()
            except:
                pass

if __name__ == "__main__":
    forwarder = TelegramForwarder()
    asyncio.run(forwarder.run())
'''
    
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
        session_file_path: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """Create and start a new forwarder container"""
        try:
            # Generate container name with proper sanitization
            safe_source = self._sanitize_container_name(source_chat_title)[:20]
            safe_target = self._sanitize_container_name(target_name)[:20]
            container_name = f"tcm-fwd-{user_id}-{safe_source}-to-{safe_target}".lower()
            
            logger.info(f"Creating forwarder container: {container_name}")
            logger.info(f"Source: {source_chat_title} -> {safe_source}")
            logger.info(f"Target: {target_name} -> {safe_target}")
            logger.info(f"Session string length: {len(session_string) if session_string else 0}")
            logger.info(f"Phone: {phone}, API ID: {api_id}")
            
            # Create config
            config = {
                "source_chat_id": source_chat_id,
                "source_chat_title": source_chat_title,
                "target_type": target_type,
                "target_id": target_id,
                "target_name": target_name
            }
            
            # Create volumes directories
            config_dir = Path(f"/tmp/tcm-configs/{container_name}")
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Write config file
            config_file = config_dir / "config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Write initial count
            count_file = config_dir / "count.txt"
            count_file.write_text("0")
            
            # Prepare volumes
            volumes = {
                str(config_dir): {"bind": "/app/configs", "mode": "rw"}
            }
            
            # If we have a session file, mount it
            if session_file_path and os.path.exists(session_file_path):
                # Copy session file to config directory
                import shutil
                session_dest = config_dir / "session.session"
                shutil.copy2(session_file_path, session_dest)
                logger.info(f"Copied session file from {session_file_path} to {session_dest}")
                
                # Use file session instead of string session
                environment = {
                    "TELEGRAM_PHONE": phone,
                    "TELEGRAM_API_ID": str(api_id),
                    "TELEGRAM_API_HASH": api_hash,
                    "SESSION_FILE": "/app/configs/session.session",
                    "CONFIG_FILE": "/app/configs/config.json"
                }
            else:
                # Use string session (backward compatibility)
                environment = {
                    "TELEGRAM_PHONE": phone,
                    "TELEGRAM_API_ID": str(api_id),
                    "TELEGRAM_API_HASH": api_hash,
                    "TELEGRAM_SESSION": session_string,
                    "CONFIG_FILE": "/app/configs/config.json"
                }
            
            # Create container with better resource management
            container = self.docker_client.containers.run(
                self.forwarder_image,
                name=container_name,
                environment=environment,
                volumes=volumes,
                network=self.network_name,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                mem_limit="256m",  # Limit memory to 256MB
                cpu_period=100000,  # CPU period in microseconds
                cpu_quota=50000   # CPU quota (50% of one core)
            )
            
            logger.info(f"Created forwarder container: {container_name}")
            return True, container_name, "Container created successfully"
            
        except Exception as e:
            logger.error(f"Failed to create forwarder container: {e}")
            return False, "", str(e)
    
    def get_container_status(self, container_name: str) -> Dict:
        """Get status of a forwarder container"""
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Read message count
            config_dir = Path(f"/tmp/tcm-configs/{container_name}")
            count_file = config_dir / "count.txt"
            message_count = 0
            if count_file.exists():
                try:
                    message_count = int(count_file.read_text().strip())
                except:
                    pass
            
            return {
                "status": container.status,
                "message_count": message_count,
                "created": container.attrs['Created'],
                "running": container.status == "running"
            }
        except docker.errors.NotFound:
            return {
                "status": "not_found",
                "message_count": 0,
                "running": False
            }
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return {
                "status": "error",
                "message_count": 0,
                "running": False,
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
            container.stop()
            container.remove()
            
            # Clean up config directory
            config_dir = Path(f"/tmp/tcm-configs/{container_name}")
            if config_dir.exists():
                import shutil
                shutil.rmtree(config_dir)
            
            logger.info(f"Stopped and removed container: {container_name}")
            return True, "Container removed successfully"
        except docker.errors.NotFound:
            return True, "Container not found (already removed)"
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            return False, str(e)
    
    def list_user_containers(self, user_id: int) -> List[str]:
        """List all containers for a specific user"""
        try:
            containers = self.docker_client.containers.list(all=True)
            user_containers = []
            
            prefix = f"tcm-fwd-{user_id}-"
            for container in containers:
                if container.name.startswith(prefix):
                    user_containers.append(container.name)
            
            return user_containers
        except Exception as e:
            logger.error(f"Failed to list user containers: {e}")
            return [] 