# Sistema Unificato di Gestione Errori e Messaggi

## Panoramica

È stato implementato un sistema unificato per la gestione degli errori e messaggi in tutto il sito web, garantendo consistenza e migliorando l'esperienza utente secondo i seguenti requisiti:

- ✅ **Messaggi persistenti**: I messaggi rimangono visibili fino a quando l'utente non li chiude manualmente o ricarica la pagina
- ✅ **Pulsante di chiusura**: Ogni messaggio ha un pulsante "×" per la chiusura manuale
- ✅ **Consistenza globale**: Tutti gli errori e messaggi utilizzano lo stesso sistema
- ✅ **Design responsive**: Ottimizzato per desktop e dispositivi mobili
- ✅ **Accessibilità**: Supporto per screen reader e navigazione da tastiera

## Modifiche Implementate

### 1. Funzione `showMessage()` Migliorata

**File modificato**: `frontend/templates/base.html`

#### Nuove Funzionalità:
- **Rimozione automatica duplicati**: Previene messaggi multipli sovrapposti
- **Pulsante di chiusura**: Aggiunta del bottone "×" con supporto accessibilità
- **Contenuto HTML**: Supporto per formattazione HTML nei messaggi
- **Scroll automatico**: Il messaggio viene reso visibile automaticamente
- **Persistenza**: Rimosso il timeout automatico di 5 secondi

#### Codice Prima:
```javascript
function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 5000);
}
```

#### Codice Dopo:
```javascript
function showMessage(message, type = 'info') {
    // Remove any existing messages to avoid duplicates
    const existingMessages = document.querySelectorAll('.message');
    existingMessages.forEach(msg => {
        if (msg.parentNode) {
            msg.parentNode.removeChild(msg);
        }
    });
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    // Create close button
    const closeButton = document.createElement('button');
    closeButton.className = 'message-close';
    closeButton.innerHTML = '&times;';
    closeButton.setAttribute('aria-label', 'Chiudi messaggio');
    closeButton.onclick = function() {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    };
    
    // Create message content
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerHTML = message; // Using innerHTML to support HTML content
    
    // Assemble message
    messageDiv.appendChild(messageContent);
    messageDiv.appendChild(closeButton);
    
    // Insert at top of main content
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.insertBefore(messageDiv, mainContent.firstChild);
    }
    
    // Scroll to message for better visibility
    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
```

### 2. Stili CSS Migliorati

**File modificato**: `frontend/static/css/style.css`

#### Nuove Funzionalità:
- **Pulsante di chiusura stilizzato**: Design consistente con hover e focus states
- **Animazioni**: Transizione fluida all'apparizione del messaggio
- **Design responsive**: Ottimizzazione per dispositivi mobili
- **Accessibilità**: Outline per focus e aria-label

#### Principali Aggiunte CSS:
```css
.message {
    position: relative;
    padding: 15px 45px 15px 15px; /* Extra padding for close button */
    border-radius: 8px;
    margin: 20px 0;
    border-left: 4px solid;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    animation: slideInDown 0.3s ease-out;
    max-width: 100%;
    word-wrap: break-word;
}

.message-close {
    position: absolute;
    top: 8px;
    right: 12px;
    background: none;
    border: none;
    font-size: 24px;
    font-weight: bold;
    cursor: pointer;
    color: inherit;
    opacity: 0.7;
    transition: opacity 0.2s ease;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
}

@keyframes slideInDown {
    from {
        transform: translateY(-20px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}
```

### 3. Gestione API Migliorata

**File modificato**: `frontend/templates/base.html`

#### Nuove Funzionalità:
- **Gestione automatica errori API**: Cattura e mostra automaticamente errori da backend
- **Gestione errori globali**: Handler per errori JavaScript non catturati
- **Messaggi di connessione**: Notifiche per problemi di rete
- **Opzione di soppressione**: Possibilità di disabilitare messaggi automatici con `suppressErrorMessage`

#### Miglioramenti della Funzione `makeRequest()`:
```javascript
// Handle API errors that return success: false or error fields
if (data && data.success === false && data.error) {
    const errorMessage = typeof data.error === 'string' ? data.error : 'Errore sconosciuto';
    if (!options.suppressErrorMessage) {
        showMessage(`❌ ${errorMessage}`, 'error');
    }
    return data;
}

// Handle server errors (5xx status codes)
if (response.status >= 500) {
    if (!options.suppressErrorMessage) {
        showMessage('❌ Errore del server. Riprova più tardi.', 'error');
    }
    return { success: false, error: 'Server error' };
}
```

### 4. Design Responsive

