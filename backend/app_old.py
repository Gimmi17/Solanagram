#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔐 Telegram Chat Manager - Backend API
Multi-user backend with authentication and Telegram session management
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from flask import Flask, jsonify, request, session
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import redis
from telethon.sync import TelegramClient
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError, SessionPasswordNeededError

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# 🔧 Configurazione Database e Redis
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://chatmanager:dev_password_123@postgres:5432/chatmanager')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
ENVIRONMENT = os.getenv('FLASK_ENV', 'development')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Telegram API Configuration
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')

# Inizializza connessioni
redis_client = redis.from_url(REDIS_URL)

def get_db_connection():
    """Ottieni connessione al database"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

# ============================================
# 🔒 UTILITY FUNCTIONS
# ============================================

def generate_session_token():
    """Genera un token di sessione sicuro"""
    return secrets.token_urlsafe(32)

def hash_phone_number(phone: str) -> str:
    """Hash del numero di telefono per privacy"""
    return hashlib.sha256(phone.encode()).hexdigest()[:16]

def validate_phone_number(phone: str) -> bool:
    """Valida formato numero di telefono"""
    import re
    # Formato internazionale: +1234567890
    pattern = r'^\+[1-9]\d{1,14}$'
    return re.match(pattern, phone) is not None

def create_user_session(user_id: int, session_token: str) -> bool:
    """Crea sessione utente in Redis"""
    try:
        session_data = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'active': True
        }
        # Sessione valida per 24 ore
        redis_client.setex(f"session:{session_token}", 86400, str(session_data))
        return True
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        return False

def get_user_from_session(session_token: str) -> Optional[Dict]:
    """Recupera utente dalla sessione"""
    try:
        session_data = redis_client.get(f"session:{session_token}")
        if session_data:
            import ast
            return ast.literal_eval(session_data.decode())
        return None
    except Exception as e:
        logger.error(f"Session retrieval error: {e}")
        return None

def require_auth(f):
    """Decorator per richiedere autenticazione"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({'error': 'Missing authorization token'}), 401
        
        if session_token.startswith('Bearer '):
            session_token = session_token[7:]
        
        user_session = get_user_from_session(session_token)
        if not user_session:
            return jsonify({'error': 'Invalid or expired session'}), 401
        
        request.current_user = user_session
        return f(*args, **kwargs)
    
    return decorated_function

# ============================================
# 🏥 HEALTH CHECK
# ============================================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database
        conn = get_db_connection()
        db_status = "connected" if conn else "disconnected"
        if conn:
            conn.close()
        
        # Test Redis
        redis_status = "connected" if redis_client.ping() else "disconnected"
        
        overall_status = "healthy" if db_status == "connected" and redis_status == "connected" else "unhealthy"
        
        return jsonify({
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": db_status,
                "redis": redis_status
            },
            "version": "1.0.0-dev",
            "component": "backend"
        }), 200 if overall_status == "healthy" else 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# ============================================
# 📋 API INFO
# ============================================

@app.route('/api/info')
def api_info():
    """Informazioni API"""
    return jsonify({
        "name": "Telegram Chat Manager API",
        "version": "1.0.0-dev",
        "description": "Backend API for multi-user Telegram chat management",
        "status": "development",
        "features": [
            "User authentication",
            "Telegram session management", 
            "Privacy-first design",
            "Multi-user support"
        ],
        "endpoints": {
            "health": "/health",
            "info": "/api/info",
            "auth": "/api/auth/*",
            "telegram": "/api/telegram/*",
            "users": "/api/users/*"
        }
    })

