// VERSIONE SEMPLIFICATA E DEBUG-FRIENDLY
console.log('🔍 [CHATS] Script inizializzato');

// Variabili globali
let allChats = [];
let filteredChats = [];

// Funzioni di utilità base
function showLoading() {
    console.log('🔍 [CHATS] showLoading chiamata');
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(el => {
        el.style.display = 'block';
        console.log('🔍 [CHATS] Loading element mostrato:', el);
    });
}

function hideLoading() {
    console.log('🔍 [CHATS] hideLoading chiamata');
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(el => {
        el.style.display = 'none';
        console.log('🔍 [CHATS] Loading element nascosto:', el);
    });
}

function showMessage(message, type = 'info') {
    console.log(`🔍 [CHATS] showMessage: ${message} (${type})`);
    
    const container = document.getElementById('errorContainer');
    if (container) {
        container.style.display = 'block';
        container.className = `status ${type}`;
        container.innerHTML = `<p>${message}</p>`;
    }
}

function showError(message) {
    console.error('🔍 [CHATS] showError:', message);
    showMessage(message, 'error');
}

// Funzione per mostrare il form di riautenticazione Telegram
function showTelegramReauthForm() {
    console.log('🔍 [CHATS] Mostrando form riautenticazione Telegram');
    
    hideLoading();
    
    const container = document.getElementById('chatsContainer');
    if (container) {
        container.style.display = 'block';
        container.innerHTML = `
            <div class="card" style="max-width: 600px; margin: 0 auto; padding: 30px;">
                <h3>🔐 Sessione Telegram Scaduta</h3>
                <p>La tua sessione Telegram è scaduta. Per continuare a utilizzare il servizio, devi riautenticarti.</p>
                
                <div id="reauthForm">
                    <p>Clicca il pulsante qui sotto per ricevere un nuovo codice di verifica via SMS:</p>
                    
                    <button id="requestCodeBtn" class="btn btn-primary" onclick="requestTelegramCode()">
                        📱 Richiedi Codice di Verifica
                    </button>
                    
                    <div id="codeInputSection" style="display: none; margin-top: 20px;">
                        <div class="form-group">
                            <label for="verificationCode">Inserisci il codice ricevuto:</label>
                            <input type="text" id="verificationCode" class="form-control" 
                                   placeholder="12345" maxlength="5" 
                                   style="font-size: 24px; text-align: center; letter-spacing: 10px;">
                        </div>
                        
                        <button id="verifyCodeBtn" class="btn btn-success" onclick="verifyTelegramCode()">
                            ✅ Verifica Codice
                        </button>
                    </div>
                    
                    <div id="reauthMessage" style="margin-top: 20px;"></div>
                </div>
                
                <hr style="margin: 30px 0;">
                
                <p style="color: #666; font-size: 14px;">
                    <strong>Nota:</strong> Questo non è un problema con la tua password o account. 
                    Telegram richiede periodicamente una nuova autenticazione per motivi di sicurezza.
                </p>
            </div>
        `;
    }
}

// Funzione per mostrare il messaggio di configurazione credenziali API
function showCredentialsSetupMessage() {
    console.log('🔍 [CHATS] Mostrando messaggio configurazione credenziali');
    
    hideLoading();
    
    const container = document.getElementById('chatsContainer');
    if (container) {
        container.style.display = 'block';
        container.innerHTML = `
            <div class="card" style="max-width: 600px; margin: 0 auto; padding: 30px;">
                <h3>🔑 Credenziali API Mancanti</h3>
                <p>Per utilizzare le funzionalità Telegram, devi prima configurare le tue credenziali API.</p>
                
                <div style="margin: 20px 0;">
                    <h4>📋 Come ottenere le credenziali:</h4>
                    <ol style="text-align: left; margin: 20px 0;">
                        <li>Vai su <a href="https://my.telegram.org" target="_blank">my.telegram.org</a></li>
                        <li>Accedi con il tuo numero di telefono</li>
                        <li>Vai su "API development tools"</li>
                        <li>Copia <strong>API ID</strong> e <strong>API Hash</strong></li>
                    </ol>
                </div>
                
                <div style="margin: 30px 0;">
                    <a href="/profile" class="btn btn-primary" style="margin-right: 10px;">
                        ⚙️ Configura Credenziali
                    </a>
                    <a href="/dashboard" class="btn btn-secondary">
                        🏠 Torna alla Dashboard
                    </a>
                </div>
                
                <hr style="margin: 30px 0;">
                
                <p style="color: #666; font-size: 14px;">
                    <strong>Nota:</strong> Le credenziali API sono necessarie per connettersi ai server Telegram 
                    e utilizzare funzionalità come la lista chat, il logging dei messaggi, ecc.
                </p>
            </div>
        `;
    }
}

