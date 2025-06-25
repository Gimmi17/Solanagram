#!/usr/bin/env python3
"""
Script per aggiornare le credenziali API Telegram di un utente
Usage: python update_credentials.py <phone_number> <new_api_id> <new_api_hash>
"""

import sys
import os
import psycopg2
import psycopg2.extras
import hashlib
from datetime import datetime

def hash_phone_number(phone: str) -> str:
    """Hash sicuro del numero di telefono"""
    return hashlib.sha256(phone.encode()).hexdigest()

def get_db_connection():
    """Connessione al database PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5433'),  # Porta mappata di Docker
            database=os.getenv('DB_NAME', 'chatmanager'),
            user=os.getenv('DB_USER', 'chatmanager'),
            password=os.getenv('DB_PASSWORD', 'chatmanager123')
        )
        return conn
    except Exception as e:
        print(f"❌ Errore connessione database: {e}")
        return None

def update_user_credentials(phone_number: str, new_api_id: int, new_api_hash: str):
    """Aggiorna le credenziali API di un utente"""
    
    phone_hash = hash_phone_number(phone_number)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Cerca l'utente
            cursor.execute("""
                SELECT id, api_id 
                FROM users 
                WHERE phone_number = %s
            """, (phone_hash,))
            
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ Utente con numero {phone_number} non trovato")
                return False
            
            print(f"📱 Utente trovato (ID: {user['id']}, API_ID attuale: {user['api_id']})")
            
            # Aggiorna le credenziali
            cursor.execute("""
                UPDATE users 
                SET api_id = %s, api_hash = %s, telegram_session = NULL
                WHERE phone_number = %s
            """, (new_api_id, new_api_hash, phone_hash))
            
            conn.commit()
            
            print(f"✅ Credenziali aggiornate con successo!")
            print(f"   📊 Nuovo API_ID: {new_api_id}")
            print(f"   🔑 Nuovo API_HASH: {new_api_hash[:10]}...")
            print(f"   🔄 Sessione Telegram resettata")
            
            return True
            
    except Exception as e:
        print(f"❌ Errore durante l'aggiornamento: {e}")
        return False
    finally:
        conn.close()

def main():
    if len(sys.argv) != 4:
        print("❌ Uso: python update_credentials.py <phone_number> <new_api_id> <new_api_hash>")
        print("📞 Esempio: python update_credentials.py +393485373976 12345678 abcd1234...")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    
    try:
        new_api_id = int(sys.argv[2])
    except ValueError:
        print("❌ API_ID deve essere un numero intero")
        sys.exit(1)
    
    new_api_hash = sys.argv[3]
    
    if not new_api_hash:
        print("❌ API_HASH non può essere vuoto")
        sys.exit(1)
    
    print(f"🔄 Aggiornamento credenziali per {phone_number}")
    print(f"📊 Nuovo API_ID: {new_api_id}")
    print(f"🔑 Nuovo API_HASH: {new_api_hash[:10]}...")
    
    confirmation = input("✋ Continuare? (s/N): ")
    if confirmation.lower() not in ['s', 'si', 'sì', 'y', 'yes']:
        print("❌ Operazione annullata")
        sys.exit(0)
    
    success = update_user_credentials(phone_number, new_api_id, new_api_hash)
    
    if success:
        print("\n🎉 Aggiornamento completato!")
        print("💡 L'utente dovrà rifare il login per usare le nuove credenziali")
    else:
        print("\n❌ Aggiornamento fallito")
        sys.exit(1)

if __name__ == "__main__":
    main() 