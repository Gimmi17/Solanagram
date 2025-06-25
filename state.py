"""
State management module.
Handles persistence of trading signals, logs, and application state.
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import asdict

from parser import TradingSignal
from config import config

logger = logging.getLogger(__name__)

class StateManager:
    """Manages application state and data persistence"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or config.data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.db_path = self.data_dir / 'trades.db'
        self.log_path = self.data_dir / 'bot.log'
        
        # Initialize database
        self._init_database()
        
        # Setup logging
        self._setup_logging()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create signals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_type TEXT NOT NULL,
                        token_address TEXT NOT NULL,
                        token_name TEXT,
                        market_cap REAL,
                        trade_score INTEGER,
                        smart_holders TEXT,  -- JSON string
                        jupiter_link TEXT,
                        timestamp TIMESTAMP,
                        raw_message TEXT,
                        processed BOOLEAN DEFAULT 0,
                        executed BOOLEAN DEFAULT 0,
                        execution_result TEXT,  -- JSON string
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create trades table (for executed transactions)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_id INTEGER,
                        transaction_hash TEXT,
                        trade_type TEXT NOT NULL,  -- BUY or SELL
                        token_address TEXT NOT NULL,
                        amount_sol REAL,
                        amount_tokens REAL,
                        price REAL,
                        slippage REAL,
                        gas_fee_sol REAL DEFAULT 0.0,
                        other_fees_sol REAL DEFAULT 0.0,
                        status TEXT,  -- pending, success, failed
                        error_message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES signals (id)
                    )
                ''')
                
                # Create blacklist table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS blacklist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        token_address TEXT UNIQUE NOT NULL,
                        reason TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create settings table for dynamic configuration
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create messages table for chat log
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_id INTEGER,
                        chat_id INTEGER,
                        user_id INTEGER,
                        username TEXT,
                        first_name TEXT,
                        message_text TEXT,
                        message_date TIMESTAMP,
                        has_signal BOOLEAN DEFAULT 0,
                        signal_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES signals (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _setup_logging(self) -> None:
        """Setup file logging"""
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
    
    def save_signal(self, signal: TradingSignal) -> int:
        """
        Save a trading signal to the database.
        
        Args:
            signal: TradingSignal to save
            
        Returns:
            Signal ID in database
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO signals (
                        signal_type, token_address, token_name, market_cap,
                        trade_score, smart_holders, jupiter_link, timestamp,
                        raw_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal.signal_type,
                    signal.token_address,
                    signal.token_name,
                    signal.market_cap,
                    signal.trade_score,
                    json.dumps(signal.smart_holders),
                    signal.jupiter_link,
                    signal.timestamp,
                    signal.raw_message
                ))
                
                signal_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Signal saved with ID {signal_id}")
                return signal_id
                
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")
            raise
    
    def get_signal(self, signal_id: int) -> Optional[Dict[str, Any]]:
        """Get a signal by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
                row = cursor.fetchone()
                
                if row:
                    signal_data = dict(row)
                    signal_data['smart_holders'] = json.loads(signal_data['smart_holders'] or '[]')
                    return signal_data
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get signal {signal_id}: {e}")
            return None
    
    def get_recent_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent signals from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM signals 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                signals = []
                for row in cursor.fetchall():
                    signal_data = dict(row)
                    signal_data['smart_holders'] = json.loads(signal_data['smart_holders'] or '[]')
                    signals.append(signal_data)
                
                return signals
                
        except Exception as e:
            logger.error(f"Failed to get recent signals: {e}")
            return []
    
    def mark_signal_processed(self, signal_id: int, executed: bool = False, 
                            execution_result: Dict[str, Any] = None) -> None:
        """Mark a signal as processed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE signals 
                    SET processed = 1, executed = ?, execution_result = ?
                    WHERE id = ?
                ''', (executed, json.dumps(execution_result) if execution_result else None, signal_id))
                
                conn.commit()
                logger.info(f"Signal {signal_id} marked as processed")
                
        except Exception as e:
            logger.error(f"Failed to mark signal processed: {e}")
    
    def save_trade(self, signal_id: int, trade_data: Dict[str, Any]) -> int:
        """Save executed trade information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO trades (
                        signal_id, transaction_hash, trade_type, token_address,
                        amount_sol, amount_tokens, price, slippage, gas_fee_sol, 
                        other_fees_sol, status, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal_id,
                    trade_data.get('transaction_hash'),
                    trade_data.get('trade_type'),
                    trade_data.get('token_address'),
                    trade_data.get('amount_sol'),
                    trade_data.get('amount_tokens'),
                    trade_data.get('price'),
                    trade_data.get('slippage'),
                    trade_data.get('gas_fee_sol', 0.0),
                    trade_data.get('other_fees_sol', 0.0),
                    trade_data.get('status'),
                    trade_data.get('error_message')
                ))
                
                trade_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Trade saved with ID {trade_id}")
                return trade_id
                
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            raise
    
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT t.*, s.token_name 
                    FROM trades t
                    LEFT JOIN signals s ON t.signal_id = s.id
                    ORDER BY t.timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []
    
    def is_token_seen_recently(self, token_address: str, hours: int = 24) -> bool:
        """Check if token was seen recently"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM signals 
                    WHERE token_address = ? 
                    AND created_at > datetime('now', '-{} hours')
                '''.format(hours), (token_address,))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            logger.error(f"Failed to check token history: {e}")
            return False
    
    def add_to_blacklist(self, token_address: str, reason: str = None) -> None:
        """Add token to blacklist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO blacklist (token_address, reason)
                    VALUES (?, ?)
                ''', (token_address, reason))
                
                conn.commit()
                logger.info(f"Token {token_address} added to blacklist")
                
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {e}")
    
    def is_token_blacklisted(self, token_address: str) -> bool:
        """Check if token is blacklisted"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT COUNT(*) FROM blacklist WHERE token_address = ?',
                    (token_address,)
                )
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            logger.error(f"Failed to check blacklist: {e}")
            return False
    
    def get_blacklist(self) -> List[Dict[str, Any]]:
        """Get all blacklisted tokens"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM blacklist ORDER BY added_at DESC')
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get blacklist: {e}")
            return []
    
    def set_setting(self, key: str, value: str) -> None:
        """Save a setting to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save setting {key}: {e}")
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
                row = cursor.fetchone()
                
                return row[0] if row else default
                
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
            return default
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total signals
                cursor.execute('SELECT COUNT(*) FROM signals')
                total_signals = cursor.fetchone()[0]
                
                # Processed signals
                cursor.execute('SELECT COUNT(*) FROM signals WHERE processed = 1')
                processed_signals = cursor.fetchone()[0]
                
                # Total trades
                cursor.execute('SELECT COUNT(*) FROM trades')
                total_trades = cursor.fetchone()[0]
                
                # Successful trades
                cursor.execute('SELECT COUNT(*) FROM trades WHERE status = "success"')
                successful_trades = cursor.fetchone()[0]
                
                # Blacklisted tokens
                cursor.execute('SELECT COUNT(*) FROM blacklist')
                blacklisted_count = cursor.fetchone()[0]
                
                # Recent signals (last 24h)
                cursor.execute('''
                    SELECT COUNT(*) FROM signals 
                    WHERE created_at > datetime('now', '-24 hours')
                ''')
                recent_signals = cursor.fetchone()[0]
                
                return {
                    'total_signals': total_signals,
                    'processed_signals': processed_signals,
                    'total_trades': total_trades,
                    'successful_trades': successful_trades,
                    'blacklisted_count': blacklisted_count,
                    'recent_signals': recent_signals
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def save_message(self, message_data: Dict[str, Any], signal_id: int = None) -> int:
        """Save a Telegram message to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO messages (
                        message_id, chat_id, user_id, username, first_name,
                        message_text, message_date, has_signal, signal_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_data.get('message_id'),
                    message_data.get('chat_id'),
                    message_data.get('user_id'),
                    message_data.get('username'),
                    message_data.get('first_name'),
                    message_data.get('message_text'),
                    message_data.get('message_date'),
                    1 if signal_id else 0,
                    signal_id
                ))
                
                msg_id = cursor.lastrowid
                conn.commit()
                
                logger.debug(f"Message saved with ID {msg_id}")
                return msg_id
                
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            raise
    
    def get_messages_with_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages with their corresponding trades/signals"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get messages with related signals and trades
                cursor.execute('''
                    SELECT 
                        m.*,
                        s.signal_type,
                        s.token_address,
                        s.token_name,
                        s.market_cap,
                        s.trade_score,
                        t.trade_type,
                        t.amount_sol,
                        t.amount_tokens,
                        t.price,
                        t.slippage,
                        t.gas_fee_sol,
                        t.other_fees_sol,
                        t.status as trade_status,
                        t.transaction_hash,
                        t.timestamp as trade_timestamp,
                        t.error_message
                    FROM messages m
                    LEFT JOIN signals s ON m.signal_id = s.id
                    LEFT JOIN trades t ON s.id = t.signal_id
                    ORDER BY m.message_date DESC
                    LIMIT ?
                ''', (limit,))
                
                messages = []
                for row in cursor.fetchall():
                    msg_data = dict(row)
                    messages.append(msg_data)
                
                return messages
                
        except Exception as e:
            logger.error(f"Failed to get messages with trades: {e}")
            return []
    
    def get_recent_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent messages from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM messages 
                    ORDER BY message_date DESC 
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []

# Global state manager instance
state = StateManager() 