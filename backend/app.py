#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔐 Real Telegram Authentication Backend
Fixed version with proper asyncio handling and code obfuscation
"""

import os
import logging
import hashlib
import secrets
import random
import asyncio
import re
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import redis

from telethon import TelegramClient, errors
from telethon.sessions import StringSession

# Import forwarder manager
from forwarder_manager import ForwarderManager

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# Error Messages in Italian for better UX
# ============================================

ERROR_MESSAGES = {
    'REQUIRED_FIELDS': 'Tutti i campi sono obbligatori',
    'INVALID_API_ID': 'Formato API ID non valido. Deve essere un numero',
    'INVALID_PHONE': 'Formato numero di telefono non valido. Usa il formato +39xxxxxxxxx',
    'PHONE_EXISTS': 'Un utente con questo numero di telefono esiste già',
    'REGISTRATION_FAILED': 'Registrazione fallita. Riprova più tardi',
    'DB_CONNECTION_FAILED': 'Connessione al database fallita',
    'REDIS_CONNECTION_FAILED': 'Connessione al sistema di cache fallita',
    'TELEGRAM_CLIENT_FAILED': 'Impossibile inizializzare il client Telegram',
    'PHONE_INVALID': 'Numero di telefono non valido o non registrato su Telegram',
    'API_CREDENTIALS_INVALID': 'Credenziali API Telegram non valide. Controlla API ID e API Hash su https://my.telegram.org',
    'VERIFICATION_CODE_INVALID': 'Codice di verifica non valido',
    'VERIFICATION_EXPIRED': 'Richiesta di verifica scaduta. Effettua nuovamente il login',
    'PASSWORD_2FA_REQUIRED': 'Password 2FA richiesta ma non fornita',
    'PASSWORD_2FA_INVALID': 'Password 2FA non valida',
    'AUTH_RESTART_REQUIRED': 'Errore di autenticazione. Riprova il login',
    'FLOOD_WAIT': 'Troppe richieste. Attendi qualche minuto prima di riprovare',
    'UNAUTHORIZED': 'Autorizzazione persa. Effettua nuovamente il login',
    'PHONE_PASSWORD_REQUIRED': 'Numero di telefono e password sono obbligatori',
    'INVALID_CREDENTIALS': 'Numero di telefono o password non validi',
    'API_CREDENTIALS_NOT_SET': 'Credenziali API non impostate per questo utente',
    'PHONE_CODE_REQUIRED': 'Numero di telefono e codice sono obbligatori',
    'ASYNCIO_LOOP_ERROR': 'Problema di connessione rilevato. Tutti i dati sono stati puliti, riprova il login',
    'UNEXPECTED_ERROR': 'Errore inaspettato: {error}'
}

def get_error_message(key: str, **kwargs) -> str:
    """Get error message with optional formatting"""
    message = ERROR_MESSAGES.get(key, f'Errore sconosciuto: {key}')
    return message.format(**kwargs) if kwargs else message

# Environment-based configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://solanagram_user:solanagram_password@solanagram-db:5432/solanagram_db')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') # Must be set in .env
    
    # ============================================
    # 📱 MULTI-CHANNEL CONFIGURATION
    # ============================================
    PRIMARY_CHANNEL_ID = os.environ.get('PRIMARY_CHANNEL_ID')
    SECONDARY_CHANNEL_ID = os.environ.get('SECONDARY_CHANNEL_ID')
    BACKUP_CHANNEL_ID = os.environ.get('BACKUP_CHANNEL_ID')
    
    # Canali configurati come lista per iterazione
    CONFIGURED_CHANNELS = [
        {"id": PRIMARY_CHANNEL_ID, "name": "primary", "priority": 1},
        {"id": SECONDARY_CHANNEL_ID, "name": "secondary", "priority": 2},
        {"id": BACKUP_CHANNEL_ID, "name": "backup", "priority": 3}
    ]

    if not ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY is not set in the environment variables.")

    try:
        fernet = Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        raise ValueError(f"Invalid ENCRYPTION_KEY format. Must be a valid Fernet key: {e}")


# Telethon is available and will be used
TELETHON_AVAILABLE = True

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=["http://localhost:8082"], supports_credentials=True, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
jwt = JWTManager(app)

# Directory for Telethon session files
SESSION_DIR = 'telethon_sessions'
os.makedirs(SESSION_DIR, exist_ok=True)

# In-memory cache for active Telethon clients to maintain sessions
active_clients: Dict[str, TelegramClient] = {}
client_locks: Dict[str, asyncio.Lock] = {}


# ============================================
#  Encryption Utilities
# ============================================

def encrypt_api_hash(api_hash: str) -> str:
    """Encrypts the API hash for secure storage."""
    try:
        return Config.fernet.encrypt(api_hash.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API hash: {e}")
        raise ValueError("Encryption failed")

def decrypt_api_hash(encrypted_hash: str) -> str:
    """Decrypts the API hash for use."""
    try:
        return Config.fernet.decrypt(encrypted_hash.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API hash: {e}")
        raise ValueError("Decryption failed")


# ============================================
#  Database & Redis Connections
# ============================================

def get_db_connection():
    """Establishes a new database connection if one doesn't exist for the current context."""
    if 'db' not in g:
        try:
            g.db = psycopg2.connect(
                Config.DATABASE_URL,
                cursor_factory=RealDictCursor,
                connect_timeout=10,
                application_name='telegram_chat_manager'
            )
            g.db.autocommit = False
            logger.info("Database connection successful.")
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            logger.error(f"Could not connect to database: {e}")
            g.db = None
    return g.db

def get_redis_connection():
    """Establishes a new Redis connection if one doesn't exist for the current context."""
    if 'redis_client' not in g:
        try:
            g.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5
            )
            g.redis_client.ping()
            logger.info("Redis connection successful.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to Redis: {e}")
            g.redis_client = None
    return g.redis_client