// Richiedi nuovo codice Telegram
async function requestTelegramCode() {
    console.log('🔍 [CHATS] Richiesta nuovo codice Telegram');
    
    const btn = document.getElementById('requestCodeBtn');
    const messageDiv = document.getElementById('reauthMessage');
    
    if (btn) btn.disabled = true;
    if (messageDiv) messageDiv.innerHTML = '<p class="text-info">⏳ Invio codice in corso...</p>';
    
    try {
        const response = await fetch('/api/auth/reactivate-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('session_token') || localStorage.getItem('access_token')}`
            }
        });
        
        const result = await response.json();
        console.log('🔍 [CHATS] Risultato richiesta codice:', result);
        
        if (result.success) {
            // Mostra sezione input codice
            const codeSection = document.getElementById('codeInputSection');
            if (codeSection) codeSection.style.display = 'block';
            
            if (messageDiv) {
                messageDiv.innerHTML = `
                    <p class="text-success">✅ Codice inviato al numero ${result.phone || 'registrato'}</p>
                    <p>Controlla i tuoi messaggi Telegram e inserisci il codice qui sopra.</p>
                `;
            }
            
            // Focus sul campo codice
            const codeInput = document.getElementById('verificationCode');
            if (codeInput) codeInput.focus();
            
            // Nascondi il pulsante di richiesta
            if (btn) btn.style.display = 'none';
        } else {
            if (messageDiv) {
                messageDiv.innerHTML = `<p class="text-danger">❌ Errore: ${result.error || 'Impossibile inviare il codice'}</p>`;
            }
            if (btn) btn.disabled = false;
        }
    } catch (error) {
        console.error('🔍 [CHATS] Errore richiesta codice:', error);
        if (messageDiv) {
            messageDiv.innerHTML = '<p class="text-danger">❌ Errore di connessione. Riprova.</p>';
        }
        if (btn) btn.disabled = false;
    }
}

// Verifica codice Telegram
async function verifyTelegramCode() {
    console.log('🔍 [CHATS] Verifica codice Telegram');
    
    const codeInput = document.getElementById('verificationCode');
    const btn = document.getElementById('verifyCodeBtn');
    const messageDiv = document.getElementById('reauthMessage');
    
    if (!codeInput || !codeInput.value) {
        if (messageDiv) {
            messageDiv.innerHTML = '<p class="text-warning">⚠️ Inserisci il codice ricevuto</p>';
        }
        return;
    }
    
    const code = codeInput.value.trim();
    
    if (btn) btn.disabled = true;
    if (messageDiv) messageDiv.innerHTML = '<p class="text-info">⏳ Verifica in corso...</p>';
    
    try {
        const response = await fetch('/api/auth/verify-session-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('session_token') || localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({ code })
        });
        
        const result = await response.json();
        console.log('🔍 [CHATS] Risultato verifica codice:', result);
        
        if (result.success) {
            if (messageDiv) {
                messageDiv.innerHTML = '<p class="text-success">✅ Sessione riattivata con successo! Ricaricamento chat...</p>';
            }
            
            // Aspetta un momento e ricarica le chat
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            if (messageDiv) {
                messageDiv.innerHTML = `<p class="text-danger">❌ Codice non valido: ${result.error || 'Riprova'}</p>`;
            }
            if (btn) btn.disabled = false;
            if (codeInput) {
                codeInput.value = '';
                codeInput.focus();
            }
        }
    } catch (error) {
        console.error('🔍 [CHATS] Errore verifica codice:', error);
        if (messageDiv) {
            messageDiv.innerHTML = '<p class="text-danger">❌ Errore di connessione. Riprova.</p>';
        }
        if (btn) btn.disabled = false;
    }
}

