#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌐 Telegram Chat Manager - Frontend Web Interface
Multi-user web interface with authentication system
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from markupsafe import Markup
import requests
from datetime import datetime
from functools import wraps

# Import menu utilities
from menu_utils import get_unified_menu, get_logout_script

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# 🔧 Configurazione
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5000')
ENVIRONMENT = os.getenv('FLASK_ENV', 'development')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# 🎨 Template HTML base
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Solanagram</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: #2c3e50; 
            color: white; 
            padding: 30px; 
            text-align: center; 
        }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { opacity: 0.8; font-size: 16px; }
        .content { padding: 40px; }
        .status { padding: 15px; border-radius: 8px; margin: 20px 0; }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .status.warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .btn { 
            display: inline-block; 
            padding: 12px 24px; 
            background: #3498db; 
            color: white; 
            text-decoration: none; 
            border-radius: 6px; 
            transition: all 0.3s ease; 
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        .btn:hover { background: #2980b9; transform: translateY(-2px); }
        .btn.danger { background: #e74c3c; }
        .btn.danger:hover { background: #c0392b; }
        .btn.success { background: #27ae60; }
        .btn.success:hover { background: #229954; }
        .footer { 
            background: #34495e; 
            color: white; 
            padding: 20px; 
            text-align: center; 
            font-size: 14px; 
        }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #e9ecef; }
        .card h3 { color: #2c3e50; margin-bottom: 10px; }
        code { background: #f1f3f4; padding: 2px 6px; border-radius: 4px; font-family: 'Monaco', monospace; }
        
        /* Form styles */
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: bold; color: #2c3e50; }
        .form-group input, .form-group textarea { 
            width: 100%; 
            padding: 12px; 
            border: 1px solid #ddd; 
            border-radius: 6px; 
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        .form-group input:focus, .form-group textarea:focus { 
            outline: none; 
            border-color: #3498db; 
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }
        .form-group small { color: #6c757d; font-size: 14px; margin-top: 5px; display: block; }
        .form-actions { text-align: center; margin-top: 30px; }
        .form-actions .btn { margin: 0 10px; }
        
        /* Loading spinner */
        .loading { 
            display: none; 
            text-align: center; 
            margin: 20px 0; 
        }
        .spinner { 
            border: 3px solid #f3f3f3; 
            border-top: 3px solid #3498db; 
            border-radius: 50%; 
            width: 30px; 
            height: 30px; 
            animation: spin 1s linear infinite; 
            margin: 0 auto;
        }
        @keyframes spin { 
            0% { transform: rotate(0deg); } 
            100% { transform: rotate(360deg); } 
        }
        
        /* Unified Menu Styles - Aligned with site design */
        .nav {
            margin-bottom: 20px;
            text-align: center;
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .nav-link {
            display: inline-block;
            margin: 0 10px;
            color: #3498db;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            transition: all 0.3s ease;
            font-weight: 500;
            border: 1px solid transparent;
        }
        
        .nav-link:hover {
            background: #3498db;
            color: white;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
        }
        
        .nav-link.active {
            background: #3498db;
            color: white;
            border-color: #2980b9;
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
        }
        
        /* Mobile responsive */
        @media (max-width: 768px) {
            .nav {
                padding: 0.5rem;
            }
            
            .nav-link {
                display: block;
                margin: 5px 0;
                padding: 0.5rem 1rem;
                font-size: 0.9rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Solanagram</h1>
            <p>{{ subtitle }}</p>
        </div>
        <div class="content">
            {{ content }}
        </div>
        <div class="footer">
            <p>🔒 Privacy-first • 🚀 Multi-user • ⚡ Fast</p>
        </div>
    </div>
    
    <script>
        // Utility functions
        async function makeRequest(url, options = {}) {
            try {
                console.log('makeRequest - URL:', url);
                
                const headers = {
                    'Content-Type': 'application/json',
                    ...options.headers
                };
                
                console.log('makeRequest - Headers:', headers);
                
                const response = await fetch(url, {
                    ...options,
                    headers
                });
                
                console.log('makeRequest - Response status:', response.status);
                const jsonResult = await response.json();
                console.log('makeRequest - JSON result:', jsonResult);
                return jsonResult;
            } catch (error) {
                console.error('makeRequest - Error:', error);
                return { error: 'Errore di connessione' };
            }
        }
        
        function showLoading() {
            const loading = document.querySelector('.loading');
            if (loading) loading.style.display = 'block';
        }
        
        function hideLoading() {
            const loading = document.querySelector('.loading');
            if (loading) loading.style.display = 'none';
        }
        
        function showMessage(message, type = 'info') {
            const statusDiv = document.createElement('div');
            statusDiv.className = `status ${type}`;
            statusDiv.innerHTML = message;
            
            const content = document.querySelector('.content');
            content.insertBefore(statusDiv, content.firstChild);
            
            // Removed auto-removal - messages will stay until page reload
        }
        
        // Global logout function
        async function logout() {
            if (confirm('Sei sicuro di voler uscire?')) {
                try {
                    const result = await makeRequest('/api/auth/logout', {
                        method: 'POST'
                    });
                    
                    // Reindirizza al login
                    if (result && result.redirect) {
                        window.location.href = result.redirect;
                    } else {
                        window.location.href = '/login';
                    }
                } catch (error) {
                    console.error('Errore durante logout:', error);
                    // Anche in caso di errore, reindirizza al login
                    window.location.href = '/login';
                }
            }
        }
    </script>
</body>
</html>
"""

def call_backend(endpoint: str, method: str = 'GET', data: Optional[Dict] = None, auth_token: Optional[str] = None) -> Optional[Dict]:
    """Effettua una chiamata al backend"""
    url = f"{BACKEND_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    logger.info(f"🔗 [BACKEND] {method} {endpoint} - Starting call")
    logger.info(f"🔗 [BACKEND] Full URL: {url}")
    
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
        logger.info(f"🔗 [BACKEND] Using provided auth_token")
    elif 'session_token' in session:
        headers['Authorization'] = f'Bearer {session["session_token"]}'
        logger.info(f"🔗 [BACKEND] Using session token")
    else:
        logger.info(f"🔗 [BACKEND] No auth token")
    
    logger.info(f"🔗 [BACKEND] Headers: {dict(headers)}")
    logger.info(f"🔗 [BACKEND] Data: {data}")

    try:
        if method.upper() == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=30)
        else:
            response = requests.get(url, headers=headers, timeout=30)

        logger.info(f"🔗 [BACKEND] Response status: {response.status_code}")
        logger.info(f"🔗 [BACKEND] Response headers: {dict(response.headers)}")
        
        # Controlla se la risposta è JSON valida
        try:
            result = response.json()
            logger.info(f"🔗 [BACKEND] Response JSON: {result}")
            return result
        except ValueError as e:
            logger.error(f"🔗 [BACKEND] Errore parsing JSON: {e}")
            logger.error(f"🔗 [BACKEND] Raw response: {response.text[:500]}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"🔗 [BACKEND] Errore connessione: {e}")
        return None

def is_authenticated() -> bool:
    """Controlla se l'utente è autenticato"""
    return 'session_token' in session and session['session_token']

def require_auth(f):
    """Decorator per richiedere autenticazione"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# 🏠 PUBLIC ROUTES
# ============================================

@app.route('/')
def index():
    """Homepage - redirect based on auth status"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/login')
def login():
    """Pagina di login"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    content = """
    <h2>🔐 Accedi</h2>
    
    <div class="status info">
        ℹ️ Inserisci il numero di telefono per accedere
    </div>
    
    <div class="status success" style="margin-bottom: 20px;">
        🔑 <strong>Sistema Future Auth Tokens Attivo</strong><br>
        Il sistema utilizza i token di autenticazione ufficiali di Telegram.<br>
        Se hai effettuato il login recentemente, puoi riutilizzare i token salvati senza richiedere nuovi codici SMS.<br>
        <small>Questo sistema ufficiale evita completamente i limiti di richieste a Telegram.</small>
    </div>
    
    <form id="loginForm">
        <div class="form-group">
            <label for="phone_number">Numero di telefono</label>
            <input type="tel" id="phone_number" name="phone_number" required 
                   placeholder="+391234567890">
            <small>Formato internazionale (es. +391234567890)</small>
        </div>
        
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required 
                   placeholder="La tua password">
            <small>Password scelta durante la registrazione</small>
        </div>
        
        <div id="cachedCodeSection" style="display: none;">
            <div class="status success">
                💾 <strong>Codice in cache disponibile!</strong>
                <br>Hai un codice di verifica salvato che puoi riutilizzare senza richiederne uno nuovo.
                <br><small>Questo aiuta a evitare limiti di richieste a Telegram.</small>
            </div>
            <div class="form-actions" style="margin-top: 10px;">
                <button type="button" id="useCachedCode" class="btn success">🔄 Usa codice salvato</button>
                <button type="button" id="requestNewCode" class="btn">📱 Richiedi nuovo codice</button>
            </div>
        </div>
        
        <div id="futureTokensSection" style="display: none;">
            <div class="status success">
                🔑 <strong>Token di autenticazione disponibili!</strong>
                <br>Hai token di autenticazione salvati che possono essere riutilizzati.
                <br><small>Questo sistema ufficiale Telegram evita di richiedere nuovi codici SMS.</small>
            </div>
            <div class="form-actions" style="margin-top: 10px;">
                <button type="button" id="useFutureTokens" class="btn success">🔄 Usa token salvati</button>
                <button type="button" id="requestNewCode" class="btn">📱 Richiedi nuovo codice</button>
            </div>
        </div>
        
        <div class="loading">
            <div class="spinner"></div>
            <p>Invio codice di verifica...</p>
        </div>
        
        <div class="form-actions">
            <button type="submit" class="btn">📱 Invia codice</button>
            <a href="/register" class="btn" style="background: #6c757d;">Registrati</a>
        </div>
    </form>
    
    <script>
        let currentPhone = '';
        let currentPassword = '';
        
        // Controlla se esiste un codice in cache quando l'utente inserisce il numero
        document.getElementById('phone_number').addEventListener('blur', async function() {
            const phone = this.value.trim();
            if (phone) {
                try {
                    const result = await makeRequest(`/api/auth/check-future-tokens?phone=${encodeURIComponent(phone)}`, {
                        method: 'GET'
                    });
                    
                    if (result.success && result.has_future_tokens) {
                        document.getElementById('futureTokensSection').style.display = 'block';
                        currentPhone = phone;
                    } else {
                        document.getElementById('futureTokensSection').style.display = 'none';
                    }
                } catch (error) {
                    console.log('Errore nel controllo future tokens:', error);
                }
            }
        });
        
        // Usa future auth tokens
        document.getElementById('useFutureTokens').addEventListener('click', async function() {
            const password = document.getElementById('password').value.trim();
            
            if (!currentPhone || !password) {
                showMessage('Inserisci numero di telefono e password', 'error');
                return;
            }
            
            showLoading();
            
            try {
                const result = await makeRequest('/api/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({ 
                        phone_number: currentPhone,
                        password: password 
                    })
                });
                
                if (result.success) {
                    if (result.direct_login) {
                        // Login diretto con token
                        showMessage(result.message, 'success');
                        setTimeout(() => {
                            window.location.href = '/dashboard';
                        }, 2000);
                    } else {
                        // Salva dati per la verifica
                        localStorage.setItem('temp_phone', currentPhone);
                        showMessage(result.message, 'success');
                        setTimeout(() => {
                            window.location.href = '/verify-code';
                        }, 2000);
                    }
                } else {
                    showMessage(result.error || 'Errore nel login', 'error');
                }
            } catch (error) {
                showMessage('Errore di connessione', 'error');
            }
            
            hideLoading();
        });
        
        // Richiedi nuovo codice
        document.getElementById('requestNewCode').addEventListener('click', async function() {
            const phone = document.getElementById('phone_number').value.trim();
            const password = document.getElementById('password').value.trim();
            
            if (!phone || !password) {
                showMessage('Inserisci numero di telefono e password', 'error');
                return;
            }
            
            showLoading();
            
            const result = await makeRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ 
                    phone_number: phone,
                    password: password 
                })
            });
            
            hideLoading();
            
            if (result.success) {
                // Salva dati per la verifica
                localStorage.setItem('temp_phone', phone);
                showMessage(result.message, 'success');
                
                // Redirect a pagina verifica codice
                setTimeout(() => {
                    window.location.href = '/verify-code';
                }, 2000);
            } else {
                showMessage(result.error || 'Errore nel login', 'error');
            }
        });
        
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const phone = document.getElementById('phone_number').value.trim();
            const password = document.getElementById('password').value.trim();
            
            if (!phone || !password) {
                showMessage('Inserisci numero di telefono e password', 'error');
                return;
            }
            
            showLoading();
            
            const result = await makeRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ 
                    phone_number: phone,
                    password: password 
                })
            });
            
            hideLoading();
            
            if (result.success) {
                // Salva user_id per la verifica
                localStorage.setItem('temp_user_id', result.user_id);
                localStorage.setItem('temp_phone', phone);
                
                showMessage(result.message, 'success');
                
                // Redirect a pagina verifica codice
                setTimeout(() => {
                    window.location.href = '/verify-code';
                }, 2000);
            } else {
                // Gestione speciale per FLOOD_WAIT
                if (result.error && result.error.includes('FLOOD_WAIT')) {
                    // Estrai il tempo di attesa dal messaggio
                    const waitMatch = result.error.match(/Attendi (\d+) secondi/);
                    if (waitMatch) {
                        const waitSeconds = parseInt(waitMatch[1]);
                        const waitHours = Math.floor(waitSeconds / 3600);
                        const waitMinutes = Math.floor((waitSeconds % 3600) / 60);
                        
                        let waitMessage = `🚫 <strong>Limite Telegram raggiunto!</strong><br><br>`;
                        waitMessage += `Hai fatto troppe richieste di codici SMS in poco tempo.<br>`;
                        waitMessage += `Telegram richiede di attendere: <strong>${waitHours} ore e ${waitMinutes} minuti</strong><br><br>`;
                        waitMessage += `💡 <strong>Suggerimenti:</strong><br>`;
                        waitMessage += `• Usa il sistema di cache per riutilizzare codici esistenti<br>`;
                        waitMessage += `• Prova con un numero di telefono diverso<br>`;
                        waitMessage += `• Aspetta che scada il limite temporaneo`;
                        
                        showMessage(waitMessage, 'error');
                    } else {
                        showMessage(result.error, 'error');
                    }
                } else {
                    showMessage(result.error || 'Errore durante il login', 'error');
                }
            }
        });
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Login",
        subtitle="Accedi alla piattaforma",
        content=Markup(content)
    )

