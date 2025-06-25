"""
Main application entry point.
Coordinates all modules and starts the bot.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Import all modules
from config import config
from state import state
from engine import engine
from wallet import wallet
from telegram_listener import create_telegram_listener
from api import create_app

logger = logging.getLogger(__name__)

class SolanagramBot:
    """Main bot coordinator"""
    
    def __init__(self):
        self.telegram_listener = None
        self.web_server = None
        self.running = False
        self.telegram_enabled = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def process_trading_signal(self, signal):
        """Process a trading signal from Telegram"""
        try:
            # Process through the trading engine
            result = engine.process_signal(signal)
            
            if result.get('should_execute'):
                logger.info(f"Executing {result['action']} for {signal.token_name}")
                
                # Execute the trade (implement Jupiter integration)
                execution_result = await self._execute_trade(result)
                
                # Update the database with execution result
                if execution_result.get('success'):
                    state.save_trade(result['signal_id'], execution_result)
                    logger.info(f"Trade executed successfully: {execution_result}")
                else:
                    logger.error(f"Trade execution failed: {execution_result}")
            else:
                logger.info(f"Signal not executed: {result['reason']}")
                
        except Exception as e:
            logger.error(f"Error processing trading signal: {e}")
    
    async def _execute_trade(self, decision):
        """Execute a trading decision"""
        try:
            is_live_mode = config.is_live_mode()
            trade_params = decision.get('trade_params', {})
            signal = decision.get('signal')
            
            if decision['action'] == 'buy':
                return await self._execute_buy(trade_params, is_live_mode)
            elif decision['action'] == 'sell':
                return await self._execute_sell(trade_params, is_live_mode)
            else:
                return {
                    'success': False,
                    'error': f"Unknown action: {decision['action']}"
                }
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_buy(self, trade_params, is_live_mode):
        """Execute a buy order"""
        try:
            amount_sol = trade_params.get('amount_sol', 0.1)
            token_address = trade_params.get('token_address')
            max_slippage = trade_params.get('max_slippage', 5.0)
            
            if is_live_mode:
                # In live mode, we would use Jupiter API to execute the swap
                # For now, this is a placeholder for Jupiter integration
                logger.warning("Live trading not implemented yet - would execute real trade")
                
                # Placeholder for Jupiter swap
                result = {
                    'success': True,
                    'trade_type': 'BUY',
                    'token_address': token_address,
                    'amount_sol': amount_sol,
                    'status': 'pending',
                    'transaction_hash': 'mock_tx_hash_' + token_address[:8],
                    'message': 'Live trading not implemented - this is a simulation'
                }
            else:
                # Dry run mode
                wallet_balance = wallet.get_balance()
                
                if wallet_balance < amount_sol:
                    return {
                        'success': False,
                        'error': f'Insufficient balance: {wallet_balance} SOL < {amount_sol} SOL'
                    }
                
                result = {
                    'success': True,
                    'trade_type': 'BUY',
                    'token_address': token_address,
                    'amount_sol': amount_sol,
                    'status': 'simulated',
                    'slippage': max_slippage,
                    'message': f'DRY RUN: Would buy {amount_sol} SOL worth of {token_address}'
                }
            
            logger.info(f"Buy execution result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Buy execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_sell(self, trade_params, is_live_mode):
        """Execute a sell order"""
        try:
            token_address = trade_params.get('token_address')
            max_slippage = trade_params.get('max_slippage', 5.0)
            
            if is_live_mode:
                # Check if we have tokens to sell
                token_balance = wallet.get_token_balance(token_address)
                
                if token_balance <= 0:
                    return {
                        'success': False,
                        'error': f'No tokens to sell for {token_address}'
                    }
                
                # Placeholder for Jupiter swap
                result = {
                    'success': True,
                    'trade_type': 'SELL',
                    'token_address': token_address,
                    'amount_tokens': token_balance,
                    'status': 'pending',
                    'transaction_hash': 'mock_sell_tx_' + token_address[:8],
                    'message': 'Live trading not implemented - this is a simulation'
                }
            else:
                # Dry run mode
                result = {
                    'success': True,
                    'trade_type': 'SELL',
                    'token_address': token_address,
                    'status': 'simulated',
                    'slippage': max_slippage,
                    'message': f'DRY RUN: Would sell all tokens of {token_address}'
                }
            
            logger.info(f"Sell execution result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Sell execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def start_web_server(self):
        """Start the web API server"""
        try:
            import uvicorn
            from api import app
            
            port = config.get('bot.web_port', 1717)
            
            # Create server config
            config_obj = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=port,
                log_level="info"
            )
            
            # Start server
            server = uvicorn.Server(config_obj)
            
            logger.info(f"Starting web server on port {port}")
            
            # Run in background
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise
    
    async def start_telegram_listener(self):
        """Start the Telegram listener"""
        try:
            # Check if Telegram is properly configured
            telegram_config = config.get_telegram_config()
            
            # Validate configuration
            api_id = telegram_config.get('api_id')
            api_hash = telegram_config.get('api_hash')
            
            # Check if values are valid (not the default placeholders)
            if (not api_id or api_id == 'your_api_id' or 
                not api_hash or api_hash == 'your_api_hash'):
                logger.warning("Telegram not configured properly. Running without Telegram integration.")
                logger.warning("To enable Telegram, configure TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")
                self.telegram_enabled = False
                return
                
            self.telegram_listener = create_telegram_listener(self.process_trading_signal)
            # Only initialize, don't start the blocking listen loop yet
            await self.telegram_listener.initialize()
            self.telegram_enabled = True
            
        except ValueError as e:
            logger.warning(f"Telegram configuration error: {e}")
            logger.warning("Running without Telegram integration.")
            self.telegram_enabled = False
        except Exception as e:
            logger.error(f"Failed to start Telegram listener: {e}")
            logger.warning("Running without Telegram integration.")
            self.telegram_enabled = False
    
    async def run_telegram_listener(self):
        """Run the Telegram listener (blocking)"""
        if self.telegram_listener:
            await self.telegram_listener.start_listening()
    
    async def run(self):
        """Main run loop"""
        try:
            logger.info("Starting Solanagram Bot...")
            
            # Check configuration (but don't exit if Telegram is not configured)
            self._check_configuration()
            
            # Initialize components
            logger.info("Initializing components...")
            
            # Check wallet
            wallet_info = wallet.get_wallet_info()
            if 'error' in wallet_info:
                logger.error(f"Wallet error: {wallet_info['error']}")
            else:
                logger.info(f"Wallet ready: {wallet_info['address']} ({wallet_info['balance_sol']:.4f} SOL)")
            
            # Get bot stats
            bot_stats = state.get_stats()
            logger.info(f"Database ready: {bot_stats.get('total_signals', 0)} signals in history")
            
            self.running = True
            
            # Start services
            tasks = []
            
            # Try to initialize Telegram if configured
            telegram_task = asyncio.create_task(self.start_telegram_listener())
            await telegram_task  # Wait to see if Telegram initializes successfully
            
            if self.telegram_enabled:
                logger.info("✅ Telegram integration enabled")
                # Add Telegram listener to tasks
                telegram_run_task = asyncio.create_task(self.run_telegram_listener())
                tasks.append(telegram_run_task)
            else:
                logger.warning("⚠️  Running without Telegram integration")
                logger.info("📱 Web dashboard is still available at http://localhost:1717")
            
            # Always start web server
            web_task = asyncio.create_task(self.start_web_server())
            tasks.append(web_task)
            
            # Wait for all services
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Bot startup failed: {e}")
            sys.exit(1)
    
    def _check_configuration(self):
        """Check if configuration is present (but don't require Telegram)"""
        # Only check for critical non-Telegram configuration
        mode = config.get('bot.mode', 'dry-run')
        logger.info(f"Bot mode: {mode.upper()}")
        
        if mode == 'live':
            logger.warning("⚠️  LIVE TRADING MODE ENABLED - Real transactions will be executed!")
        else:
            logger.info("✅ Dry-run mode - No real transactions will be executed")

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('solana').setLevel(logging.WARNING)

def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    
    logger.info("=" * 50)
    logger.info("🚀 Solanagram Trading Bot Starting...")
    logger.info("=" * 50)
    
    # Create and run bot
    bot = SolanagramBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 