// Funzione di caricamento SEMPLIFICATA
async function loadChats() {
    console.log('🔍 [CHATS] === INIZIO loadChats() ===');
    
    // Update debug info
    const debugInfo = document.getElementById('debugInfo');
    if (debugInfo) {
        debugInfo.innerHTML += '<p>✅ loadChats() AVVIATA</p>';
    }
    
    showLoading();
    showMessage('🔄 Caricamento chat in corso...', 'info');
    
    try {
        console.log('🔍 [CHATS] Preparazione richiesta API...');
        
        // Token check
        const sessionToken = localStorage.getItem('session_token');
        const accessToken = localStorage.getItem('access_token');
        console.log('🔍 [CHATS] Tokens disponibili:', {
            sessionToken: sessionToken ? 'PRESENTE' : 'MISSING',
            accessToken: accessToken ? 'PRESENTE' : 'MISSING'
        });
        
        if (debugInfo) {
            debugInfo.innerHTML += `<p>🔍 Token check: session=${sessionToken ? 'OK' : 'MISSING'}, access=${accessToken ? 'OK' : 'MISSING'}</p>`;
        }
        
        // Costruisci headers
        const headers = {
            'Content-Type': 'application/json'
        };
        
        const token = sessionToken || accessToken;
        if (token) {
            headers.Authorization = `Bearer ${token}`;
            console.log('🔍 [CHATS] Authorization header aggiunto');
        } else {
            console.error('🔍 [CHATS] NESSUN TOKEN DISPONIBILE!');
            throw new Error('Nessun token di autenticazione disponibile');
        }
        
        console.log('🔍 [CHATS] Headers preparati:', headers);
        
        // Chiamata API diretta con fetch nativo
        console.log('🔍 [CHATS] Chiamata fetch...');
        
        if (debugInfo) {
            debugInfo.innerHTML += '<p>🔄 Chiamata API in corso...</p>';
        }
        
        const response = await fetch('/api/telegram/get-chats', {
            method: 'GET',
            headers: headers
        });
        
        console.log('🔍 [CHATS] Response ricevuta:', {
            status: response.status,
            ok: response.ok,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries())
        });
        
        if (debugInfo) {
            debugInfo.innerHTML += `<p>📡 Response status: ${response.status}</p>`;
        }
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('🔍 [CHATS] Response non ok:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('🔍 [CHATS] JSON parsato:', result);
        
        if (debugInfo) {
            debugInfo.innerHTML += `<p>✅ JSON ricevuto: ${JSON.stringify(result).substring(0, 200)}...</p>`;
        }
        
        hideLoading();
        
        // ✅ NUOVO: Gestione specifica per sessione Telegram scaduta
        if (!result.success && result.error_code === 'TELEGRAM_SESSION_EXPIRED') {
            console.log('🔍 [CHATS] Sessione Telegram scaduta rilevata');
            
            if (debugInfo) {
                debugInfo.innerHTML += '<p>🔐 TELEGRAM SESSION EXPIRED - Riautenticazione richiesta</p>';
            }
            
            // Mostra il form di riautenticazione
            showTelegramReauthForm();
            return;
        }
        
        // ✅ NUOVO: Gestione credenziali API mancanti
        if (!result.success && result.error_code === 'API_CREDENTIALS_NOT_SET') {
            console.log('🔍 [CHATS] Credenziali API mancanti rilevate');
            
            if (debugInfo) {
                debugInfo.innerHTML += '<p>🔑 API CREDENTIALS NOT SET - Configurazione richiesta</p>';
            }
            
            // Mostra messaggio per configurare credenziali
            showCredentialsSetupMessage();
            return;
        }
        
        if (result.success) {
            console.log('🔍 [CHATS] Successo! Chat trovate:', result.chats.length);
            
            allChats = result.chats || [];
            
            if (debugInfo) {
                debugInfo.innerHTML += `<p>🎉 SUCCESS: ${allChats.length} chat caricate</p>`;
            }
            
            // Mostra risultato semplificato
            showMessage(`✅ Successo! ${allChats.length} chat caricate`, 'success');
            
            renderChats();
            
            const chatsContainer = document.getElementById('chatsContainer');
            if (chatsContainer) {
                chatsContainer.style.display = 'block';
            }
            
        } else {
            console.error('🔍 [CHATS] API error:', result.error);
            
            if (debugInfo) {
                debugInfo.innerHTML += `<p>❌ API ERROR: ${result.error}</p>`;
            }
            
            throw new Error(result.error || 'Errore API sconosciuto');
        }
        
    } catch (error) {
        console.error('🔍 [CHATS] ERRORE FATALE:', error);
        
        hideLoading();
        
        if (debugInfo) {
            debugInfo.innerHTML += `<p>💥 EXCEPTION: ${error.message}</p>`;
        }
        
        showError(`Errore: ${error.message}`);
    }
    
    console.log('🔍 [CHATS] === FINE loadChats() ===');
}

