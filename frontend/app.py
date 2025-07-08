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
from flask import Flask, render_template, render_template_string, request, jsonify, redirect, url_for, session
from markupsafe import Markup
import requests
from datetime import datetime
from functools import wraps

# Import menu utilities
from menu_utils import get_unified_menu, get_logout_script, get_menu_styles, get_menu_scripts

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

# 🎨 Modern Corporate Template
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Solanagram</title>
    {{ menu_styles|safe }}
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            min-height: 100vh;
            color: #334155;
            line-height: 1.6;
        }
        
        .main-content {
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .page-header {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
        }
        
        .page-header h1 {
            font-size: 2rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.5rem;
        }
        
        .page-header p {
            color: #64748b;
            font-size: 1.1rem;
        }
        
        .content-section {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
        }
        
        /* Messages/Status */
        .message, .status {
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid;
        }
        
        .message-success, .status.success {
            background: #f0fdf4;
            color: #166534;
            border-left-color: #22c55e;
        }
        
        .message-error, .status.error {
            background: #fef2f2;
            color: #dc2626;
            border-left-color: #ef4444;
        }
        
        .message-info, .status.info {
            background: #eff6ff;
            color: #1d4ed8;
            border-left-color: #3b82f6;
        }
        
        .message-warning, .status.warning {
            background: #fefce8;
            color: #a16207;
            border-left-color: #eab308;
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        }
        
        .btn:hover {
            background: #5a67d8;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .btn-primary { background: #3b82f6; }
        .btn-primary:hover { background: #2563eb; }
        
        .btn-success { background: #10b981; }
        .btn-success:hover { background: #059669; }
        
        .btn-danger { background: #ef4444; }
        .btn-danger:hover { background: #dc2626; }
        
        .btn-warning { background: #f59e0b; color: white; }
        .btn-warning:hover { background: #d97706; }
        
        .btn-secondary { background: #6b7280; }
        .btn-secondary:hover { background: #4b5563; }
        
        /* Forms */
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #374151;
        }
        
        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
            background: white;
        }
        
        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .form-group small {
            display: block;
            margin-top: 0.25rem;
            color: #6b7280;
            font-size: 0.875rem;
        }
        
        .form-actions {
            text-align: center;
            margin-top: 2rem;
        }
        
        .form-actions .btn {
            margin: 0 0.5rem;
        }
        
        /* Cards and Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin: 1.5rem 0;
        }
        
        .card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }
        
        .card h3 {
            color: #1e293b;
            margin-bottom: 1rem;
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .card h4 {
            color: #374151;
            margin-bottom: 0.75rem;
            font-size: 1.1rem;
            font-weight: 500;
        }
        
        /* Loading Spinner */
        .loading {
            display: none;
            text-align: center;
            margin: 2rem 0;
        }
        
        .spinner {
            border: 3px solid #f3f4f6;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Utilities */
        .text-center { text-align: center; }
        .text-left { text-align: left; }
        .text-right { text-align: right; }
        
        .mb-1 { margin-bottom: 0.25rem; }
        .mb-2 { margin-bottom: 0.5rem; }
        .mb-3 { margin-bottom: 1rem; }
        .mb-4 { margin-bottom: 1.5rem; }
        .mb-5 { margin-bottom: 3rem; }
        
        .mt-1 { margin-top: 0.25rem; }
        .mt-2 { margin-top: 0.5rem; }
        .mt-3 { margin-top: 1rem; }
        .mt-4 { margin-top: 1.5rem; }
        .mt-5 { margin-top: 3rem; }
        
        /* Badge styling */
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }
        
        .badge-success {
            background: #dcfce7;
            color: #166534;
        }
        
        .badge-danger {
            background: #fef2f2;
            color: #dc2626;
        }
        
        .badge-warning {
            background: #fefce8;
            color: #a16207;
        }
        
        .badge-info {
            background: #eff6ff;
            color: #1d4ed8;
        }
        
        .badge-secondary {
            background: #f1f5f9;
            color: #64748b;
        }
        
        /* Code styling */
        code {
            background: #f1f5f9;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
            font-size: 0.875rem;
            color: #e11d48;
        }
        
        pre {
            background: #f8fafc;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid #e2e8f0;
        }
        
        pre code {
            background: none;
            padding: 0;
            color: inherit;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .main-content {
                padding: 1rem;
            }
            
            .page-header {
                padding: 1.5rem;
            }
            
            .content-section {
                padding: 1.5rem;
            }
            
            .grid {
                grid-template-columns: 1fr;
                gap: 1rem;
            }
            
            .form-actions .btn {
                display: block;
                margin: 0.5rem 0;
                width: 100%;
            }
        }
    </style>
</head>
<body>
    {{ menu_html|safe }}
    
    <main class="main-content">
        <div class="page-header">
            <h1>{{ title }}</h1>
            <p>{{ subtitle }}</p>
        </div>
        
        <div class="content-section">
            {{ content|safe }}
        </div>
    </main>
    
    {{ menu_scripts|safe }}
    
    <script>
        // Enhanced makeRequest function
        async function makeRequest(url, options = {}) {
            try {
                console.log('makeRequest - URL:', url);
                
                const headers = {
                    'Content-Type': 'application/json',
                    ...options.headers
                };
                
                const response = await fetch(url, {
                    ...options,
                    headers
                });
                
                if (response.status === 401) {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('session_token');
                    window.location.href = '/login';
                    return null;
                }
                
                const jsonResult = await response.json();
                console.log('makeRequest - Result:', jsonResult);
                return jsonResult;
            } catch (error) {
                console.error('makeRequest - Error:', error);
                return { error: 'Errore di connessione' };
            }
        }
        
        // Loading state management
        function showLoading() {
            const loadingElements = document.querySelectorAll('.loading');
            loadingElements.forEach(element => {
                element.style.display = 'block';
            });
        }
        
        function hideLoading() {
            const loadingElements = document.querySelectorAll('.loading');
            loadingElements.forEach(element => {
                element.style.display = 'none';
            });
        }
        
        // Enhanced message system
        function showMessage(message, type = 'info') {
            // Remove existing messages
            const existingMessages = document.querySelectorAll('.message');
            existingMessages.forEach(msg => msg.remove());
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message message-${type}`;
            messageDiv.innerHTML = message;
            
            const contentSection = document.querySelector('.content-section');
            if (contentSection) {
                contentSection.insertBefore(messageDiv, contentSection.firstChild);
            }
            
            // Auto-remove success and info messages after 5 seconds
            if (type === 'success' || type === 'info') {
                setTimeout(() => {
                    if (messageDiv.parentNode) {
                        messageDiv.remove();
                    }
                }, 5000);
            }
        }
        
        // Page load animations
        document.addEventListener('DOMContentLoaded', function() {
            // Add fade-in animation to content
            const cards = document.querySelectorAll('.card');
            cards.forEach((card, index) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    card.style.transition = 'all 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, index * 100);
            });
        });
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
            response = requests_put(url, json=data, headers=headers, timeout=30)
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
        <br><br>
        <small>ℹ️ <strong>Nota:</strong> Il sistema effettua automaticamente più tentativi per garantire una connessione stabile con i server Telegram. Se la connessione si interrompe, verrà automaticamente ristabilita. In caso di errori persistenti, il pulsante "Invia codice" può essere cliccato nuovamente.</small>
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
                <button type="button" id="requestNewCode2" class="btn">📱 Richiedi nuovo codice</button>
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
        
        // Richiedi nuovo codice (secondo bottone)
        document.getElementById('requestNewCode2').addEventListener('click', async function() {
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
            
            // FIXED: Better UX with informative loading message
            showLoading();
            showMessage('🔄 Connessione a Telegram in corso... Il sistema effettuerà automaticamente dei tentativi per garantire una connessione stabile.', 'info');
            
            try {
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
            } catch (error) {
                hideLoading();
                console.error('Login error:', error);
                showMessage('❌ Errore di connessione. Riprova tra qualche secondo.', 'error');
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
    <h2>Dashboard</h2>
    
    <div class="message message-success">
        Benvenuto, <strong>{user_data.get('phone_number', 'Utente')}</strong>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>Account Information</h3>
            <p><strong>Telefono:</strong> {user_data.get('phone_number', 'N/A')}</p>
            <p><strong>API ID:</strong> {user_data.get('api_id', 'N/A')}</p>
            <p><strong>Registrato:</strong> {user_data.get('created_at', 'N/A')[:10] if user_data.get('created_at') else 'N/A'}</p>
            <p><strong>Stato:</strong> <span class="badge badge-{'success' if user_data.get('is_active') else 'danger'}">{'Attivo' if user_data.get('is_active') else 'Disattivo'}</span></p>
            <br>
            <a href="/profile" class="btn btn-primary">Gestisci Profilo</a>
        </div>
        
        <div class="card">
            <h3>Chat Management</h3>
            <p>Visualizza tutte le tue chat Telegram con ID e dettagli per la gestione dei reindirizzamenti</p>
            <br>
            <a href="/chats" class="btn btn-primary">Visualizza Chat</a>
        </div>
        
        <div class="card">
            <h3>Chat Search</h3>
            <p>Cerca l'ID di una chat Telegram inserendo username o nome del gruppo</p>
            <br>
            <a href="/find" class="btn btn-primary">Cerca Chat</a>
        </div>
        
        <div class="card">
            <h3>System Status</h3>
            <p><strong>Backend:</strong> <span class="badge badge-{'success' if backend_info and backend_info.get('status') == 'healthy' else 'danger'}">{'Online' if backend_info and backend_info.get('status') == 'healthy' else 'Offline'}</span></p>
            <p><strong>Ambiente:</strong> <code>{ENVIRONMENT}</code></p>
            <p><strong>Sessione:</strong> <span class="badge badge-success">Attiva</span></p>
        </div>
    </div>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Dashboard",
        subtitle="Pannello di controllo",
        content=Markup(content),
        menu_html=Markup(menu_html),
        menu_styles=Markup(get_menu_styles()),
        menu_scripts=Markup(get_menu_scripts())
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
        ℹ️ Qui puoi visualizzare e modificare le tue informazioni, credenziali API e password
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
        
        <!-- Cambio Password -->
        <div class="card">
            <h3>🔐 Cambio Password</h3>
            <p>Modifica la password del tuo account per mantenere la sicurezza.</p>
            <br>
            <button onclick="showPasswordForm()" class="btn">🔒 Cambia Password</button>
        </div>
    </div>
    
    <!-- Form di modifica credenziali API (nascosto di default) -->
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
    
    <!-- Form di cambio password (nascosto di default) -->
    <div id="passwordForm" style="display: none; margin-top: 30px;">
        <div class="card">
            <h3>🔐 Cambio Password</h3>
            
            <div class="status info">
                ℹ️ <strong>Informazioni:</strong> Inserisci la password attuale e la nuova password desiderata.
            </div>
            
            <form id="changePasswordForm">
                <div class="form-group">
                    <label for="currentPassword">Password Attuale</label>
                    <input type="password" id="currentPassword" name="current_password" required 
                           placeholder="Inserisci la password attuale">
                    <small>Password attualmente in uso per il tuo account</small>
                </div>
                
                <div class="form-group">
                    <label for="newPassword">Nuova Password</label>
                    <input type="password" id="newPassword" name="new_password" required 
                           placeholder="Inserisci la nuova password" minlength="6">
                    <small>La nuova password deve essere di almeno 6 caratteri</small>
                </div>
                
                <div class="form-group">
                    <label for="confirmPassword">Conferma Nuova Password</label>
                    <input type="password" id="confirmPassword" name="confirm_password" required 
                           placeholder="Conferma la nuova password" minlength="6">
                    <small>Ripeti la nuova password per confermare</small>
                </div>
                
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Aggiornamento password in corso...</p>
                </div>
                
                <div class="form-actions">
                    <button type="submit" class="btn success">🔒 Cambia Password</button>
                    <button type="button" onclick="hidePasswordForm()" class="btn" style="margin-left: 10px;">❌ Annulla</button>
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
        
        function showPasswordForm() {{
            document.getElementById('passwordForm').style.display = 'block';
            document.getElementById('currentPassword').focus();
        }}
        
        function hidePasswordForm() {{
            document.getElementById('passwordForm').style.display = 'none';
            document.getElementById('changePasswordForm').reset();
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
            
            if (!confirm('Sei sicuro di voler aggiornare le credenziali API? Dovrai rifare il login per usare le nuove API.')) {{
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
            
            document.getElementById('changePasswordForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const currentPassword = formData.get('current_password');
                const newPassword = formData.get('new_password');
                const confirmPassword = formData.get('confirm_password');
                
                if (!currentPassword || !newPassword || !confirmPassword) {{
                    showMessage('Compila tutti i campi', 'error');
                    return;
                }}
                
                if (newPassword.length < 6) {{
                    showMessage('La nuova password deve essere di almeno 6 caratteri', 'error');
                    return;
                }}
                
                if (newPassword !== confirmPassword) {{
                    showMessage('Le nuove password non coincidono', 'error');
                    return;
                }}
                
                if (!confirm('Sei sicuro di voler cambiare la password?')) {{
                    return;
                }}
                
                showLoading();
                
                try {{
                    const result = await makeRequest('/api/user/change-password', {{
                        method: 'POST',
                        body: JSON.stringify({{
                            current_password: currentPassword,
                            new_password: newPassword,
                            confirm_password: confirmPassword
                        }})
                    }});
                    
                    hideLoading();
                    
                    if (result.success) {{
                        showMessage(result.message, 'success');
                        hidePasswordForm();
                        
                        // Opzionale: logout automatico dopo cambio password
                        setTimeout(() => {{
                            if (confirm('Password aggiornata con successo! Per sicurezza, ti consigliamo di effettuare il logout e rifare il login. Vuoi procedere?')) {{
                                logout();
                            }}
                        }}, 2000);
                        
                    }} else {{
                        showMessage(result.error || 'Errore durante il cambio password', 'error');
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
        content=Markup(content),
        menu_html=Markup(menu_html),
        menu_styles=Markup(get_menu_styles()),
        menu_scripts=Markup(get_menu_scripts())
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
        content=Markup(content),
        menu_html=Markup(menu_html),
        menu_styles=Markup(get_menu_styles()),
        menu_scripts=Markup(get_menu_scripts())
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
        content=Markup(content),
        menu_html=Markup(menu_html),
        menu_styles=Markup(get_menu_styles()),
        menu_scripts=Markup(get_menu_scripts())
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
        content=Markup(content),
        menu_html=Markup(menu_html),
        menu_styles=Markup(get_menu_styles()),
        menu_scripts=Markup(get_menu_scripts())
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
        content=Markup(content),
        menu_html=Markup(menu_html),
        menu_styles=Markup(get_menu_styles()),
        menu_scripts=Markup(get_menu_scripts())
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

@app.route('/api/auth/validate-session', methods=['GET'])
def api_validate_session():
    """Proxy per validare la sessione corrente"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend('/api/auth/validate-session', 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

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
        content=Markup(content),
        menu_html=Markup(""),
        menu_styles=Markup(get_menu_styles()),
        menu_scripts=Markup(get_menu_scripts())
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

@app.route('/api/auth/session-token', methods=['GET'])
def get_session_token():
    """Get current session token for frontend JavaScript"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    return jsonify({
        'success': True,
        'token': session['session_token']
    })

# ========================================================================================
# CRYPTO SIGNAL API PROXIES
# ========================================================================================

@app.route('/api/crypto/processors', methods=['GET', 'POST'])
def api_crypto_processors():
    """Proxy per gestione processori crypto"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    if request.method == 'GET':
        result = call_backend('/api/crypto/processors', 'GET', auth_token=session['session_token'])
    else:
        data = request.get_json()
        result = call_backend('/api/crypto/processors', 'POST', data, auth_token=session['session_token'])
    
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/crypto/test-parse', methods=['POST'])
def api_crypto_test_parse():
    """Proxy per test parser crypto"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/crypto/test-parse', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/crypto/signals/<source_chat_id>', methods=['GET'])
def api_crypto_signals(source_chat_id):
    """Proxy per recupero segnali crypto"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    query_string = request.query_string.decode()
    endpoint = f'/api/crypto/signals/{source_chat_id}'
    if query_string:
        endpoint += f'?{query_string}'
    
    result = call_backend(endpoint, 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/crypto/top-performers', methods=['GET'])
def api_crypto_top_performers():
    """Proxy per top performers crypto"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    query_string = request.query_string.decode()
    endpoint = '/api/crypto/top-performers'
    if query_string:
        endpoint += f'?{query_string}'
    
    result = call_backend(endpoint, 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/crypto/process-message', methods=['POST'])
def api_crypto_process_message():
    """Proxy per processare messaggio crypto"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/crypto/process-message', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

# ========================================================================================
# EXISTING API PROXIES
# ========================================================================================

@app.route('/crypto-signals')
@require_auth
def crypto_signals():
    """Pagina per il processamento dei segnali crypto"""
    return render_template('crypto_signals.html')

@app.route('/crypto-dashboard')
@require_auth
def crypto_dashboard():
    """Dashboard principale per le funzionalità crypto"""
    
    # Use unified menu
    menu_html = get_unified_menu('crypto-dashboard')
    
    content = f"""
    {menu_html}
    
    <h2>🚀 Crypto Signal Management</h2>
    
    <div class="grid">
        <div class="card">
            <h3>⚙️ Configuratore Regole</h3>
            <p>Configura le regole di estrazione dati per i tuoi gruppi crypto.</p>
            <a href="/crypto-configurator" class="btn btn-primary">
                🔧 Configura Estrattore
            </a>
        </div>
        
        <div class="card">
            <h3>📊 Storico Messaggi</h3>
            <p>Visualizza tutti i messaggi crypto processati e i dati estratti.</p>
            <a href="/crypto-history" class="btn btn-info">
                📈 Visualizza Storico
            </a>
        </div>
        
        <div class="card">
            <h3>🧪 Test Parser</h3>
            <p>Testa il parser sui tuoi messaggi crypto (modalità legacy).</p>
            <a href="/crypto-signals" class="btn btn-secondary">
                🔍 Test Parser
            </a>
        </div>
    </div>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Crypto Dashboard",
        subtitle="Gestione segnali crypto",
        content=Markup(content)
    )



@app.route('/message-manager')
@require_auth
def message_manager():
    """Pagina gestione messaggi unificata"""
    
    # Use unified menu
    menu_html = get_unified_menu('message-manager')
    
    # Define JavaScript separately to avoid syntax conflicts
    script_content = """
    <script>
        let allChats = [];
        let filteredChats = [];
        let listeners = {};
        
        document.addEventListener('DOMContentLoaded', async () => {
            await loadChats();
            await loadListeners();
        });
        
        async function loadChats() {
            showLoading();
            
            try {
                const result = await makeRequest('/api/telegram/get-chats', {
                    method: 'GET'
                });
                
                hideLoading();
                
                if (result.success) {
                    allChats = result.chats;
                    filteredChats = [...allChats];
                    
                    document.getElementById('chatsContainer').style.display = 'block';
                    document.getElementById('searchFilter').addEventListener('input', filterChats);
                    
                    // Load listeners before rendering
                    await loadListeners();
                    renderChats();
                } else {
                    showError(result.error || 'Errore durante il caricamento chat');
                }
            } catch (error) {
                hideLoading();
                showError('Errore di connessione');
            }
        }
        
        async function loadListeners() {
            try {
                const result = await makeRequest('/api/message-listeners', {
                    method: 'GET'
                });
                
                if (result.success) {
                    // Create a map of chat_id -> listener
                    listeners = {};
                    result.listeners.forEach(listener => {
                        listeners[listener.source_chat_id] = listener;
                    });
                }
            } catch (error) {
                console.error('Error loading listeners:', error);
            }
        }
        
        function renderChats() {
            const container = document.getElementById('chatsList');
            
            if (filteredChats.length === 0) {
                container.innerHTML = `
                    <div class="status warning">
                        <p>🔍 Nessuna chat trovata con i criteri di ricerca</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <strong>📊 ${filteredChats.length} chat trovate</strong>
                </div>
                
                ${filteredChats.map(chat => {
                    const listener = listeners[chat.id];
                    const isListening = listener && listener.container_status === 'running';
                    const hasElaborations = listener && listener.elaboration_count > 0;
                    
                    return `
                    <div class="card" style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h3>${escapeHtml(chat.title)} <span class="chat-icon">${getChatIcon(chat.type)}</span></h3>
                                <p><strong>ID:</strong> <code>${chat.id}</code></p>
                                <p><strong>Tipo:</strong> ${getChatTypeLabel(chat.type)}</p>
                                ${chat.username ? `<p><strong>Username:</strong> @${chat.username}</p>` : ''}
                                ${chat.members_count ? `<p><strong>Membri:</strong> ${chat.members_count}</p>` : ''}
                                
                                ${listener ? `
                                    <div style="margin-top: 10px; padding: 10px; background: #f0f8ff; border-radius: 5px;">
                                        <p><strong>📊 Stato:</strong> <span class="${isListening ? 'text-success' : 'text-danger'}">${isListening ? '✅ In ascolto' : '❌ Fermo'}</span></p>
                                        <p><strong>📨 Messaggi ricevuti:</strong> ${listener.messages_received || 0}</p>
                                        ${listener.last_message_at ? `<p><strong>🕐 Ultimo messaggio:</strong> ${new Date(listener.last_message_at).toLocaleString('it-IT')}</p>` : ''}
                                        ${hasElaborations ? `<p><strong>🔧 Elaborazioni:</strong> ${listener.elaboration_count} (${listener.extractor_count} extractor, ${listener.redirect_count} redirect)</p>` : ''}
                                    </div>
                                ` : ''}
                                
                                <div style="margin-top: 15px;">
                                    ${!listener ? `
                                        <button onclick="activateListener('${chat.id}', '${escapeHtml(chat.title).replace(/'/g, "\\\\'")}', '${chat.type}')" class="btn btn-primary">
                                            📡 Attiva ascolto messaggi
                                        </button>
                                    ` : `
                                        <button onclick="toggleListener('${listener.id}', ${isListening})" class="btn ${isListening ? 'btn-warning' : 'btn-success'}">
                                            ${isListening ? '⏸️ Ferma ascolto' : '▶️ Riprendi ascolto'}
                                        </button>
                                        <button onclick="window.location.href='/message-elaborations/${listener.id}'" class="btn btn-primary" style="margin-left: 10px;">
                                            🔧 Gestisci elaborazioni
                                        </button>
                                        <button onclick="deleteListener('${listener.id}')" class="btn btn-danger" style="margin-left: 10px;">
                                            🗑️ Elimina
                                        </button>
                                    `}
                                </div>
                            </div>
                        </div>
                    </div>
                    `;
                }).join('')}
            `;
        }
        
        async function activateListener(chatId, chatTitle, chatType) {
            if (!confirm(`Vuoi attivare l'ascolto messaggi per "${chatTitle}"?`)) {
                return;
            }
            
            showMessage('Attivazione ascolto messaggi...', 'info');
            
            try {
                const result = await makeRequest('/api/message-listeners', {
                    method: 'POST',
                    body: JSON.stringify({
                        source_chat_id: chatId,
                        source_chat_title: chatTitle,
                        source_chat_type: chatType
                    })
                });
                
                if (result.success) {
                    showMessage('✅ Ascolto messaggi attivato con successo!', 'success');
                    await loadListeners();
                    renderChats();
                } else {
                    // Show detailed error message
                    let errorMsg = `❌ Errore durante l'attivazione`;
                    if (result.error) {
                        errorMsg += `: ${result.error}`;
                    }
                    if (result.details) {
                        errorMsg += `<br><small>Dettagli: ${result.details}</small>`;
                    }
                    showMessage(errorMsg, 'error');
                }
            } catch (error) {
                console.error('Error activating listener:', error);
                let errorMsg = '❌ Errore di connessione durante l\'attivazione';
                
                // Check if it's a specific HTTP error
                if (error.message && error.message.includes('HTTP error')) {
                    errorMsg += `<br><small>Codice errore: ${error.message}</small>`;
                } else if (error.message) {
                    errorMsg += `<br><small>Dettagli: ${error.message}</small>`;
                }
                
                showMessage(errorMsg, 'error');
            }
        }
        
        async function toggleListener(listenerId, isRunning) {
            const action = isRunning ? 'stop' : 'start';
            
            try {
                const result = await makeRequest(`/api/message-listeners/${listenerId}/${action}`, {
                    method: 'POST'
                });
                
                if (result.success) {
                    showMessage(`✅ Listener ${isRunning ? 'fermato' : 'riavviato'} con successo!`, 'success');
                    await loadListeners();
                    renderChats();
                } else {
                    showMessage(`❌ Errore: ${result.error}`, 'error');
                }
            } catch (error) {
                console.error('Error toggling listener:', error);
                showMessage('❌ Errore di connessione', 'error');
            }
        }
        
        async function deleteListener(listenerId) {
            if (!confirm('Sei sicuro di voler eliminare questo listener? Verranno eliminate anche tutte le elaborazioni associate.')) {
                return;
            }
            
            try {
                const result = await makeRequest(`/api/message-listeners/${listenerId}`, {
                    method: 'DELETE'
                });
                
                if (result.success) {
                    showMessage('✅ Listener eliminato con successo!', 'success');
                    await loadListeners();
                    renderChats();
                } else {
                    showMessage(`❌ Errore: ${result.error}`, 'error');
                }
            } catch (error) {
                console.error('Error deleting listener:', error);
                showMessage('❌ Errore di connessione', 'error');
            }
        }
        
        function filterChats() {
            const query = document.getElementById('searchFilter').value.toLowerCase().trim();
            
            if (!query) {
                filteredChats = [...allChats];
            } else {
                filteredChats = allChats.filter(chat => 
                    chat.title.toLowerCase().includes(query) ||
                    chat.id.toString().includes(query) ||
                    (chat.username && chat.username.toLowerCase().includes(query))
                );
            }
            
            renderChats();
        }
        
        function getChatIcon(type) {
            switch(type) {
                case 'private': return '👤';
                case 'group': return '👥';
                case 'supergroup': return '👥';
                case 'channel': return '📢';
                default: return '💬';
            }
        }
        
        function getChatTypeLabel(type) {
            switch(type) {
                case 'private': return 'Chat privata';
                case 'group': return 'Gruppo';
                case 'supergroup': return 'Supergruppo';
                case 'channel': return 'Canale';
                default: return type;
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function showError(message) {
            document.getElementById('errorMessage').textContent = message;
            document.getElementById('errorContainer').style.display = 'block';
            document.getElementById('chatsContainer').style.display = 'none';
        }
        
        function showLoading() {
            document.querySelector('.loading').style.display = 'block';
        }
        
        function hideLoading() {
            document.querySelector('.loading').style.display = 'none';
        }
    </script>
    """
    
    content = f"""
    {menu_html}
    
    <h2>📨 Gestione Messaggi</h2>
    
    <div class="status info">
        ℹ️ Configura l'ascolto dei messaggi e le elaborazioni per ogni chat
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
                <small>Ricerca in tempo reale</small>
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
    
    {script_content}
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Gestione Messaggi",
        subtitle="Configura ascolto e elaborazioni",
        content=Markup(content)
    )

@app.route('/message-elaborations/<int:listener_id>')
@require_auth
def message_elaborations(listener_id):
    """Pagina gestione elaborazioni per un listener"""
    
    # Use unified menu
    menu_html = get_unified_menu('message-manager')
    
    content = f"""
    {menu_html}
    
    <h2>🔧 Gestione Elaborazioni</h2>
    <p><a href="/message-manager">← Torna a Gestione Messaggi</a></p>
    
    <div class="card" style="margin-bottom: 20px;">
        <h3 id="listenerTitle">Caricamento...</h3>
        <p><strong>ID Listener:</strong> {listener_id}</p>
        <p id="listenerStats"></p>
    </div>
    
    <div class="loading">
        <div class="spinner"></div>
        <p>Caricamento elaborazioni...</p>
    </div>
    
    <div id="elaborationsContainer" style="display: none;">
        <div style="margin-bottom: 20px;">
            <button onclick="showNewElaborationForm()" class="btn btn-success">
                ➕ Aggiungi elaborazione
            </button>
        </div>
        
        <div id="newElaborationForm" style="display: none; margin-bottom: 20px;" class="card">
            <h3>➕ Nuova Elaborazione</h3>
            <form onsubmit="createElaboration(event)">
                <div class="form-group">
                    <label>Tipo elaborazione</label>
                    <select id="elaborationType" name="elaborationType" required onchange="updateElaborationForm()">
                        <option value="">Seleziona...</option>
                        <option value="extractor">🔍 Extractor - Estrai dati dai messaggi</option>
                        <option value="redirect">🔄 Redirect - Inoltra a un'altra chat</option>
                    </select>
                </div>
                
                <div id="elaborationConfig" style="display: none;">
                    <!-- Dynamic content based on type -->
                </div>
                
                <div class="form-actions" style="display: none;" id="formActions">
                    <button type="submit" class="btn btn-primary">✅ Crea elaborazione</button>
                    <button type="button" onclick="hideNewElaborationForm()" class="btn">❌ Annulla</button>
                </div>
            </form>
        </div>
        
        <div id="elaborationsList"></div>
    </div>
    
    <div id="errorContainer" style="display: none;">
        <div class="status error">
            <h3>❌ Errore</h3>
            <p id="errorMessage"></p>
        </div>
    </div>
    
    <script>
        const listenerId = {listener_id};
        let listener = null;
        let elaborations = [];
        let availableChats = [];
        
        document.addEventListener('DOMContentLoaded', async () => {{
            await loadListener();
            await loadElaborations();
            await loadAvailableChats();
        }});
        
        async function loadListener() {{
            try {{
                const result = await makeRequest('/api/message-listeners', {{
                    method: 'GET'
                }});
                
                if (result.success) {{
                    listener = result.listeners.find(l => l.id === listenerId);
                    if (listener) {{
                        document.getElementById('listenerTitle').innerHTML = `
                            📡 Listener: ${{escapeHtml(listener.source_chat_title)}}
                        `;
                        document.getElementById('listenerStats').innerHTML = `
                            <strong>Messaggi ricevuti:</strong> ${{listener.messages_received || 0}} |
                            <strong>Stato:</strong> <span class="${{listener.container_status === 'running' ? 'text-success' : 'text-danger'}}">${{listener.container_status}}</span>
                        `;
                    }}
                }}
            }} catch (error) {{
                console.error('Error loading listener:', error);
            }}
        }}
        
        async function loadElaborations() {{
            showLoading();
            
            try {{
                const result = await makeRequest(`/api/message-listeners/${{listenerId}}/elaborations`, {{
                    method: 'GET'
                }});
                
                hideLoading();
                
                if (result.success) {{
                    elaborations = result.elaborations;
                    document.getElementById('elaborationsContainer').style.display = 'block';
                    renderElaborations();
                }} else {{
                    showError(result.error || 'Errore durante il caricamento elaborazioni');
                }}
            }} catch (error) {{
                hideLoading();
                showError('Errore di connessione');
            }}
        }}
        
        async function loadAvailableChats() {{
            try {{
                const result = await makeRequest('/api/telegram/get-chats', {{
                    method: 'GET'
                }});
                
                if (result.success) {{
                    availableChats = result.chats;
                }}
            }} catch (error) {{
                console.error('Error loading chats:', error);
            }}
        }}
        
        function renderElaborations() {{
            const container = document.getElementById('elaborationsList');
            
            if (elaborations.length === 0) {{
                container.innerHTML = `
                    <div class="status info">
                        <p>📭 Nessuna elaborazione configurata</p>
                        <p>Clicca su "Aggiungi elaborazione" per iniziare</p>
                    </div>
                `;
                return;
            }}
            
            container.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <strong>📊 ${{elaborations.length}} elaborazioni configurate</strong>
                </div>
                
                ${{elaborations.map(elab => `
                    <div class="card" style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h4>${{getElaborationIcon(elab.elaboration_type)}} ${{escapeHtml(elab.elaboration_name)}}</h4>
                                <p><strong>Tipo:</strong> ${{getElaborationTypeLabel(elab.elaboration_type)}}</p>
                                <p><strong>Stato:</strong> <span class="${{elab.is_active ? 'text-success' : 'text-danger'}}">${{elab.is_active ? '✅ Attivo' : '❌ Disattivo'}}</span></p>
                                <p><strong>Messaggi processati:</strong> ${{elab.processed_count || 0}}</p>
                                ${{elab.error_count > 0 ? `<p class="text-danger"><strong>Errori:</strong> ${{elab.error_count}}</p>` : ''}}
                                
                                ${{renderElaborationConfig(elab)}}
                                
                                <div style="margin-top: 15px;">
                                    <button onclick="toggleElaboration(${{elab.id}}, ${{elab.is_active}})" class="btn ${{elab.is_active ? 'btn-warning' : 'btn-success'}}">
                                        ${{elab.is_active ? '⏸️ Disattiva' : '▶️ Attiva'}}
                                    </button>
                                    <button onclick="deleteElaboration(${{elab.id}})" class="btn btn-danger" style="margin-left: 10px;">
                                        🗑️ Elimina
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}}
            `;
        }}
        
        function renderElaborationConfig(elab) {{
            const config = elab.config || {{}};
            
            if (elab.elaboration_type === 'extractor') {{
                const rules = config.rules || [];
                return `
                    <div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                        <strong>Regole di estrazione:</strong>
                        <ul>
                            ${{rules.map(rule => `
                                <li>
                                    <strong>${{escapeHtml(rule.rule_name)}}:</strong> 
                                    Cerca "${{escapeHtml(rule.search_text)}}" e estrai ${{rule.value_length}} caratteri
                                </li>
                            `).join('')}}
                        </ul>
                    </div>
                `;
            }} else if (elab.elaboration_type === 'redirect') {{
                return `
                    <div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                        <p><strong>Destinazione:</strong> ${{escapeHtml(config.target_name || config.target_id)}}</p>
                        <p><strong>Tipo:</strong> ${{config.target_type}}</p>
                    </div>
                `;
            }}
            
            return '';
        }}
        
        function showNewElaborationForm() {{
            document.getElementById('newElaborationForm').style.display = 'block';
        }}
        
        function hideNewElaborationForm() {{
            document.getElementById('newElaborationForm').style.display = 'none';
            document.getElementById('elaborationType').value = '';
            document.getElementById('elaborationConfig').innerHTML = '';
            document.getElementById('elaborationConfig').style.display = 'none';
            document.getElementById('formActions').style.display = 'none';
        }}
        
        function updateElaborationForm() {{
            const type = document.getElementById('elaborationType').value;
            const configDiv = document.getElementById('elaborationConfig');
            const formActions = document.getElementById('formActions');
            
            if (!type) {{
                configDiv.style.display = 'none';
                formActions.style.display = 'none';
                return;
            }}
            
            configDiv.style.display = 'block';
            formActions.style.display = 'block';
            
            if (type === 'extractor') {{
                configDiv.innerHTML = `
                    <h4>Regole di estrazione</h4>
                    <div id="extractorRules">
                        <div class="rule-row" data-rule-index="0">
                            <div class="form-group">
                                <label>Nome regola</label>
                                <input type="text" name="rule_name[]" class="form-control" placeholder="es. token_address" required>
                            </div>
                            <div class="form-group">
                                <label>Testo da cercare</label>
                                <input type="text" name="search_text[]" class="form-control" placeholder="es. Address: " required>
                            </div>
                            <div class="form-group">
                                <label>Lunghezza valore da estrarre</label>
                                <input type="number" name="value_length[]" class="form-control" placeholder="44" min="1" required>
                            </div>
                            <button type="button" class="btn btn-danger btn-sm" onclick="removeRule(0)">🗑️ Rimuovi</button>
                        </div>
                    </div>
                    <button type="button" class="btn btn-success btn-sm" onclick="addRule()">➕ Aggiungi regola</button>
                `;
            }} else if (type === 'redirect') {{
                // Check if redirect already exists
                const hasRedirect = elaborations.some(e => e.elaboration_type === 'redirect');
                if (hasRedirect) {{
                    configDiv.innerHTML = `
                        <div class="status error">
                            <p>⚠️ È già presente un redirect per questo listener</p>
                            <p>Puoi avere solo un redirect per chat</p>
                        </div>
                    `;
                    formActions.style.display = 'none';
                    return;
                }}
                
                configDiv.innerHTML = `
                    <h4>Destinazione redirect</h4>
                    <div class="form-group">
                        <label>Tipo destinazione</label>
                        <select name="target_type" required onchange="updateTargetOptions()">
                            <option value="">Seleziona...</option>
                            <option value="user">👤 Utente</option>
                            <option value="group">👥 Gruppo</option>
                            <option value="channel">📢 Canale</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Seleziona destinazione</label>
                        <select name="target_id" required>
                            <option value="">Prima seleziona il tipo</option>
                        </select>
                    </div>
                `;
            }}
        }}
        
        let ruleIndex = 1;
        function addRule() {{
            const rulesDiv = document.getElementById('extractorRules');
            const newRule = document.createElement('div');
            newRule.className = 'rule-row';
            newRule.setAttribute('data-rule-index', ruleIndex);
            newRule.innerHTML = `
                <div class="form-group">
                    <label>Nome regola</label>
                    <input type="text" name="rule_name[]" class="form-control" placeholder="es. token_address" required>
                </div>
                <div class="form-group">
                    <label>Testo da cercare</label>
                    <input type="text" name="search_text[]" class="form-control" placeholder="es. Address: " required>
                </div>
                <div class="form-group">
                    <label>Lunghezza valore da estrarre</label>
                    <input type="number" name="value_length[]" class="form-control" placeholder="44" min="1" required>
                </div>
                <button type="button" class="btn btn-danger btn-sm" onclick="removeRule(${{ruleIndex}})">🗑️ Rimuovi</button>
            `;
            rulesDiv.appendChild(newRule);
            ruleIndex++;
        }}
        
        function removeRule(index) {{
            const rule = document.querySelector(`[data-rule-index="${{index}}"]`);
            if (rule) {{
                rule.remove();
            }}
        }}
        
        function updateTargetOptions() {{
            const targetType = document.querySelector('select[name="target_type"]').value;
            const targetSelect = document.querySelector('select[name="target_id"]');
            
            if (!targetType) {{
                targetSelect.innerHTML = '<option value="">Prima seleziona il tipo</option>';
                return;
            }}
            
            // Filter chats based on type
            const filteredChats = availableChats.filter(chat => {{
                if (targetType === 'user') return chat.type === 'private';
                if (targetType === 'group') return chat.type === 'group' || chat.type === 'supergroup';
                if (targetType === 'channel') return chat.type === 'channel';
                return false;
            }});
            
            targetSelect.innerHTML = `
                <option value="">Seleziona...</option>
                ${{filteredChats.map(chat => `
                    <option value="${{chat.id}}" data-name="${{escapeHtml(chat.title)}}">
                        ${{escapeHtml(chat.title)}} ${{chat.username ? `(@${{chat.username}})` : ''}}
                    </option>
                `).join('')}}
            `;
        }}
        
        async function createElaboration(event) {{
            event.preventDefault();
            
            const type = document.getElementById('elaborationType').value;
            let config = {{}};
            let name = '';
            
            if (type === 'extractor') {{
                // Collect rules
                const rules = [];
                const ruleRows = document.querySelectorAll('.rule-row');
                
                ruleRows.forEach(row => {{
                    const ruleName = row.querySelector('input[name="rule_name[]"]').value;
                    const searchText = row.querySelector('input[name="search_text[]"]').value;
                    const valueLength = parseInt(row.querySelector('input[name="value_length[]"]').value);
                    
                    rules.push({{
                        rule_name: ruleName,
                        search_text: searchText,
                        value_length: valueLength
                    }});
                }});
                
                config = {{ rules }};
                name = `Extractor con ${{rules.length}} regole`;
                
            }} else if (type === 'redirect') {{
                const targetType = document.querySelector('select[name="target_type"]').value;
                const targetSelect = document.querySelector('select[name="target_id"]');
                const targetId = targetSelect.value;
                const targetName = targetSelect.selectedOptions[0]?.getAttribute('data-name') || targetId;
                
                config = {{
                    target_type: targetType,
                    target_id: targetId,
                    target_name: targetName
                }};
                name = `Redirect verso ${{targetName}}`;
            }}
            
            showMessage('Creazione elaborazione...', 'info');
            
            try {{
                const result = await makeRequest(`/api/message-listeners/${{listenerId}}/elaborations`, {{
                    method: 'POST',
                    body: JSON.stringify({{
                        elaboration_type: type,
                        elaboration_name: name,
                        config: config
                    }})
                }});
                
                if (result.success) {{
                    showMessage('✅ Elaborazione creata con successo!', 'success');
                    hideNewElaborationForm();
                    await loadElaborations();
                }} else {{
                    showMessage(`❌ Errore: ${{result.error}}`, 'error');
                }}
            }} catch (error) {{
                console.error('Error creating elaboration:', error);
                showMessage('❌ Errore di connessione', 'error');
            }}
        }}
        
        async function toggleElaboration(elaborationId, isActive) {{
            const action = isActive ? 'deactivate' : 'activate';
            
            try {{
                const result = await makeRequest(`/api/elaborations/${{elaborationId}}/${{action}}`, {{
                    method: 'POST'
                }});
                
                if (result.success) {{
                    showMessage(`✅ Elaborazione ${{isActive ? 'disattivata' : 'attivata'}} con successo!`, 'success');
                    await loadElaborations();
                }} else {{
                    showMessage(`❌ Errore: ${{result.error}}`, 'error');
                }}
            }} catch (error) {{
                console.error('Error toggling elaboration:', error);
                showMessage('❌ Errore di connessione', 'error');
            }}
        }}
        
        async function deleteElaboration(elaborationId) {{
            if (!confirm('Sei sicuro di voler eliminare questa elaborazione?')) {{
                return;
            }}
            
            try {{
                const result = await makeRequest(`/api/elaborations/${{elaborationId}}`, {{
                    method: 'DELETE'
                }});
                
                if (result.success) {{
                    showMessage('✅ Elaborazione eliminata con successo!', 'success');
                    await loadElaborations();
                }} else {{
                    showMessage(`❌ Errore: ${{result.error}}`, 'error');
                }}
            }} catch (error) {{
                console.error('Error deleting elaboration:', error);
                showMessage('❌ Errore di connessione', 'error');
            }}
        }}
        
        function getElaborationIcon(type) {{
            switch(type) {{
                case 'extractor': return '🔍';
                case 'redirect': return '🔄';
                default: return '🔧';
            }}
        }}
        
        function getElaborationTypeLabel(type) {{
            switch(type) {{
                case 'extractor': return 'Estrazione dati';
                case 'redirect': return 'Reindirizzamento';
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
            document.getElementById('elaborationsContainer').style.display = 'none';
        }}
        
        function showLoading() {{
            document.querySelector('.loading').style.display = 'block';
        }}
        
        function hideLoading() {{
            document.querySelector('.loading').style.display = 'none';
        }}
        
        function showMessage(message, type = 'info') {{
            const statusDiv = document.createElement('div');
            statusDiv.className = `status ${{type}}`;
            statusDiv.innerHTML = message;
            
            const container = document.querySelector('.content') || document.body;
            container.insertBefore(statusDiv, container.firstChild);
            
            setTimeout(() => statusDiv.remove(), 5000);
        }}
    </script>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Gestione Elaborazioni",
        subtitle=f"Listener ID: {listener_id}",
        content=Markup(content)
    )

@app.route('/crypto-configurator')
@require_auth
def crypto_configurator():
    """Configuratore regole di estrazione crypto"""
    
    # Use unified menu
    menu_html = get_unified_menu('crypto-configurator')
    
    content = f"""
    {menu_html}
    
    <h2>⚙️ Configuratore Regole Estrazione</h2>
    
    <div class="card">
        <h3>Seleziona Gruppo</h3>
        <div class="form-group">
            <label for="chatSelect">Gruppo Telegram</label>
            <select id="chatSelect" class="form-control">
                <option value="">Seleziona un gruppo...</option>
            </select>
        </div>
    </div>
    
    <div class="card">
        <h3>Regole di Estrazione</h3>
        <div id="rulesContainer">
            <div class="rule-row" id="rule-0">
                <div class="form-group">
                    <label>Nome Campo</label>
                    <input type="text" class="form-control rule-name" placeholder="es. token_address">
                </div>
                <div class="form-group">
                    <label>Testo da Cercare</label>
                    <input type="text" class="form-control search-text" placeholder="es. Address: ">
                </div>
                <div class="form-group">
                    <label>Lunghezza Valore</label>
                    <input type="number" class="form-control value-length" placeholder="44" min="1">
                </div>
                <button type="button" class="btn btn-danger btn-sm" onclick="removeRule(0)">
                    🗑️ Rimuovi
                </button>
            </div>
        </div>
        
        <button type="button" class="btn btn-success" onclick="addRule()">
            ➕ Aggiungi Regola
        </button>
        
        <div class="form-actions">
            <button type="button" class="btn btn-primary" onclick="saveRules()">
                💾 Salva Configurazione
            </button>
        </div>
    </div>
    
    <div class="card">
        <h3>Regole Esistenti</h3>
        <div id="existingRules">
            <p class="text-muted">Seleziona un gruppo per vedere le regole esistenti</p>
        </div>
    </div>
    
    <div class="card">
        <h3>🐳 Stato Container Extractor</h3>
        <div id="containerStatus">
            <p class="text-muted">Seleziona un gruppo per vedere lo stato del container</p>
        </div>
    </div>
    
    <script>
        const apiBase = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port;
        let ruleCounter = 1;
        
        document.addEventListener('DOMContentLoaded', function() {{
            loadUserChats();
        }});
        
        function loadUserChats() {{
            const token = localStorage.getItem('access_token') || localStorage.getItem('session_token');
            
            fetch('/api/telegram/get-chats', {{
                method: 'GET',
                headers: {{
                    'Authorization': 'Bearer ' + token
                }}
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    const select = document.getElementById('chatSelect');
                    select.innerHTML = '<option value="">Seleziona un gruppo...</option>';
                    
                    data.chats.forEach(chat => {{
                        select.innerHTML += `<option value="${{chat.chat_id || chat.id}}">${{chat.title}}</option>`;
                    }});
                    
                    select.addEventListener('change', function() {{
                        loadExistingRules();
                        loadContainerStatus();
                    }});
                }}
            }})
            .catch(error => console.error('Error loading chats:', error));
        }}
        
        function loadContainerStatus() {{
            const chatId = document.getElementById('chatSelect').value;
            if (!chatId) {{
                document.getElementById('containerStatus').innerHTML = '<p class="text-muted">Seleziona un gruppo per vedere lo stato del container</p>';
                return;
            }}
            
            const token = localStorage.getItem('access_token') || localStorage.getItem('session_token');
            
            fetch(apiBase + '/api/crypto/extractors/' + chatId + '/status', {{
                method: 'GET',
                headers: {{
                    'Authorization': 'Bearer ' + token
                }}
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    displayContainerStatus(data);
                }}
            }})
            .catch(error => console.error('Error loading container status:', error));
        }}
        
        function displayContainerStatus(data) {{
            const container = document.getElementById('containerStatus');
            
            if (data.status === 'not_configured' || data.status === 'not_created') {{
                container.innerHTML = `
                    <div class="status warning">
                        <p>⚠️ ${{data.message}}</p>
                    </div>
                `;
                return;
            }}
            
            const statusColor = data.running ? '#28a745' : '#dc3545';
            const statusText = data.running ? 'In esecuzione' : 'Fermato';
            const statusIcon = data.running ? '✅' : '❌';
            
            container.innerHTML = `
                <div style="padding: 20px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                        <div>
                            <h4 style="margin: 0; color: ${{statusColor}};">
                                ${{statusIcon}} ${{statusText}}
                            </h4>
                            <p style="margin: 5px 0; color: #666; font-size: 12px;">
                                Container: ${{data.container_name}}
                            </p>
                        </div>
                        <div>
                            ${{data.running ? `
                                <button class="btn btn-warning btn-sm" onclick="restartExtractor()">
                                    🔄 Riavvia
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="stopExtractor()">
                                    ⏹️ Ferma
                                </button>
                            ` : `
                                <button class="btn btn-success btn-sm" onclick="startExtractor()">
                                    ▶️ Avvia
                                </button>
                            `}}
                        </div>
                    </div>
                    
                    ${{data.running ? `
                        <div class="grid" style="grid-template-columns: repeat(3, 1fr); gap: 15px;">
                            <div style="text-align: center;">
                                <p style="margin: 0; font-size: 24px; font-weight: bold;">
                                    ${{data.message_count || 0}}
                                </p>
                                <p style="margin: 0; color: #666; font-size: 12px;">
                                    Messaggi processati
                                </p>
                            </div>
                            <div style="text-align: center;">
                                <p style="margin: 0; font-size: 24px; font-weight: bold;">
                                    ${{data.memory_usage_mb || 0}} MB
                                </p>
                                <p style="margin: 0; color: #666; font-size: 12px;">
                                    Memoria utilizzata
                                </p>
                            </div>
                            <div style="text-align: center;">
                                <p style="margin: 0; font-size: 24px; font-weight: bold;">
                                    ${{data.cpu_percent || 0}}%
                                </p>
                                <p style="margin: 0; color: #666; font-size: 12px;">
                                    CPU utilizzata
                                </p>
                            </div>
                        </div>
                    ` : ''}}
                </div>
            `;
        }}
        
        function restartExtractor() {{
            const chatId = document.getElementById('chatSelect').value;
            if (!chatId) return;
            
            if (!confirm('Sei sicuro di voler riavviare l\\'extractor?')) return;
            
            const token = localStorage.getItem('access_token') || localStorage.getItem('session_token');
            
            fetch(apiBase + '/api/crypto/extractors/' + chatId + '/restart', {{
                method: 'POST',
                headers: {{
                    'Authorization': 'Bearer ' + token
                }}
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert('Extractor riavviato con successo!');
                    loadContainerStatus();
                }} else {{
                    alert('Errore: ' + (data.error || 'Errore sconosciuto'));
                }}
            }})
            .catch(error => {{
                console.error('Error restarting extractor:', error);
                alert('Errore nel riavvio');
            }});
        }}
        
        function stopExtractor() {{
            const chatId = document.getElementById('chatSelect').value;
            if (!chatId) return;
            
            if (!confirm('Sei sicuro di voler fermare l\\'extractor? Dovrai ricreare le regole per riavviarlo.')) return;
            
            const token = localStorage.getItem('access_token') || localStorage.getItem('session_token');
            
            fetch(apiBase + '/api/crypto/extractors/' + chatId + '/stop', {{
                method: 'POST',
                headers: {{
                    'Authorization': 'Bearer ' + token
                }}
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert('Extractor fermato con successo!');
                    loadContainerStatus();
                }} else {{
                    alert('Errore: ' + (data.error || 'Errore sconosciuto'));
                }}
            }})
            .catch(error => {{
                console.error('Error stopping extractor:', error);
                alert('Errore nell\\'arresto');
            }});
        }}
        
        function startExtractor() {{
            alert('Per avviare l\\'extractor, ricrea le regole e salva la configurazione.');
        }}
        
        function addRule() {{
            const container = document.getElementById('rulesContainer');
            const newRule = document.createElement('div');
            newRule.className = 'rule-row';
            newRule.id = `rule-${{ruleCounter}}`;
            newRule.innerHTML = `
                <div class="form-group">
                    <label>Nome Campo</label>
                    <input type="text" class="form-control rule-name" placeholder="es. trade_score">
                </div>
                <div class="form-group">
                    <label>Testo da Cercare</label>
                    <input type="text" class="form-control search-text" placeholder="es. TradeScore: ">
                </div>
                <div class="form-group">
                    <label>Lunghezza Valore</label>
                    <input type="number" class="form-control value-length" placeholder="2" min="1">
                </div>
                <button type="button" class="btn btn-danger btn-sm" onclick="removeRule(${{ruleCounter}})">
                    🗑️ Rimuovi
                </button>
            `;
            container.appendChild(newRule);
            ruleCounter++;
        }}
        
        function removeRule(id) {{
            const rule = document.getElementById(`rule-${{id}}`);
            if (rule) rule.remove();
        }}
        
        function saveRules() {{
            alert('Funzione saveRules chiamata!');
            
            const token = localStorage.getItem('access_token') || localStorage.getItem('session_token');
            
            fetch(apiBase + '/api/debug/log', {{
                method: 'POST',
                headers: {{
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{
                    message: "SAVE RULES FUNCTION CALLED",
                    data: {{ timestamp: new Date().toISOString() }}
                }})
            }});
            
            const chatId = document.getElementById('chatSelect').value;
            
            if (!chatId) {{
                alert('Seleziona un gruppo');
                return;
            }}
            
            const chatSelect = document.getElementById('chatSelect');
            const selectedOption = chatSelect.options[chatSelect.selectedIndex];
            const chatTitle = selectedOption.text;
            
            const rules = [];
            document.querySelectorAll('.rule-row').forEach(row => {{
                const name = row.querySelector('.rule-name').value;
                const search = row.querySelector('.search-text').value;
                const length = row.querySelector('.value-length').value;
                
                if (name && search && length) {{
                    rules.push({{
                        rule_name: name,
                        search_text: search,
                        value_length: parseInt(length)
                    }});
                }}
            }});
            
            if (rules.length === 0) {{
                alert('Aggiungi almeno una regola valida');
                return;
            }}
            
            const requestData = {{
                source_chat_id: chatId,
                source_chat_title: chatTitle,
                rules: rules
            }};
            
            fetch(apiBase + '/api/debug/log', {{
                method: 'POST',
                headers: {{
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{
                    message: "SAVE RULES ATTEMPT",
                    data: {{
                        chatId: chatId,
                        chatTitle: chatTitle,
                        rulesCount: rules.length,
                        hasToken: !!token
                    }}
                }})
            }});
            
            fetch(apiBase + '/api/crypto/rules', {{
                method: 'POST',
                headers: {{
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify(requestData)
            }})
            .then(response => {{
                fetch(apiBase + '/api/debug/log', {{
                    method: 'POST',
                    headers: {{
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        message: "SAVE RULES RESPONSE STATUS",
                        data: {{ status: response.status }}
                    }})
                }});
                return response.json();
            }})
            .then(data => {{
                fetch(apiBase + '/api/debug/log', {{
                    method: 'POST',
                    headers: {{
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        message: "SAVE RULES RESPONSE DATA",
                        data: data
                    }})
                }});
                
                if (data.code_sent) {{
                    // Telegram code requested - show prompt
                    const code = prompt('Inserisci il codice di verifica ricevuto su Telegram:');
                    if (code) {{
                        // Resend with code
                        const dataWithCode = {{
                            source_chat_id: chatId,
                            source_chat_title: chatTitle,
                            rules: rules,
                            code: code
                        }};
                        
                        fetch(apiBase + '/api/crypto/rules', {{
                            method: 'POST',
                            headers: {{
                                'Authorization': 'Bearer ' + token,
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify(dataWithCode)
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                alert('Regole salvate con successo! Container extractor avviato: ' + (data.container_name || 'N/A'));
                                loadExistingRules();
                                loadContainerStatus();
                            }} else {{
                                alert('Errore nel salvataggio: ' + (data.error || 'Errore sconosciuto'));
                            }}
                        }})
                        .catch(error => {{
                            alert('Errore nella verifica del codice: ' + error.message);
                        }});
                    }}
                }} else if (data.success) {{
                    alert('Regole salvate con successo! Container extractor avviato: ' + (data.container_name || 'N/A'));
                    loadExistingRules();
                    loadContainerStatus();
                }} else {{
                    alert('Errore nel salvataggio: ' + (data.error || 'Errore sconosciuto'));
                }}
            }})
            .catch(error => {{
                fetch(apiBase + '/api/debug/log', {{
                    method: 'POST',
                    headers: {{
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        message: "SAVE RULES ERROR",
                        data: {{ error: error.toString() }}
                    }})
                }});
                console.error('Error saving rules:', error);
                alert('Errore nel salvataggio delle regole: ' + error.message + '. Verifica la connessione al server.');
            }});
        }}
        
        function loadExistingRules() {{
            const chatId = document.getElementById('chatSelect').value;
            if (!chatId) {{
                document.getElementById('existingRules').innerHTML = '<p class="text-muted">Seleziona un gruppo per vedere le regole esistenti</p>';
                return;
            }}
            
            const token = localStorage.getItem('access_token') || localStorage.getItem('session_token');
            
            fetch(apiBase + '/api/crypto/rules?chat_id=' + chatId, {{
                method: 'GET',
                headers: {{
                    'Authorization': 'Bearer ' + token
                }}
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    displayExistingRules(data.rules);
                }}
            }})
            .catch(error => console.error('Error loading rules:', error));
        }}
        
        function displayExistingRules(rules) {{
            const container = document.getElementById('existingRules');
            
            if (rules.length === 0) {{
                container.innerHTML = '<p class="text-muted">Nessuna regola configurata per questo gruppo</p>';
                return;
            }}
            
            let html = '<div class="grid">';
            rules.forEach(rule => {{
                html += `
                    <div class="card">
                        <h4>${{rule.rule_name}}</h4>
                        <p><strong>Cerca:</strong> "${{rule.search_text}}"</p>
                        <p><strong>Lunghezza:</strong> ${{rule.value_length}} caratteri</p>
                        <button class="btn btn-danger btn-sm" onclick="deleteRule(${{rule.id}})">
                            🗑️ Elimina
                        </button>
                    </div>
                `;
            }});
            html += '</div>';
            
            container.innerHTML = html;
        }}
        
        function deleteRule(ruleId) {{
            if (!confirm('Sei sicuro di voler eliminare questa regola?')) return;
            
            const token = localStorage.getItem('access_token') || localStorage.getItem('session_token');
            
            fetch(apiBase + '/api/crypto/rules/' + ruleId, {{
                method: 'DELETE',
                headers: {{
                    'Authorization': 'Bearer ' + token
                }}
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert('Regola eliminata con successo!');
                    loadExistingRules();
                }} else {{
                    alert('Errore: ' + (data.error || 'Errore sconosciuto'));
                }}
            }})
            .catch(error => {{
                console.error('Error deleting rule:', error);
                alert('Errore nell\\'eliminazione');
            }});
        }}
    </script>
    
    <style>
        .rule-row {{
            border: 1px solid #e9ecef;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            background: #f8f9fa;
        }}
        
        .rule-row .form-group {{
            display: inline-block;
            width: 30%;
            margin-right: 2%;
            vertical-align: top;
        }}
        
        .rule-row button {{
            margin-top: 25px;
        }}
    </style>
    """
    
    return render_template_string(
        BASE_TEMPLATE,
        title="Configuratore Crypto",
        subtitle="Configura regole di estrazione dati",
        content=Markup(content)
    )

# Message Listeners API Proxy Routes
@app.route('/api/message-listeners', methods=['GET'])
def api_get_message_listeners():
    """Proxy per recupero message listeners"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend('/api/message-listeners', 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/message-listeners', methods=['POST'])
def api_create_message_listener():
    """Proxy per creazione message listener"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend('/api/message-listeners', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/message-listeners/<int:listener_id>/start', methods=['POST'])
def api_start_message_listener(listener_id):
    """Proxy per avvio message listener"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/message-listeners/{listener_id}/start', 'POST', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/message-listeners/<int:listener_id>/stop', methods=['POST'])
def api_stop_message_listener(listener_id):
    """Proxy per stop message listener"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/message-listeners/{listener_id}/stop', 'POST', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/message-listeners/<int:listener_id>', methods=['DELETE'])
def api_delete_message_listener(listener_id):
    """Proxy per eliminazione message listener"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/message-listeners/{listener_id}', 'DELETE', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/message-listeners/<int:listener_id>/elaborations', methods=['GET'])
def api_get_elaborations(listener_id):
    """Proxy per recupero elaborazioni"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/message-listeners/{listener_id}/elaborations', 'GET', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/message-listeners/<int:listener_id>/elaborations', methods=['POST'])
def api_create_elaboration(listener_id):
    """Proxy per creazione elaborazione"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    data = request.get_json()
    result = call_backend(f'/api/message-listeners/{listener_id}/elaborations', 'POST', data, auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/elaborations/<int:elaboration_id>/activate', methods=['POST'])
def api_activate_elaboration(elaboration_id):
    """Proxy per attivazione elaborazione"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/elaborations/{elaboration_id}/activate', 'POST', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/elaborations/<int:elaboration_id>/deactivate', methods=['POST'])
def api_deactivate_elaboration(elaboration_id):
    """Proxy per disattivazione elaborazione"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/elaborations/{elaboration_id}/deactivate', 'POST', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/elaborations/<int:elaboration_id>', methods=['DELETE'])
def api_delete_elaboration(elaboration_id):
    """Proxy per eliminazione elaborazione"""
    if not is_authenticated():
        return jsonify({'error': 'Autenticazione richiesta'}), 401
    
    result = call_backend(f'/api/elaborations/{elaboration_id}', 'DELETE', auth_token=session['session_token'])
    return jsonify(result or {'error': 'Backend non disponibile'})

@app.route('/api/debug/log', methods=['POST'])
def proxy_debug_log():
    """Proxy debug log to backend"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    data = request.get_json()
    
    response = call_backend('/api/debug/log', 'POST', data, token)
    if response:
        return jsonify(response), 200
    else:
        return jsonify({"success": False, "error": "Backend call failed"}), 500

@app.route('/api/crypto/rules', methods=['GET', 'POST'])
def proxy_crypto_rules():
    """Proxy crypto rules to backend"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if request.method == 'GET':
        chat_id = request.args.get('chat_id')
        response = call_backend(f'/api/crypto/rules?chat_id={chat_id}', 'GET', None, token)
    else:
        data = request.get_json()
        response = call_backend('/api/crypto/rules', 'POST', data, token)
    
    if response:
        return jsonify(response), 200
    else:
        return jsonify({"success": False, "error": "Backend call failed"}), 500

@app.route('/api/crypto/extractors/<source_chat_id>/status', methods=['GET'])
def proxy_extractor_status(source_chat_id):
    """Proxy extractor status to backend"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    response = call_backend(f'/api/crypto/extractors/{source_chat_id}/status', 'GET', None, token)
    
    if response:
        return jsonify(response), 200
    else:
        return jsonify({"success": False, "error": "Backend call failed"}), 500

@app.route('/api/crypto/extractors/<source_chat_id>/restart', methods=['POST'])
def proxy_extractor_restart(source_chat_id):
    """Proxy extractor restart to backend"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    response = call_backend(f'/api/crypto/extractors/{source_chat_id}/restart', 'POST', None, token)
    
    if response:
        return jsonify(response), 200
    else:
        return jsonify({"success": False, "error": "Backend call failed"}), 500

@app.route('/api/crypto/extractors/<source_chat_id>/stop', methods=['POST'])
def proxy_extractor_stop(source_chat_id):
    """Proxy extractor stop to backend"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    response = call_backend(f'/api/crypto/extractors/{source_chat_id}/stop', 'POST', None, token)
    
    if response:
        return jsonify(response), 200
    else:
        return jsonify({"success": False, "error": "Backend call failed"}), 500

@app.route('/api/crypto/rules/<rule_id>', methods=['DELETE'])
def proxy_delete_crypto_rule(rule_id):
    """Proxy delete crypto rule to backend"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    response = call_backend(f'/api/crypto/rules/{rule_id}', 'DELETE', None, token)
    
    if response:
        return jsonify(response), 200
    else:
        return jsonify({"success": False, "error": "Backend call failed"}), 500

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