@app.route('/register')
def register():
    """Pagina di registrazione"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    content = """
    <h2>📝 Registrazione</h2>
    
    <div class="status info">
        ℹ️ Crea un nuovo account per accedere alla piattaforma
    </div>
    
    <form id="registerForm">
        <div class="form-group">
            <label for="phone_number">Numero di telefono</label>
            <input type="tel" id="phone_number" name="phone_number" required 
                   placeholder="+391234567890">
            <small>Formato internazionale (es. +391234567890)</small>
        </div>
        
        <div class="form-group">
            <label for="api_id">Telegram API ID</label>
            <input type="number" id="api_id" name="api_id" required 
                   placeholder="12345678">
            <small>Ottieni da <a href="https://my.telegram.org" target="_blank">my.telegram.org</a></small>
        </div>
        
        <div class="form-group">
            <label for="api_hash">Telegram API Hash</label>
            <input type="text" id="api_hash" name="api_hash" required 
                   placeholder="abcdef1234567890abcdef1234567890" maxlength="32">
            <small>Hash di 32 caratteri da my.telegram.org</small>
        </div>
        
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required 
                   placeholder="Scegli una password sicura" minlength="6">
            <small>Minimo 6 caratteri - per accedere alla piattaforma</small>
        </div>
        
        <div class="loading">
            <div class="spinner"></div>
            <p>Creazione account...</p>
        </div>
        
        <div class="form-actions">
            <button type="submit" class="btn success">✅ Registrati</button>
            <a href="/login" class="btn" style="background: #6c757d;">Hai già un account?</a>
        </div>
    </form>
    
    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            
            // Validazione client-side
            if (!data.phone_number || !data.api_id || !data.api_hash || !data.password) {
                showMessage('Compila tutti i campi richiesti', 'error');
                return;
            }
            
            if (data.api_hash.length !== 32) {
                showMessage('API Hash deve essere di 32 caratteri', 'error');
                return;
            }
            
            if (data.password.length < 6) {
                showMessage('Password deve essere di almeno 6 caratteri', 'error');
                return;
            }
            
            showLoading();
            
            const result = await makeRequest('/api/auth/register', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            
            hideLoading();
            
            if (result.success) {
                showMessage('Account creato con successo! Ora puoi accedere.', 'success');
                
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            } else {
                showMessage(result.error || 'Errore durante la registrazione', 'error');
            }
        });
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Registrazione",
        subtitle="Crea un nuovo account",
        content=Markup(content)
    )

@app.route('/verify-code')
def verify_code():
    """Pagina verifica codice Telegram"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    # Recupera numero di telefono dal localStorage (via JavaScript)
    content = """
    <h2>📱 Verifica codice Telegram</h2>
    
    <div class="status warning">
        ⏱️ Inserisci il codice ricevuto via Telegram
    </div>
    
    <form id="verifyForm">
        <div class="form-group">
            <label for="display_phone">Numero di telefono</label>
            <input type="text" id="display_phone" readonly 
                   style="background: #f8f9fa; border: 1px solid #dee2e6; color: #6c757d;">
            <small>Account per cui stai inserendo il codice</small>
        </div>
        
        <div class="form-group">
            <label for="code">Codice di verifica</label>
            <input type="text" id="code" name="code" required 
                   placeholder="12345" maxlength="5" style="text-align: center; font-size: 24px; letter-spacing: 5px;">
            <small>Codice a 5 cifre ricevuto via Telegram</small>
        </div>
        
        <div class="form-group" id="passwordGroup" style="display: none;">
            <label for="password">Password 2FA (se richiesta)</label>
            <input type="password" id="password" name="password" 
                   placeholder="Password per autenticazione a due fattori">
            <small>Solo se hai attivato l'autenticazione a due fattori</small>
        </div>
        
        <div class="loading">
            <div class="spinner"></div>
            <p>Verifica codice...</p>
        </div>
        
        <div class="form-actions">
            <button type="submit" class="btn success">✅ Verifica</button>
            <a href="/login" class="btn" style="background: #6c757d;">← Torna al login</a>
        </div>
    </form>
    
    <script>
        // Popola il numero di telefono dal localStorage
        const savedPhone = localStorage.getItem('temp_phone');
        if (savedPhone) {
            document.getElementById('display_phone').value = savedPhone;
        } else {
            // Se non c'è numero salvato, torna al login
            window.location.href = '/login';
        }
        
        document.getElementById('verifyForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const code = document.getElementById('code').value.trim();
            const password = document.getElementById('password').value.trim();
            const phone_number = localStorage.getItem('temp_phone');
            
            if (!code || !phone_number) {
                showMessage('Codice e numero di telefono richiesti', 'error');
                return;
            }
            
            showLoading();
            
            const result = await makeRequest('/api/auth/verify-code', {
                method: 'POST',
                body: JSON.stringify({ 
                    phone_number: phone_number, 
                    code: code,
                    password: password || undefined
                })
            });
            
            hideLoading();
            
            if (result.success) {
                // Salva session token
                localStorage.setItem('session_token', result.session_token);
                localStorage.removeItem('temp_user_id');
                localStorage.removeItem('temp_phone');
                
                showMessage('Login completato! Reindirizzamento...', 'success');
                
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } else {
                if (result.requires_2fa) {
                    document.getElementById('passwordGroup').style.display = 'block';
                    showMessage('Password 2FA richiesta', 'warning');
                } else {
                    showMessage(result.error || 'Codice non valido', 'error');
                }
            }
        });
        
        // Auto-focus e auto-submit
        document.getElementById('code').addEventListener('input', (e) => {
            if (e.target.value.length === 5) {
                // Auto submit quando il codice è completo
                setTimeout(() => {
                    document.getElementById('verifyForm').dispatchEvent(new Event('submit'));
                }, 500);
            }
        });
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Verifica Codice",
        subtitle="Attivazione sessione Telegram",
        content=Markup(content)
    )

# ============================================
# 🔒 PROTECTED ROUTES
# ============================================