@app.teardown_appcontext
def teardown_db(exception=None):
    """Closes database and other connections at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            if not db.closed:
                db.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    # No need to explicitly close Redis connections managed by the library pool


# ============================================
#  Telethon Client Management
# ============================================

def hash_phone_number(phone: str) -> str:
    """Hashes the phone number for privacy when used in filenames."""
    return hashlib.sha256(phone.encode()).hexdigest()

async def cleanup_phone_completely(phone: str):
    """
    Completely cleans up all data for a phone number to solve asyncio loop issues.
    This includes client disconnection, session file removal, and cache cleanup.
    """
    try:
        # Disconnect and remove from active clients
        if phone in active_clients:
            try:
                client = active_clients[phone]
                if client.is_connected():
                    await client.disconnect()
                logger.info(f"Disconnected client for {phone}")
            except Exception as e:
                logger.warning(f"Error disconnecting client for {phone}: {e}")
            finally:
                del active_clients[phone]
        
        # Remove client lock if exists
        if phone in client_locks:
            del client_locks[phone]
        
        # Remove session file
        session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.info(f"Removed session file for {phone}")
        
        # Clear Redis verification data
        redis_conn = get_redis_connection()
        if redis_conn:
            verification_key = f"verification:{phone}"
            redis_conn.delete(verification_key)
            logger.info(f"Cleared Redis data for {phone}")
            
        logger.info(f"Complete cleanup performed for {phone}")
    except Exception as e:
        logger.error(f"Error during complete cleanup for {phone}: {e}")

async def get_telethon_client(phone: str, api_id: int, api_hash: str, use_string_session: bool = False) -> Optional[TelegramClient]:
    """
    Creates a new Telethon client for a given phone number.
    Uses file-based sessions by default to avoid SQLite database locking issues.
    Properly cleans up old clients to prevent connection conflicts.
    FIXED: Improved client management and reduced race conditions.
    """
    try:
        # Check if we already have a working client for this phone
        if phone in active_clients:
            existing_client = active_clients[phone]
            try:
                # Test if existing client is still working
                if existing_client.is_connected():
                    logger.info(f"Reusing existing connected client for {phone}")
                    return existing_client
                else:
                    # Try to reconnect existing client
                    await existing_client.connect()
                    if existing_client.is_connected():
                        logger.info(f"Reconnected existing client for {phone}")
                        return existing_client
            except Exception as e:
                logger.warning(f"Existing client for {phone} failed, will create new one: {e}")
                
            # Clean up failed client
            try:
                if existing_client.is_connected():
                    await existing_client.disconnect()
            except:
                pass
            finally:
                del active_clients[phone]

        logger.info(f"Creating a new Telethon client for phone {phone} (string_session={use_string_session})")
        
        if use_string_session:
            # For StringSession, first check if we have a saved session
            session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
            session_string = ""
            
            # Try to load existing session string if we have a file session
            if os.path.exists(session_file):
                try:
                    # Create a temporary client to extract the session string
                    temp_client = TelegramClient(session_file, api_id, api_hash)
                    await asyncio.wait_for(temp_client.connect(), timeout=10.0)
                    if temp_client.is_connected():
                        session_string = temp_client.session.save()
                        await temp_client.disconnect()
                        logger.info(f"Extracted session string from file for {phone}, length: {len(session_string)}")
                except Exception as e:
                    logger.warning(f"Could not extract session string from file for {phone}: {e}")
                    # Remove corrupted session file
                    try:
                        os.remove(session_file)
                        logger.info(f"Removed corrupted session file for {phone}")
                    except:
                        pass
            
            # Create client with StringSession
            from telethon.sessions import StringSession
            client = TelegramClient(StringSession(session_string), api_id, api_hash)
        else:
            # Normal file-based session
            session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
            client = TelegramClient(session_file, api_id, api_hash)
        
        # FIXED: Reduced timeout and added better error handling
        try:
            await asyncio.wait_for(client.connect(), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning(f"First connection attempt timed out for {phone}, retrying...")
            # Second attempt with fresh client
            if not use_string_session:
                session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
                client = TelegramClient(session_file, api_id, api_hash)
            await asyncio.wait_for(client.connect(), timeout=10.0)
        
        if not client.is_connected():
            raise Exception("Failed to establish connection to Telegram servers")
        
        # FIXED: Shorter stabilization delay
        await asyncio.sleep(0.2)
        
        # Verify connection is actually working
        try:
            await asyncio.wait_for(client.get_me(), timeout=5.0)
            logger.info(f"Client connection verified for {phone}")
        except:
            # Connection not fully working, but don't fail - let the calling function handle it
            logger.warning(f"Could not verify client connection for {phone}, but proceeding")
        
        # Store the new client
        active_clients[phone] = client
        logger.info(f"New client for {phone} created and connected.")
        return client
        
    except asyncio.TimeoutError:
        logger.error(f"Timeout connecting to Telegram for {phone}")
        return None
    except errors.ApiIdInvalidError:
        logger.error(f"Invalid API ID for {phone}")
        return None
    except Exception as e:
        logger.error(f"Fatal error connecting new Telethon client for {phone}: {e}")
        # Cleanup on failure
        if phone in active_clients:
            del active_clients[phone]
        return None

# ========================================================================================
# CODE CACHING SYSTEM
# ========================================================================================

def get_cached_code(phone: str) -> dict:
    """Get cached verification code for a phone number"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return None
    
    cache_key = f"cached_code:{phone}"
    cached_data = redis_conn.get(cache_key)
    
    if cached_data:
        try:
            data = json.loads(cached_data)
            # Check if code is still valid (not expired)
            if data.get('expires_at', 0) > time.time():
                return data
            else:
                # Clean up expired code
                redis_conn.delete(cache_key)
        except (json.JSONDecodeError, KeyError):
            redis_conn.delete(cache_key)
    
    return None