# ============================================
# 🔐 AUTHENTICATION ENDPOINTS
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registrazione nuovo utente"""
    try:
        data = request.get_json()
        
        # Validazione input
        required_fields = ['phone_number', 'api_id', 'api_hash']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} richiesto'}), 400
        
        phone_number = data['phone_number'].strip()
        api_id = str(data['api_id']).strip()
        api_hash = data['api_hash'].strip()
        landing = data.get('landing', '').strip()
        
        # Validazione numero di telefono
        if not validate_phone_number(phone_number):
            return jsonify({'error': 'Formato numero di telefono non valido. Usa formato internazionale (+1234567890)'}), 400
        
        # Validazione API ID
        try:
            api_id_int = int(api_id)
            if api_id_int <= 0:
                raise ValueError()
        except ValueError:
            return jsonify({'error': 'API ID deve essere un numero positivo'}), 400
        
        # Validazione API Hash
        if len(api_hash) != 32:
            return jsonify({'error': 'API Hash deve essere di 32 caratteri'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Controlla se utente esiste già
            cur.execute("SELECT user_id FROM users WHERE phone_number = %s", (phone_number,))
            existing_user = cur.fetchone()
            
            if existing_user:
                return jsonify({'error': 'Numero di telefono già registrato'}), 409
            
            # Crea nuovo utente
            cur.execute("""
                INSERT INTO users (phone_number, api_id, api_hash, landing, created_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id, phone_number, created_at
            """, (phone_number, api_id_int, api_hash, landing, datetime.now(), True))
            
            new_user = cur.fetchone()
            
            logger.info(f"New user registered: {hash_phone_number(phone_number)}")
            
            return jsonify({
                'success': True,
                'message': 'Utente registrato con successo',
                'user': {
                    'user_id': new_user['user_id'],
                    'phone_number': new_user['phone_number'],
                    'created_at': new_user['created_at'].isoformat()
                }
            }), 201
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login utente - inizio processo autenticazione"""
    try:
        data = request.get_json()
        
        if not data.get('phone_number'):
            return jsonify({'error': 'Numero di telefono richiesto'}), 400
        
        phone_number = data['phone_number'].strip()
        
        if not validate_phone_number(phone_number):
            return jsonify({'error': 'Formato numero di telefono non valido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Trova utente
            cur.execute("""
                SELECT user_id, phone_number, api_id, api_hash, is_active 
                FROM users 
                WHERE phone_number = %s
            """, (phone_number,))
            
            user = cur.fetchone()
            
            if not user:
                return jsonify({'error': 'Utente non trovato. Registrati prima di fare il login.'}), 404
            
            if not user['is_active']:
                return jsonify({'error': 'Account disattivato. Contatta il supporto.'}), 403
            
            # Crea client Telegram temporaneo per inviare codice
            session_name = f"temp_session_{user['user_id']}_{datetime.now().timestamp()}"
            client = TelegramClient(session_name, user['api_id'], user['api_hash'])
            
            try:
                client.connect()
                
                # Invia codice di verifica
                sent_code = client.send_code_request(phone_number)
                
                # Salva info sessione temporanea in Redis
                temp_session_data = {
                    'user_id': user['user_id'],
                    'phone_number': phone_number,
                    'api_id': user['api_id'],
                    'api_hash': user['api_hash'],
                    'phone_code_hash': sent_code.phone_code_hash,
                    'session_file': session_name,
                    'created_at': datetime.now().isoformat()
                }
                
                temp_session_key = f"temp_auth:{user['user_id']}"
                redis_client.setex(temp_session_key, 600, str(temp_session_data))  # 10 minuti
                
                logger.info(f"Login code sent to user: {hash_phone_number(phone_number)}")
                
                return jsonify({
                    'success': True,
                    'message': 'Codice di verifica inviato via Telegram',
                    'user_id': user['user_id'],
                    'next_step': 'verify_code'
                }), 200
                
            except PhoneNumberInvalidError:
                return jsonify({'error': 'Numero di telefono non valido o non registrato su Telegram'}), 400
            except Exception as telegram_error:
                logger.error(f"Telegram error during login: {telegram_error}")
                return jsonify({'error': 'Errore durante l\'invio del codice. Riprova.'}), 500
            finally:
                await client.disconnect()
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

@app.route('/api/auth/verify-code', methods=['POST'])
def verify_code():
    """Verifica codice Telegram e completa login"""
    try:
        data = request.get_json()
        
        if not data.get('user_id') or not data.get('code'):
            return jsonify({'error': 'User ID e codice richiesti'}), 400
        
        user_id = int(data['user_id'])
        code = data['code'].strip()
        password = data.get('password', '').strip()  # Per 2FA se necessario
        
        # Recupera sessione temporanea
        temp_session_key = f"temp_auth:{user_id}"
        temp_session_data = redis_client.get(temp_session_key)
        
        if not temp_session_data:
            return jsonify({'error': 'Sessione scaduta. Riprova il login.'}), 400
        
        import ast
        temp_data = ast.literal_eval(temp_session_data.decode())
        
        # Crea client Telegram
        client = TelegramClient(
            temp_data['session_file'], 
            int(temp_data['api_id']), 
            temp_data['api_hash']
        )
        
        try:
            await client.connect()
            
            # Verifica codice
            try:
                await client.sign_in(
                    phone=temp_data['phone_number'],
                    code=code,
                    phone_code_hash=temp_data['phone_code_hash']
                )
            except SessionPasswordNeededError:
                if not password:
                    return jsonify({
                        'error': 'Password di 2FA richiesta',
                        'requires_2fa': True
                    }), 400
                await client.sign_in(password=password)
            except PhoneCodeInvalidError:
                return jsonify({'error': 'Codice non valido'}), 400
            
            # Login riuscito - salva sessione Telegram
            session_string = client.session.save()
            
            # Aggiorna database
            conn = get_db_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE users 
                        SET telegram_session = %s, last_login = %s, updated_at = %s
                        WHERE user_id = %s
                    """, (session_string, datetime.now(), datetime.now(), user_id))
                finally:
                    conn.close()
            
            # Crea sessione applicazione
            session_token = generate_session_token()
            create_user_session(user_id, session_token)
            
            # Pulisci sessione temporanea
            redis_client.delete(temp_session_key)
            
            logger.info(f"User logged in successfully: {hash_phone_number(temp_data['phone_number'])}")
            
            return jsonify({
                'success': True,
                'message': 'Login completato con successo',
                'session_token': session_token,
                'user_id': user_id
            }), 200
            
        finally:
            await client.disconnect()
            
    except Exception as e:
        logger.error(f"Code verification error: {e}")
        return jsonify({'error': 'Errore durante la verifica. Riprova.'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout utente"""
    try:
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        # Rimuovi sessione da Redis
        redis_client.delete(f"session:{session_token}")
        
        logger.info(f"User logged out: {request.current_user['user_id']}")
        
        return jsonify({
            'success': True,
            'message': 'Logout completato'
        }), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Errore durante il logout'}), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Informazioni utente corrente"""
    try:
        user_id = request.current_user['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT user_id, phone_number, landing, created_at, last_login, is_active
                FROM users 
                WHERE user_id = %s
            """, (user_id,))
            
            user = cur.fetchone()
            
            if not user:
                return jsonify({'error': 'Utente non trovato'}), 404
            
            return jsonify({
                'success': True,
                'user': {
                    'user_id': user['user_id'],
                    'phone_number': user['phone_number'],
                    'landing': user['landing'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'last_login': user['last_login'].isoformat() if user['last_login'] else None,
                    'is_active': user['is_active']
                }
            }), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

# ============================================
# 📱 TELEGRAM ENDPOINTS (Protected)
# ============================================

@app.route('/api/telegram/find-chat', methods=['POST'])
@require_auth
def find_chat():
    """Trova chat Telegram (richiede autenticazione)"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query di ricerca richiesta'}), 400
        
        # TODO: Implementare ricerca chat usando la sessione Telegram dell'utente
        # Per ora ritorniamo un placeholder
        
        return jsonify({
            'success': True,
            'message': f'Ricerca per "{query}" (funzionalità in sviluppo)',
            'chat': {
                'id': 'placeholder',
                'title': f'Chat trovata per: {query}',
                'type': 'group',
                'username': None,
                'members_count': None
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Find chat error: {e}")
        return jsonify({'error': 'Errore durante la ricerca'}), 500

# ============================================
# 🚀 RUN APPLICATION
# ============================================

if __name__ == '__main__':
    logger.info("🚀 Starting Telegram Chat Manager Backend")
    logger.info(f"🌍 Environment: {ENVIRONMENT}")
    logger.info(f"🔧 Debug: {DEBUG}")
    logger.info(f"🔗 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Unknown'}")
    logger.info(f"🔗 Redis: {REDIS_URL}")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=DEBUG
    ) 