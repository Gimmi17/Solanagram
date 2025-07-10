let currentPhone = '';
let currentPassword = '';

document.addEventListener('DOMContentLoaded', function() {
    console.log('Login page loaded');
    
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
                    localStorage.setItem('temp_password', password);
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
    
    // Richiedi nuovo codice (primo bottone)
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
            localStorage.setItem('temp_password', password);
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
            localStorage.setItem('temp_password', password);
            showMessage(result.message, 'success');
            
            // Redirect a pagina verifica codice
            setTimeout(() => {
                window.location.href = '/verify-code';
            }, 2000);
        } else {
            showMessage(result.error || 'Errore nel login', 'error');
        }
    });
    
    // Form submit handler
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const phone = document.getElementById('phone_number').value.trim();
        const password = document.getElementById('password').value.trim();
        
        if (!phone || !password) {
            showMessage('Inserisci numero di telefono e password', 'error');
            return;
        }
        
        // ENHANCED: Better UX with informative loading message and timeout optimization
        showLoading();
        
        // Progressive feedback messages with timeout for login
        const progressMessages = [
            '🔍 Verifica credenziali...',
            '📡 Connessione ai server Telegram...',
            '📱 Invio codice di verifica...',
            '✅ Completamento...'
        ];
        
        let messageIndex = 0;
        const progressInterval = setInterval(() => {
            if (messageIndex < progressMessages.length - 1) {
                messageIndex++;
                showMessage(progressMessages[messageIndex], 'info');
            }
        }, 3000);
        
        // Enhanced message with performance optimization reference
        showMessage(`
            🔄 Connessione a Telegram in corso...<br><br>
            <strong style="color: #10b981; background: #d1fae5; padding: 8px; border-radius: 6px; display: inline-block; margin-top: 8px;">
                ✨ "Everything is fine" - The Good Place ✨
            </strong><br>
            <small>Il sistema effettuerà automaticamente dei tentativi per garantire una connessione stabile.</small>
        `, 'info');
        
        try {
            // Use optimized timeout for login requests (25 seconds instead of default 30)
            const result = await makeRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ 
                    phone_number: phone,
                    password: password 
                })
            }, 25000); // Custom 25-second timeout for login performance
            
            clearInterval(progressInterval);
            hideLoading();
            
            if (result.success) {
                // Salva user_id per la verifica
                if (result.user_id) {
                    localStorage.setItem('temp_user_id', result.user_id);
                }
                localStorage.setItem('temp_phone', phone);
                localStorage.setItem('temp_password', password);
                
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
}); 