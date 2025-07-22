document.addEventListener('DOMContentLoaded', function() {
    console.log('Verify code page loaded');
    
    // Popola il numero di telefono dal localStorage
    const savedPhone = localStorage.getItem('temp_phone');
    if (savedPhone) {
        document.getElementById('display_phone').value = savedPhone;
        
        // ✅ NUOVO: Controlla se c'è un codice in cache disponibile
        checkCachedCode(savedPhone);
    } else {
        // Se non c'è numero salvato, torna al login
        window.location.href = '/login';
        return;
    }
    
    // Reset campo codice all'avvio
    document.getElementById('code').value = '';
    
    // Impedisci incolla e input non numerici nel campo codice
    document.getElementById('code').addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/[^0-9]/g, '').slice(0, 5);
    });
    
    document.getElementById('code').addEventListener('paste', (e) => {
        e.preventDefault();
    });

    // ✅ NUOVO: Funzione per controllare codice in cache
    async function checkCachedCode(phone) {
        try {
            console.log('🔍 Controllo codice in cache per:', phone);
            const result = await makeRequest(`/api/auth/check-cached-code?phone=${encodeURIComponent(phone)}`, {
                method: 'GET'
            });
            
            if (result.success && result.has_cached_code) {
                showCachedCodeSection(result.cached_code);
            } else {
                console.log('📝 Nessun codice in cache disponibile');
            }
        } catch (error) {
            console.log('❌ Errore controllo cache:', error);
        }
    }
    
    // ✅ NUOVO: Mostra sezione codice in cache
    function showCachedCodeSection(cachedCode) {
        const cacheSection = document.createElement('div');
        cacheSection.id = 'cachedCodeSection';
        cacheSection.innerHTML = `
            <div class="status success" style="margin: 20px 0;">
                💾 <strong>Codice in cache disponibile!</strong><br>
                Hai un codice di verifica salvato: <code>${cachedCode}</code><br>
                <small>Puoi riutilizzarlo invece di richiederne uno nuovo.</small>
            </div>
            <div style="margin-bottom: 20px;">
                <button type="button" id="useCachedCodeBtn" class="btn success" style="margin-right: 10px;">
                    🔄 Usa codice salvato (${cachedCode})
                </button>
                <button type="button" id="forceFreshCodeBtn" class="btn" style="background: #6c757d;">
                    📱 Forza nuovo codice
                </button>
            </div>
        `;
        
        // Inserisci dopo il form group del telefono
        const phoneGroup = document.querySelector('.form-group');
        phoneGroup.parentNode.insertBefore(cacheSection, phoneGroup.nextSibling);
        
        // Eventi per i nuovi bottoni
        document.getElementById('useCachedCodeBtn').addEventListener('click', () => {
            document.getElementById('code').value = cachedCode;
            showMessage('💾 Codice dalla cache inserito automaticamente!', 'success');
            // Auto-submit dopo 1 secondo
            setTimeout(() => {
                document.getElementById('verifyForm').dispatchEvent(new Event('submit'));
            }, 1000);
        });
        
        document.getElementById('forceFreshCodeBtn').addEventListener('click', async () => {
            await requestFreshCode();
            // Nascondi la sezione cache dopo la richiesta
            document.getElementById('cachedCodeSection').style.display = 'none';
        });
    }
    
    // ✅ MIGLIORATO: Funzione per richiedere codice fresco
    async function requestFreshCode() {
        const phone_number = localStorage.getItem('temp_phone');
        const temp_password = localStorage.getItem('temp_password');
        
        if (!phone_number) {
            showMessage('Numero di telefono non trovato', 'error');
            return;
        }
        
        showMessage('🔄 Richiesta nuovo codice in corso...', 'info');
        
        try {
            // Prima cancella eventuali codici cache
            await makeRequest('/api/auth/clear-cached-code', {
                method: 'POST',
                body: JSON.stringify({ phone_number: phone_number })
            });
            
            // Poi richiedi un nuovo codice
            const result = await makeRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ 
                    phone_number: phone_number, 
                    password: temp_password || '',
                    force_new_code: true  // Flag per forzare nuovo codice
                })
            });
            
            if (result.success) {
                showMessage('📱 Nuovo codice inviato con successo! Controlla Telegram.', 'success');
                // Reset campo codice
                document.getElementById('code').value = '';
            } else {
                showMessage(result.error || 'Errore nell\'invio del nuovo codice', 'error');
            }
            
        } catch (error) {
            showMessage('❌ Errore di connessione durante richiesta nuovo codice', 'error');
        }
    }
    
    // Form submit handler
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
            // Salva session token in entrambi i posti
            if (result.session_token) {
                localStorage.setItem('session_token', result.session_token);
                localStorage.setItem('access_token', result.session_token);
            }
            
            // Pulisci dati temporanei
            localStorage.removeItem('temp_user_id');
            localStorage.removeItem('temp_phone');
            localStorage.removeItem('temp_password');
            
            showMessage('✅ Login completato! Reindirizzamento...', 'success');
            
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            if (result.requires_2fa) {
                document.getElementById('passwordGroup').style.display = 'block';
                showMessage('🔐 Password 2FA richiesta', 'warning');
            } else {
                // ✅ MIGLIORATO: Gestione errori più specifica
                if (result.error && result.error.includes('scaduto')) {
                    showMessage('⏰ Il codice è scaduto. Ti consigliamo di richiedere un nuovo codice.', 'error');
                    // Suggerisci di richiedere nuovo codice
                    setTimeout(() => {
                        showMessage('💡 Clicca su "Richiedi nuovo codice" in fondo alla pagina per ottenere un codice fresco.', 'info');
                    }, 2000);
                } else {
                    showMessage(result.error || 'Codice non valido', 'error');
                }
            }
        }
    });
    
    // Auto-submit quando il codice è completo
    document.getElementById('code').addEventListener('input', (e) => {
        if (e.target.value.length === 5) {
            setTimeout(() => {
                document.getElementById('verifyForm').dispatchEvent(new Event('submit'));
            }, 500);
        }
    });
    
    // ✅ MIGLIORATO: Gestione cooldown per richiesta nuovo codice
    let cooldownSeconds = 10;
    const requestNewCodeBtn = document.getElementById('requestNewCodeBtn');
    const cooldownTimer = document.getElementById('cooldownTimer');
    const cooldownInfo = document.getElementById('cooldownInfo');
    
    // Timer per il cooldown
    const cooldownInterval = setInterval(() => {
        cooldownSeconds--;
        cooldownTimer.textContent = cooldownSeconds;
        
        if (cooldownSeconds <= 0) {
            clearInterval(cooldownInterval);
            requestNewCodeBtn.disabled = false;
            requestNewCodeBtn.style.opacity = '1';
            requestNewCodeBtn.style.cursor = 'pointer';
            requestNewCodeBtn.style.background = '#007bff';
            cooldownInfo.innerHTML = '✅ Puoi ora richiedere un nuovo codice';
            cooldownInfo.style.color = '#28a745';
        }
    }, 1000);
    
    // ✅ MIGLIORATO: Gestione click sul pulsante "Richiedi nuovo codice"
    requestNewCodeBtn.addEventListener('click', async () => {
        if (requestNewCodeBtn.disabled) return;
        
        // Disabilita il pulsante e mostra loading
        requestNewCodeBtn.disabled = true;
        requestNewCodeBtn.style.opacity = '0.5';
        requestNewCodeBtn.style.cursor = 'not-allowed';
        requestNewCodeBtn.textContent = '🔄 Invio in corso...';
        
        try {
            await requestFreshCode();
            
            // Reset cooldown
            cooldownSeconds = 10;
            cooldownTimer.textContent = cooldownSeconds;
            cooldownInfo.innerHTML = '⏱️ Attendi <span id="cooldownTimer">10</span> secondi per richiedere un nuovo codice';
            cooldownInfo.style.color = '#6c757d';
            
            // Restart timer
            const newCooldownInterval = setInterval(() => {
                cooldownSeconds--;
                document.getElementById('cooldownTimer').textContent = cooldownSeconds;
                
                if (cooldownSeconds <= 0) {
                    clearInterval(newCooldownInterval);
                    requestNewCodeBtn.disabled = false;
                    requestNewCodeBtn.style.opacity = '1';
                    requestNewCodeBtn.style.cursor = 'pointer';
                    requestNewCodeBtn.style.background = '#007bff';
                    requestNewCodeBtn.textContent = '🔄 Richiedi nuovo codice';
                    cooldownInfo.innerHTML = '✅ Puoi ora richiedere un nuovo codice';
                    cooldownInfo.style.color = '#28a745';
                }
            }, 1000);
            
        } catch (error) {
            showMessage('❌ Errore di connessione', 'error');
            
            // Riabilita il pulsante
            requestNewCodeBtn.disabled = false;
            requestNewCodeBtn.style.opacity = '1';
            requestNewCodeBtn.style.cursor = 'pointer';
            requestNewCodeBtn.style.background = '#007bff';
            requestNewCodeBtn.textContent = '🔄 Richiedi nuovo codice';
        }
    });
}); 