def save_cached_code(phone: str, code: str, phone_code_hash: str, api_id: int, api_hash: str, password: str = None) -> None:
    """Save verification code to cache with expiration"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return
    
    # Cache code for 5 minutes (300 seconds)
    expires_at = time.time() + 300
    
    cache_data = {
        'code': code,
        'phone_code_hash': phone_code_hash,
        'api_id': api_id,
        'api_hash': api_hash,
        'password': password,
        'expires_at': expires_at,
        'created_at': time.time()
    }
    
    cache_key = f"cached_code:{phone}"
    redis_conn.setex(cache_key, 300, json.dumps(cache_data))
    logger.info(f"Cached verification code for {phone}")

def clear_cached_code(phone: str) -> None:
    """Clear cached verification code for a phone number"""
    redis_conn = get_redis_connection()
    if redis_conn:
        cache_key = f"cached_code:{phone}"
        redis_conn.delete(cache_key)
        logger.info(f"Cleared cached code for {phone}")

# ========================================================================================
# ASYNC TELETHON HELPERS
# ========================================================================================

async def send_telegram_code_async(phone: str, api_id: int, api_hash: str, password: str) -> dict:
    """
    Initializes a client, sends a verification code, and stores necessary data in Redis.
    Enhanced with detailed error messages and better error handling.
    """
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"success": False, "status": "error", "error": get_error_message('REDIS_CONNECTION_FAILED')}

    # Check if we have a cached code first
    cached_code_data = get_cached_code(phone)
    if cached_code_data:
        logger.info(f"Found cached code for {phone}, reusing without requesting new one")
        
        # Store verification data in Redis for verification step
        verification_key = f"verification:{phone}"
        verification_data = {
            "api_id": cached_code_data["api_id"],
            "api_hash": cached_code_data["api_hash"],
            "phone_code_hash": cached_code_data["phone_code_hash"],
            "password": cached_code_data.get("password"),
            "cached_code": cached_code_data["code"]  # Include the cached code
        }
        redis_conn.set(verification_key, json.dumps(verification_data), ex=600)  # 10-minute expiry
        
        # Get counter status without incrementing (since we're reusing cached code)
        counter_status = get_sms_code_counter(phone)
        
        return {
            "success": True, 
            "status": "success", 
            "message": f"Codice di verifica disponibile per {phone} (riutilizzato da cache)",
            "rate_limit": counter_status,
            "cached": True
        }

    # FIXED: Improved error handling and retry logic
    max_retries = 2
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt + 1} for sending code to {phone}")
                # Clean up any existing clients before retry
                if phone in active_clients:
                    try:
                        await active_clients[phone].disconnect()
                    except:
                        pass
                    del active_clients[phone]
                
                # Short delay before retry
                await asyncio.sleep(1.0)
            
            client = await get_telethon_client(phone, api_id, api_hash)
            if not client:
                last_error = get_error_message('TELEGRAM_CLIENT_FAILED')
                if attempt == max_retries - 1:
                    return {"success": False, "status": "error", "error": last_error}
                continue

            # FIXED: Better connection verification
            if not client.is_connected():
                logger.warning(f"Client for {phone} not connected, attempting to reconnect...")
                try:
                    await asyncio.wait_for(client.connect(), timeout=10.0)
                except asyncio.TimeoutError:
                    last_error = "Connection timeout to Telegram servers"
                    if attempt == max_retries - 1:
                        return {"success": False, "status": "error", "error": last_error}
                    continue
                
                if not client.is_connected():
                    last_error = "Cannot establish connection to Telegram servers"
                    if attempt == max_retries - 1:
                        return {"success": False, "status": "error", "error": last_error}
                    continue

            # FIXED: Added timeout and better error handling for send_code_request
            try:
                result = await asyncio.wait_for(client.send_code_request(phone, force_sms=True), timeout=15.0)
            except asyncio.TimeoutError:
                last_error = "Timeout while requesting verification code"
                if attempt == max_retries - 1:
                    return {"success": False, "status": "error", "error": last_error}
                continue
            except Exception as e:
                last_error = f"Error requesting verification code: {str(e)}"
                if attempt == max_retries - 1:
                    return {"success": False, "status": "error", "error": last_error}
                continue
            
            # Success! Increment counter and store verification data
            counter_status = increment_sms_code_counter(phone)
            
            verification_key = f"verification:{phone}"
            verification_data = {
                "api_id": api_id,
                "api_hash": api_hash,
                "phone_code_hash": result.phone_code_hash,
                "password": password,  # Store password for 2FA verification
            }
            redis_conn.set(verification_key, json.dumps(verification_data), ex=600)  # 10-minute expiry

            logger.info(f"Successfully sent code to {phone} and stored verification data in Redis (attempt {attempt + 1}).")
            
            # Prepare response with counter info
            response = {
                "success": True, 
                "status": "success", 
                "message": f"Codice di verifica inviato a {phone}",
                "rate_limit": counter_status
            }
            
            # Add warning if approaching limit
            if counter_status["count"] >= SMS_CODE_WARNING_THRESHOLD:
                response["warning"] = f"Attenzione: hai fatto {counter_status['count']} richieste su {counter_status['limit']}. Limite raggiunto tra {counter_status['remaining']} richieste."
            
            return response
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1} failed for {phone}: {e}")
            if attempt == max_retries - 1:
                break
    
    # All attempts failed
    logger.error(f"All {max_retries} attempts failed for sending code to {phone}. Last error: {last_error}")
    return {"success": False, "status": "error", "error": last_error or "Errore nell'invio del codice di verifica"}

async def verify_telegram_code_async(phone: str, code: str) -> dict:
    """
    Asynchronously verifies the Telegram code using data from Redis.
    Enhanced with detailed error messages and code caching.
    """
    redis_conn = get_redis_connection()
    verification_key = f"verification:{phone}"
    
    if not redis_conn or not redis_conn.exists(verification_key):
        logger.error(f"No verification data found in Redis for phone {phone}.")
        return {"success": False, "status": "error", "error": get_error_message('VERIFICATION_EXPIRED')}

    verification_data = json.loads(redis_conn.get(verification_key))
    api_id = verification_data["api_id"]
    api_hash = verification_data["api_hash"]
    phone_code_hash = verification_data["phone_code_hash"]
    password = verification_data.get("password")
    cached_code = verification_data.get("cached_code")

    # Use file-based sessions like the working system
    client = await get_telethon_client(phone, api_id, api_hash)
    if not client:
        return {"success": False, "status": "error", "error": get_error_message('TELEGRAM_CLIENT_FAILED')}
        
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        logger.info(f"Successfully signed in user {phone}.")
        
        # If this is a new code (not from cache), save it for future use
        if not cached_code:
            save_cached_code(phone, code, phone_code_hash, api_id, api_hash, password)
            logger.info(f"Saved new verification code for {phone} to cache")
        
    except errors.SessionPasswordNeededError:
        logger.info(f"2FA password needed for {phone}. Trying to supply stored password.")
        if not password:
            return {"success": False, "status": "error", "error": get_error_message('PASSWORD_2FA_REQUIRED')}
        try:
            await client.sign_in(password=password)
            logger.info(f"Successfully signed in user {phone} with 2FA password.")
            
            # If this is a new code (not from cache), save it for future use
            if not cached_code:
                save_cached_code(phone, code, phone_code_hash, api_id, api_hash, password)
                logger.info(f"Saved new verification code for {phone} to cache (with 2FA)")
                
        except errors.PasswordHashInvalidError:
            logger.error(f"Invalid 2FA password for user {phone}.")
            return {"success": False, "status": "error", "error": get_error_message('PASSWORD_2FA_INVALID')}
        except Exception as e:
            logger.error(f"An error occurred during 2FA sign in for {phone}: {e}")
            return {"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}

    except errors.PhoneCodeInvalidError:
        logger.error(f"Invalid verification code for phone {phone}.")
        return {"success": False, "status": "error", "error": get_error_message('VERIFICATION_CODE_INVALID')}

    except errors.FloodWaitError as e:
        logger.error(f"Flood wait error during verification for {phone}: {e.seconds} seconds")
        return {"success": False, "status": "error", "error": f"{get_error_message('FLOOD_WAIT')} (Attendi {e.seconds} secondi)"}
        
    except Exception as e:
        logger.error(f"An error occurred during sign in for {phone}: {e}")
        return {"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}

    # If sign in is successful, clean up Redis and find user in DB
    redis_conn.delete(verification_key)
    db = get_db_connection()
    if not db:
        return {"success": False, "status": "error", "error": get_error_message('DB_CONNECTION_FAILED')}
        
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, phone FROM users WHERE phone = %s", (phone,))
            user = cursor.fetchone()
        
        if not user:
            return {"success": False, "status": "error", "error": "Utente non trovato nel database"}
            
        return {"success": True, "status": "success", "user": user}
    except Exception as e:
        logger.error(f"Database error during verification for {phone}: {e}")
        return {"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}


async def get_user_chats_async(phone: str) -> dict:
    """
    Asynchronously fetches user's dialogs/chats from Telegram.
    Uses file-based sessions for better compatibility with chat loading.
    """
    db = get_db_connection()
    with db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT api_id, api_hash_encrypted FROM users WHERE phone = %s", (phone,))
        user_creds = cursor.fetchone()

    if not user_creds or not user_creds['api_id'] or not user_creds['api_hash_encrypted']:
        return {"success": False, "error": "API credentials not found for this user."}

    api_id = user_creds['api_id']
    api_hash = decrypt_api_hash(user_creds['api_hash_encrypted'])

    # Use file-based sessions for chat loading (like the working system)
    client = await get_telethon_client(phone, api_id, api_hash)
    if not client or not await client.is_user_authorized():
        logger.error(f"User {phone} is not authorized. Please log in again.")
        return {"success": False, "error": "Authorization lost. Please log in again."}

    chats = []
    try:
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                # Get entity for more details
                entity = dialog.entity
                chat_type = "private"
                if dialog.is_channel:
                    chat_type = "channel"
                elif dialog.is_group:
                    chat_type = "supergroup" if hasattr(entity, 'megagroup') and entity.megagroup else "group"
                
                chat_data = {
                    "id": dialog.id,
                    "title": dialog.name or "Unnamed Chat",
                    "type": chat_type,
                    "username": getattr(entity, 'username', None),
                    "members_count": getattr(entity, 'participants_count', None),
                    "description": getattr(entity, 'about', None),
                    "unread_count": dialog.unread_count if hasattr(dialog, 'unread_count') else 0,
                    "last_message_date": dialog.date.isoformat() if dialog.date else None
                }
                chats.append(chat_data)
        
        logger.info(f"Found {len(chats)} chats for user {phone}")
        return {"success": True, "chats": chats}
    except Exception as e:
        logger.error(f"Failed to fetch chats for {phone}: {e}")
        return {"success": False, "error": "Failed to fetch chats. Please try logging in again."}

# ============================================
# 📱 MULTI-CHANNEL ENDPOINTS
# ============================================

@app.route('/api/telegram/get-configured-channels', methods=['GET'])
@jwt_required()
def get_configured_channels():
    """Restituisce i canali configurati nell'ambiente"""
    try:
        phone = get_jwt_identity()
        if not phone:
            return jsonify({'error': get_error_message('UNAUTHORIZED')}), 401
        
        configured_channels = []
        for channel in Config.CONFIGURED_CHANNELS:
            if channel["id"]:  # Solo se l'ID è impostato
                configured_channels.append({
                    "id": channel["id"],
                    "name": channel["name"],
                    "priority": channel["priority"],
                    "configured": True
                })
        
        return jsonify({
            'success': True,
            'configured_channels': configured_channels,
            'total_configured': len(configured_channels)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching configured channels: {e}")
        return jsonify({'error': get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/telegram/channel-action', methods=['POST'])
@jwt_required()
def channel_action():
    """Esegue azioni specifiche su un canale configurato"""
    try:
        phone = get_jwt_identity()
        if not phone:
            return jsonify({'error': get_error_message('UNAUTHORIZED')}), 401
        
        data = request.get_json()
        channel_id = data.get('channel_id')
        action = data.get('action')  # 'info', 'members', 'recent_messages'
        
        if not channel_id or not action:
            return jsonify({'error': 'channel_id e action sono obbligatori'}), 400
        
        # Verifica che il canale sia tra quelli configurati
        is_configured = any(
            str(ch["id"]) == str(channel_id) 
            for ch in Config.CONFIGURED_CHANNELS 
            if ch["id"]
        )
        
        if not is_configured:
            return jsonify({'error': 'Canale non configurato nel sistema'}), 403
        
        # Esegui l'azione richiesta
        result = asyncio.run(execute_channel_action_async(phone, channel_id, action))
        
        return jsonify(result), 200 if result.get('success') else 400
        
    except Exception as e:
        logger.error(f"Error in channel action: {e}")
        return jsonify({'error': get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

async def execute_channel_action_async(phone: str, channel_id: str, action: str) -> dict:
    """Esegue azioni specifiche su un canale"""
    db = get_db_connection()
    with db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT api_id, api_hash_encrypted FROM users WHERE phone = %s", (phone,))
        user_creds = cursor.fetchone()

    if not user_creds:
        return {"success": False, "error": "Credenziali utente non trovate"}

    api_id = user_creds['api_id']
    api_hash = decrypt_api_hash(user_creds['api_hash_encrypted'])

    # Use file-based sessions for channel actions (like the working system)
    client = await get_telethon_client(phone, api_id, api_hash)
    if not client or not await client.is_user_authorized():
        return {"success": False, "error": "Autorizzazione Telegram persa"}

    try:
        channel_entity = await client.get_entity(int(channel_id))
        
        if action == 'info':
            return {
                "success": True,
                "action": "info",
                "channel": {
                    "id": channel_entity.id,
                    "title": channel_entity.title,
                    "username": getattr(channel_entity, 'username', None),
                    "participants_count": getattr(channel_entity, 'participants_count', None),
                    "description": getattr(channel_entity, 'about', None),
                    "is_channel": hasattr(channel_entity, 'broadcast'),
                    "is_group": hasattr(channel_entity, 'megagroup')
                }
            }
        
        elif action == 'members':
            participants = []
            async for user in client.iter_participants(channel_entity, limit=100):
                participants.append({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_bot": user.bot
                })
            
            return {
                "success": True,
                "action": "members",
                "channel_id": channel_id,
                "members": participants,
                "total_shown": len(participants)
            }
        
        elif action == 'recent_messages':
            messages = []
            async for message in client.iter_messages(channel_entity, limit=10):
                messages.append({
                    "id": message.id,
                    "text": message.text or "[Media/File]",
                    "date": message.date.isoformat() if message.date else None,
                    "sender_id": message.sender_id,
                    "views": getattr(message, 'views', None)
                })
            
            return {
                "success": True,
                "action": "recent_messages",
                "channel_id": channel_id,
                "messages": messages,
                "total_shown": len(messages)
            }
        
        else:
            return {"success": False, "error": f"Azione '{action}' non supportata"}
    
    except Exception as e:
        logger.error(f"Error executing channel action {action} on {channel_id}: {e}")
        return {"success": False, "error": f"Errore durante l'esecuzione: {str(e)}"}

# ============================================
# 📱 RATE LIMITING SYSTEM
# ============================================

# Constants for rate limiting
SMS_CODE_LIMIT = 30  # Maximum SMS code requests before FLOOD_WAIT (more realistic)
SMS_CODE_RESET_HOURS = 24  # Hours to reset the counter
SMS_CODE_WARNING_THRESHOLD = 20  # Show warning when approaching limit

def get_sms_code_counter(phone: str) -> dict:
    """Get SMS code request counter for a phone number"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"count": 0, "reset_time": None, "remaining": SMS_CODE_LIMIT}
    
    counter_key = f"sms_counter:{phone}"
    reset_key = f"sms_reset:{phone}"
    
    # Get current count
    count = int(redis_conn.get(counter_key) or 0)
    
    # Get reset time
    reset_time = redis_conn.get(reset_key)
    if reset_time:
        reset_time = int(reset_time)
        # Check if reset time has passed
        if time.time() > reset_time:
            # Reset counter
            redis_conn.delete(counter_key)
            redis_conn.delete(reset_key)
            count = 0
            reset_time = None
    
    remaining = max(0, SMS_CODE_LIMIT - count)
    
    return {
        "count": count,
        "reset_time": reset_time,
        "remaining": remaining,
        "limit": SMS_CODE_LIMIT
    }

def increment_sms_code_counter(phone: str) -> dict:
    """Increment SMS code request counter and return current status"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"count": 1, "reset_time": None, "remaining": SMS_CODE_LIMIT - 1}
    
    counter_key = f"sms_counter:{phone}"
    reset_key = f"sms_reset:{phone}"
    
    # Get current status
    current = get_sms_code_counter(phone)
    
    # Increment counter
    new_count = current["count"] + 1
    redis_conn.set(counter_key, new_count)
    
    # Set reset time if not already set
    if not current["reset_time"]:
        reset_time = int(time.time() + (SMS_CODE_RESET_HOURS * 3600))
        redis_conn.set(reset_key, reset_time)
        current["reset_time"] = reset_time
    
    current["count"] = new_count
    current["remaining"] = max(0, SMS_CODE_LIMIT - new_count)
    
    return current

def can_request_sms_code(phone: str) -> dict:
    """Check if SMS code can be requested for this phone"""
    counter = get_sms_code_counter(phone)
    
    if counter["count"] >= SMS_CODE_LIMIT:
        # Calculate time remaining
        if counter["reset_time"]:
            time_remaining = counter["reset_time"] - int(time.time())
            if time_remaining > 0:
                hours = time_remaining // 3600
                minutes = (time_remaining % 3600) // 60
                return {
                    "can_request": False,
                    "reason": "limit_exceeded",
                    "time_remaining": time_remaining,
                    "time_formatted": f"{hours}h {minutes}m",
                    "counter": counter
                }
    
    return {
        "can_request": True,
        "counter": counter
    }

def sync_flood_wait_from_telegram(phone: str, flood_wait_seconds: int) -> dict:
    """Sync our counter with Telegram's FLOOD_WAIT response"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"count": 0, "reset_time": None, "remaining": SMS_CODE_LIMIT}
    
    counter_key = f"sms_counter:{phone}"
    reset_key = f"sms_reset:{phone}"
    
    # Calculate when the FLOOD_WAIT will expire
    reset_time = int(time.time() + flood_wait_seconds)
    
    # Set counter to limit and reset time
    redis_conn.set(counter_key, SMS_CODE_LIMIT)
    redis_conn.set(reset_key, reset_time)
    
    # Calculate time remaining
    hours = flood_wait_seconds // 3600
    minutes = (flood_wait_seconds % 3600) // 60
    
    return {
        "count": SMS_CODE_LIMIT,
        "reset_time": reset_time,
        "remaining": 0,
        "limit": SMS_CODE_LIMIT,
        "telegram_flood_wait": True,
        "time_formatted": f"{hours}h {minutes}m"
    }

# ============================================
#  API Endpoints
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker container monitoring."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }
    
    # Check database connection
    try:
        db = get_db_connection()
        if db and not db.closed:
            with db.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            health_status["services"]["database"] = "healthy"
        else:
            health_status["services"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis connection
    try:
        redis_conn = get_redis_connection()
        if redis_conn:
            redis_conn.ping()
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] != "unhealthy" else 503
    return jsonify(health_status), status_code

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user with phone, password, and Telegram API credentials."""
    data = request.get_json()
    
    # Supporta sia 'phone' che 'phone_number' per compatibilità
    phone = data.get('phone') or data.get('phone_number')
    password = data.get('password')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    
    logger.info(f"Registration attempt for phone: {phone}")
    
    if not all([phone, password, api_id, api_hash]):
        logger.error(f"Missing required fields. phone: {bool(phone)}, password: {bool(password)}, api_id: {bool(api_id)}, api_hash: {bool(api_hash)}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('REQUIRED_FIELDS')}), 400
    
    try:
        api_id = int(api_id)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid API ID format: {api_id}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('INVALID_API_ID')}), 400
    
    # Validate phone format
    if not re.match(r'^\+\d{10,15}$', phone):
        logger.error(f"Invalid phone number format: {phone}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('INVALID_PHONE')}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "status": "error", "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            existing_user = cursor.fetchone()
            if existing_user:
                return jsonify({"success": False, "status": "error", "error": get_error_message('PHONE_EXISTS')}), 409
            
            # Hash password and encrypt API hash
            password_hash = generate_password_hash(password)
            api_hash_encrypted = encrypt_api_hash(api_hash)
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users (phone, password_hash, api_id, api_hash_encrypted, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (phone, password_hash, api_id, api_hash_encrypted, datetime.now(timezone.utc)))
            
            result = cursor.fetchone()
            if not result:
                raise Exception("Failed to insert user - no ID returned")
                
            user_id = result['id']
            db.commit()
            
            logger.info(f"New user registered: {phone} (ID: {user_id})")
            return jsonify({
                "success": True,
                "status": "success", 
                "message": "User registered successfully",
                "user_id": user_id
            }), 201
            
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed for {phone}: {e}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('REGISTRATION_FAILED')}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Handles user login. Does not start Telegram session, just verifies DB user
    and sends a verification code via Telegram.
    """
    data = request.get_json()
    # Supporta sia 'phone' che 'phone_number' per compatibilità
    phone = data.get('phone') or data.get('phone_number')
    password = data.get('password')

    if not phone or not password:
        return jsonify({"success": False, "status": "error", "error": get_error_message('PHONE_PASSWORD_REQUIRED')}), 400

    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "status": "error", "error": get_error_message('DB_CONNECTION_FAILED')}), 500
        
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
            user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            if not user.get('api_id') or not user.get('api_hash_encrypted'):
                return jsonify({"success": False, "status": "error", "error": get_error_message('API_CREDENTIALS_NOT_SET')}), 400

            api_id = user['api_id']
            api_hash = decrypt_api_hash(user['api_hash_encrypted'])
            
            # FIXED: Better event loop management to avoid conflicts
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create task instead of asyncio.run()
                    import asyncio
                    import concurrent.futures
                    
                    # Use thread pool for async operation to avoid loop conflicts
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            send_telegram_code_async(phone, api_id, api_hash, password)
                        )
                        result = future.result(timeout=60)  # 60 second timeout
                else:
                    # No running loop, safe to use asyncio.run()
                    result = asyncio.run(send_telegram_code_async(phone, api_id, api_hash, password))
            except RuntimeError:
                # Fallback to creating new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(send_telegram_code_async(phone, api_id, api_hash, password))
                finally:
                    loop.close()
            
            if result.get("success"):
                return jsonify({"success": True, "status": "success", "message": result.get("message")})
            else:
                return jsonify(result), 400
        else:
            return jsonify({"success": False, "status": "error", "error": get_error_message('INVALID_CREDENTIALS')}), 401
    except Exception as e:
        logger.error(f"Login error for {phone}: {e}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/auth/verify-code', methods=['POST'])
def verify_code():
    """
    Verifies the Telegram login code provided by the user.
    """
    data = request.get_json()
    # Supporta sia 'phone' che 'phone_number' per compatibilità
    phone = data.get('phone') or data.get('phone_number')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({"success": False, "status": "error", "error": get_error_message('PHONE_CODE_REQUIRED')}), 400

    logger.info(f"Attempting to verify code for phone: {phone}")
    
    try:
        result = asyncio.run(verify_telegram_code_async(phone, code))
        
        if result.get("success"):
            user = result.get("user")
            access_token = create_access_token(identity=user['id'])
            return jsonify({
                "success": True,
                "status": "success",
                "message": "Verifica completata con successo",
                "access_token": access_token,
                "user": {
                    "id": user['id'],
                    "phone": user['phone'],
                }
            })
        else:
            return jsonify(result), 401
    except Exception as e:
        logger.error(f"Error verifying code: {e}", exc_info=True)
        return jsonify({"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/user/profile', methods=['GET', 'PUT'])
@jwt_required()
def user_profile():
    """Get or update user profile information"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    if request.method == 'GET':
        try:
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, phone, api_id, created_at, last_login, is_active 
                    FROM users WHERE id = %s
                """, (current_user_id,))
                user = cursor.fetchone()
            
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            
            # Convert datetime objects to strings for JSON serialization
            user_data = dict(user)
            if user_data.get('created_at'):
                user_data['created_at'] = user_data['created_at'].isoformat()
            if user_data.get('last_login'):
                user_data['last_login'] = user_data['last_login'].isoformat()
            
            return jsonify({
                "success": True,
                "user": user_data
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching user profile for ID {current_user_id}: {e}")
            return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500
    
    elif request.method == 'PUT':
        # Handle profile updates (e.g., API credentials)
        data = request.get_json()
        api_id = data.get('api_id')
        api_hash = data.get('api_hash')
        
        if not api_id or not api_hash:
            return jsonify({"success": False, "error": "API ID and API Hash are required"}), 400
        
        try:
            api_id = int(api_id)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": get_error_message('INVALID_API_ID')}), 400
        
        try:
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                # Encrypt the new API hash
                api_hash_encrypted = encrypt_api_hash(api_hash)
                
                cursor.execute("""
                    UPDATE users 
                    SET api_id = %s, api_hash_encrypted = %s 
                    WHERE id = %s
                """, (api_id, api_hash_encrypted, current_user_id))
                
                db.commit()
                
                logger.info(f"Updated API credentials for user ID {current_user_id}")
                return jsonify({
                    "success": True,
                    "message": "API credentials updated successfully",
                    "api_id": api_id
                }), 200
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user profile for ID {current_user_id}: {e}")
            return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/user/chats', methods=['GET'])
@jwt_required()
def get_user_chats():
    """
    Fetches the list of chats for the authenticated user.
    """
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    with db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
        user_record = cursor.fetchone()
    
    if not user_record:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    phone = user_record['phone']
    logger.info(f"Fetching chats for user {phone} (ID: {current_user_id})")

    try:
        result = asyncio.run(get_user_chats_async(phone))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching user chats: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500

# ============================================
# 🔄 FORWARDER ENDPOINTS
# ============================================

@app.route('/api/forwarders/<source_chat_id>', methods=['GET'])
@jwt_required()
def get_forwarders(source_chat_id):
    """Get all forwarders for a specific chat"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, source_chat_id, source_chat_title, target_type, 
                       target_id, target_name, container_name, container_status, 
                       messages_forwarded, created_at, last_forwarded_at
                FROM forwarders 
                WHERE user_id = %s AND source_chat_id = %s
                ORDER BY created_at DESC
            """, (current_user_id, source_chat_id))
            forwarders = cursor.fetchall()
        
        # Get container status for each forwarder
        forwarder_manager = ForwarderManager()
        for forwarder in forwarders:
            if forwarder['container_name']:
                container_status = forwarder_manager.get_container_status(forwarder['container_name'])
                forwarder['container_status'] = container_status['status']
                forwarder['message_count'] = container_status.get('message_count', forwarder['messages_forwarded'])
                forwarder['is_running'] = container_status.get('running', False)
            else:
                forwarder['container_status'] = 'not_created'
                forwarder['is_running'] = False
            
            # Convert datetime to ISO format
            if forwarder.get('created_at'):
                forwarder['created_at'] = forwarder['created_at'].isoformat()
            if forwarder.get('last_forwarded_at'):
                forwarder['last_message_at'] = forwarder['last_forwarded_at'].isoformat()
            else:
                forwarder['last_message_at'] = None
        
        return jsonify({
            "success": True,
            "forwarders": forwarders,
            "total": len(forwarders)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching forwarders: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/auth/reactivate-session', methods=['POST'])
@jwt_required()
def reactivate_telegram_session():
    """Send verification code to reactivate Telegram session"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted, password_hash
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        api_id = user['api_id']
        api_hash = decrypt_api_hash(user['api_hash_encrypted'])
        
        # Send verification code
        result = asyncio.run(send_telegram_code_async(phone, api_id, api_hash, "temp_password"))
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": "Codice di verifica inviato",
                "phone": phone  # Return phone for frontend use
            }), 200
        else:
            return jsonify({"success": False, "error": result.get("error", "Errore invio codice")}), 400
            
    except Exception as e:
        logger.error(f"Error reactivating session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/verify-session-code', methods=['POST'])
@jwt_required()
def verify_session_code():
    """Verify code to reactivate Telegram session"""
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({"success": False, "error": "Codice richiesto"}), 400
    
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        
        # Verify the code
        result = asyncio.run(verify_telegram_code_async(phone, code))
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": "Sessione riattivata con successo"
            }), 200
        else:
            return jsonify({"success": False, "error": result.get("error", "Codice non valido")}), 400
            
    except Exception as e:
        logger.error(f"Error verifying session code: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/check-session', methods=['POST'])
@jwt_required()
def check_telegram_session():
    """Check if user has an active Telegram session"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted 
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        
        # Check if client exists and is authorized
        if phone in active_clients:
            client = active_clients[phone]
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                is_authorized = loop.run_until_complete(client.is_user_authorized())
                loop.close()
                
                if is_authorized:
                    return jsonify({
                        "success": True, 
                        "session_active": True,
                        "message": "Sessione Telegram attiva"
                    }), 200
            except:
                pass
        
        return jsonify({
            "success": True,
            "session_active": False,
            "message": "Sessione Telegram non attiva. È necessario effettuare l'accesso."
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/forwarders/prepare', methods=['POST'])
@jwt_required()
def prepare_forwarder():
    """Prepare forwarder session - send verification code"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['source_chat_id', 'source_chat_title']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Campo richiesto: {field}"}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Get user credentials
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted 
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        api_id = user['api_id']
        api_hash = decrypt_api_hash(user['api_hash_encrypted'])
        source_chat_id = data['source_chat_id']
        
        # --- Gestione automatica della sessione forwarder ----------------------------------
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        session_file = os.path.join(SESSION_DIR, f"{session_name}.session")

        code_from_client: Optional[str] = data.get('code')

        # Controlliamo se esiste già una sessione forwarder valida
        session_exists_and_valid = False
        if os.path.exists(session_file):
            try:
                async def _check_session():
                    client = TelegramClient(session_file, api_id, api_hash)
                    await client.connect()
                    authorized = await client.is_user_authorized()
                    await client.disconnect()
                    return authorized

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                session_exists_and_valid = loop.run_until_complete(_check_session())
                loop.close()
                logger.info(f"Session {session_name} exists and is valid: {session_exists_and_valid}")
            except Exception as e:
                logger.warning(f"Session {session_name} exists but is invalid: {e}")
                # Rimuoviamo il file di sessione corrotto
                os.remove(session_file)
                session_exists_and_valid = False

        # Se la sessione è valida, non serve richiedere il codice
        if session_exists_and_valid:
            logger.info(f"Using existing valid session for {session_name}")
            # For now, we'll use empty session string as we're using file session
            session_string = ""
        else:
            # SEMPRE chiediamo il codice per un nuovo forwarder
            verification_key = f"forwarder_verification:{current_user_id}:{source_chat_id}"
            redis_conn = get_redis_connection()

            # 1) L'utente NON ha inviato alcun codice -> inviamo codice e salviamo phone_code_hash
            if not code_from_client:
                # Check rate limiting first
                rate_check = can_request_sms_code(phone)
                if not rate_check["can_request"]:
                    return jsonify({
                        "success": False, 
                        "error": f"Limite SMS raggiunto. Riprova tra {rate_check['time_formatted']}",
                        "rate_limit": rate_check
                    }), 429
                
                try:
                    async def _send_code():
                        # Se esiste già un file sessione, rimuoviamolo per iniziare da zero
                        if os.path.exists(session_file):
                            os.remove(session_file)
                            logger.info(f"Removed existing session file for {session_name}")
                        
                        client = TelegramClient(session_file, api_id, api_hash)
                        await client.connect()
                        result = await client.send_code_request(phone)

                        if redis_conn:
                            verification_data = {
                                "phone_code_hash": result.phone_code_hash,
                                "session_name": session_name,
                                "api_id": api_id,
                                "api_hash": api_hash
                            }
                            redis_conn.set(verification_key, json.dumps(verification_data), ex=600)
                        await client.disconnect()

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_send_code())
                    loop.close()

                    # Increment counter after successful request
                    counter_status = increment_sms_code_counter(phone)
                    
                    # Prepare response with counter info
                    response = {
                        "success": True,
                        "code_sent": True,
                        "message": f"Codice di verifica inviato a {phone}",
                        "phone": phone,
                        "rate_limit": counter_status
                    }
                    
                    # Add warning if approaching limit
                    if counter_status["count"] >= SMS_CODE_WARNING_THRESHOLD:
                        response["warning"] = f"Attenzione: hai fatto {counter_status['count']} richieste su {counter_status['limit']}. Limite raggiunto tra {counter_status['remaining']} richieste."

                    return jsonify(response), 202  # 202 Accepted -> client deve inviare 'code'
                except Exception as e:
                    logger.error(f"Error sending code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # 2) Abbiamo ricevuto un codice -> verifichiamo
            else:
                if not redis_conn or not redis_conn.exists(verification_key):
                    return jsonify({"success": False, "error": "Richiesta di verifica scaduta o assente"}), 400

                try:
                    verification_data = json.loads(redis_conn.get(verification_key))

                    async def _verify_code():
                        client = TelegramClient(session_file, verification_data['api_id'], verification_data['api_hash'])
                        await client.connect()
                        await client.sign_in(phone, code_from_client, phone_code_hash=verification_data['phone_code_hash'])
                        authorized = await client.is_user_authorized()
                        await client.disconnect()
                        return authorized

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ok = loop.run_until_complete(_verify_code())
                    loop.close()

                    if not ok:
                        return jsonify({"success": False, "error": "Codice non valido"}), 400

                    # Puliamo la chiave redis e proseguiamo con la creazione del container
                    redis_conn.delete(verification_key)
                    logger.info(f"Forwarder session created for {session_name}")
                except Exception as e:
                    logger.error(f"Error verifying code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # For now, we'll use empty session string as we're using file session
            session_string = ""
        
        # Resolve target name if not provided
        target_name = data.get('target_name', '')
        if not target_name:
            try:
                # Try to get target entity name
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def get_target_name():
                    try:
                        if data['target_type'] == 'user' and data['target_id'].startswith('@'):
                            entity = await client.get_entity(data['target_id'])
                        else:
                            entity = await client.get_entity(int(data['target_id']))
                        
                        if hasattr(entity, 'username') and entity.username:
                            return f"@{entity.username}"
                        elif hasattr(entity, 'first_name'):
                            return f"{entity.first_name} {getattr(entity, 'last_name', '')}".strip()
                        elif hasattr(entity, 'title'):
                            return entity.title
                        else:
                            return data['target_id']
                    except:
                        return data['target_id']
                
                target_name = loop.run_until_complete(get_target_name())
                loop.close()
            except:
                target_name = data['target_id']
        
        # Build forwarder image if needed
        forwarder_manager = ForwarderManager()
        # Image is ensured in ForwarderManager.__init__()
        
        # Get forwarder-specific session file path
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        forwarder_session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
        
        # Create container
        success, container_name, message = forwarder_manager.create_forwarder_container(
            user_id=current_user_id,
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            source_chat_id=data['source_chat_id'],
            source_chat_title=data['source_chat_title'],
            target_type=data['target_type'],
            target_id=data['target_id'],
            target_name=target_name,
            session_file_path=forwarder_session_file
        )
        
        if not success:
            return jsonify({"success": False, "error": f"Errore creazione container: {message}"}), 500
        
        # Save to database
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                INSERT INTO forwarders (
                    user_id, source_chat_id, source_chat_title, 
                    target_type, target_id, target_name, 
                    container_name, container_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                current_user_id, data['source_chat_id'], data['source_chat_title'],
                data['target_type'], data['target_id'], target_name,
                container_name, 'running'
            ))
            
            forwarder_id = cursor.fetchone()['id']
            db.commit()
        
        logger.info(f"Created forwarder {forwarder_id} with container {container_name}")
        
        return jsonify({
            "success": True,
            "message": "Inoltro creato con successo",
            "forwarder_id": forwarder_id,
            "container_name": container_name
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error preparing forwarder: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/verify-code', methods=['POST'])
@jwt_required()
def verify_forwarder_code():
    """Verify code and create forwarder session"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('code') or not data.get('source_chat_id'):
        return jsonify({"success": False, "error": "Codice e source_chat_id richiesti"}), 400
    
    redis_conn = get_redis_connection()
    verification_key = f"forwarder_verification:{current_user_id}:{data['source_chat_id']}"
    
    if not redis_conn or not redis_conn.exists(verification_key):
        return jsonify({"success": False, "error": "Richiesta di verifica scaduta"}), 400
    
    try:
        verification_data = json.loads(redis_conn.get(verification_key))
        session_name = verification_data['session_name']
        session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
        
        async def verify_and_save():
            client = TelegramClient(
                session_file,
                verification_data['api_id'],
                verification_data['api_hash']
            )
            await client.connect()
            
            db = get_db_connection()
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
                user = cursor.fetchone()
            
            await client.sign_in(
                user['phone'],
                data['code'],
                phone_code_hash=verification_data['phone_code_hash']
            )
            
            is_authorized = await client.is_user_authorized()
            await client.disconnect()
            return is_authorized
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        is_authorized = loop.run_until_complete(verify_and_save())
        loop.close()
        
        if is_authorized:
            redis_conn.delete(verification_key)
            return jsonify({
                "success": True,
                "message": "Sessione creata con successo"
            }), 200
        else:
            return jsonify({"success": False, "error": "Autorizzazione fallita"}), 400
            
    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/forwarders', methods=['POST'])
@jwt_required()
def create_forwarder():
    """Create a new forwarder"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['source_chat_id', 'source_chat_title', 'target_type', 'target_id']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Campo richiesto: {field}"}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Get user credentials
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted 
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        api_id = user['api_id']
        api_hash = decrypt_api_hash(user['api_hash_encrypted'])
        source_chat_id = data['source_chat_id']
        
        # --- Gestione automatica della sessione forwarder ----------------------------------
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        session_file = os.path.join(SESSION_DIR, f"{session_name}.session")

        code_from_client: Optional[str] = data.get('code')

        # Controlliamo se esiste già una sessione forwarder valida
        session_exists_and_valid = False
        if os.path.exists(session_file):
            try:
                async def _check_session():
                    client = TelegramClient(session_file, api_id, api_hash)
                    await client.connect()
                    authorized = await client.is_user_authorized()
                    await client.disconnect()
                    return authorized

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                session_exists_and_valid = loop.run_until_complete(_check_session())
                loop.close()
                logger.info(f"Session {session_name} exists and is valid: {session_exists_and_valid}")
            except Exception as e:
                logger.warning(f"Session {session_name} exists but is invalid: {e}")
                # Rimuoviamo il file di sessione corrotto
                os.remove(session_file)
                session_exists_and_valid = False

        # Se la sessione è valida, non serve richiedere il codice
        if session_exists_and_valid:
            logger.info(f"Using existing valid session for {session_name}")
            # For now, we'll use empty session string as we're using file session
            session_string = ""
        else:
            # SEMPRE chiediamo il codice per un nuovo forwarder
            verification_key = f"forwarder_verification:{current_user_id}:{source_chat_id}"
            redis_conn = get_redis_connection()

            # 1) L'utente NON ha inviato alcun codice -> inviamo codice e salviamo phone_code_hash
            if not code_from_client:
                # Check rate limiting first
                rate_check = can_request_sms_code(phone)
                if not rate_check["can_request"]:
                    return jsonify({
                        "success": False, 
                        "error": f"Limite SMS raggiunto. Riprova tra {rate_check['time_formatted']}",
                        "rate_limit": rate_check
                    }), 429
                
                try:
                    async def _send_code():
                        # Se esiste già un file sessione, rimuoviamolo per iniziare da zero
                        if os.path.exists(session_file):
                            os.remove(session_file)
                            logger.info(f"Removed existing session file for {session_name}")
                        
                        client = TelegramClient(session_file, api_id, api_hash)
                        await client.connect()
                        result = await client.send_code_request(phone)

                        if redis_conn:
                            verification_data = {
                                "phone_code_hash": result.phone_code_hash,
                                "session_name": session_name,
                                "api_id": api_id,
                                "api_hash": api_hash
                            }
                            redis_conn.set(verification_key, json.dumps(verification_data), ex=600)
                        await client.disconnect()

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_send_code())
                    loop.close()

                    # Increment counter after successful request
                    counter_status = increment_sms_code_counter(phone)
                    
                    # Prepare response with counter info
                    response = {
                        "success": True,
                        "code_sent": True,
                        "message": f"Codice di verifica inviato a {phone}",
                        "phone": phone,
                        "rate_limit": counter_status
                    }
                    
                    # Add warning if approaching limit
                    if counter_status["count"] >= SMS_CODE_WARNING_THRESHOLD:
                        response["warning"] = f"Attenzione: hai fatto {counter_status['count']} richieste su {counter_status['limit']}. Limite raggiunto tra {counter_status['remaining']} richieste."

                    return jsonify(response), 202  # 202 Accepted -> client deve inviare 'code'
                except Exception as e:
                    logger.error(f"Error sending code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # 2) Abbiamo ricevuto un codice -> verifichiamo
            else:
                if not redis_conn or not redis_conn.exists(verification_key):
                    return jsonify({"success": False, "error": "Richiesta di verifica scaduta o assente"}), 400

                try:
                    verification_data = json.loads(redis_conn.get(verification_key))

                    async def _verify_code():
                        client = TelegramClient(session_file, verification_data['api_id'], verification_data['api_hash'])
                        await client.connect()
                        await client.sign_in(phone, code_from_client, phone_code_hash=verification_data['phone_code_hash'])
                        authorized = await client.is_user_authorized()
                        await client.disconnect()
                        return authorized

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ok = loop.run_until_complete(_verify_code())
                    loop.close()

                    if not ok:
                        return jsonify({"success": False, "error": "Codice non valido"}), 400

                    # Puliamo la chiave redis e proseguiamo con la creazione del container
                    redis_conn.delete(verification_key)
                    logger.info(f"Forwarder session created for {session_name}")
                except Exception as e:
                    logger.error(f"Error verifying code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # For now, we'll use empty session string as we're using file session
            session_string = ""
        
        # Resolve target name if not provided
        target_name = data.get('target_name', '')
        if not target_name:
            try:
                # Try to get target entity name
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def get_target_name():
                    try:
                        if data['target_type'] == 'user' and data['target_id'].startswith('@'):
                            entity = await client.get_entity(data['target_id'])
                        else:
                            entity = await client.get_entity(int(data['target_id']))
                        
                        if hasattr(entity, 'username') and entity.username:
                            return f"@{entity.username}"
                        elif hasattr(entity, 'first_name'):
                            return f"{entity.first_name} {getattr(entity, 'last_name', '')}".strip()
                        elif hasattr(entity, 'title'):
                            return entity.title
                        else:
                            return data['target_id']
                    except:
                        return data['target_id']
                
                target_name = loop.run_until_complete(get_target_name())
                loop.close()
            except:
                target_name = data['target_id']
        
        # Build forwarder image if needed
        forwarder_manager = ForwarderManager()
        # Image is ensured in ForwarderManager.__init__()
        
        # Get forwarder-specific session file path
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        forwarder_session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
        
        # Create container
        success, container_name, message = forwarder_manager.create_forwarder_container(
            user_id=current_user_id,
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            source_chat_id=data['source_chat_id'],
            source_chat_title=data['source_chat_title'],
            target_type=data['target_type'],
            target_id=data['target_id'],
            target_name=target_name,
            session_file_path=forwarder_session_file
        )
        
        if not success:
            return jsonify({"success": False, "error": f"Errore creazione container: {message}"}), 500
        
        # Save to database
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                INSERT INTO forwarders (
                    user_id, source_chat_id, source_chat_title, 
                    target_type, target_id, target_name, 
                    container_name, container_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                current_user_id, data['source_chat_id'], data['source_chat_title'],
                data['target_type'], data['target_id'], target_name,
                container_name, 'running'
            ))
            
            forwarder_id = cursor.fetchone()['id']
            db.commit()
        
        logger.info(f"Created forwarder {forwarder_id} with container {container_name}")
        
        return jsonify({
            "success": True,
            "message": "Inoltro creato con successo",
            "forwarder_id": forwarder_id,
            "container_name": container_name
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error creating forwarder: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/<int:forwarder_id>', methods=['DELETE'])
@jwt_required()
def delete_forwarder(forwarder_id):
    """Delete a forwarder and its container"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Verify ownership
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT container_name 
                FROM forwarders 
                WHERE id = %s AND user_id = %s
            """, (forwarder_id, current_user_id))
            forwarder = cursor.fetchone()
        
        if not forwarder:
            logger.warning(f"Forwarder {forwarder_id} not found for user {current_user_id}")
            return jsonify({"success": False, "error": "Inoltro non trovato"}), 404
        
        container_name = forwarder['container_name']
        logger.info(f"Attempting to delete forwarder {forwarder_id} with container {container_name}")
        
        # Stop and remove container (this will succeed even if container doesn't exist)
        forwarder_manager = ForwarderManager()
        success, message = forwarder_manager.stop_and_remove_container(container_name)
        
        logger.info(f"Container removal result: success={success}, message={message}")
        
        # Delete from database regardless of container removal status
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM forwarders WHERE id = %s", (forwarder_id,))
            db.commit()
        
        # Force a small delay to ensure transaction is visible
        time.sleep(0.1)
        
        logger.info(f"Successfully deleted forwarder {forwarder_id} from database")
        
        return jsonify({
            "success": True,
            "message": "Inoltro eliminato con successo",
            "container_removed": success,
            "container_message": message
        }), 200
            
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error deleting forwarder {forwarder_id}: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/<int:forwarder_id>/restart', methods=['POST'])
@jwt_required()
def restart_forwarder(forwarder_id):
    """Restart a forwarder container"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Verify ownership
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT container_name 
                FROM forwarders 
                WHERE id = %s AND user_id = %s
            """, (forwarder_id, current_user_id))
            forwarder = cursor.fetchone()
        
        if not forwarder:
            return jsonify({"success": False, "error": "Inoltro non trovato"}), 404
        
        # Restart container
        forwarder_manager = ForwarderManager()
        success, message = forwarder_manager.restart_container(forwarder['container_name'])
        
        if success:
            # Update status in database
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE forwarders 
                    SET container_status = 'running' 
                    WHERE id = %s
                """, (forwarder_id,))
                db.commit()
            
            return jsonify({
                "success": True,
                "message": "Container riavviato con successo"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Errore riavvio: {message}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error restarting forwarder: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/cleanup-orphaned', methods=['POST'])
@jwt_required()
def cleanup_orphaned_forwarders():
    """Clean up forwarders that exist in database but don't have containers"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Get all forwarders for the user
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, container_name 
                FROM forwarders 
                WHERE user_id = %s
            """, (current_user_id,))
            forwarders = cursor.fetchall()
        
        orphaned_count = 0
        forwarder_manager = ForwarderManager()
        
        for forwarder in forwarders:
            container_status = forwarder_manager.get_container_status(forwarder['container_name'])
            
            # If container doesn't exist, mark as orphaned
            if container_status['status'] == 'not_found':
                logger.info(f"Found orphaned forwarder {forwarder['id']} with container {forwarder['container_name']}")
                
                # Delete from database
                with db.cursor() as cursor:
                    cursor.execute("DELETE FROM forwarders WHERE id = %s", (forwarder['id'],))
                
                orphaned_count += 1
        
        if orphaned_count > 0:
            db.commit()
            logger.info(f"Cleaned up {orphaned_count} orphaned forwarders for user {current_user_id}")
        
        return jsonify({
            "success": True,
            "message": f"Pulizia completata. Rimossi {orphaned_count} inoltri orfani.",
            "orphaned_count": orphaned_count
        }), 200
        
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error cleaning up orphaned forwarders: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

# ============================================
# Application Bootstrap
# ============================================

def create_app():
    with app.app_context():
        get_db_connection()
        get_redis_connection()
    return app

@app.route('/api/auth/sms-status', methods=['GET'])
@jwt_required()
def get_sms_status():
    """Get SMS code request status for current user"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        rate_check = can_request_sms_code(phone)
        
        return jsonify({
            "success": True,
            "phone": phone,
            "rate_limit": rate_check
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting SMS status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/reset-sms-counter', methods=['POST'])
@jwt_required()
def reset_sms_counter():
    """Force reset SMS code counter for current user (for testing)"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        redis_conn = get_redis_connection()
        
        if redis_conn:
            # Reset counter
            counter_key = f"sms_counter:{phone}"
            reset_key = f"sms_reset:{phone}"
            redis_conn.delete(counter_key)
            redis_conn.delete(reset_key)
            
            logger.info(f"Reset SMS counter for {phone}")
        
        return jsonify({
            "success": True,
            "message": "Contatore SMS resettato",
            "phone": phone
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting SMS counter: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/check-cached-code', methods=['GET'])
def check_cached_code():
    """Check if there's a cached verification code available for a phone number"""
    phone = request.args.get('phone')
    
    if not phone:
        return jsonify({"success": False, "error": "Numero di telefono richiesto"}), 400
    
    cached_code_data = get_cached_code(phone)
    
    if cached_code_data:
        # Calculate remaining time
        remaining_time = int(cached_code_data['expires_at'] - time.time())
        if remaining_time > 0:
            return jsonify({
                "success": True,
                "has_cached_code": True,
                "remaining_time": remaining_time,
                "message": f"Codice in cache disponibile per {remaining_time} secondi"
            })
    
    return jsonify({
        "success": True,
        "has_cached_code": False,
        "message": "Nessun codice in cache disponibile"
    })

@app.route('/api/auth/use-cached-code', methods=['POST'])
def use_cached_code():
    """Use a cached verification code instead of requesting a new one"""
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone:
        return jsonify({"success": False, "error": "Numero di telefono richiesto"}), 400
    
    cached_code_data = get_cached_code(phone)
    
    if not cached_code_data:
        return jsonify({"success": False, "error": "Nessun codice in cache disponibile"}), 404
    
    # Store verification data in Redis for verification step
    redis_conn = get_redis_connection()
    if not redis_conn:
        return jsonify({"success": False, "error": "Errore di connessione Redis"}), 500
    
    verification_key = f"verification:{phone}"
    verification_data = {
        "api_id": cached_code_data["api_id"],
        "api_hash": cached_code_data["api_hash"],
        "phone_code_hash": cached_code_data["phone_code_hash"],
        "password": cached_code_data.get("password"),
        "cached_code": cached_code_data["code"]
    }
    redis_conn.set(verification_key, json.dumps(verification_data), ex=600)
    
    # Get counter status without incrementing
    counter_status = get_sms_code_counter(phone)
    
    return jsonify({
        "success": True,
        "message": f"Codice in cache attivato per {phone}",
        "rate_limit": counter_status,
        "cached": True
    })

@app.route('/api/auth/clear-cached-code', methods=['POST'])
def clear_cached_code():
    """Clear cached verification code for a phone number"""
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone:
        return jsonify({"success": False, "error": "Numero di telefono richiesto"}), 400
    
    clear_cached_code(phone)
    
    return jsonify({
        "success": True,
        "message": f"Codice in cache cancellato per {phone}"
    })

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True) 