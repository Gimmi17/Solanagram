"""
Telegram listener module.
Handles connection to Telegram and listening for new messages in the trading group.
"""
import asyncio
import logging
from typing import Callable, Optional
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import Message

from config import config
from parser import parser, TradingSignal
from state import state

logger = logging.getLogger(__name__)

class TelegramListener:
    """Telegram client for listening to trading signals"""
    
    def __init__(self, message_handler: Optional[Callable[[TradingSignal], None]] = None):
        self.client = None
        self.message_handler = message_handler
        self.running = False
        
        # Get Telegram configuration
        telegram_config = config.get_telegram_config()
        self.api_id = telegram_config.get('api_id')
        self.api_hash = telegram_config.get('api_hash')
        self.phone = telegram_config.get('phone')
        self.group_id = telegram_config.get('group_id')
        
        # Validate configuration
        if not all([self.api_id, self.api_hash, self.phone]):
            raise ValueError("Missing Telegram configuration. Check your .env file.")
        
        # Convert group_id to int if it's a string
        if self.group_id:
            try:
                if isinstance(self.group_id, str):
                    # Handle negative IDs (supergroups)
                    self.group_id = int(self.group_id)
            except ValueError:
                logger.error(f"Invalid group ID format: {self.group_id}")
                self.group_id = None
    
    async def initialize(self) -> None:
        """Initialize Telegram client and authenticate"""
        try:
            # Create client with session file in data directory
            session_path = config.data_dir / 'telegram_session'
            self.client = TelegramClient(str(session_path), self.api_id, self.api_hash)
            
            # Connect to Telegram
            await self.client.connect()
            
            # Check if we're already authenticated
            if not await self.client.is_user_authorized():
                logger.info("Not authenticated, requesting code...")
                
                # Send code request
                await self.client.send_code_request(self.phone)
                
                # In a real deployment, you'd need to handle this interactively
                # For now, we'll log instructions
                logger.error("""
                ==========================================
                TELEGRAM AUTHENTICATION REQUIRED
                ==========================================
                
                You need to authenticate with Telegram first.
                
                1. Run this script interactively outside Docker
                2. Enter the verification code when prompted
                3. Once authenticated, the session will be saved
                4. Then you can run in Docker with the saved session
                
                For interactive authentication, use:
                python -c "from telegram_listener import TelegramListener; 
                import asyncio; 
                asyncio.run(TelegramListener().interactive_auth())"
                ==========================================
                """)
                raise Exception("Telegram authentication required")
            
            logger.info("Successfully connected to Telegram")
            
            # Set up message handler
            if self.group_id:
                self.client.add_event_handler(
                    self._handle_new_message,
                    events.NewMessage(chats=[self.group_id])
                )
                logger.info(f"Listening for messages in group {self.group_id}")
            else:
                logger.warning("No group ID configured - listening to all messages")
                self.client.add_event_handler(
                    self._handle_new_message,
                    events.NewMessage()
                )
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            raise
    
    async def interactive_auth(self) -> None:
        """Interactive authentication for initial setup"""
        try:
            session_path = config.data_dir / 'telegram_session'
            self.client = TelegramClient(str(session_path), self.api_id, self.api_hash)
            
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                # Send code request
                await self.client.send_code_request(self.phone)
                
                # Get code from user
                code = input("Enter the verification code: ")
                
                try:
                    await self.client.sign_in(self.phone, code)
                except SessionPasswordNeededError:
                    # Two-factor authentication enabled
                    password = input("Enter your 2FA password: ")
                    await self.client.sign_in(password=password)
                
                print("Successfully authenticated!")
            else:
                print("Already authenticated!")
            
            await self.client.disconnect()
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    async def _handle_new_message(self, event) -> None:
        """Handle incoming Telegram messages"""
        try:
            message: Message = event.message
            
            # Skip empty messages
            if not message.text:
                return
            
            # Get sender info
            sender_id = message.sender_id if hasattr(message, 'sender_id') else None
            
            # Get sender details if possible
            sender_username = None
            sender_first_name = None
            try:
                if message.sender:
                    sender_username = getattr(message.sender, 'username', None)
                    sender_first_name = getattr(message.sender, 'first_name', None)
            except:
                pass
            
            # Prepare message data for saving
            message_data = {
                'message_id': message.id,
                'chat_id': message.chat_id if hasattr(message, 'chat_id') else None,
                'user_id': sender_id,
                'username': sender_username,
                'first_name': sender_first_name,
                'message_text': message.text,
                'message_date': message.date
            }
            
            # Log message info (without full content for privacy)
            logger.debug(f"Received message from {sender_id}, length: {len(message.text)}")
            
            # Parse the message for trading signals
            signal = parser.parse_message(message.text)
            signal_id = None
            
            if signal and parser.validate_signal(signal):
                logger.info(f"Valid {signal.signal_type} signal detected for {signal.token_name}")
                
                # Save the signal first
                try:
                    signal_id = state.save_signal(signal)
                    logger.debug(f"Signal saved with ID: {signal_id}")
                except Exception as e:
                    logger.error(f"Error saving signal: {e}")
                
                # Call the message handler if provided
                if self.message_handler:
                    try:
                        if asyncio.iscoroutinefunction(self.message_handler):
                            await self.message_handler(signal)
                        else:
                            self.message_handler(signal)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
            else:
                logger.debug("No valid trading signal found in message")
            
            # Save message to database (always save, regardless of signal)
            try:
                msg_id = state.save_message(message_data, signal_id)
                logger.debug(f"Message saved with ID: {msg_id}")
            except Exception as e:
                logger.error(f"Error saving message: {e}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def start_listening(self) -> None:
        """Start listening for messages"""
        try:
            if not self.client:
                await self.initialize()
            
            self.running = True
            logger.info("Started listening for Telegram messages...")
            
            # Keep the client running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error in message listener: {e}")
            self.running = False
            raise
    
    async def stop_listening(self) -> None:
        """Stop listening for messages"""
        try:
            self.running = False
            if self.client and self.client.is_connected():
                await self.client.disconnect()
            logger.info("Stopped listening for Telegram messages")
        except Exception as e:
            logger.error(f"Error stopping listener: {e}")
    
    def set_message_handler(self, handler: Callable[[TradingSignal], None]) -> None:
        """Set the message handler function"""
        self.message_handler = handler
    
    async def send_message(self, text: str, chat_id: Optional[int] = None) -> None:
        """Send a message to Telegram (for notifications)"""
        try:
            if not self.client or not self.client.is_connected():
                logger.warning("Telegram client not connected - cannot send message")
                return
            
            target_chat = chat_id or self.group_id
            if not target_chat:
                logger.warning("No target chat specified for message")
                return
            
            await self.client.send_message(target_chat, text)
            logger.info(f"Message sent to chat {target_chat}")
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def get_chat_info(self) -> dict:
        """Get information about the configured chat"""
        try:
            if not self.client or not self.client.is_connected():
                return {"error": "Client not connected"}
            
            if not self.group_id:
                return {"error": "No group ID configured"}
            
            entity = await self.client.get_entity(self.group_id)
            
            return {
                "id": entity.id,
                "title": getattr(entity, 'title', 'Unknown'),
                "type": type(entity).__name__,
                "participants_count": getattr(entity, 'participants_count', None)
            }
            
        except Exception as e:
            logger.error(f"Failed to get chat info: {e}")
            return {"error": str(e)}
    
    def is_running(self) -> bool:
        """Check if the listener is running"""
        return self.running and self.client and self.client.is_connected()

# Function to create and configure telegram listener
def create_telegram_listener(message_handler: Optional[Callable[[TradingSignal], None]] = None) -> TelegramListener:
    """Create a configured Telegram listener"""
    return TelegramListener(message_handler) 