@app.route('/dashboard')
@require_auth
def dashboard():
    """Dashboard principale (protetta)"""
    
    # Recupera info utente dal backend
    user_info = call_backend('/api/user/profile', 'GET', auth_token=session['session_token'])
    backend_info = call_backend('/health', 'GET')
    
    user_data = user_info.get('user', {}) if user_info and user_info.get('success') else {}
    
    # Use unified menu
    menu_html = get_unified_menu('dashboard')
    
    content = f"""
    {menu_html}
    
    <h2>📊 Dashboard</h2>
    
    <div class="status success">
        ✅ Benvenuto, <strong>{user_data.get('phone_number', 'Utente')}</strong>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>👤 Il tuo account</h3>
            <p><strong>Telefono:</strong> {user_data.get('phone_number', 'N/A')}</p>
            <p><strong>API ID:</strong> {user_data.get('api_id', 'N/A')}</p>
            <p><strong>Registrato:</strong> {user_data.get('created_at', 'N/A')[:10] if user_data.get('created_at') else 'N/A'}</p>
            <p><strong>Stato:</strong> {'✅ Attivo' if user_data.get('is_active') else '❌ Disattivo'}</p>
            <br>
            <a href="/profile" class="btn">📝 Gestisci Profilo</a>
        </div>
        
        <div class="card">
            <h3>💬 Le mie Chat</h3>
            <p>Visualizza tutte le tue chat Telegram con ID e dettagli</p>
            <br>
            <a href="/chats" class="btn">Vedi tutte le chat</a>
        </div>
        
        <div class="card">
            <h3>🔍 Trova Chat</h3>
            <p>Cerca l'ID di una chat Telegram inserendo username o nome</p>
            <br>
            <a href="/find" class="btn">Inizia ricerca</a>
        </div>
        
        <div class="card">
            <h3>🔧 Stato Sistema</h3>
            <p><strong>Backend:</strong> {'✅ Online' if backend_info and backend_info.get('status') == 'healthy' else '❌ Offline'}</p>
            <p><strong>Ambiente:</strong> <code>{ENVIRONMENT}</code></p>
            <p><strong>Sessione:</strong> ✅ Attiva</p>
        </div>
    </div>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Dashboard",
        subtitle="Pannello di controllo",
        content=Markup(content)
    )

@app.route('/profile')
@require_auth
def profile():
    """Pagina profilo utente (protetta)"""
    
    # Recupera info utente dal backend
    user_info = call_backend('/api/user/profile', 'GET', auth_token=session['session_token'])
    user_data = user_info.get('user', {}) if user_info and user_info.get('success') else {}
    
    # Use unified menu
    menu_html = get_unified_menu('profile')
    
    content = f"""
    {menu_html}
    
    <h2>👤 Gestione Profilo</h2>
    
    <div class="status info">
        ℹ️ Qui puoi visualizzare e modificare le tue informazioni e credenziali API
    </div>
    
    <div class="grid">
        <!-- Informazioni Account -->
        <div class="card">
            <h3>📱 Informazioni Account</h3>
            <p><strong>Telefono:</strong> {user_data.get('phone_number', 'N/A')}</p>
            <p><strong>ID Utente:</strong> {user_data.get('id', 'N/A')}</p>
            <p><strong>Registrato:</strong> {user_data.get('created_at', 'N/A')[:10] if user_data.get('created_at') else 'N/A'}</p>
            <p><strong>Ultimo login:</strong> {user_data.get('last_login', 'N/A')[:10] if user_data.get('last_login') else 'N/A'}</p>
            <p><strong>Stato account:</strong> {'✅ Attivo' if user_data.get('is_active') else '❌ Disattivo'}</p>
        </div>
        
        <!-- Credenziali API -->
        <div class="card">
            <h3>🔑 Credenziali API Telegram</h3>
            <p><strong>API ID:</strong> <span id="currentApiId">{user_data.get('api_id', 'N/A')}</span></p>
            <p><strong>API Hash:</strong> <span id="currentApiHash">{'•••••••••••' if user_data.get('api_id') else 'N/A'}</span></p>
            <br>
            <button onclick="showEditForm()" class="btn">✏️ Modifica Credenziali</button>
            <a href="https://my.telegram.org/apps" target="_blank" class="btn" style="margin-left: 10px; background: #27ae60;">🔗 Ottieni nuove API</a>
        </div>
    </div>
    
    <!-- Form di modifica (nascosto di default) -->
    <div id="editForm" style="display: none; margin-top: 30px;">
        <div class="card">
            <h3>✏️ Aggiorna Credenziali API</h3>
            
            <div class="status warning">
                ⚠️ <strong>Attenzione:</strong> Dopo aver aggiornato le credenziali dovrai rifare il login per usare le nuove API.
            </div>
            
            <form id="updateCredentialsForm">
                <div class="form-group">
                    <label for="newApiId">Nuovo API ID</label>
                    <input type="number" id="newApiId" name="api_id" required 
                           placeholder="Es: 12345678" value="{user_data.get('api_id', '')}">
                    <small>Numero intero fornito da my.telegram.org</small>
                </div>
                
                <div class="form-group">
                    <label for="newApiHash">Nuovo API Hash</label>
                    <input type="text" id="newApiHash" name="api_hash" required 
                           placeholder="Es: abcd1234efgh5678...">
                    <small>Stringa alfanumerica fornita da my.telegram.org</small>
                </div>
                
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Aggiornamento in corso...</p>
                </div>
                
                <div class="form-actions">
                    <button type="submit" class="btn success">💾 Salva Credenziali</button>
                    <button type="button" onclick="hideEditForm()" class="btn" style="margin-left: 10px;">❌ Annulla</button>
                </div>
            </form>
        </div>
    </div>
    
    <!-- Istruzioni -->
    <div class="card" style="margin-top: 30px;">
        <h3>📖 Come ottenere le credenziali API</h3>
        <ol style="margin-left: 20px; line-height: 1.6;">
            <li>Vai su <a href="https://my.telegram.org/apps" target="_blank" style="color: #3498db;">https://my.telegram.org/apps</a></li>
            <li>Fai login con il tuo account Telegram</li>
            <li>Crea una nuova applicazione o modifica quella esistente</li>
            <li>Copia l'<strong>API ID</strong> (numero) e l'<strong>API Hash</strong> (stringa)</li>
            <li>Incolla i valori nel form sopra e salva</li>
        </ol>
        
        <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 6px;">
            <strong>💡 Perché servono?</strong><br>
            Le credenziali API identificano la tua applicazione presso i server di Telegram e sono necessarie per accedere alle chat.
        </div>
    </div>
    
    <script>
        function showEditForm() {{
            document.getElementById('editForm').style.display = 'block';
            document.getElementById('newApiHash').focus();
        }}
        
        function hideEditForm() {{
            document.getElementById('editForm').style.display = 'none';
            document.getElementById('updateCredentialsForm').reset();
        }}
        
        document.getElementById('updateCredentialsForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const apiId = formData.get('api_id');
            const apiHash = formData.get('api_hash');
            
            if (!apiId || !apiHash) {{
                showMessage('Compila tutti i campi', 'error');
                return;
            }}
            
            if (!/^\d+$/.test(apiId)) {{
                showMessage('API ID deve essere un numero', 'error');
                return;
            }}
            
            if (!confirm('Sei sicuro di voler aggiornare le credenziali API? Dovrai rifare il login.')) {{
                return;
            }}
            
            showLoading();
            
            try {{
                const result = await makeRequest('/api/auth/update-credentials', {{
                    method: 'PUT',
                    body: JSON.stringify({{
                        api_id: parseInt(apiId),
                        api_hash: apiHash
                    }})
                }});
                
                hideLoading();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    
                    // Aggiorna i valori visualizzati
                    document.getElementById('currentApiId').textContent = result.api_id;
                    document.getElementById('currentApiHash').textContent = '•••••••••••';
                    
                    hideEditForm();
                    
                    // Opzionale: logout automatico
                    setTimeout(() => {{
                        if (confirm('Credenziali aggiornate! Vuoi effettuare il logout ora per rifare il login con le nuove credenziali?')) {{
                            logout();
                        }}
                    }}, 2000);
                    
                }} else {{
                    showMessage(result.error || 'Errore durante l\'aggiornamento', 'error');
                }}
                
            }} catch (error) {{
                hideLoading();
                showMessage('Errore di connessione', 'error');
            }}
        }});
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Profilo",
        subtitle="Gestione account e credenziali",
        content=Markup(content)
    )

