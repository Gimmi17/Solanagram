#!/bin/bash

# Script per applicare la migrazione del database per il sistema di logging
# Questo script deve essere eseguito dopo aver avviato il container del database

set -e

echo "🔧 Applicazione migrazione database per il sistema di logging..."

# Controlla se il database è disponibile
echo "📊 Controllo connessione database..."
until docker exec solanagram-db pg_isready -U solanagram_user -d solanagram_db; do
    echo "⏳ Database non ancora pronto, attendo..."
    sleep 2
done

echo "✅ Database pronto!"

# Applica la migrazione
echo "📝 Applicazione schema logging..."
docker exec -i solanagram-db psql -U solanagram_user -d solanagram_db < database/add_logging_table.sql

echo "✅ Migrazione completata con successo!"
echo ""
echo "📊 Tabelle create:"
echo "   - message_logs (messaggi loggati)"
echo "   - logging_sessions (sessioni di logging)"
echo ""
echo "🔍 Views create:"
echo "   - active_logging_sessions"
echo "   - chat_logging_stats"
echo ""
echo "🧹 Funzioni create:"
echo "   - cleanup_orphaned_logging_sessions()"
echo "   - get_logging_session_id()"
echo ""
echo "🎉 Il sistema di logging è ora pronto per l'uso!"