#### Desktop (> 768px):
- Messaggi con padding completo e font size normale
- Pulsante di chiusura 30x30px

#### Tablet (≤ 768px):
- Messaggi con padding ridotto
- Font size 14px
- Pulsante di chiusura 28x28px

#### Mobile (≤ 480px):
- Messaggi compatti con padding minimo
- Font size 13px  
- Pulsante di chiusura 26x26px

## Tipi di Messaggio Supportati

### 1. Success (Successo)
```javascript
showMessage('✅ Operazione completata con successo!', 'success');
```
- **Colore**: Verde (#28a745)
- **Uso**: Conferme di operazioni riuscite

### 2. Error (Errore)
```javascript
showMessage('❌ Errore durante l\'operazione', 'error');
```
- **Colore**: Rosso (#dc3545)
- **Uso**: Errori, fallimenti, problemi critici

### 3. Warning (Avviso)
```javascript
showMessage('⚠️ Attenzione: verifica i dati inseriti', 'warning');
```
- **Colore**: Giallo (#ffc107)
- **Uso**: Avvisi, attenzioni, dati da verificare

### 4. Info (Informazione)
```javascript
showMessage('ℹ️ Processo in corso...', 'info');
```
- **Colore**: Blu (#17a2b8)
- **Uso**: Informazioni generali, stati di processo

## Esempi di Utilizzo

### Gestione Errori API Automatica
```javascript
// Errori vengono mostrati automaticamente
const result = await makeRequest('/api/endpoint', {
    method: 'POST',
    body: JSON.stringify(data)
});

// Per sopprimere messaggi automatici
const result = await makeRequest('/api/endpoint', {
    method: 'POST',
    body: JSON.stringify(data),
    suppressErrorMessage: true
});
```

### Messaggi Manuali
```javascript
// Successo con HTML
showMessage('✅ Account creato con successo!<br><small>Controlla la tua email per confermare</small>', 'success');

// Errore con dettagli
showMessage('❌ Errore durante il login<br>Verifica username e password', 'error');

// Info con progress
showMessage('🔄 Connessione in corso...<br>Attendere prego', 'info');
```

## Benefici del Sistema Unificato

### 1. **Esperienza Utente Migliorata**
- Messaggi persistenti che non spariscono automaticamente
- Controllo completo dell'utente tramite pulsante di chiusura
- Design consistente in tutto il sito

### 2. **Accessibilità**
- Supporto screen reader con `aria-label`
- Navigazione da tastiera con `outline` su focus
- Contrasto colori rispettoso delle linee guida WCAG

### 3. **Manutenibilità**
- Sistema centralizzato per tutti i messaggi
- Stili CSS unificati e riutilizzabili
- Facile aggiunta di nuovi tipi di messaggio

### 4. **Robustezza**
- Gestione automatica errori API
- Fallback per errori di rete
- Prevenzione duplicati messaggi

## Compatibilità e Prestazioni

- ✅ **Browser moderni**: Chrome, Firefox, Safari, Edge
- ✅ **Dispositivi mobili**: iOS Safari, Chrome Mobile
- ✅ **Prestazioni**: Animazioni CSS ottimizzate
- ✅ **Memoria**: Rimozione automatica DOM degli elementi

## Note per Sviluppatori

### Quando Utilizzare `suppressErrorMessage: true`
```javascript
// Usa quando vuoi gestire l'errore manualmente
const result = await makeRequest('/api/login', {
    method: 'POST',
    body: JSON.stringify({username, password}),
    suppressErrorMessage: true
});

if (!result.success) {
    // Gestione custom dell'errore
    if (result.error.includes('2FA')) {
        showMessage('🔐 Codice 2FA richiesto', 'warning');
        show2FAModal();
    } else {
        showMessage('❌ Credenziali non valide', 'error');
    }
}
```

### Estendere il Sistema
Per aggiungere un nuovo tipo di messaggio:

1. **Aggiungi stili CSS**:
```css
.message-custom {
    background: #e1f5fe;
    color: #01579b;
    border-left-color: #03a9f4;
}
```

2. **Usa il nuovo tipo**:
```javascript
showMessage('💡 Suggerimento personalizzato', 'custom');
```

## Conclusioni

Il sistema unificato di gestione errori e messaggi garantisce:
- **Consistenza** in tutto il sito web
- **Controllo utente** sui messaggi visualizzati
- **Accessibilità** e usabilità migliorate
- **Manutenibilità** del codice

Tutti i messaggi ora seguono lo stesso pattern, migliorando significativamente l'esperienza utente e la qualità complessiva dell'applicazione.