@app.route('/chats')
@require_auth
def chats_list():
    """Pagina lista chat (protetta)"""
    
    # Use unified menu
    menu_html = get_unified_menu('chats')
    
    content = f"""
    {menu_html}
    
    <h2>💬 Le mie Chat Telegram</h2>
    
    <div class="status info">
        ℹ️ Tutte le tue chat con ID e dettagli - clicca sui bottoni per copiare
    </div>
    
    <div class="loading">
        <div class="spinner"></div>
        <p>Caricamento chat...</p>
    </div>
    
    <div id="chatsContainer" style="display: none;">
        <div style="margin-bottom: 30px; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px; background: #f8f9fa;">
            <h3>🔍 Filtra chat</h3>
            <div class="form-group">
                <input type="text" id="searchFilter" placeholder="Cerca per nome, ID o username..." 
                       style="width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 4px;">
                <small>Ricerca in tempo reale - prova "ROS" per trovare "Rossetto"</small>
            </div>
        </div>
        
        <div id="chatsList"></div>
    </div>
    
    <div id="errorContainer" style="display: none;">
        <div class="status error">
            <h3>❌ Errore</h3>
            <p id="errorMessage"></p>
        </div>
    </div>
    
    <script>
        let allChats = [];
        let filteredChats = [];
        
        // Carica le chat all'avvio
        document.addEventListener('DOMContentLoaded', loadChats);
        
        async function loadChats() {{
            showLoading();
            
            try {{
                const result = await makeRequest('/api/telegram/get-chats', {{
                    method: 'GET'
                }});
                
                hideLoading();
                
                if (result.success) {{
                    allChats = result.chats;
                    filteredChats = [...allChats];
                    
                    // Salva le chat in sessionStorage per la navigazione
                    sessionStorage.setItem('userChats', JSON.stringify(allChats));
                    
                    renderChats();
                    
                    document.getElementById('chatsContainer').style.display = 'block';
                    
                    // Setup filtro di ricerca
                    document.getElementById('searchFilter').addEventListener('input', filterChats);
                    
                }} else {{
                    // Controlla se è un errore di autorizzazione persa
                    if (result.error && result.error.includes('Authorization lost')) {{
                        showReactivationPrompt();
                    }} else {{
                        showError(result.error || 'Errore durante il caricamento chat');
                    }}
                }}
            }} catch (error) {{
                hideLoading();
                showError('Errore di connessione');
            }}
        }}
        
        function renderChats() {{
            const container = document.getElementById('chatsList');
            
            if (filteredChats.length === 0) {{
                container.innerHTML = `
                    <div class="status warning">
                        <p>🔍 Nessuna chat trovata con i criteri di ricerca</p>
                    </div>
                `;
                return;
            }}
            
            container.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <strong>📊 ${{filteredChats.length}} chat trovate (su ${{allChats.length}} totali)</strong>
                </div>
                
                ${{filteredChats.map(chat => `
                    <div class="card" style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: between; align-items: start;">
                            <div style="flex: 1;">
                                <h3>${{escapeHtml(chat.title)}} ${{getChatIcon(chat.type)}}</h3>
                                <p><strong>ID:</strong> 
                                    <code style="background: #e9ecef; padding: 2px 6px; border-radius: 3px; user-select: all;">${{chat.id}}</code>
                                    <button onclick="copyToClipboard('${{chat.id}}')" class="btn" style="margin-left: 10px; padding: 5px 10px; font-size: 12px;">📋 Copia ID</button>
                                </p>
                                <p><strong>Tipo:</strong> ${{getChatTypeLabel(chat.type)}}</p>
                                ${{chat.username ? `<p><strong>Username:</strong> @${{chat.username}} 
                                    <button onclick="copyToClipboard('@${{chat.username}}')" class="btn" style="margin-left: 10px; padding: 5px 10px; font-size: 12px;">📋 Copia @</button>
                                </p>` : ''}}
                                ${{chat.members_count ? `<p><strong>Membri:</strong> ${{chat.members_count}}</p>` : ''}}
                                ${{chat.description ? `<p><strong>Descrizione:</strong> ${{escapeHtml(chat.description.substring(0, 100))}}${{chat.description.length > 100 ? '...' : ''}}</p>` : ''}}
                                ${{chat.unread_count ? `<p><strong>Non letti:</strong> ${{chat.unread_count}} messaggi</p>` : ''}}
                                ${{chat.last_message_date ? `<p><strong>Ultimo messaggio:</strong> ${{new Date(chat.last_message_date).toLocaleDateString('it-IT')}}</p>` : ''}}
                                
                                <div style="margin-top: 15px;">
                                    <a href="/forwarders/${{chat.id}}" class="btn btn-primary">
                                        🔄 Vedi inoltri
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}}
            `;
        }}
        
        function filterChats() {{
            const query = document.getElementById('searchFilter').value.toLowerCase().trim();
            
            if (!query) {{
                filteredChats = [...allChats];
            }} else {{
                filteredChats = allChats.filter(chat => 
                    chat.title.toLowerCase().includes(query) ||
                    chat.id.toString().includes(query) ||
                    (chat.username && chat.username.toLowerCase().includes(query)) ||
                    (chat.description && chat.description.toLowerCase().includes(query))
                );
            }}
            
            renderChats();
        }}
        
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                showMessage(`Copiato: ${{text}}`, 'success');
            }}).catch(() => {{
                // Fallback per browser più vecchi
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showMessage(`Copiato: ${{text}}`, 'success');
            }});
        }}
        
        function getChatIcon(type) {{
            switch(type) {{
                case 'private': return '👤';
                case 'group': return '👥';
                case 'supergroup': return '👥';
                case 'channel': return '📢';
                default: return '💬';
            }}
        }}
        
        function getChatTypeLabel(type) {{
            switch(type) {{
                case 'private': return 'Chat privata';
                case 'group': return 'Gruppo';
                case 'supergroup': return 'Supergruppo';
                case 'channel': return 'Canale';
                default: return type;
            }}
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function showError(message) {{
            document.getElementById('errorMessage').textContent = message;
            document.getElementById('errorContainer').style.display = 'block';
            document.getElementById('chatsContainer').style.display = 'none';
        }}
        
        function showReactivationPrompt() {{
            document.getElementById('errorContainer').style.display = 'block';
            document.getElementById('errorMessage').innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <h3>🔐 Sessione Telegram scaduta</h3>
                    <p>La tua sessione Telegram è scaduta. Devi riattivarla per continuare.</p>
                    <br>
                    <a href="/dashboard" class="btn btn-primary">🔄 Riattiva Sessione</a>
                </div>
            `;
        }}
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Le mie Chat",
        subtitle="Gestione chat Telegram",
        content=Markup(content)
    )

@app.route('/find')
@require_auth
def find_chat():
    """Pagina ricerca chat (protetta)"""
    
    # Use unified menu
    menu_html = get_unified_menu('find')
    
    content = f"""
    {menu_html}
    
    <h2>🔍 Trova Chat Telegram</h2>
    
    <div class="status info">
        ℹ️ Inserisci il nome utente o il nome della chat per trovare l'ID
    </div>
    
    <form id="searchForm">
        <div class="form-group">
            <label for="query">Nome utente o nome chat</label>
            <input type="text" id="query" name="query" required 
                   placeholder="@username o nome della chat">
            <small>Usa @ per gli username o inserisci il nome completo del gruppo</small>
        </div>
        
        <div class="loading">
            <div class="spinner"></div>
            <p>Ricerca in corso...</p>
        </div>
        
        <div class="form-actions">
            <button type="submit" class="btn">🔍 Cerca Chat</button>
        </div>
    </form>
    
    <div id="result" style="margin-top: 30px;"></div>
    
    <script>
        document.getElementById('searchForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            
            const query = document.getElementById('query').value.trim();
            if (!query) {{
                showMessage('Inserisci una query di ricerca', 'error');
                return;
            }}
            
            showLoading();
            
            const result = await makeRequest('/api/telegram/find-chat', {{
                method: 'POST',
                body: JSON.stringify({{ query: query }})
            }});
            
            hideLoading();
            
            if (result.success) {{
                const chat = result.chat;
                document.getElementById('result').innerHTML = `
                    <div class="card">
                        <h3>✅ Chat trovata!</h3>
                        <p><strong>ID:</strong> <code>${{chat.id}}</code></p>
                        <p><strong>Titolo:</strong> ${{chat.title}}</p>
                        <p><strong>Tipo:</strong> ${{chat.type}}</p>
                        ${{chat.username ? `<p><strong>Username:</strong> @${{chat.username}}</p>` : ''}}
                        ${{chat.members_count ? `<p><strong>Membri:</strong> ${{chat.members_count}}</p>` : ''}}
                        <br>
                        <small>⚠️ Risultato MOCK per test - implementazione Telegram in corso</small>
                    </div>
                `;
                showMessage('Chat trovata con successo!', 'success');
            }} else {{
                document.getElementById('result').innerHTML = '';
                showMessage(result.error || 'Chat non trovata', 'error');
            }}
        }});
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Trova Chat",
        subtitle="Ricerca ID chat Telegram",
        content=Markup(content)
    )

