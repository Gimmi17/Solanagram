let allChats = [];
let filteredChats = [];

// Performance optimization: Simple cache system
const chatCache = {
    data: null,
    timestamp: null,
    ttl: 60000, // 1 minute TTL for chat cache
    
    isValid() {
        return this.data && this.timestamp && (Date.now() - this.timestamp) < this.ttl;
    },
    
    set(data) {
        this.data = data;
        this.timestamp = Date.now();
        console.log('🔄 [CACHE] Chat data cached');
    },
    
    get() {
        if (this.isValid()) {
            console.log('✅ [CACHE] Using cached chat data');
            return this.data;
        }
        return null;
    },
    
    clear() {
        this.data = null;
        this.timestamp = null;
        console.log('🗑️ [CACHE] Chat cache cleared');
    }
};

// Funzioni di utilità
function showLoading() {
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(el => el.style.display = 'block');
}

function hideLoading() {
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(el => el.style.display = 'none');
}

function showMessage(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `status ${type}`;
    toast.innerHTML = message; // Cambiato da textContent a innerHTML per supportare HTML
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.maxWidth = '400px';
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, type === 'error' ? 7000 : 3000); // Errori rimangono più a lungo
}

// Funzione per verificare autenticazione prima di procedere
async function checkAuthenticationBeforeLoad() {
    console.log('🔍 [AUTH] Verifica autenticazione...');
    
    const sessionToken = localStorage.getItem('session_token');
    const accessToken = localStorage.getItem('access_token');
    
    // Se non ci sono token, redirect immediato al login
    if (!sessionToken && !accessToken) {
        console.warn('🔒 [AUTH] Nessun token trovato, redirect al login');
        showMessage(`
            <div style="text-align: center;">
                <strong>🔒 Accesso Richiesto</strong><br>
                Non sei autenticato.<br>
                <small>Verrai reindirizzato al login...</small>
            </div>
        `, 'warning');
        
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
        return false;
    }
    
    // Verifica se i token sono nel formato corretto (JWT)
    const token = sessionToken || accessToken;
    const tokenParts = token.split('.');
    if (tokenParts.length !== 3) {
        console.warn('🔒 [AUTH] Token formato non valido, pulizia e redirect');
        clearExpiredTokens();
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
        return false;
    }
    
    // Prova a sincronizzare con Flask session
    try {
        const syncResult = await fetch('/api/auth/sync-session', {
            method: 'GET',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (syncResult.ok) {
            const syncData = await syncResult.json();
            if (syncData.success) {
                console.log('🔍 [AUTH] Sincronizzazione Flask session riuscita');
                // Aggiorna localStorage se necessario
                if (syncData.session_token && syncData.session_token !== sessionToken) {
                    localStorage.setItem('session_token', syncData.session_token);
                }
                return true;
            }
        }
        
        // Se sync fallisce, proviamo a validare il token direttamente con il backend
        console.log('🔍 [AUTH] Sync fallita, validazione diretta del token...');
        const validateResult = await fetch('/api/auth/validate-session', {
            method: 'GET',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (validateResult.ok) {
            const validateData = await validateResult.json();
            if (validateData.success && validateData.session_valid) {
                console.log('🔍 [AUTH] Token valido, procediamo');
                return true;
            }
        }
        
    } catch (error) {
        console.error('🔒 [AUTH] Errore durante verifica:', error);
    }
    
    // Se arriviamo qui, l'autenticazione è fallita
    console.warn('🔒 [AUTH] Autenticazione fallita, redirect al login');
    showMessage(`
        <div style="text-align: center;">
            <strong>🔒 Sessione Scaduta</strong><br>
            I tuoi token di accesso non sono più validi.<br>
            <small>Verrai reindirizzato al login...</small>
        </div>
    `, 'warning');
    
    clearExpiredTokens();
    setTimeout(() => {
        window.location.href = '/login';
    }, 3000);
    return false;
}

// Funzione per pulire token scaduti
function clearExpiredTokens() {
    localStorage.removeItem('session_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('temp_phone');
    localStorage.removeItem('temp_password');
    localStorage.removeItem('temp_user_id');
}

// Funzione per rilevare token scaduti/invalidi
function isTokenExpiredError(error) {
    if (!error) return false;
    
    const expiredMessages = [
        'Not enough segments',
        'Token expired', 
        'Invalid token',
        'JWT token has expired',
        'Authentication failed',
        'Signature verification failed'
    ];
    
    return expiredMessages.some(msg => error.includes(msg));
}

// Funzione per rilevare sessione Telegram scaduta
function isTelegramSessionExpired(error) {
    if (!error) return false;
    
    const telegramExpiredMessages = [
        'Authorization lost. Please log in again',
        'User +39',  // Inizia con numero di telefono
        'is not authorized',
        'Please log in again'
    ];
    
    return telegramExpiredMessages.some(msg => error.includes(msg));
}

// Funzione per forzare logout su token scaduto
function handleTokenExpired() {
    console.log('🔒 Token JWT scaduto rilevato, pulizia e redirect al login');
    
    // Clear cache on token expiry for performance optimization
    chatCache.clear();
    console.log('🔍 [CACHE] Cache cleared due to JWT token expiry');
    
    clearExpiredTokens();
    
    showMessage(`
        <div style="text-align: center;">
            <strong>🔒 Token Scaduto</strong><br>
            Il tuo token di accesso è scaduto.<br>
            <small>Verrai reindirizzato al login...</small>
        </div>
    `, 'warning');
    
    setTimeout(() => {
        window.location.href = '/login';
    }, 3000);
}

// Funzione per gestire sessione Telegram scaduta
function handleTelegramSessionExpired() {
    console.log('📱 Sessione Telegram scaduta rilevata');
    
    // Clear cache on session expiry for performance optimization
    chatCache.clear();
    console.log('🔍 [CACHE] Cache cleared due to Telegram session expiry');
    
    showMessage(`
        <div style="text-align: center; padding: 20px;">
            <strong>📱 Sessione Telegram Scaduta</strong><br><br>
            La tua sessione Telegram è scaduta ma il tuo account è ancora valido.<br>
            <strong>Riattiva la sessione per continuare.</strong><br><br>
            <a href="/dashboard" style="display: inline-block; background: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                🔄 Riattiva Sessione Telegram
            </a><br><br>
            <small style="color: #666;">Non perdere i tuoi dati: è necessario solo verificare il codice Telegram</small>
        </div>
    `, 'warning');
    
    // Nasconde contenuto e mostra messaggio
    document.getElementById('chatsContainer').style.display = 'none';
    document.getElementById('errorContainer').style.display = 'none';
    
    // Non fare logout automatico - l'utente deve scegliere
}

// Funzione per inviare log al server
async function sendLogToServer(level, message, data = null) {
    try {
        await fetch('/api/debug/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                level: level,
                message: message,
                data: data,
                timestamp: new Date().toISOString(),
                url: window.location.href
            })
        });
    } catch (error) {
        console.error('Errore nell\'invio log:', error);
    }
}

// Override console methods per catturare tutti i log
const originalConsole = {
    log: console.log,
    error: console.error,
    warn: console.warn,
    info: console.info
};

console.log = function(...args) {
    originalConsole.log.apply(console, args);
    sendLogToServer('log', args.join(' '));
};

console.error = function(...args) {
    originalConsole.error.apply(console, args);
    sendLogToServer('error', args.join(' '));
};

console.warn = function(...args) {
    originalConsole.warn.apply(console, args);
    sendLogToServer('warn', args.join(' '));
};

console.info = function(...args) {
    originalConsole.info.apply(console, args);
    sendLogToServer('info', args.join(' '));
};

// Cattura errori JavaScript non gestiti
window.addEventListener('error', function(event) {
    console.error('JavaScript Error:', event.error || event.message, 'at', event.filename, 'line', event.lineno);
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled Promise Rejection:', event.reason);
});

// Test immediato per verificare che JavaScript funzioni
console.log('🔍 [DEBUG] Script caricato');

// Debug localStorage
const sessionToken = localStorage.getItem('session_token');
const accessToken = localStorage.getItem('access_token');
console.log('🔍 [DEBUG] localStorage session_token:', sessionToken ? 'PRESENTE' : 'MISSING');
console.log('🔍 [DEBUG] localStorage access_token:', accessToken ? 'PRESENTE' : 'MISSING');

// Carica le chat all'avvio con verifica autenticazione
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🔍 [DEBUG] DOMContentLoaded triggered');
    document.getElementById('debugInfo').innerHTML = '<p>✅ DOMContentLoaded eseguito</p>';
    document.getElementById('debugInfo').innerHTML += '<p>🔍 session_token: ' + (sessionToken ? 'PRESENTE' : 'MISSING') + '</p>';
    document.getElementById('debugInfo').innerHTML += '<p>🔍 access_token: ' + (accessToken ? 'PRESENTE' : 'MISSING') + '</p>';
    
    // Verifica autenticazione prima di procedere
    const isAuthenticated = await checkAuthenticationBeforeLoad();
    
    if (isAuthenticated) {
        console.log('🔍 [DEBUG] Autenticazione verificata, procediamo con loadChats');
        document.getElementById('debugInfo').innerHTML += '<p>✅ Autenticazione verificata</p>';
        loadChats();
    } else {
        console.log('🔍 [DEBUG] Autenticazione fallita, non procediamo');
        document.getElementById('debugInfo').innerHTML += '<p>❌ Autenticazione fallita</p>';
    }
});

