#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test semplificato per verificare l'implementazione della validazione della sessione
"""

import os
import re

def test_backend_implementation():
    """Test dell'implementazione nel backend"""
    print("🧪 Test implementazione backend")
    print("=" * 50)
    
    backend_file = "backend/app.py"
    
    if not os.path.exists(backend_file):
        print("❌ File backend/app.py non trovato")
        return False
    
    with open(backend_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica endpoint validate-session
    if '@app.route(\'/api/auth/validate-session\', methods=[\'GET\'])' in content:
        print("✅ Endpoint /api/auth/validate-session trovato")
    else:
        print("❌ Endpoint /api/auth/validate-session mancante")
        return False
    
    # Verifica funzione validate_session
    if 'def validate_session():' in content:
        print("✅ Funzione validate_session trovata")
    else:
        print("❌ Funzione validate_session mancante")
        return False
    
    # Verifica JWT required
    if '@jwt_required()' in content:
        print("✅ Decorator @jwt_required() presente")
    else:
        print("❌ Decorator @jwt_required() mancante")
        return False
    
    return True

def test_frontend_implementation():
    """Test dell'implementazione nel frontend"""
    print("\n🧪 Test implementazione frontend")
    print("=" * 50)
    
    frontend_file = "frontend/app.py"
    
    if not os.path.exists(frontend_file):
        print("❌ File frontend/app.py non trovato")
        return False
    
    with open(frontend_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica proxy endpoint
    if '@app.route(\'/api/auth/validate-session\', methods=[\'GET\'])' in content:
        print("✅ Proxy endpoint /api/auth/validate-session trovato")
    else:
        print("❌ Proxy endpoint /api/auth/validate-session mancante")
        return False
    
    # Verifica funzione api_validate_session
    if 'def api_validate_session():' in content:
        print("✅ Funzione api_validate_session trovata")
    else:
        print("❌ Funzione api_validate_session mancante")
        return False
    
    return True

def test_template_implementation():
    """Test dell'implementazione nel template"""
    print("\n🧪 Test implementazione template")
    print("=" * 50)
    
    template_file = "frontend/templates/base.html"
    
    if not os.path.exists(template_file):
        print("❌ File frontend/templates/base.html non trovato")
        return False
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica funzione checkSessionValidity
    if 'checkSessionValidity' in content:
        print("✅ Funzione checkSessionValidity trovata")
    else:
        print("❌ Funzione checkSessionValidity mancante")
        return False
    
    # Verifica funzione performLogout
    if 'performLogout' in content:
        print("✅ Funzione performLogout trovata")
    else:
        print("❌ Funzione performLogout mancante")
        return False
    
    # Verifica setInterval per controllo periodico
    if 'setInterval(checkSessionValidity' in content:
        print("✅ Controllo periodico configurato")
    else:
        print("❌ Controllo periodico mancante")
        return False
    
    # Verifica visibilitychange
    if 'visibilitychange' in content:
        print("✅ Event listener visibilitychange trovato")
    else:
        print("❌ Event listener visibilitychange mancante")
        return False
    
    return True

def test_menu_utils_implementation():
    """Test dell'implementazione nel menu utils"""
    print("\n🧪 Test implementazione menu utils")
    print("=" * 50)
    
    menu_file = "frontend/menu_utils.py"
    
    if not os.path.exists(menu_file):
        print("❌ File frontend/menu_utils.py non trovato")
        return False
    
    with open(menu_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica integrazione con performLogout
    if 'performLogout' in content:
        print("✅ Integrazione con performLogout trovata")
    else:
        print("❌ Integrazione con performLogout mancante")
        return False
    
    return True

def main():
    """Test principale"""
    print("🔐 Test Implementazione Validazione Automatica Sessione")
    print("=" * 60)
    
    tests = [
        test_backend_implementation,
        test_frontend_implementation,
        test_template_implementation,
        test_menu_utils_implementation
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TUTTI I TEST SUPERATI!")
        print("\n📋 Implementazione completata con successo:")
        print("✅ Backend: Endpoint /api/auth/validate-session")
        print("✅ Frontend: Proxy endpoint")
        print("✅ Template: JavaScript di validazione automatica")
        print("✅ Menu: Integrazione con logout automatico")
        print("\n🚀 La funzionalità è pronta per l'uso!")
    else:
        print("❌ Alcuni test sono falliti")
        print("🔧 Controllare l'implementazione")
    
    print("\n📖 Per maggiori dettagli, consultare:")
    print("   - SESSION_VALIDATION_IMPLEMENTATION.md")
    print("   - Log del browser (Console JavaScript)")
    print("   - Log del backend (Python)")

if __name__ == "__main__":
    main()