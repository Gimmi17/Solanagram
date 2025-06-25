"""
Message parser module.
Analyzes Telegram messages to extract trading signals and relevant data.
"""
import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """Data structure for a trading signal"""
    signal_type: str  # 'BUY' or 'SELL'
    token_address: str
    token_name: str
    market_cap: float
    trade_score: int
    smart_holders: List[Dict[str, str]]
    jupiter_link: Optional[str]
    timestamp: datetime
    raw_message: str

class MessageParser:
    """Parser for Telegram trading signals"""
    
    def __init__(self):
        # Regex patterns for signal detection
        self.buy_pattern = re.compile(r'❗\s*0\s*close', re.IGNORECASE)
        self.sell_pattern = re.compile(r'❗\s*1\s*close', re.IGNORECASE)
        
        # Pattern for token address (Solana addresses are base58 encoded, typically 32-44 chars)
        self.address_pattern = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
        
        # Pattern for market cap (various formats like $1.2M, $500K, etc.)
        self.mcap_pattern = re.compile(r'\$(\d+(?:\.\d+)?)\s*([KMB]?)', re.IGNORECASE)
        
        # Pattern for trade score
        self.score_pattern = re.compile(r'TradeScore[:\s]*(\d+)', re.IGNORECASE)
        
        # Pattern for smart holders
        self.holder_pattern = re.compile(r'🟢\s*([^$\n]+)\s*\(\$([^)]+)\)', re.MULTILINE)
        
        # Pattern for red holders (sell signals)
        self.red_holder_pattern = re.compile(r'🔴\s*([^$\n]+)', re.MULTILINE)
        
        # Pattern for Jupiter link
        self.jupiter_pattern = re.compile(r'(https://jup\.ag/swap/[^\s]+)', re.IGNORECASE)
        
        # Pattern for token name (usually appears early in the message)
        self.token_name_pattern = re.compile(r'^([A-Za-z0-9\s]+)', re.MULTILINE)
    
    def parse_message(self, message_text: str) -> Optional[TradingSignal]:
        """
        Parse a Telegram message and extract trading signal information.
        
        Args:
            message_text: Raw message text from Telegram
            
        Returns:
            TradingSignal object if valid signal is found, None otherwise
        """
        try:
            # Determine signal type
            signal_type = self._detect_signal_type(message_text)
            if not signal_type:
                logger.debug("No valid signal type detected")
                return None
            
            # Extract token address
            token_address = self._extract_token_address(message_text)
            if not token_address:
                logger.warning("No token address found in message")
                return None
            
            # Extract token name
            token_name = self._extract_token_name(message_text)
            if not token_name:
                token_name = "Unknown Token"
            
            # Extract market cap
            market_cap = self._extract_market_cap(message_text)
            
            # Extract trade score
            trade_score = self._extract_trade_score(message_text)
            
            # Extract smart holders
            smart_holders = self._extract_smart_holders(message_text, signal_type)
            
            # Extract Jupiter link
            jupiter_link = self._extract_jupiter_link(message_text)
            
            signal = TradingSignal(
                signal_type=signal_type,
                token_address=token_address,
                token_name=token_name,
                market_cap=market_cap,
                trade_score=trade_score,
                smart_holders=smart_holders,
                jupiter_link=jupiter_link,
                timestamp=datetime.now(),
                raw_message=message_text
            )
            
            logger.info(f"Parsed {signal_type} signal for {token_name} ({token_address})")
            return signal
            
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None
    
    def _detect_signal_type(self, text: str) -> Optional[str]:
        """Detect if message is a BUY or SELL signal"""
        if self.buy_pattern.search(text):
            # Additional check for green holders to confirm BUY signal
            if self.holder_pattern.search(text):
                return 'BUY'
        elif self.sell_pattern.search(text):
            # Additional check for red holders to confirm SELL signal
            if self.red_holder_pattern.search(text):
                return 'SELL'
        return None
    
    def _extract_token_address(self, text: str) -> Optional[str]:
        """Extract Solana token address from message"""
        matches = self.address_pattern.findall(text)
        if matches:
            # Return the first match that looks like a Solana address
            for match in matches:
                if len(match) >= 32:
                    return match
        return None
    
    def _extract_token_name(self, text: str) -> Optional[str]:
        """Extract token name from message"""
        lines = text.strip().split('\n')
        for line in lines[:3]:  # Check first few lines
            line = line.strip()
            if line and not line.startswith(('❗', '🟢', '🔴', 'http', '$')):
                # Clean up the line
                clean_line = re.sub(r'[^\w\s]', '', line).strip()
                if clean_line and len(clean_line) < 50:
                    return clean_line
        return None
    
    def _extract_market_cap(self, text: str) -> float:
        """Extract market cap from message and convert to USD"""
        match = self.mcap_pattern.search(text)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            
            multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
            multiplier = multipliers.get(unit, 1)
            
            return value * multiplier
        return 0.0
    
    def _extract_trade_score(self, text: str) -> int:
        """Extract trade score from message"""
        match = self.score_pattern.search(text)
        if match:
            return int(match.group(1))
        return 0
    
    def _extract_smart_holders(self, text: str, signal_type: str) -> List[Dict[str, str]]:
        """Extract smart holders information"""
        holders = []
        
        if signal_type == 'BUY':
            # Extract green holders for BUY signals
            matches = self.holder_pattern.findall(text)
            for name, amount in matches:
                holders.append({
                    'name': name.strip(),
                    'amount': amount.strip(),
                    'type': 'green'
                })
        elif signal_type == 'SELL':
            # Extract red holders for SELL signals
            matches = self.red_holder_pattern.findall(text)
            for name in matches:
                holders.append({
                    'name': name.strip(),
                    'amount': '',
                    'type': 'red'
                })
        
        return holders
    
    def _extract_jupiter_link(self, text: str) -> Optional[str]:
        """Extract Jupiter swap link from message"""
        match = self.jupiter_pattern.search(text)
        if match:
            return match.group(1)
        return None
    
    def validate_signal(self, signal: TradingSignal) -> bool:
        """
        Validate if a trading signal meets basic requirements.
        
        Args:
            signal: TradingSignal to validate
            
        Returns:
            True if signal is valid, False otherwise
        """
        if not signal:
            return False
        
        # Check required fields
        if not signal.token_address or not signal.signal_type:
            logger.warning("Signal missing required fields")
            return False
        
        # Check token address format
        if len(signal.token_address) < 32:
            logger.warning(f"Invalid token address format: {signal.token_address}")
            return False
        
        # Check if we have smart holders for validation
        if not signal.smart_holders:
            logger.warning("No smart holders found in signal")
            return False
        
        # For BUY signals, ensure we have green holders
        if signal.signal_type == 'BUY':
            green_holders = [h for h in signal.smart_holders if h['type'] == 'green']
            if not green_holders:
                logger.warning("BUY signal without green holders")
                return False
        
        # For SELL signals, ensure we have red holders
        if signal.signal_type == 'SELL':
            red_holders = [h for h in signal.smart_holders if h['type'] == 'red']
            if not red_holders:
                logger.warning("SELL signal without red holders")
                return False
        
        logger.info(f"Signal validation passed for {signal.token_name}")
        return True

# Create global parser instance
parser = MessageParser() 