async function loadChats() {
    console.log('🔍 [DEBUG] loadChats() chiamata');
    document.getElementById('debugInfo').innerHTML += '<p>✅ loadChats() chiamata</p>';
    
    // Check cache first for performance optimization
    const cachedData = chatCache.get();
    if (cachedData) {
        console.log('🔍 [DEBUG] Usando dati dalla cache');
        document.getElementById('debugInfo').innerHTML += '<p>⚡ Usando cache (performance ottimizzata)</p>';
        renderChatsFromCache(cachedData);
        return;
    }
    
    showLoading();
    
    try {
        console.log('🔍 [DEBUG] Chiamando API /api/telegram/get-chats');
        document.getElementById('debugInfo').innerHTML += '<p>🔄 Chiamando API...</p>';
        
        // Use optimized timeout for chat loading (20 seconds)
        const result = await makeRequest('/api/telegram/get-chats', {
            method: 'GET'
        }, 20000);
        
        console.log('🔍 [DEBUG] Risposta API ricevuta:', result);
        document.getElementById('debugInfo').innerHTML += '<p>✅ API chiamata completata</p>';
        hideLoading();
        
        // Controlla se il risultato è null (token scaduto gestito da makeRequest)
        if (result === null) {
            console.log('🔍 [DEBUG] makeRequest ha restituito null, probabilmente token scaduto');
            return; // makeRequest ha già gestito il logout
        }
        
        if (result.success) {
            console.log('🔍 [DEBUG] API success, chat ricevute:', result.chats.length);
            document.getElementById('debugInfo').innerHTML += '<p>✅ API success, chat ricevute: ' + result.chats.length + '</p>';
            
            // Cache the successful result for performance
            chatCache.set(result);
            
            // Render the chats
            renderChatsFromCache(result);
            
        } else {
            console.error('🔍 [DEBUG] API error:', result.error);
            document.getElementById('debugInfo').innerHTML += '<p>❌ API error: ' + result.error + '</p>';
            
            // Controlla se è un errore di sessione Telegram scaduta
            if (isTelegramSessionExpired(result.error)) {
                console.log('🔍 [DEBUG] Sessione Telegram scaduta rilevata');
                handleTelegramSessionExpired();
            } else if (isTokenExpiredError(result.error)) {
                console.log('🔍 [DEBUG] Token JWT scaduto rilevato');
                handleTokenExpired();
            } else {
                showError(result.error || 'Errore durante il caricamento chat');
            }
        }
    } catch (error) {
        console.error('🔍 [DEBUG] Exception in loadChats:', error);
        document.getElementById('debugInfo').innerHTML += '<p>❌ Exception: ' + error.message + '</p>';
        hideLoading();
        
        // Controlla se è un errore di sessione Telegram scaduta o token JWT scaduto
        if (isTelegramSessionExpired(error.message)) {
            console.log('🔍 [DEBUG] Exception sessione Telegram scaduta rilevata');
            handleTelegramSessionExpired();
        } else if (isTokenExpiredError(error.message)) {
            console.log('🔍 [DEBUG] Exception token JWT scaduto rilevata');
            handleTokenExpired();
        } else {
            showError('Errore di connessione');
        }
    }
}

