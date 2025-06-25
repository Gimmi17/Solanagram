"""
Trading engine module.
Implements decision logic, filtering, and signal processing.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from parser import TradingSignal
from config import config
from state import state

logger = logging.getLogger(__name__)

class TradingEngine:
    """Main trading decision engine"""
    
    def __init__(self):
        self.processed_signals = set()  # Track processed signals to avoid duplicates
    
    def process_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        Process a trading signal through all filters and decision logic.
        
        Args:
            signal: TradingSignal to process
            
        Returns:
            Processing result with decision and reasoning
        """
        try:
            # Create unique signal ID for deduplication
            signal_id = f"{signal.token_address}_{signal.signal_type}_{signal.timestamp.isoformat()}"
            
            if signal_id in self.processed_signals:
                return {
                    'action': 'skip',
                    'reason': 'Signal already processed',
                    'should_execute': False
                }
            
            self.processed_signals.add(signal_id)
            
            # Save signal to database first
            db_signal_id = state.save_signal(signal)
            
            logger.info(f"Processing {signal.signal_type} signal for {signal.token_name} (ID: {db_signal_id})")
            
            # Run through all filters
            filter_result = self._apply_filters(signal)
            
            if not filter_result['passed']:
                logger.info(f"Signal filtered out: {filter_result['reason']}")
                state.mark_signal_processed(db_signal_id, executed=False, execution_result=filter_result)
                return {
                    'action': 'filtered',
                    'reason': filter_result['reason'],
                    'should_execute': False,
                    'signal_id': db_signal_id
                }
            
            # Determine action based on signal type and additional logic
            decision = self._make_trading_decision(signal)
            
            logger.info(f"Trading decision: {decision['action']} - {decision['reason']}")
            
            # Mark as processed
            state.mark_signal_processed(
                db_signal_id, 
                executed=decision['should_execute'], 
                execution_result=decision
            )
            
            return {
                **decision,
                'signal_id': db_signal_id,
                'signal': signal
            }
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return {
                'action': 'error',
                'reason': f'Processing error: {str(e)}',
                'should_execute': False
            }
    
    def _apply_filters(self, signal: TradingSignal) -> Dict[str, Any]:
        """Apply all filters to determine if signal should be processed"""
        
        # 1. Blacklist filter
        if self._is_blacklisted(signal.token_address):
            return {
                'passed': False,
                'reason': 'Token is blacklisted',
                'filter': 'blacklist'
            }
        
        # 2. Market cap filter
        min_mcap = config.get('bot.min_market_cap', 100000)
        if signal.market_cap > 0 and signal.market_cap < min_mcap:
            return {
                'passed': False,
                'reason': f'Market cap too low: ${signal.market_cap:,.0f} < ${min_mcap:,.0f}',
                'filter': 'market_cap'
            }
        
        # 3. Trade score filter
        min_score = config.get('bot.min_trade_score', 70)
        if signal.trade_score > 0 and signal.trade_score < min_score:
            return {
                'passed': False,
                'reason': f'Trade score too low: {signal.trade_score} < {min_score}',
                'filter': 'trade_score'
            }
        
        # 4. Smart holders filter
        min_holders = config.get('filters.min_holder_count', 3)
        if len(signal.smart_holders) < min_holders:
            return {
                'passed': False,
                'reason': f'Not enough smart holders: {len(signal.smart_holders)} < {min_holders}',
                'filter': 'smart_holders'
            }
        
        # 5. Recently seen filter (avoid spam)
        if state.is_token_seen_recently(signal.token_address, hours=1):
            return {
                'passed': False,
                'reason': 'Token signal received recently (within 1 hour)',
                'filter': 'recent_duplicate'
            }
        
        # 6. Trusted holders filter (optional enhancement)
        trusted_holders = config.get('filters.trusted_holders', [])
        if trusted_holders:
            has_trusted = any(
                holder['name'].lower() in [t.lower() for t in trusted_holders]
                for holder in signal.smart_holders
            )
            if not has_trusted:
                return {
                    'passed': False,
                    'reason': 'No trusted smart holders found',
                    'filter': 'trusted_holders'
                }
        
        return {
            'passed': True,
            'reason': 'All filters passed'
        }
    
    def _make_trading_decision(self, signal: TradingSignal) -> Dict[str, Any]:
        """Make final trading decision based on signal and current state"""
        
        # Check if we're in live mode
        is_live_mode = config.is_live_mode()
        
        # Calculate trade parameters
        trade_params = self._calculate_trade_parameters(signal)
        
        # Determine action
        if signal.signal_type == 'BUY':
            action = 'buy'
            reasoning = self._get_buy_reasoning(signal, trade_params)
        elif signal.signal_type == 'SELL':
            action = 'sell' 
            reasoning = self._get_sell_reasoning(signal, trade_params)
        else:
            return {
                'action': 'skip',
                'reason': 'Unknown signal type',
                'should_execute': False
            }
        
        return {
            'action': action,
            'reason': reasoning,
            'should_execute': True,
            'trade_params': trade_params,
            'mode': 'live' if is_live_mode else 'dry-run'
        }
    
    def _calculate_trade_parameters(self, signal: TradingSignal) -> Dict[str, Any]:
        """Calculate trade parameters like amount, slippage, etc."""
        
        # Get configuration
        trade_amount_sol = config.get('bot.trade_amount_sol', 0.1)
        max_slippage = config.get('bot.max_slippage', 5.0)
        
        # Calculate priority based on signal strength
        priority_score = self._calculate_priority_score(signal)
        
        # Adjust trade amount based on signal strength (optional)
        adjusted_amount = trade_amount_sol
        if priority_score > 90:
            adjusted_amount *= 1.5  # Increase for very strong signals
        elif priority_score < 70:
            adjusted_amount *= 0.5  # Decrease for weaker signals
        
        return {
            'amount_sol': adjusted_amount,
            'max_slippage': max_slippage,
            'priority_score': priority_score,
            'token_address': signal.token_address,
            'jupiter_link': signal.jupiter_link
        }
    
    def _calculate_priority_score(self, signal: TradingSignal) -> float:
        """Calculate a priority score for the signal (0-100)"""
        score = 0.0
        
        # Base score from trade score
        if signal.trade_score > 0:
            score += min(signal.trade_score, 50)  # Max 50 points from trade score
        
        # Points for smart holders count
        holder_count = len(signal.smart_holders)
        score += min(holder_count * 5, 20)  # Max 20 points from holders (4+ holders)
        
        # Points for market cap (favor medium market caps)
        if signal.market_cap > 0:
            if 1_000_000 <= signal.market_cap <= 50_000_000:  # Sweet spot
                score += 20
            elif 100_000 <= signal.market_cap < 1_000_000:
                score += 10
            elif signal.market_cap > 50_000_000:
                score += 5
        
        # Bonus points for trusted holders
        trusted_holders = config.get('filters.trusted_holders', [])
        if trusted_holders:
            trusted_count = sum(
                1 for holder in signal.smart_holders
                if holder['name'].lower() in [t.lower() for t in trusted_holders]
            )
            score += trusted_count * 5  # 5 points per trusted holder
        
        return min(score, 100.0)
    
    def _get_buy_reasoning(self, signal: TradingSignal, trade_params: Dict[str, Any]) -> str:
        """Generate reasoning for BUY decision"""
        reasons = []
        
        if signal.trade_score > 80:
            reasons.append(f"High trade score ({signal.trade_score})")
        
        if len(signal.smart_holders) >= 5:
            reasons.append(f"Strong smart holder activity ({len(signal.smart_holders)} holders)")
        
        if signal.market_cap > 0:
            reasons.append(f"Market cap: ${signal.market_cap:,.0f}")
        
        priority = trade_params.get('priority_score', 0)
        if priority > 90:
            reasons.append("Exceptional signal strength")
        elif priority > 80:
            reasons.append("Strong signal")
        
        return f"BUY signal - {', '.join(reasons)}"
    
    def _get_sell_reasoning(self, signal: TradingSignal, trade_params: Dict[str, Any]) -> str:
        """Generate reasoning for SELL decision"""
        reasons = []
        
        red_holders = [h for h in signal.smart_holders if h['type'] == 'red']
        if red_holders:
            reasons.append(f"Smart holder exit detected ({len(red_holders)} holders)")
        
        if signal.trade_score > 0:
            reasons.append(f"Trade score: {signal.trade_score}")
        
        return f"SELL signal - {', '.join(reasons)}"
    
    def _is_blacklisted(self, token_address: str) -> bool:
        """Check if token is blacklisted"""
        # Check both config and database blacklists
        config_blacklist = config.is_token_blacklisted(token_address)
        db_blacklist = state.is_token_blacklisted(token_address)
        
        return config_blacklist or db_blacklist
    
    def add_to_blacklist(self, token_address: str, reason: str = None) -> None:
        """Add token to blacklist"""
        try:
            state.add_to_blacklist(token_address, reason)
            config.add_blacklisted_token(token_address)
            logger.info(f"Added {token_address} to blacklist: {reason}")
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {e}")
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            'processed_signals_session': len(self.processed_signals),
            'filters': {
                'min_market_cap': config.get('bot.min_market_cap'),
                'min_trade_score': config.get('bot.min_trade_score'),
                'min_holder_count': config.get('filters.min_holder_count'),
                'trusted_holders_count': len(config.get('filters.trusted_holders', [])),
                'blacklisted_tokens': len(config.get('filters.blacklisted_tokens', []))
            },
            'trading_params': {
                'mode': config.get('bot.mode'),
                'trade_amount_sol': config.get('bot.trade_amount_sol'),
                'max_slippage': config.get('bot.max_slippage')
            }
        }
    
    def update_filter_settings(self, settings: Dict[str, Any]) -> None:
        """Update filter settings"""
        try:
            for key, value in settings.items():
                if key in ['min_market_cap', 'min_trade_score', 'max_slippage', 'trade_amount_sol']:
                    config.set(f'bot.{key}', value)
                elif key in ['min_holder_count', 'trusted_holders']:
                    config.set(f'filters.{key}', value)
            
            logger.info("Filter settings updated")
            
        except Exception as e:
            logger.error(f"Failed to update filter settings: {e}")
            raise

# Global engine instance
engine = TradingEngine() 