// Funzione di rendering chat SEMPLIFICATA
function renderChats() {
    console.log('🔍 [CHATS] renderChats chiamata, chat da mostrare:', allChats.length);
    
    const container = document.getElementById('chatsList');
    if (!container) {
        console.error('🔍 [CHATS] Container chatsList non trovato!');
        return;
    }
    
    if (allChats.length === 0) {
        container.innerHTML = '<p>Nessuna chat trovata.</p>';
        return;
    }
    
    // Rendering semplificato
    container.innerHTML = allChats.map(chat => `
        <div class="chat-item" style="padding: 10px; border: 1px solid #ddd; margin-bottom: 10px;">
            <h4>${chat.title || 'Chat senza titolo'}</h4>
            <p>ID: ${chat.id}</p>
            <p>Tipo: ${chat.type}</p>
            <button onclick="startLogging(${JSON.stringify(chat)})" class="btn btn-success">Attiva Logging</button>
        </div>
    `).join('');
    
    console.log('🔍 [CHATS] Rendering completato');
}

// Nuova funzione per attivare logging
async function startLogging(chat) {
    console.log('🔍 [LOGGING] Attivazione logging per chat:', chat);
    
    try {
        showLoading();
        
        const response = await fetch('/api/logging/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('session_token') || localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                chat_id: chat.id.toString(),
                chat_title: chat.title || '',
                chat_username: chat.username || '',
                chat_type: chat.type || 'unknown'
            })
        });
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showMessage(`✅ Logging attivato per ${chat.title}! Container: ${result.container_name}`, 'success');
        } else {
            showMessage(`❌ Errore: ${result.error}`, 'error');
        }
    } catch (error) {
        hideLoading();
        showMessage(`❌ Errore di connessione: ${error.message}`, 'error');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listener principale SEMPLIFICATO
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 [CHATS] DOMContentLoaded triggered');
    
    const debugInfo = document.getElementById('debugInfo');
    if (debugInfo) {
        debugInfo.innerHTML = '<p>🚀 Script inizializzato</p>';
        
        // Info sui token
        const sessionToken = localStorage.getItem('session_token');
        const accessToken = localStorage.getItem('access_token');
        
        debugInfo.innerHTML += `<p>🔐 session_token: ${sessionToken ? 'PRESENTE' : 'MISSING'}</p>`;
        debugInfo.innerHTML += `<p>🔐 access_token: ${accessToken ? 'PRESENTE' : 'MISSING'}</p>`;
        
        // Info sui DOM elements
        debugInfo.innerHTML += `<p>🏗️ chatsList: ${document.getElementById('chatsList') ? 'FOUND' : 'MISSING'}</p>`;
        debugInfo.innerHTML += `<p>🏗️ chatsContainer: ${document.getElementById('chatsContainer') ? 'FOUND' : 'MISSING'}</p>`;
        debugInfo.innerHTML += `<p>🏗️ errorContainer: ${document.getElementById('errorContainer') ? 'FOUND' : 'MISSING'}</p>`;
    }
    
    // Avvia caricamento senza controlli di autenticazione complessi
    console.log('🔍 [CHATS] Avvio loadChats() diretto...');
    loadChats();
});

console.log('🔍 [CHATS] Script completamente caricato e pronto'); 