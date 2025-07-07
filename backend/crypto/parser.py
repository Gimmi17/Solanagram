#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crypto Signal Parser
Parses buy/sell signals from crypto trading messages
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class CryptoSignalParser:
    """Parser for crypto trading signals"""
    
    def __init__(self):
        self.buy_pattern = r"🦚\s*\d+\s*smart holders"
        self.sell_pattern = r"❗\s*\d+\s*close"
        
    def parse_signal(self, message: str) -> Dict:
        """
        Parse a crypto signal message and extract relevant information
        
        Args:
            message: The raw message text
            
        Returns:
            Dict containing parsed signal data
        """
        try:
            # Determine signal type
            signal_type = self._determine_signal_type(message)
            
            # Extract basic information
            data = {
                'type': signal_type,
                'timestamp': datetime.now().isoformat(),
                'address': self._extract_address(message),
                'name': self._extract_name(message),
                'mcap': self._extract_mcap(message),
                'trade_score': self._extract_trade_score(message),
                'smart_holders': self._extract_smart_holders(message),
                'closed_positions': self._extract_closed_positions(message),
                'links': self._extract_links(message),
                'raw_message': message
            }
            
            # Calculate additional metrics
            data['total_holdings'] = self._calculate_total_holdings(data['smart_holders'])
            data['average_holding'] = self._calculate_average_holding(data['smart_holders'])
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing crypto signal: {e}")
            return {
                'type': 'unknown',
                'error': str(e),
                'raw_message': message
            }
    
    def _determine_signal_type(self, message: str) -> str:
        """Determine if this is a buy or sell signal"""
        # Check for closed positions - if present, it's a sell signal
        if "❗" in message and "close" in message:
            closed_count = self._extract_close_count(message)
            if closed_count > 0:
                return 'sell'
        return 'buy'
    
    def _extract_address(self, message: str) -> Optional[str]:
        """Extract the token address"""
        match = re.search(r'🔎 Address: ([A-Za-z0-9]+)', message)
        return match.group(1) if match else None
    
    def _extract_name(self, message: str) -> Optional[str]:
        """Extract the token name"""
        match = re.search(r'💰 Name: (.+?)(?:\n|$)', message)
        return match.group(1).strip() if match else None
    
    def _extract_mcap(self, message: str) -> Optional[float]:
        """Extract and parse market cap"""
        match = re.search(r'📈 MCap: ([\d.]+)([KM])?', message)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            if unit == 'K':
                return value * 1000
            elif unit == 'M':
                return value * 1000000
            return value
        return None
    
    def _extract_trade_score(self, message: str) -> Optional[int]:
        """Extract the trade score"""
        match = re.search(r'💯 TradeScore: (\d+)', message)
        return int(match.group(1)) if match else None
    
    def _extract_close_count(self, message: str) -> int:
        """Extract the number of closed positions"""
        match = re.search(r'❗\s*(\d+)\s*close', message)
        return int(match.group(1)) if match else 0
    
    def _extract_smart_holders(self, message: str) -> List[Dict]:
        """Extract information about smart holders"""
        holders = []
        
        # Pattern for holder lines
        pattern = r'🟢\s*([^$]+?)\s*\(\$(\d+)\)\s*\(([^)]+)\)'
        
        for match in re.finditer(pattern, message):
            name = match.group(1).strip()
            amount = int(match.group(2))
            timestamp = match.group(3).strip()
            
            holders.append({
                'name': name,
                'amount': amount,
                'timestamp': timestamp,
                'status': 'active'
            })
        
        return holders
    
    def _extract_closed_positions(self, message: str) -> List[str]:
        """Extract names of closed positions"""
        closed = []
        
        # Pattern for closed positions
        pattern = r'🔴\s*(.+?)(?:\n|$)'
        
        for match in re.finditer(pattern, message):
            name = match.group(1).strip()
            closed.append(name)
        
        return closed
    
    def _extract_links(self, message: str) -> Dict[str, str]:
        """Extract trading platform links"""
        links = {}
        
        # Patterns for different platforms
        platforms = {
            'jupiter': r'⚡ Jupiter \((https://[^)]+)\)',
            'gmgn': r'🐸 Gmgn \((https://[^)]+)\)',
            'photon': r'🚀 Photon \((https://[^)]+)\)',
            'bullx': r'🐂 Bullx \((https://[^)]+)\)'
        }
        
        for platform, pattern in platforms.items():
            match = re.search(pattern, message)
            if match:
                links[platform] = match.group(1)
        
        return links
    
    def _calculate_total_holdings(self, holders: List[Dict]) -> int:
        """Calculate total holdings amount"""
        return sum(holder['amount'] for holder in holders)
    
    def _calculate_average_holding(self, holders: List[Dict]) -> float:
        """Calculate average holding amount"""
        if not holders:
            return 0
        return self._calculate_total_holdings(holders) / len(holders)
    
    def format_signal_summary(self, signal_data: Dict) -> str:
        """Format parsed signal data into a readable summary"""
        if signal_data.get('type') == 'unknown':
            return f"❌ Failed to parse signal: {signal_data.get('error', 'Unknown error')}"
        
        summary = []
        summary.append(f"📊 **Signal Type**: {signal_data['type'].upper()}")
        summary.append(f"🪙 **Token**: {signal_data['name']} ({signal_data['address'][:8]}...)")
        summary.append(f"💹 **Market Cap**: ${signal_data['mcap']:,.0f}")
        summary.append(f"⭐ **Trade Score**: {signal_data['trade_score']}")
        summary.append(f"👥 **Active Holders**: {len(signal_data['smart_holders'])}")
        summary.append(f"💰 **Total Holdings**: ${signal_data['total_holdings']:,.0f}")
        summary.append(f"📊 **Average Holding**: ${signal_data['average_holding']:,.2f}")
        
        if signal_data['type'] == 'sell' and signal_data['closed_positions']:
            summary.append(f"🔴 **Closed Positions**: {len(signal_data['closed_positions'])}")
            summary.append(f"   → {', '.join(signal_data['closed_positions'])}")
        
        return '\n'.join(summary) 