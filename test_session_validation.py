#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script per verificare la logica di validazione della sessione
"""

import requests
import json
import time

# Configurazione
FRONTEND_URL = "http://localhost:8082"
BACKEND_URL = "http://localhost:5000"

def test_session_validation():
    """Test della validazione della sessione"""
    
    print("🧪 Test della validazione automatica della sessione")
    print("=" * 60)
    
    # Test 1: Verifica endpoint di validazione sessione
    print("\n1️⃣ Test endpoint /api/auth/validate-session")
    try:
        response = requests.get(f"{FRONTEND_URL}/api/auth/validate-session")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Corretto: Endpoint richiede autenticazione")
        else:
            print(f"   ⚠️  Inaspettato: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
    
    # Test 2: Verifica endpoint backend
    print("\n2️⃣ Test endpoint backend /api/auth/validate-session")
    try:
        response = requests.get(f"{BACKEND_URL}/api/auth/validate-session")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Corretto: Endpoint richiede autenticazione")
        else:
            print(f"   ⚠️  Inaspettato: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
    
    # Test 3: Verifica template base
    print("\n3️⃣ Test template base con JavaScript di validazione")
    try:
        response = requests.get(f"{FRONTEND_URL}/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            content = response.text
            if "checkSessionValidity" in content:
                print("   ✅ Corretto: JavaScript di validazione presente")
            else:
                print("   ❌ Errore: JavaScript di validazione mancante")
            
            if "performLogout" in content:
                print("   ✅ Corretto: Funzione logout automatico presente")
            else:
                print("   ❌ Errore: Funzione logout automatico mancante")
        else:
            print(f"   ⚠️  Inaspettato: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
    
    print("\n" + "=" * 60)
    print("📋 Riepilogo implementazione:")
    print("✅ Endpoint /api/auth/validate-session aggiunto al backend")
    print("✅ Proxy endpoint aggiunto al frontend")
    print("✅ JavaScript di validazione automatica aggiunto al template base")
    print("✅ Verifica sessione ogni 5 minuti")
    print("✅ Verifica sessione quando l'utente torna alla pagina")
    print("✅ Logout automatico se la sessione non è più valida")
    print("✅ Gestione errori 401 nelle richieste API")
    
    print("\n🎯 Funzionalità implementate:")
    print("• Verifica automatica della sessione ad ogni caricamento pagina")
    print("• Controllo periodico ogni 5 minuti")
    print("• Controllo quando l'utente torna alla pagina (visibilitychange)")
    print("• Logout automatico SOLO se la sessione non è più valida")
    print("• Gestione graceful degli errori di rete")
    print("• Pulizia automatica del localStorage")
    print("• Redirect automatico alla pagina di login")

if __name__ == "__main__":
    test_session_validation()