function renderChatsFromCache(result) {
    console.log('🔍 [DEBUG] Rendering chats from cache/API result');
    allChats = result.chats;
    
    // Mostra le prime 3 chat per debug + info cache
    const firstChats = result.chats.slice(0, 3);
    const cacheInfo = chatCache.isValid() ? '⚡ Dati dalla cache (performance ottimizzata)' : '🌐 Dati dall\'API';
    
    document.getElementById('chatsList').innerHTML = `
        <div style="background: #e3f2fd; padding: 10px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #2196f3;">
            <strong>📊 Performance Status:</strong> ${cacheInfo}<br>
            <small>Cache TTL: ${Math.round((chatCache.ttl - (Date.now() - (chatCache.timestamp || 0))) / 1000)}s rimanenti</small>
        </div>
        <h3>Prime 3 chat trovate (${result.chats.length} totali):</h3>
        ${firstChats.map(chat => `
            <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 5px;">
                <strong>${chat.title}</strong> (ID: ${chat.id})
            </div>
        `).join('')}
        
        <div style="margin-top: 20px; padding: 15px; background: #f0f9ff; border-radius: 8px; border: 1px solid #e0f2fe;">
            <h4>🚀 Performance Optimizations Attive:</h4>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li>✅ Cache intelligente (TTL: 60s)</li>
                <li>✅ Timeout ottimizzati (20s per chat, 25s per login)</li>
                <li>✅ Gestione errori avanzata</li>
                <li>✅ Feedback progressivo utente</li>
            </ul>
            <small style="color: #666;">
                Sistema ottimizzato per ridurre i tempi di attesa e migliorare l'esperienza utente.
            </small>
        </div>
    `;
    
    document.getElementById('chatsContainer').style.display = 'block';
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorContainer').style.display = 'block';
    document.getElementById('chatsContainer').style.display = 'none';
} 