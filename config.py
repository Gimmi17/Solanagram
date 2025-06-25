"""
Configuration management module.
Handles loading/saving configuration from environment variables and files.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/.env')  # Specify explicit path for Docker

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the bot"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or os.getenv('DATA_DIR', './data'))
        self.data_dir.mkdir(exist_ok=True)
        self.config_file = self.data_dir / 'config.json'
        
        # Default configuration
        self._config = {
            # Telegram settings
            'telegram': {
                'api_id': os.getenv('TELEGRAM_API_ID'),
                'api_hash': os.getenv('TELEGRAM_API_HASH'),
                'phone': os.getenv('TELEGRAM_PHONE'),
                'group_id': os.getenv('TELEGRAM_GROUP_ID'),
            },
            
            # Solana settings
            'solana': {
                'rpc_url': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
                'jupiter_api': os.getenv('JUPITER_API_URL', 'https://quote-api.jup.ag/v6'),
            },
            
            # Bot settings
            'bot': {
                'mode': os.getenv('MODE', 'dry-run'),  # dry-run or live
                'web_port': int(os.getenv('WEB_PORT', '8000')),
                'api_token': os.getenv('API_TOKEN', 'default-token'),
                'min_market_cap': 100000,  # Minimum market cap to consider
                'min_trade_score': 70,     # Minimum trade score to consider
                'max_slippage': 5.0,       # Maximum slippage percentage
                'trade_amount_sol': 0.1,   # Amount in SOL to trade
            },
            
            # Filters
            'filters': {
                'blacklisted_tokens': [],
                'trusted_holders': [],
                'min_holder_count': 3,
            }
        }
        
        # Load existing configuration if available
        self.load()
    
    def load(self) -> None:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self._merge_config(saved_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
    
    def save(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """Merge new configuration with existing one"""
        def merge_dict(base: dict, update: dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(self._config, new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'telegram.api_id')"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save()
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Get Telegram configuration"""
        return self._config['telegram']
    
    def get_solana_config(self) -> Dict[str, Any]:
        """Get Solana configuration"""
        return self._config['solana']
    
    def get_bot_config(self) -> Dict[str, Any]:
        """Get bot configuration"""
        return self._config['bot']
    
    def is_live_mode(self) -> bool:
        """Check if bot is in live trading mode"""
        return self.get('bot.mode') == 'live'
    
    def set_mode(self, mode: str) -> None:
        """Set trading mode (dry-run or live)"""
        if mode not in ['dry-run', 'live']:
            raise ValueError("Mode must be 'dry-run' or 'live'")
        self.set('bot.mode', mode)
    
    def add_blacklisted_token(self, token_address: str) -> None:
        """Add token to blacklist"""
        blacklist = self.get('filters.blacklisted_tokens', [])
        if token_address not in blacklist:
            blacklist.append(token_address)
            self.set('filters.blacklisted_tokens', blacklist)
    
    def is_token_blacklisted(self, token_address: str) -> bool:
        """Check if token is blacklisted"""
        blacklist = self.get('filters.blacklisted_tokens', [])
        return token_address in blacklist
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self._config.copy()

# Global configuration instance
config = Config() 