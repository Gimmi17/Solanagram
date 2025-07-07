#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crypto Signal Processor
Processes and stores crypto trading signals
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

from .parser import CryptoSignalParser

logger = logging.getLogger(__name__)

class CryptoSignalProcessor:
    """Processor for crypto trading signals"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.parser = CryptoSignalParser()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure crypto signals tables exist"""
        try:
            with self.db.cursor() as cursor:
                # Create crypto_signals table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS crypto_signals (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        source_chat_id BIGINT NOT NULL,
                        signal_type VARCHAR(10) NOT NULL,
                        token_address VARCHAR(255) NOT NULL,
                        token_name VARCHAR(255),
                        market_cap DECIMAL(20, 2),
                        trade_score INTEGER,
                        total_holdings DECIMAL(20, 2),
                        average_holding DECIMAL(20, 2),
                        smart_holders_count INTEGER,
                        closed_positions_count INTEGER,
                        parsed_data JSONB,
                        raw_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_crypto_signals_user_id ON crypto_signals(user_id);
                    CREATE INDEX IF NOT EXISTS idx_crypto_signals_token ON crypto_signals(token_address);
                    CREATE INDEX IF NOT EXISTS idx_crypto_signals_type ON crypto_signals(signal_type);
                    CREATE INDEX IF NOT EXISTS idx_crypto_signals_created ON crypto_signals(created_at);
                """)
                
                # Create crypto_processors table for configuration
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS crypto_processors (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        source_chat_id BIGINT NOT NULL,
                        processor_name VARCHAR(255) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        config JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE(user_id, source_chat_id)
                    );
                """)
                
                # Create extraction_rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS extraction_rules (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        source_chat_id BIGINT NOT NULL,
                        rule_name VARCHAR(255) NOT NULL,
                        search_text VARCHAR(255) NOT NULL,
                        value_length INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE(user_id, source_chat_id, rule_name)
                    );
                """)
                
                # Create extracted_values table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS extracted_values (
                        id SERIAL PRIMARY KEY,
                        message_id INTEGER NOT NULL REFERENCES crypto_signals(id) ON DELETE CASCADE,
                        rule_id INTEGER NOT NULL REFERENCES extraction_rules(id) ON DELETE CASCADE,
                        occurrence_index INTEGER NOT NULL DEFAULT 0,
                        extracted_value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                self.db.commit()
                logger.info("Crypto signal tables ensured")
        except Exception as e:
            logger.error(f"Error creating crypto tables: {e}")
            self.db.rollback()
            raise
    
    def process_message(self, user_id: int, source_chat_id: int, message: str) -> Dict:
        """
        Process a crypto signal message
        
        Args:
            user_id: User ID
            source_chat_id: Source chat ID
            message: Raw message text
            
        Returns:
            Dict with processing result
        """
        try:
            # Parse the signal
            signal_data = self.parser.parse_signal(message)
            
            if signal_data['type'] == 'unknown':
                return {
                    'success': False,
                    'error': 'Failed to parse signal',
                    'details': signal_data.get('error')
                }
            
            # Add raw message to signal data
            signal_data['raw_message'] = message
            
            # Store in database
            signal_id = self._store_signal(user_id, source_chat_id, signal_data)
            
            # Get statistics
            stats = self._get_token_statistics(signal_data['address'])
            
            return {
                'success': True,
                'signal_id': signal_id,
                'signal_type': signal_data['type'],
                'token_name': signal_data['name'],
                'token_address': signal_data['address'],
                'market_cap': signal_data['mcap'],
                'summary': self.parser.format_signal_summary(signal_data),
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error processing crypto signal: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _store_signal(self, user_id: int, source_chat_id: int, signal_data: Dict) -> int:
        """Store parsed signal in database"""
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO crypto_signals (
                    user_id, source_chat_id, signal_type, token_address,
                    token_name, market_cap, trade_score, total_holdings,
                    average_holding, smart_holders_count, closed_positions_count,
                    parsed_data, raw_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                source_chat_id,
                signal_data['type'],
                signal_data['address'],
                signal_data['name'],
                signal_data['mcap'],
                signal_data['trade_score'],
                signal_data['total_holdings'],
                signal_data['average_holding'],
                len(signal_data['smart_holders']),
                len(signal_data['closed_positions']),
                json.dumps(signal_data),
                signal_data['raw_message']
            ))
            
            signal_id = cursor.fetchone()[0]
            self.db.commit()
            return signal_id
    
    def _get_token_statistics(self, token_address: str) -> Dict:
        """Get statistics for a specific token"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get signal counts
            cursor.execute("""
                SELECT 
                    signal_type,
                    COUNT(*) as count
                FROM crypto_signals
                WHERE token_address = %s
                GROUP BY signal_type
            """, (token_address,))
            
            signal_counts = {row['signal_type']: row['count'] for row in cursor.fetchall()}
            
            # Get latest market cap trend
            cursor.execute("""
                SELECT 
                    market_cap,
                    created_at
                FROM crypto_signals
                WHERE token_address = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (token_address,))
            
            mcap_trend = cursor.fetchall()
            
            return {
                'buy_signals': signal_counts.get('buy', 0),
                'sell_signals': signal_counts.get('sell', 0),
                'total_signals': sum(signal_counts.values()),
                'market_cap_trend': mcap_trend
            }
    
    def get_processor_config(self, user_id: int, source_chat_id: int) -> Optional[Dict]:
        """Get processor configuration for a specific chat"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM crypto_processors
                WHERE user_id = %s AND source_chat_id = %s
            """, (user_id, source_chat_id))
            
            return cursor.fetchone()
    
    def save_processor_config(self, user_id: int, source_chat_id: int, 
                            processor_name: str, config: Dict) -> bool:
        """Save or update processor configuration"""
        try:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO crypto_processors (user_id, source_chat_id, processor_name, config)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, source_chat_id)
                    DO UPDATE SET 
                        processor_name = EXCLUDED.processor_name,
                        config = EXCLUDED.config,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, source_chat_id, processor_name, json.dumps(config)))
                
                self.db.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving processor config: {e}")
            self.db.rollback()
            return False
    
    def get_recent_signals(self, user_id: int, hours: int = 24, 
                          signal_type: Optional[str] = None) -> List[Dict]:
        """Get recent signals for a user"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT * FROM crypto_signals
                WHERE user_id = %s
                AND created_at > %s
            """
            params = [user_id, datetime.now() - timedelta(hours=hours)]
            
            if signal_type:
                query += " AND signal_type = %s"
                params.append(signal_type)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_signals_by_chat(self, user_id: int, source_chat_id: int, 
                            hours: int = 24, signal_type: Optional[str] = None) -> List[Dict]:
        """Get recent signals for a specific chat"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT * FROM crypto_signals
                WHERE user_id = %s AND source_chat_id = %s
                AND created_at > %s
            """
            params = [user_id, source_chat_id, datetime.now() - timedelta(hours=hours)]
            
            if signal_type:
                query += " AND signal_type = %s"
                params.append(signal_type)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_all_processors(self, user_id: int) -> List[Dict]:
        """Get all processors for a user"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    cp.*,
                    c.title as chat_title
                FROM crypto_processors cp
                LEFT JOIN chats c ON cp.source_chat_id = c.chat_id AND cp.user_id = c.user_id
                WHERE cp.user_id = %s
                ORDER BY cp.created_at DESC
            """, (user_id,))
            
            return cursor.fetchall()
    
    def delete_processor(self, user_id: int, processor_id: int) -> bool:
        """Delete a processor configuration"""
        try:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM crypto_processors
                    WHERE id = %s AND user_id = %s
                """, (processor_id, user_id))
                
                self.db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting processor: {e}")
            self.db.rollback()
            return False
    
    def get_top_performers(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get top performing tokens by market cap growth"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                WITH token_performance AS (
                    SELECT 
                        token_address,
                        token_name,
                        FIRST_VALUE(market_cap) OVER (
                            PARTITION BY token_address ORDER BY created_at DESC
                        ) as latest_mcap,
                        FIRST_VALUE(market_cap) OVER (
                            PARTITION BY token_address ORDER BY created_at ASC
                        ) as first_mcap,
                        COUNT(*) as signal_count
                    FROM crypto_signals
                    WHERE user_id = %s
                    GROUP BY token_address, token_name, market_cap, created_at
                )
                SELECT DISTINCT
                    token_address,
                    token_name,
                    latest_mcap,
                    first_mcap,
                    CASE 
                        WHEN first_mcap > 0 THEN 
                            ((latest_mcap - first_mcap) / first_mcap * 100)
                        ELSE 0 
                    END as growth_percentage,
                    signal_count
                FROM token_performance
                WHERE latest_mcap IS NOT NULL AND first_mcap IS NOT NULL
                ORDER BY growth_percentage DESC
                LIMIT %s
            """, (user_id, limit))
            
            return cursor.fetchall() 