@app.route('/configured-channels')
@require_auth
def configured_channels():
    """Pagina lista reindirizzamenti raggruppati per canale (protetta)"""
    
    # Use unified menu
    menu_html = get_unified_menu('configured-channels')
    
    content = f"""
    {menu_html}
    
    <h2>🔄 Tutti i Reindirizzamenti</h2>
    
    <div class="status info">
        ℹ️ Visualizzazione di tutti i reindirizzamenti raggruppati per canale di origine
    </div>
    
    <div class="loading">
        <div class="spinner"></div>
        <p>Caricamento reindirizzamenti...</p>
    </div>
    
    <div id="forwardersContainer" style="display: none;">
        <div id="forwardersList"></div>
    </div>
    
    <div id="errorContainer" style="display: none;">
        <div class="status error">
            <h3>❌ Errore</h3>
            <p id="errorMessage"></p>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', loadAllForwarders);
        
        async function loadAllForwarders() {{
            showLoading();
            
            try {{
                const result = await makeRequest('/api/forwarders/all', {{
                    method: 'GET'
                }});
                
                hideLoading();
                
                if (result.success) {{
                    renderAllForwarders(result.forwarders_by_channel);
                    document.getElementById('forwardersContainer').style.display = 'block';
                }} else {{
                    showError(result.error || 'Errore durante il caricamento reindirizzamenti');
                }}
            }} catch (error) {{
                hideLoading();
                showError('Errore di connessione');
            }}
        }}
        
        function renderAllForwarders(forwardersByChannel) {{
            const container = document.getElementById('forwardersList');
            
            if (!forwardersByChannel || Object.keys(forwardersByChannel).length === 0) {{
                container.innerHTML = `
                    <div class="status warning">
                        <h3>📭 Nessun reindirizzamento configurato</h3>
                        <p>Non ci sono reindirizzamenti attivi nel sistema.</p>
                        <p>Vai alla pagina <a href="/chats">Le mie Chat</a> per creare nuovi reindirizzamenti.</p>
                    </div>
                `;
                return;
            }}
            
            let totalForwarders = 0;
            Object.values(forwardersByChannel).forEach(channel => {{
                totalForwarders += channel.forwarders.length;
            }});
            
            container.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <strong>📊 ${{totalForwarders}} reindirizzamenti totali in ${{Object.keys(forwardersByChannel).length}} canali</strong>
                </div>
                
                ${{Object.entries(forwardersByChannel).map(([channelId, channelData]) => `
                    <div class="card" style="margin-bottom: 25px;">
                        <div style="border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 15px;">
                            <h3>${{getChatIcon(channelData.chat_type)}} ${{escapeHtml(channelData.chat_title)}}</h3>
                            <p style="margin: 5px 0; color: #6c757d;">
                                <strong>ID Canale:</strong> <code>${{channelId}}</code>
                                ${{channelData.chat_username ? `<strong>Username:</strong> @${{channelData.chat_username}}` : ''}}
                            </p>
                            <p style="margin: 5px 0; color: #28a745; font-weight: bold;">
                                📊 ${{channelData.forwarders.length}} reindirizzamenti attivi
                            </p>
                        </div>
                        
                        ${{channelData.forwarders.map(fwd => `
                            <div style="border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #f8f9fa;">
                                <div style="display: flex; justify-content: space-between; align-items: start;">
                                    <div style="flex: 1;">
                                        <h4>${{getTargetIcon(fwd.target_type)}} Inoltro verso: ${{escapeHtml(fwd.target_name || fwd.target_id)}}</h4>
                                        
                                        <div style="margin: 10px 0;">
                                            <p style="margin-bottom: 5px;"><strong>Container Docker:</strong></p>
                                            <code style="display: block; padding: 8px; background: #e9ecef; border-radius: 4px; font-size: 12px; word-break: break-all;">
                                                ${{fwd.container_name}}
                                            </code>
                                        </div>
                                        
                                        <p><strong>Tipo destinatario:</strong> ${{getTargetTypeLabel(fwd.target_type)}}</p>
                                        <p><strong>Stato:</strong> 
                                            <span class="badge" style="background: ${{fwd.is_running ? '#28a745' : '#dc3545'}}; color: white;">
                                                ${{fwd.is_running ? '🟢 ATTIVO' : '🔴 FERMO'}}
                                            </span>
                                        </p>
                                        <p><strong>Numero messaggi inoltrati:</strong> 
                                            <span style="font-weight: bold;">${{fwd.message_count || 0}} messaggi</span>
                                        </p>
                                        ${{fwd.last_message_at ? `<p><strong>Ultimo messaggio inoltrato:</strong> ${{new Date(fwd.last_message_at).toLocaleString('it-IT')}}</p>` : ''}}
                                        <p><strong>Data Creazione Inoltro:</strong> ${{new Date(fwd.created_at).toLocaleString('it-IT')}}</p>
                                        
                                        <div style="margin-top: 15px; padding: 10px; background: #f0f8ff; border-radius: 5px;">
                                            <h5 style="margin: 0 0 10px 0;">📊 Risorse Container</h5>
                                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                                <div>
                                                    <strong>RAM:</strong> ${{fwd.memory_usage_mb || 0}}MB / ${{fwd.memory_limit_mb || 256}}MB
                                                    <div style="background: #e0e0e0; height: 10px; border-radius: 5px; margin-top: 5px;">
                                                        <div style="background: ${{getResourceColor(fwd.memory_percent)}}; height: 100%; border-radius: 5px; width: ${{Math.min(fwd.memory_percent || 0, 100)}}%;"></div>
                                                    </div>
                                                    <small>${{(fwd.memory_percent || 0).toFixed(1)}}%</small>
                                                </div>
                                                <div>
                                                    <strong>CPU:</strong> ${{(fwd.cpu_percent || 0).toFixed(1)}}%
                                                    <div style="background: #e0e0e0; height: 10px; border-radius: 5px; margin-top: 5px;">
                                                        <div style="background: ${{getResourceColor(fwd.cpu_percent)}}; height: 100%; border-radius: 5px; width: ${{Math.min(fwd.cpu_percent || 0, 100)}}%;"></div>
                                                    </div>
                                                    <small>Max: 50% (0.5 core)</small>
                                                </div>
                                            </div>
                                            ${{fwd.restart_count > 0 ? `<p style="margin-top: 10px; color: #ff6b6b;"><strong>⚠️ Riavvii:</strong> ${{fwd.restart_count}}</p>` : ''}}
                                        </div>
                                    </div>
                                    
                                    <div style="display: flex; gap: 10px;">
                                        <button onclick="restartForwarder(${{fwd.id}})" class="btn btn-warning" title="Riavvia">
                                            🔄 Riavvia
                                        </button>
                                        <button onclick="deleteForwarder(${{fwd.id}})" class="btn btn-danger" title="Elimina">
                                            🗑️ Elimina
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `).join('')}}
                    </div>
                `).join('')}}
            `;
        }}
        
        async function restartForwarder(forwarderId) {{
            if (!confirm('Sei sicuro di voler riavviare questo reindirizzamento?')) {{
                return;
            }}
            
            try {{
                const result = await makeRequest(`/api/forwarders/${{forwarderId}}/restart`, {{
                    method: 'POST'
                }});
                
                if (result.success) {{
                    showMessage('Reindirizzamento riavviato con successo!', 'success');
                    // Ricarica la lista
                    loadAllForwarders();
                }} else {{
                    showMessage(result.error || 'Errore durante il riavvio', 'error');
                }}
            }} catch (error) {{
                showMessage('Errore di connessione', 'error');
            }}
        }}
        
        async function deleteForwarder(forwarderId) {{
            if (!confirm('Sei sicuro di voler eliminare questo reindirizzamento? Questa azione non può essere annullata.')) {{
                return;
            }}
            
            try {{
                const result = await makeRequest(`/api/forwarders/${{forwarderId}}`, {{
                    method: 'DELETE'
                }});
                
                if (result.success) {{
                    showMessage('Reindirizzamento eliminato con successo!', 'success');
                    // Ricarica la lista
                    loadAllForwarders();
                }} else {{
                    showMessage(result.error || 'Errore durante l\'eliminazione', 'error');
                }}
            }} catch (error) {{
                showMessage('Errore di connessione', 'error');
            }}
        }}
        
        function getChatIcon(type) {{
            switch(type) {{
                case 'private': return '👤';
                case 'group': return '👥';
                case 'supergroup': return '👥';
                case 'channel': return '📢';
                default: return '💬';
            }}
        }}
        
        function getTargetIcon(type) {{
            switch(type) {{
                case 'user': return '👤';
                case 'group': return '👥';
                case 'channel': return '📢';
                default: return '📍';
            }}
        }}
        
        function getTargetTypeLabel(type) {{
            switch(type) {{
                case 'user': return 'Persona/Bot';
                case 'group': return 'Gruppo';
                case 'channel': return 'Canale';
                default: return type;
            }}
        }}
        
        function getResourceColor(percent) {{
            if (percent < 50) return '#4CAF50';  // Verde
            if (percent < 75) return '#FFC107';  // Giallo
            if (percent < 90) return '#FF9800';  // Arancione
            return '#F44336';  // Rosso
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function showError(message) {{
            document.getElementById('errorMessage').textContent = message;
            document.getElementById('errorContainer').style.display = 'block';
            document.getElementById('forwardersContainer').style.display = 'none';
        }}
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Tutti i Reindirizzamenti",
        subtitle="Gestione reindirizzamenti per canale",
        content=Markup(content)
    )

@app.route('/forwarders/<source_chat_id>')
@require_auth
def forwarders_page(source_chat_id):
    """Pagina gestione inoltri per una specifica chat"""
    
    # Use unified menu
    menu_html = get_unified_menu('forwarders')
    
    # Recupera info sulla chat dalla sessione o chiamata API
    content = f"""
    {menu_html}
    
    <h2>🔄 Gestione Inoltri</h2>
    <p><a href="/chats">← Torna alla lista chat</a></p>
    
    <div class="card" style="margin-bottom: 20px;">
        <h3 id="chatTitle">Caricamento...</h3>
        <p><strong>ID Chat:</strong> <code>{source_chat_id}</code></p>
    </div>
    
    <div class="loading" id="mainLoading">
        <div class="spinner"></div>
        <p>Caricamento inoltri...</p>
    </div>
    
    <div id="forwardersContainer" style="display: none;">
        <div style="margin-bottom: 20px;">
            <button onclick="showNewForwarderForm()" class="btn btn-success">
                ➕ Inserisci nuovo inoltro
            </button>
            <button onclick="cleanupOrphanedForwarders()" class="btn btn-warning" style="margin-left: 10px;">
                🧹 Pulisci inoltri orfani
            </button>
        </div>
        
        <div id="newForwarderForm" style="display: none; margin-bottom: 20px;" class="card">
            <h3>➕ Nuovo Inoltro</h3>
            <form onsubmit="createForwarder(event)">
                <div class="form-group">
                    <label>Tipo destinazione</label>
                    <select id="targetType" name="targetType" required onchange="updateTargetPlaceholder()">
                        <option value="">Seleziona...</option>
                        <option value="user">👤 Utente</option>
                        <option value="group">👥 Gruppo</option>
                        <option value="channel">📢 Canale</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="targetId">ID o Username destinazione</label>
                    <input type="text" id="targetId" name="targetId" required 
                           placeholder="Seleziona prima il tipo">
                    <small id="targetHelp">Inserisci l'username (@username) o l'ID numerico</small>
                </div>
                
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">✅ Crea inoltro</button>
                    <button type="button" onclick="hideNewForwarderForm()" class="btn">❌ Annulla</button>
                </div>
            </form>
        </div>
        
        <div id="forwardersList"></div>
    </div>
    
    <div id="errorContainer" style="display: none;">
        <div class="status error">
            <h3>❌ Errore</h3>
            <p id="errorMessage"></p>
        </div>
    </div>
    
    <script>
        const sourceChatId = '{source_chat_id}';
        let chatInfo = null;
        let forwarders = [];
        
        document.addEventListener('DOMContentLoaded', () => {{
            console.log('=== FORWARDERS PAGE DEBUG START ===');
            console.log('DOMContentLoaded fired for source_chat_id:', sourceChatId);
            console.log('Current URL:', window.location.href);
            console.log('Auth token in localStorage:', localStorage.getItem('session_token') ? 'PRESENT' : 'MISSING');
            console.log('Starting loadChatInfo...');
            loadChatInfo();
            console.log('Starting loadForwarders...');
            loadForwarders();
        }});
        
        async function loadChatInfo() {{
            console.log('loadChatInfo() - Starting...');
            // Carica info chat dalla lista precedente se disponibile
            const cachedChats = sessionStorage.getItem('userChats');
            console.log('loadChatInfo() - Cached chats:', cachedChats ? 'found' : 'not found');
            if (cachedChats) {{
                const chats = JSON.parse(cachedChats);
                console.log('loadChatInfo() - Parsed chats count:', chats.length);
                chatInfo = chats.find(c => c.id.toString() === sourceChatId);
                console.log('loadChatInfo() - Found chat info:', chatInfo ? 'YES' : 'NO');
                if (chatInfo) {{
                    console.log('loadChatInfo() - Chat title:', chatInfo.title);
                    document.getElementById('chatTitle').innerHTML = `
                        ${{getChatIcon(chatInfo.type)}} ${{escapeHtml(chatInfo.title)}}
                        ${{chatInfo.username ? `<small style="color: #6c757d; margin-left: 10px;">@${{chatInfo.username}}</small>` : ''}}
                    `;
                }}
            }}
            console.log('loadChatInfo() - Completed');
        }}
        
        async function loadForwarders() {{
            console.log('loadForwarders() - Starting for chat:', sourceChatId);
            console.log('loadForwarders() - Auth token check:', localStorage.getItem('session_token') ? 'PRESENT' : 'MISSING');
            
            // Controlla se elementi DOM esistono
            const loadingEl = document.getElementById('mainLoading');
            const containerEl = document.getElementById('forwardersContainer');
            const errorEl = document.getElementById('errorContainer');
            console.log('loadForwarders() - DOM elements check:');
            console.log('  - mainLoading:', loadingEl ? 'FOUND' : 'MISSING');
            console.log('  - forwardersContainer:', containerEl ? 'FOUND' : 'MISSING');
            console.log('  - errorContainer:', errorEl ? 'FOUND' : 'MISSING');
            
            try {{
                const apiUrl = '/api/forwarders/' + sourceChatId;
                console.log('loadForwarders() - Making request to:', apiUrl);
                
                const result = await makeRequest(apiUrl, {{
                    method: 'GET'
                }});
                
                console.log('loadForwarders() - API response:', result);
                
                // Nascondi loading
                console.log('loadForwarders() - Hiding loading...');
                hideLoading();
                
                if (result && result.success) {{
                    forwarders = result.forwarders || [];
                    console.log('loadForwarders() - Forwarders loaded successfully, count:', forwarders.length);
                    console.log('loadForwarders() - Calling renderForwarders()...');
                    renderForwarders();
                    console.log('loadForwarders() - Showing forwarders container...');
                    document.getElementById('forwardersContainer').style.display = 'block';
                    
                    // Aggiorna contatori periodicamente
                    console.log('loadForwarders() - Setting up periodic update interval...');
                    setInterval(updateMessageCounts, 30000); // ogni 30 secondi
                    console.log('loadForwarders() - SUCCESS COMPLETED');
                }} else {{
                    console.error('loadForwarders() - API error:', result ? result.error : 'No result');
                    const errorMsg = (result && result.error) || 'Errore durante il caricamento inoltri';
                    console.log('loadForwarders() - Showing error:', errorMsg);
                    showError(errorMsg);
                }}
            }} catch (error) {{
                console.error('loadForwarders() - Exception caught:', error);
                console.error('loadForwarders() - Exception stack:', error.stack);
                hideLoading();
                showError('Errore di connessione');
                console.log('loadForwarders() - ERROR COMPLETED');
            }}
        }}
        
        function renderForwarders() {{
            console.log('renderForwarders() - Starting with', forwarders.length, 'forwarders');
            const container = document.getElementById('forwardersList');
            console.log('renderForwarders() - Container element:', container ? 'FOUND' : 'MISSING');
            
            if (forwarders.length === 0) {{
                console.log('renderForwarders() - No forwarders, showing empty state');
                container.innerHTML = `
                    <div class="status info">
                        <p>📭 Nessun inoltro configurato per questa chat</p>
                        <p>Clicca su "Inserisci nuovo inoltro" per iniziare</p>
                    </div>
                `;
                console.log('renderForwarders() - Empty state HTML set');
                return;
            }}
            
            console.log('renderForwarders() - Generating HTML for', forwarders.length, 'forwarders');
            container.innerHTML = `
                <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                    <strong>📊 ${{forwarders.length}} inoltri attivi</strong>
                    <small style="color: #6c757d;">
                        <span class="spinner-border spinner-border-sm" style="width: 12px; height: 12px; border-width: 2px;"></span>
                        Aggiornamento automatico ogni 30 secondi
                    </small>
                </div>
                
                ${{forwarders.map(fwd => `
                    <div class="card" style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h4>${{getTargetIcon(fwd.target_type)}} Inoltro verso: ${{escapeHtml(fwd.target_name || fwd.target_id)}}</h4>
                                
                                <div style="margin: 10px 0;">
                                    <p style="margin-bottom: 5px;"><strong>Container Docker:</strong></p>
                                    <code style="display: block; padding: 8px; background: #e9ecef; border-radius: 4px; font-size: 12px; word-break: break-all;">
                                        ${{fwd.container_name}}
                                    </code>
                                </div>
                                
                                <p><strong>Tipo destinatario:</strong> ${{getTargetTypeLabel(fwd.target_type)}}</p>
                                <p><strong>Numero messaggi inoltrati:</strong> 
                                    <span id="msgCount_${{fwd.id}}" style="font-weight: bold;">${{fwd.message_count || 0}} messaggi</span>
                                </p>
                                ${{fwd.last_message_at ? `<p><strong>Ultimo messaggio inoltrato:</strong> ${{new Date(fwd.last_message_at).toLocaleString('it-IT')}}</p>` : ''}}
                                <p><strong>Data Creazione Inoltro:</strong> ${{new Date(fwd.created_at).toLocaleString('it-IT')}}</p>
                                
                                <div style="margin-top: 15px; padding: 10px; background: #f0f8ff; border-radius: 5px;">
                                    <h5 style="margin: 0 0 10px 0;">📊 Risorse Container</h5>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                        <div>
                                            <strong>RAM:</strong> ${{fwd.memory_usage_mb || 0}}MB / ${{fwd.memory_limit_mb || 256}}MB
                                            <div style="background: #e0e0e0; height: 10px; border-radius: 5px; margin-top: 5px;">
                                                <div style="background: ${{getResourceColor(fwd.memory_percent)}}; height: 100%; border-radius: 5px; width: ${{Math.min(fwd.memory_percent || 0, 100)}}%;"></div>
                                            </div>
                                            <small>${{(fwd.memory_percent || 0).toFixed(1)}}%</small>
                                        </div>
                                        <div>
                                            <strong>CPU:</strong> ${{(fwd.cpu_percent || 0).toFixed(1)}}%
                                            <div style="background: #e0e0e0; height: 10px; border-radius: 5px; margin-top: 5px;">
                                                <div style="background: ${{getResourceColor(fwd.cpu_percent)}}; height: 100%; border-radius: 5px; width: ${{Math.min(fwd.cpu_percent || 0, 100)}}%;"></div>
                                            </div>
                                            <small>Max: 50% (0.5 core)</small>
                                        </div>
                                    </div>
                                    ${{fwd.restart_count > 0 ? `<p style="margin-top: 10px; color: #ff6b6b;"><strong>⚠️ Riavvii:</strong> ${{fwd.restart_count}}</p>` : ''}}
                                </div>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <button onclick="restartForwarder(${{fwd.id}})" class="btn btn-warning" title="Riavvia">
                                    🔄 Riavvia
                                </button>
                                <button onclick="deleteForwarder(${{fwd.id}})" class="btn btn-danger" title="Elimina">
                                    🗑️ Elimina
                                </button>
                            </div>
                        </div>
                    </div>
                `).join('')}}
            `;
            console.log('renderForwarders() - HTML generated and set to container');
            console.log('renderForwarders() - COMPLETED');
        }}
        
        function showNewForwarderForm() {{
            document.getElementById('newForwarderForm').style.display = 'block';
            document.getElementById('targetType').focus();
        }}
        
        function hideNewForwarderForm() {{
            document.getElementById('newForwarderForm').style.display = 'none';
            document.getElementById('targetType').value = '';
            document.getElementById('targetId').value = '';
        }}
        
        function updateTargetPlaceholder() {{
            const type = document.getElementById('targetType').value;
            const input = document.getElementById('targetId');
            const help = document.getElementById('targetHelp');
            
            switch(type) {{
                case 'user':
                    input.placeholder = '@username o ID utente';
                    help.textContent = 'Es: @mario123 o 123456789';
                    break;
                case 'group':
                    input.placeholder = 'ID del gruppo';
                    help.textContent = 'Es: -1001234567890';
                    break;
                case 'channel':
                    input.placeholder = 'ID del canale';
                    help.textContent = 'Es: -1001234567890';
                    break;
                default:
                    input.placeholder = 'Seleziona prima il tipo';
                    help.textContent = 'Inserisci l\\\'username (@username) o l\\\'ID numerico';
            }}
        }}
        
        async function createForwarder(event) {{
            event.preventDefault();
            
            const targetType = document.getElementById('targetType').value;
            const targetId = document.getElementById('targetId').value.trim();
            
            if (!targetType || !targetId) {{
                showMessage('Compila tutti i campi', 'error');
                return;
            }}
            
            // Store form data for later use
            window.pendingForwarder = {{
                targetType: targetType,
                targetId: targetId
            }};
            
            // Direct creation - the backend will handle session checking
            showMessage('Creazione inoltro...', 'info');
            
            try {{
                const result = await makeRequest('/api/forwarders', {{
                    method: 'POST',
                    body: JSON.stringify({{
                        source_chat_id: sourceChatId,
                        source_chat_title: chatInfo ? chatInfo.title : 'Chat ' + sourceChatId,
                        target_type: targetType,
                        target_id: targetId
                    }})
                }});
                
                console.log('createForwarder response:', result);
                
                if (result.success) {{
                    if (result.code_sent) {{
                        // Backend sent verification code
                        showMessage(`📱 Codice di verifica inviato a ${{result.phone}}`, 'info');
                        showCodeVerificationDialog();
                    }} else {{
                        // Forwarder created successfully
                        const containerName = result.container_name || 'N/A';
                        const forwarderId = result.forwarder_id || 'N/A';
                        
                        showMessage(`✅ Inoltro creato con successo!<br>
                            <strong>Container:</strong> ${{containerName}}<br>
                            <strong>ID Inoltro:</strong> ${{forwarderId}}`, 'success');
                        
                        // Clear pending data
                        delete window.pendingForwarder;
                        
                        // Hide form and reload list
                        setTimeout(() => {{
                            hideNewForwarderForm();
                        }}, 2000);
                        
                        setTimeout(async () => {{
                            await loadForwarders();
                        }}, 2500);
                    }}
                }} else {{
                    showMessage(`❌ Errore: ${{result.error}}`, 'error');
                }}
            }} catch (error) {{
                console.error('createForwarder error:', error);
                showMessage(`❌ Errore: ${{error.message}}`, 'error');
            }}
        }}
        
        function showCodeVerificationDialog() {{
            // Create modal for code input
            const modal = document.createElement('div');
            modal.innerHTML = `
                <div class="modal" style="display: block; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
                    <div class="modal-content" style="position: relative; top: 50%; transform: translateY(-50%); margin: 0 auto; width: 90%; max-width: 400px; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h3 style="margin-bottom: 15px;">🔐 Verifica Sessione Forwarder</h3>
                        <p style="margin-bottom: 15px;">Inserisci il codice di verifica che hai ricevuto su Telegram:</p>
                        <input type="text" id="verificationCode" placeholder="Codice (es: 12345)" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 15px;">
                        <div style="display: flex; gap: 10px;">
                            <button onclick="verifyForwarderCode()" class="btn btn-primary" style="flex: 1;">✅ Verifica</button>
                            <button onclick="cancelVerification()" class="btn btn-secondary" style="flex: 1;">❌ Annulla</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            document.getElementById('verificationCode').focus();
        }}
        
        window.verifyForwarderCode = async function() {{
            const code = document.getElementById('verificationCode').value.trim();
            if (!code) {{
                showMessage('Inserisci il codice', 'error');
                return;
            }}
            
            const forwarderData = window.pendingForwarder;
            if (!forwarderData) {{
                showMessage('Dati forwarder persi', 'error');
                return;
            }}
            
            showMessage('Verifica codice e creazione container...', 'info');
            
            try {{
                // Resend the creation request with the code
                const result = await makeRequest('/api/forwarders', {{
                    method: 'POST',
                    body: JSON.stringify({{
                        source_chat_id: sourceChatId,
                        source_chat_title: chatInfo ? chatInfo.title : 'Chat ' + sourceChatId,
                        target_type: forwarderData.targetType,
                        target_id: forwarderData.targetId,
                        code: code  // Include the verification code
                    }})
                }});
                
                if (result.success) {{
                    // Remove modal
                    document.querySelector('.modal').remove();
                    
                    const containerName = result.container_name || 'N/A';
                    const forwarderId = result.forwarder_id || 'N/A';
                    
                    showMessage(`✅ Inoltro creato con successo!<br>
                        <strong>Container:</strong> ${{containerName}}<br>
                        <strong>ID Inoltro:</strong> ${{forwarderId}}`, 'success');
                    
                    // Clear pending data
                    delete window.pendingForwarder;
                    
                    // Hide form and reload list
                    setTimeout(() => {{
                        hideNewForwarderForm();
                    }}, 2000);
                    
                    setTimeout(async () => {{
                        await loadForwarders();
                    }}, 2500);
                }} else {{
                    showMessage(`❌ Errore: ${{result.error}}`, 'error');
                }}
            }} catch (error) {{
                console.error('verifyCode error:', error);
                showMessage(`❌ Errore verifica: ${{error.message}}`, 'error');
            }}
        }}
        
        window.cancelVerification = function() {{
            document.querySelector('.modal').remove();
            showMessage('Operazione annullata', 'warning');
        }}

        
        async function restartForwarder(forwarderId) {{
            if (!confirm('Sei sicuro di voler riavviare questo inoltro?')) {{
                return;
            }}
            
            showMessage('Riavvio in corso...', 'info');
            
            try {{
                const result = await makeRequest(`/api/forwarders/${{forwarderId}}/restart`, {{
                    method: 'POST'
                }});
                
                if (result.success) {{
                    showMessage('Inoltro riavviato con successo!', 'success');
                    await loadForwarders(); // Ricarica lista
                }} else {{
                    showMessage(result.error || 'Errore durante il riavvio', 'error');
                }}
            }} catch (error) {{
                showMessage('Errore di connessione', 'error');
            }}
        }}
        
        async function deleteForwarder(forwarderId) {{
            if (!confirm('Sei sicuro di voler eliminare questo inoltro? L\\\'azione non può essere annullata.')) {{
                return;
            }}
            
            showMessage('Eliminazione in corso...', 'info');
            
            try {{
                const result = await makeRequest(`/api/forwarders/${{forwarderId}}`, {{
                    method: 'DELETE'
                }});
                
                if (result.success) {{
                    // Show success message with container info if available
                    let message = 'Inoltro eliminato con successo!';
                    if (result.container_message) {{
                        message += ` (Container: ${{result.container_message}})`; 
                    }}
                    showMessage(message, 'success');
                    
                    // Rimuovi immediatamente l'elemento dall'array locale
                    forwarders = forwarders.filter(fwd => fwd.id !== forwarderId);
                    
                    // Aggiorna immediatamente la UI
                    renderForwarders();
                    
                    // Ricarica la lista dal server dopo un breve delay per sicurezza
                    setTimeout(async () => {{
                        await loadForwarders();
                    }}, 1000);
                }} else {{
                    showMessage(result.error || 'Errore durante l\\\'eliminazione', 'error');
                }}
            }} catch (error) {{
                console.error('Delete forwarder error:', error);
                showMessage('Errore di connessione durante l\\\'eliminazione', 'error');
            }}
        }}
        
        async function cleanupOrphanedForwarders() {{
            if (!confirm('Vuoi pulire gli inoltri orfani (quelli senza container)? Questa operazione rimuoverà gli inoltri che non hanno più un container associato.')) {{
                return;
            }}
            
            showMessage('Pulizia inoltri orfani in corso...', 'info');
            
            try {{
                const result = await makeRequest('/api/forwarders/cleanup-orphaned', {{
                    method: 'POST'
                }});
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    
                    // Ricarica la lista per mostrare i cambiamenti
                    setTimeout(async () => {{
                        await loadForwarders();
                    }}, 1000);
                }} else {{
                    showMessage(result.error || 'Errore durante la pulizia', 'error');
                }}
            }} catch (error) {{
                console.error('Cleanup error:', error);
                showMessage('Errore di connessione durante la pulizia', 'error');
            }}
        }}
        
        async function updateMessageCounts() {{
            // Aggiorna solo i contatori senza ricaricare tutta la lista
            try {{
                const result = await makeRequest('/api/forwarders/' + sourceChatId, {{
                    method: 'GET'
                }});
                
                if (result.success) {{
                    result.forwarders.forEach(fwd => {{
                        const countEl = document.getElementById(`msgCount_${{fwd.id}}`);
                        if (countEl) {{
                            countEl.textContent = fwd.message_count || 0;
                        }}
                    }});
                }}
            }} catch (error) {{
                // Ignora errori nell'aggiornamento automatico
            }}
        }}
        
        function getChatIcon(type) {{
            switch(type) {{
                case 'private': return '👤';
                case 'group': return '👥';
                case 'supergroup': return '👥';
                case 'channel': return '📢';
                default: return '💬';
            }}
        }}
        
        function getTargetIcon(type) {{
            switch(type) {{
                case 'user': return '👤';
                case 'group': return '👥';
                case 'channel': return '📢';
                default: return '📍';
            }}
        }}
        
        function getTargetTypeLabel(type) {{
            switch(type) {{
                case 'user': return 'Persona/Bot';
                case 'group': return 'Gruppo';
                case 'channel': return 'Canale';
                default: return type;
            }}
        }}
        
        function getResourceColor(percent) {{
            if (percent < 50) return '#4CAF50';  // Verde
            if (percent < 75) return '#FFC107';  // Giallo
            if (percent < 90) return '#FF9800';  // Arancione
            return '#F44336';  // Rosso
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function showError(message) {{
            document.getElementById('errorMessage').textContent = message;
            document.getElementById('errorContainer').style.display = 'block';
            document.getElementById('forwardersContainer').style.display = 'none';
        }}
        
        function showMessage(message, type = 'info') {{
            // Crea un div temporaneo per i messaggi
            const statusDiv = document.createElement('div');
            statusDiv.className = `status ${{type}}`;
            statusDiv.innerHTML = message;
            
            // Aggiunge il messaggio all'inizio del container principale
            const container = document.querySelector('.content') || document.body;
            container.insertBefore(statusDiv, container.firstChild);
            
            // Removed auto-removal - messages will stay until page reload
        }}
        
        function hideLoading() {{
            document.getElementById('mainLoading').style.display = 'none';
        }}
        

    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Gestione Inoltri",
        subtitle=f"Chat ID: {source_chat_id}",
        content=Markup(content)
    )

# ============================================
# 🌐 API ENDPOINTS
# ============================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Proxy per login backend"""
    data = request.get_json()
    result = call_backend('/api/auth/login', 'POST', data)
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Proxy per registrazione backend"""
    data = request.get_json()
    result = call_backend('/api/auth/register', 'POST', data)
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/auth/verify-code', methods=['POST'])
def api_verify_code():
    """Proxy per verifica codice backend"""
    data = request.get_json()
    result = call_backend('/api/auth/verify-code', 'POST', data)
    
    if result and result.get('success'):
        # Salva session token in Flask session
        session['session_token'] = result['access_token']
        session['user_id'] = result['user']['id']
        
        # Aggiungi session_token per il JavaScript
        result['session_token'] = result['access_token']
    
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Proxy per logout con pulizia sessione"""
    try:
        # Chiama il backend per logout
        result = call_backend('/api/auth/logout', 'POST', request.get_json())
        
        # Pulisci la sessione Flask
        session.clear()
        
        logger.info("🔐 [LOGOUT] Sessione pulita con successo")
        
        return jsonify({
            'success': True,
            'message': 'Logout completato con successo',
            'redirect': '/login'
        })
    except Exception as e:
        logger.error(f"🔐 [LOGOUT] Errore durante logout: {e}")
        # Pulisci comunque la sessione anche in caso di errore
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Logout completato',
            'redirect': '/login'
        })

@app.route('/api/telegram/get-chats', methods=['GET'])
def api_get_chats():
    """Proxy per recupero chat backend"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend('/api/user/chats', 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/telegram/find-chat', methods=['POST'])
def api_find_chat():
    """Proxy per ricerca chat backend"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/telegram/find-chat', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/auth/update-credentials', methods=['PUT'])
def api_update_credentials():
    """Proxy per aggiornamento credenziali backend"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/auth/update-credentials', 'PUT', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/telegram/get-configured-channels', methods=['GET'])
def api_get_configured_channels():
    """Proxy per recupero canali configurati backend"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend('/api/telegram/get-configured-channels', 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/telegram/channel-action', methods=['POST'])
def api_channel_action():
    """Proxy per azioni sui canali configurati backend"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/telegram/channel-action', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/forwarders/<source_chat_id>', methods=['GET'])
def api_get_forwarders(source_chat_id):
    """Proxy per recupero inoltri di una chat"""
    logger.info(f"🔍 [API] GET /api/forwarders/{source_chat_id} - Request received")
    logger.info(f"🔍 [API] User authenticated: {is_authenticated()}")
    logger.info(f"🔍 [API] Session token present: {'session_token' in session}")
    
    if not is_authenticated():
        logger.warning(f"🔍 [API] GET /api/forwarders/{source_chat_id} - Authentication failed")
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    logger.info(f"🔍 [API] Calling backend: /api/forwarders/{source_chat_id}")
    result = call_backend(f'/api/forwarders/{source_chat_id}', 'GET', auth_token=session['session_token'])
    logger.info(f"🔍 [API] Backend response: {result}")
    
    final_result = result or {'error': 'Backend non disponibile'}
    logger.info(f"🔍 [API] Final response: {final_result}")
    return jsonify(final_result)

@app.route('/api/forwarders', methods=['POST'])
def api_create_forwarder():
    """Proxy per creazione nuovo inoltro"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/forwarders', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/forwarders/<int:forwarder_id>/restart', methods=['POST'])
def api_restart_forwarder(forwarder_id):
    """Proxy per riavvio inoltro"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/forwarders/{forwarder_id}/restart', 'POST', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/forwarders/<int:forwarder_id>', methods=['DELETE'])
def api_delete_forwarder(forwarder_id):
    """Proxy per eliminazione inoltro"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/forwarders/{forwarder_id}', 'DELETE', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/forwarders/cleanup-orphaned', methods=['POST'])
def api_cleanup_orphaned_forwarders():
    """Proxy per pulizia inoltri orfani"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend('/api/forwarders/cleanup-orphaned', 'POST', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/auth/check-future-tokens', methods=['GET'])
def api_check_future_tokens():
    """Proxy per controllare future auth tokens"""
    return call_backend('/api/auth/check-future-tokens', 'GET')

@app.route('/api/auth/clear-future-tokens', methods=['POST'])
def api_clear_future_tokens():
    """Proxy per cancellare future auth tokens"""
    return call_backend('/api/auth/clear-future-tokens', 'POST', request.get_json())

@app.route('/api/forwarders/all', methods=['GET'])
def api_get_all_forwarders():
    """Proxy per recupero di tutti i reindirizzamenti raggruppati per canale"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend('/api/forwarders/all', 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

# ============================================
# 🏥 HEALTH & UTILS
# ============================================

@app.route('/health')
def health():
    """Health check endpoint"""
    backend_status = call_backend('/health')
    
    return jsonify({
        'status': 'healthy',
        'frontend': 'ok',
        'backend': 'ok' if backend_status else 'error',
        'timestamp': datetime.now().isoformat(),
        'environment': ENVIRONMENT,
        'authenticated': is_authenticated()
    })

@app.errorhandler(404)
def not_found(error):
    """Gestione errori 404"""
    content = """
    <h2>❌ Pagina non trovata</h2>
    
    <div class="status error">
        La pagina richiesta non esiste o è stata spostata.
    </div>
    
    <div class="card">
        <h3>🧭 Navigazione</h3>
        <p>Puoi tornare alla homepage o usare uno dei link qui sotto:</p>
        <br>
        <a href="/" class="btn">🏠 Homepage</a>
        <a href="/login" class="btn" style="margin-left: 10px;">🔐 Login</a>
    </div>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Pagina non trovata",
        subtitle="Errore 404",
        content=Markup(content)
    ), 404

# ========================================================================================
# LEGACY PROXIES (DEPRECATED)
# ========================================================================================

@app.route('/api/auth/check-cached-code', methods=['GET'])
def api_check_cached_code():
    """Proxy deprecato per controllare codice in cache"""
    return call_backend('/api/auth/check-cached-code', 'GET')

@app.route('/api/auth/use-cached-code', methods=['POST'])
def api_use_cached_code():
    """Proxy deprecato per usare codice in cache"""
    return call_backend('/api/auth/use-cached-code', 'POST', request.get_json())

@app.route('/api/auth/clear-cached-code', methods=['POST'])
def api_clear_cached_code():
    """Proxy deprecato per cancellare codice in cache"""
    return call_backend('/api/auth/clear-cached-code', 'POST', request.get_json())

@app.route('/api/auth/rotate-credentials', methods=['POST'])
def api_rotate_credentials():
    """Proxy per rotazione credenziali"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/auth/rotate-credentials', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/auth/check-credentials-status', methods=['GET'])
def api_check_credentials_status():
    """Proxy per controllo stato credenziali"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend('/api/auth/check-credentials-status', 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

# ========================================================================================
# EXISTING API PROXIES
# ========================================================================================

@app.route('/security')
@require_auth
def security_page():
    """Pagina sicurezza e gestione credenziali"""
    
    # Use unified menu
    menu_html = get_unified_menu('security')
    
    content = f"""
    {menu_html}
    
    <h2>🔐 Sicurezza Account</h2>
    
    <div class="card">
        <h3>📊 Stato Sicurezza</h3>
        <div id="securityStatus" class="loading">
            <div class="spinner"></div>
            <p>Controllo stato sicurezza...</p>
        </div>
    </div>
    
    <div class="card" style="margin-top: 20px;">
        <h3>🔄 Rotazione Credenziali</h3>
        <div class="status warning">
            <p><strong>⚠️ Attenzione:</strong> La rotazione delle credenziali fermerà tutti i reindirizzamenti attivi.</p>
            <p>Dovrai ricreare tutti i forwarder dopo aver aggiornato le credenziali.</p>
        </div>
        
        <form id="rotateCredentialsForm" onsubmit="rotateCredentials(event)" style="margin-top: 20px;">
            <div class="form-group">
                <label for="newApiId">Nuovo API ID</label>
                <input type="text" id="newApiId" name="newApiId" required 
                       placeholder="Es: 12345678" pattern="[0-9]+" 
                       title="Solo numeri">
            </div>
            
            <div class="form-group">
                <label for="newApiHash">Nuovo API Hash</label>
                <input type="text" id="newApiHash" name="newApiHash" required 
                       placeholder="Es: a1b2c3d4e5f6..." pattern="[a-f0-9]{{32}}"
                       title="32 caratteri esadecimali">
            </div>
            
            <button type="submit" class="btn btn-danger">
                🔄 Ruota Credenziali
            </button>
        </form>
    </div>
    
    <div class="card" style="margin-top: 20px;">
        <h3>📚 Best Practices di Sicurezza</h3>
        <ul>
            <li>Ruota le credenziali API ogni 3 mesi</li>
            <li>Non condividere mai le tue credenziali API</li>
            <li>Usa password complesse per il tuo account</li>
            <li>Monitora regolarmente i container per attività sospette</li>
            <li>Rimuovi i forwarder non più utilizzati</li>
        </ul>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', checkSecurityStatus);
        
        async function checkSecurityStatus() {{
            try {{
                const result = await makeRequest('/api/auth/check-credentials-status', {{
                    method: 'GET'
                }});
                
                if (result.success) {{
                    renderSecurityStatus(result);
                }} else {{
                    showError('Errore nel controllo sicurezza');
                }}
            }} catch (error) {{
                showError('Errore di connessione');
            }}
        }}
        
        function renderSecurityStatus(data) {{
            const container = document.getElementById('securityStatus');
            
            let statusIcon = '✅';
            let statusColor = '#28a745';
            let statusText = 'Sicuro';
            
            if (data.status === 'warning') {{
                statusIcon = '⚠️';
                statusColor = '#ffc107';
                statusText = 'Attenzione';
            }} else if (data.status === 'danger') {{
                statusIcon = '❌';
                statusColor = '#dc3545';
                statusText = 'A rischio';
            }}
            
            container.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 48px;">${{statusIcon}}</div>
                    <h4 style="color: ${{statusColor}};">${{statusText}}</h4>
                    <p>Credenziali aggiornate ${{data.days_since_update}} giorni fa</p>
                </div>
                
                ${{data.recommendations.length > 0 ? `
                    <div style="margin-top: 20px;">
                        <h5>Raccomandazioni:</h5>
                        <ul>
                            ${{data.recommendations.map(rec => `
                                <li>
                                    <strong>${{rec.message}}</strong><br>
                                    <small>${{rec.action}}</small>
                                </li>
                            `).join('')}}
                        </ul>
                    </div>
                ` : ''}}
            `;
        }}
        
        async function rotateCredentials(event) {{
            event.preventDefault();
            
            if (!confirm('Sei sicuro di voler ruotare le credenziali? Tutti i forwarder verranno fermati.')) {{
                return;
            }}
            
            const newApiId = document.getElementById('newApiId').value;
            const newApiHash = document.getElementById('newApiHash').value;
            
            showMessage('Rotazione credenziali in corso...', 'info');
            
            try {{
                const result = await makeRequest('/api/auth/rotate-credentials', {{
                    method: 'POST',
                    body: JSON.stringify({{
                        new_api_id: newApiId,
                        new_api_hash: newApiHash
                    }})
                }});
                
                if (result.success) {{
                    showMessage(`✅ ${{result.message}}<br>
                        <strong>Container fermati:</strong> ${{result.stopped_containers}}<br>
                        <strong>Azione richiesta:</strong> ${{result.action_required}}`, 'success');
                    
                    // Refresh security status
                    setTimeout(checkSecurityStatus, 2000);
                    
                    // Clear form
                    document.getElementById('rotateCredentialsForm').reset();
                }} else {{
                    showMessage(`❌ Errore: ${{result.error}}`, 'error');
                }}
            }} catch (error) {{
                showMessage('❌ Errore di connessione', 'error');
            }}
        }}
        
        function showError(message) {{
            document.getElementById('securityStatus').innerHTML = `
                <div class="status error">
                    <p>${{message}}</p>
                </div>
            `;
        }}
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Sicurezza",
        subtitle="Gestione sicurezza e credenziali",
        content=Markup(content)
    )

if __name__ == '__main__':
    logger.info("🌐 Starting Telegram Chat Manager Frontend")
    logger.info(f"📍 Host: 0.0.0.0:8080")
    logger.info(f"🔧 Debug: {DEBUG}")
    logger.info(f"🌍 Environment: {ENVIRONMENT}")
    
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=DEBUG
    ) 