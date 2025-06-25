"""
Web API module.
FastAPI server for the dashboard interface.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config import config
from state import state
from wallet import wallet
from engine import engine

logger = logging.getLogger(__name__)

# Pydantic models for API
class ModeUpdate(BaseModel):
    mode: str  # 'dry-run' or 'live'

class FilterUpdate(BaseModel):
    min_market_cap: int = None
    min_trade_score: int = None
    min_holder_count: int = None
    max_slippage: float = None
    trade_amount_sol: float = None

class BlacklistAdd(BaseModel):
    token_address: str
    reason: str = None

# Create FastAPI app
app = FastAPI(title="Solanagram Dashboard", version="1.0.0")

# Setup templates (we'll create simple HTML templates)
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Setup static files (for CSS/JS)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Authentication dependency (simple token-based)
def verify_token(request: Request):
    """Simple token verification"""
    api_token = config.get('bot.api_token', 'default-token')
    
    # Check for token in header or query param
    auth_header = request.headers.get('Authorization', '')
    token_param = request.query_params.get('token', '')
    
    provided_token = None
    if auth_header.startswith('Bearer '):
        provided_token = auth_header[7:]
    elif token_param:
        provided_token = token_param
    
    if not provided_token or provided_token != api_token:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")
    
    return True

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/chat-log", response_class=HTMLResponse)
async def chat_log_page(request: Request):
    """Chat log page with messages and trades"""
    return templates.TemplateResponse("chat_log.html", {"request": request})

@app.get("/api/status")
async def get_status(authorized: bool = Depends(verify_token)):
    """Get bot status information"""
    try:
        wallet_info = wallet.get_wallet_info()
        bot_stats = state.get_stats()
        engine_stats = engine.get_engine_stats()
        
        return {
            "status": "running",
            "mode": config.get('bot.mode'),
            "wallet": wallet_info,
            "stats": bot_stats,
            "engine": engine_stats,
            "telegram": {
                "connected": False,  # TODO: implement telegram status check
                "group_id": config.get('telegram.group_id')
            }
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals")
async def get_signals(limit: int = 50, authorized: bool = Depends(verify_token)):
    """Get recent trading signals"""
    try:
        signals = state.get_recent_signals(limit)
        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades")
async def get_trades(limit: int = 100, authorized: bool = Depends(verify_token)):
    """Get recent trades"""
    try:
        trades = state.get_trades(limit)
        return {"trades": trades}
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat-log")
async def get_chat_log(limit: int = 50, authorized: bool = Depends(verify_token)):
    """Get messages with their corresponding trades"""
    try:
        messages_with_trades = state.get_messages_with_trades(limit)
        return {"chat_log": messages_with_trades}
    except Exception as e:
        logger.error(f"Error getting chat log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mode")
async def update_mode(mode_update: ModeUpdate, authorized: bool = Depends(verify_token)):
    """Update bot trading mode"""
    try:
        if mode_update.mode not in ['dry-run', 'live']:
            raise HTTPException(status_code=400, detail="Mode must be 'dry-run' or 'live'")
        
        config.set_mode(mode_update.mode)
        
        return {
            "success": True,
            "message": f"Mode updated to {mode_update.mode}",
            "new_mode": mode_update.mode
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/filters")
async def update_filters(filter_update: FilterUpdate, authorized: bool = Depends(verify_token)):
    """Update trading filters"""
    try:
        # Build update dict with only provided values
        updates = {}
        if filter_update.min_market_cap is not None:
            updates['min_market_cap'] = filter_update.min_market_cap
        if filter_update.min_trade_score is not None:
            updates['min_trade_score'] = filter_update.min_trade_score
        if filter_update.min_holder_count is not None:
            updates['min_holder_count'] = filter_update.min_holder_count
        if filter_update.max_slippage is not None:
            updates['max_slippage'] = filter_update.max_slippage
        if filter_update.trade_amount_sol is not None:
            updates['trade_amount_sol'] = filter_update.trade_amount_sol
        
        engine.update_filter_settings(updates)
        
        return {
            "success": True,
            "message": "Filters updated successfully",
            "updated": updates
        }
    except Exception as e:
        logger.error(f"Error updating filters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/blacklist")
async def get_blacklist(authorized: bool = Depends(verify_token)):
    """Get blacklisted tokens"""
    try:
        blacklist = state.get_blacklist()
        return {"blacklist": blacklist}
    except Exception as e:
        logger.error(f"Error getting blacklist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/blacklist")
async def add_to_blacklist(blacklist_add: BlacklistAdd, authorized: bool = Depends(verify_token)):
    """Add token to blacklist"""
    try:
        engine.add_to_blacklist(blacklist_add.token_address, blacklist_add.reason)
        
        return {
            "success": True,
            "message": f"Token {blacklist_add.token_address} added to blacklist"
        }
    except Exception as e:
        logger.error(f"Error adding to blacklist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wallet")
async def get_wallet_info(authorized: bool = Depends(verify_token)):
    """Get wallet information"""
    try:
        wallet_info = wallet.get_wallet_info()
        
        # Add transaction history
        transactions = wallet.get_transaction_history(10)
        wallet_info['recent_transactions'] = transactions
        
        return wallet_info
    except Exception as e:
        logger.error(f"Error getting wallet info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
async def get_config(authorized: bool = Depends(verify_token)):
    """Get bot configuration"""
    try:
        config_dict = config.to_dict()
        
        # Remove sensitive information
        if 'telegram' in config_dict:
            config_dict['telegram'] = {
                'api_id': '***' if config_dict['telegram'].get('api_id') else None,
                'api_hash': '***' if config_dict['telegram'].get('api_hash') else None,
                'phone': '***' if config_dict['telegram'].get('phone') else None,
                'group_id': config_dict['telegram'].get('group_id')
            }
        
        return {"config": config_dict}
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs(lines: int = 100, authorized: bool = Depends(verify_token)):
    """Get recent log entries"""
    try:
        log_file = state.log_path
        
        if not log_file.exists():
            return {"logs": []}
        
        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {"logs": [line.strip() for line in recent_lines]}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "solanagram-bot"}

# Create app factory
def create_app() -> FastAPI:
    """Factory function to create the app"""
    return app

# Create simple HTML template if it doesn't exist
def create_dashboard_template():
    """Create a simple dashboard template"""
    template_file = templates_dir / "dashboard.html"
    
    if not template_file.exists():
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solanagram Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status { display: flex; justify-content: space-between; align-items: center; }
        .mode-live { color: #e74c3c; font-weight: bold; }
        .mode-dry-run { color: #27ae60; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .signal-buy { color: #27ae60; }
        .signal-sell { color: #e74c3c; }
        button { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-success { background: #27ae60; color: white; }
        input, select { padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Solanagram Trading Bot Dashboard</h1>
        
        <div class="card">
            <div class="status">
                <h2>Bot Status</h2>
                <div id="bot-mode" class="mode-dry-run">DRY-RUN MODE</div>
            </div>
            <div id="status-info">Loading...</div>
            <button class="btn-primary" onclick="toggleMode()">Toggle Mode</button>
            <button class="btn-success" onclick="refreshData()">Refresh</button>
            <button class="btn-primary" onclick="window.location.href='/chat-log'">📱 Chat Log</button>
        </div>

        <div class="card">
            <h2>Wallet Information</h2>
            <div id="wallet-info">Loading...</div>
        </div>

        <div class="card">
            <h2>Recent Signals</h2>
            <div id="signals-table">Loading...</div>
        </div>

        <div class="card">
            <h2>Recent Trades</h2>
            <div id="trades-table">Loading...</div>
        </div>

        <div class="card">
            <h2>Filter Settings</h2>
            <div>
                <label>Min Market Cap: <input type="number" id="min_market_cap" placeholder="100000"></label>
                <label>Min Trade Score: <input type="number" id="min_trade_score" placeholder="70"></label>
                <label>Trade Amount (SOL): <input type="number" step="0.01" id="trade_amount_sol" placeholder="0.1"></label>
                <button class="btn-primary" onclick="updateFilters()">Update Filters</button>
            </div>
        </div>
    </div>

    <script>
        const API_TOKEN = 'default-token'; // Replace with your token
        
        async function apiCall(endpoint, method = 'GET', body = null) {
            const options = {
                method,
                headers: {
                    'Authorization': `Bearer ${API_TOKEN}`,
                    'Content-Type': 'application/json'
                }
            };
            
            if (body) {
                options.body = JSON.stringify(body);
            }
            
            const response = await fetch(`/api${endpoint}`, options);
            return response.json();
        }
        
        async function loadStatus() {
            try {
                const data = await apiCall('/status');
                const modeElement = document.getElementById('bot-mode');
                modeElement.textContent = data.mode.toUpperCase() + ' MODE';
                modeElement.className = data.mode === 'live' ? 'mode-live' : 'mode-dry-run';
                
                document.getElementById('status-info').innerHTML = `
                    <p><strong>Signals:</strong> ${data.stats.total_signals} total, ${data.stats.recent_signals} last 24h</p>
                    <p><strong>Trades:</strong> ${data.stats.total_trades} total, ${data.stats.successful_trades} successful</p>
                    <p><strong>Wallet:</strong> ${data.wallet.balance_sol?.toFixed(4) || 'N/A'} SOL</p>
                `;
            } catch (error) {
                console.error('Error loading status:', error);
            }
        }
        
        async function loadWallet() {
            try {
                const data = await apiCall('/wallet');
                document.getElementById('wallet-info').innerHTML = `
                    <p><strong>Address:</strong> ${data.address || 'N/A'}</p>
                    <p><strong>Balance:</strong> ${data.balance_sol?.toFixed(4) || 'N/A'} SOL (~$${data.balance_usd?.toFixed(2) || 'N/A'})</p>
                    <p><strong>Network:</strong> ${data.network || 'Unknown'}</p>
                `;
            } catch (error) {
                console.error('Error loading wallet:', error);
            }
        }
        
        async function loadSignals() {
            try {
                const data = await apiCall('/signals?limit=10');
                const table = data.signals.map(signal => `
                    <tr>
                        <td><span class="signal-${signal.signal_type.toLowerCase()}">${signal.signal_type}</span></td>
                        <td>${signal.token_name || 'Unknown'}</td>
                        <td>${signal.market_cap ? '$' + signal.market_cap.toLocaleString() : 'N/A'}</td>
                        <td>${signal.trade_score || 'N/A'}</td>
                        <td>${signal.smart_holders?.length || 0}</td>
                        <td>${new Date(signal.created_at).toLocaleString()}</td>
                    </tr>
                `).join('');
                
                document.getElementById('signals-table').innerHTML = `
                    <table>
                        <tr><th>Type</th><th>Token</th><th>Market Cap</th><th>Score</th><th>Holders</th><th>Time</th></tr>
                        ${table}
                    </table>
                `;
            } catch (error) {
                console.error('Error loading signals:', error);
            }
        }
        
        async function loadTrades() {
            try {
                const data = await apiCall('/trades?limit=10');
                const table = data.trades.map(trade => `
                    <tr>
                        <td>${trade.trade_type}</td>
                        <td>${trade.token_name || 'Unknown'}</td>
                        <td>${trade.amount_sol?.toFixed(4) || 'N/A'} SOL</td>
                        <td>${trade.status}</td>
                        <td>${new Date(trade.timestamp).toLocaleString()}</td>
                    </tr>
                `).join('');
                
                document.getElementById('trades-table').innerHTML = `
                    <table>
                        <tr><th>Type</th><th>Token</th><th>Amount</th><th>Status</th><th>Time</th></tr>
                        ${table}
                    </table>
                `;
            } catch (error) {
                console.error('Error loading trades:', error);
            }
        }
        
        async function toggleMode() {
            try {
                const statusData = await apiCall('/status');
                const newMode = statusData.mode === 'live' ? 'dry-run' : 'live';
                
                if (newMode === 'live') {
                    if (!confirm('Are you sure you want to enable LIVE trading? Real money will be used!')) {
                        return;
                    }
                }
                
                await apiCall('/mode', 'POST', { mode: newMode });
                await loadStatus();
            } catch (error) {
                console.error('Error toggling mode:', error);
                alert('Error toggling mode: ' + error.message);
            }
        }
        
        async function updateFilters() {
            try {
                const filters = {
                    min_market_cap: parseInt(document.getElementById('min_market_cap').value) || null,
                    min_trade_score: parseInt(document.getElementById('min_trade_score').value) || null,
                    trade_amount_sol: parseFloat(document.getElementById('trade_amount_sol').value) || null
                };
                
                await apiCall('/filters', 'POST', filters);
                alert('Filters updated successfully!');
            } catch (error) {
                console.error('Error updating filters:', error);
                alert('Error updating filters: ' + error.message);
            }
        }
        
        function refreshData() {
            loadStatus();
            loadWallet();
            loadSignals();
            loadTrades();
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
        """
        
        with open(template_file, 'w') as f:
            f.write(html_content.strip())
        
        logger.info("Created dashboard template")

def create_chat_log_template():
    """Create chat log template"""
    template_file = templates_dir / "chat_log.html"
    
    if not template_file.exists():
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Log - Solanagram</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            background: #f5f5f5; 
            height: 100vh;
        }
        .header {
            background: white;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .container { 
            display: flex; 
            height: calc(100vh - 80px);
            max-width: 1400px;
            margin: 0 auto;
            gap: 20px;
            padding: 20px;
        }
        .chat-column, .trades-column {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .chat-column {
            flex: 1;
            max-width: 60%;
        }
        .trades-column {
            flex: 1;
            max-width: 40%;
        }
        .column-header {
            background: #3498db;
            color: white;
            padding: 15px 20px;
            font-weight: bold;
            border-bottom: 1px solid #ddd;
        }
        .chat-content, .trades-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 12px 15px;
            margin: 10px 0;
            border-left: 4px solid #ddd;
        }
        .message.has-signal {
            border-left-color: #3498db;
            background: #e3f2fd;
        }
        .message-header {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        .message-text {
            color: #333;
            line-height: 1.4;
        }
        .trade-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid #ddd;
        }
        .trade-card.buy {
            border-left: 4px solid #27ae60;
            background: #d5f4e6;
        }
        .trade-card.sell {
            border-left: 4px solid #e74c3c;
            background: #ffeaea;
        }
        .trade-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .trade-type {
            font-weight: bold;
            font-size: 14px;
            padding: 4px 8px;
            border-radius: 4px;
            color: white;
        }
        .trade-type.buy {
            background: #27ae60;
        }
        .trade-type.sell {
            background: #e74c3c;
        }
        .trade-details {
            font-size: 13px;
            line-height: 1.5;
        }
        .trade-amount {
            font-weight: bold;
            font-size: 16px;
        }
        .profit {
            font-weight: bold;
        }
        .profit.positive {
            color: #27ae60;
        }
        .profit.negative {
            color: #e74c3c;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-secondary {
            background: #95a5a6;
            color: white;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .no-data {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .timestamp {
            font-size: 11px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📱 Chat Log - Solanagram</h1>
        <div>
            <button class="btn btn-secondary" onclick="window.location.href='/'">← Back to Dashboard</button>
            <button class="btn btn-primary" onclick="refreshChatLog()">🔄 Refresh</button>
        </div>
    </div>

    <div class="container">
        <div class="chat-column">
            <div class="column-header">
                💬 Telegram Messages
            </div>
            <div class="chat-content" id="chat-content">
                <div class="loading">Loading messages...</div>
            </div>
        </div>

        <div class="trades-column">
            <div class="column-header">
                📊 Trade Results
            </div>
            <div class="trades-content" id="trades-content">
                <div class="loading">Loading trades...</div>
            </div>
        </div>
    </div>

    <script>
        const API_TOKEN = 'default-token'; // Replace with your token
        
        async function apiCall(endpoint, method = 'GET', body = null) {
            const options = {
                method,
                headers: {
                    'Authorization': `Bearer ${API_TOKEN}`,
                    'Content-Type': 'application/json'
                }
            };
            
            if (body) {
                options.body = JSON.stringify(body);
            }
            
            const response = await fetch(`/api${endpoint}`, options);
            return response.json();
        }
        
        function formatDate(dateString) {
            if (!dateString) return 'Unknown';
            const date = new Date(dateString);
            return date.toLocaleString();
        }
        
        function formatAmount(amount, decimals = 4) {
            if (amount === null || amount === undefined) return 'N/A';
            return parseFloat(amount).toFixed(decimals);
        }
        
        function calculateProfit(trade) {
            // Simplified profit calculation
            // In reality this would need more complex logic
            if (!trade.amount_sol || !trade.price) return null;
            
            const estimatedGasFees = 0.002; // SOL
            const baseAmount = trade.amount_sol;
            
            if (trade.trade_type === 'SELL') {
                // For sell, calculate profit based on some assumptions
                const estimatedProfit = baseAmount * 0.1; // Placeholder: 10% gain
                return estimatedProfit - estimatedGasFees;
            }
            
            return null;
        }
        
        async function loadChatLog() {
            try {
                const data = await apiCall('/chat-log?limit=100');
                
                // Separate messages and trades
                const messagesMap = new Map();
                const tradesMap = new Map();
                
                data.chat_log.forEach(item => {
                    const messageKey = item.message_id || item.id;
                    
                    if (!messagesMap.has(messageKey)) {
                        messagesMap.set(messageKey, {
                            id: item.id,
                            message_id: item.message_id,
                            username: item.username,
                            first_name: item.first_name,
                            message_text: item.message_text,
                            message_date: item.message_date,
                            has_signal: item.has_signal,
                            signal_id: item.signal_id
                        });
                    }
                    
                    if (item.trade_type && item.signal_id) {
                        if (!tradesMap.has(item.signal_id)) {
                            tradesMap.set(item.signal_id, []);
                        }
                        tradesMap.get(item.signal_id).push({
                            trade_type: item.trade_type,
                            token_name: item.token_name,
                            token_address: item.token_address,
                            amount_sol: item.amount_sol,
                            amount_tokens: item.amount_tokens,
                            price: item.price,
                            slippage: item.slippage,
                            status: item.trade_status,
                            transaction_hash: item.transaction_hash,
                            timestamp: item.trade_timestamp,
                            error_message: item.error_message,
                            signal_id: item.signal_id
                        });
                    }
                });
                
                displayMessages(Array.from(messagesMap.values()));
                displayTrades(Array.from(tradesMap.values()).flat());
                
            } catch (error) {
                console.error('Error loading chat log:', error);
                document.getElementById('chat-content').innerHTML = '<div class="no-data">Error loading messages</div>';
                document.getElementById('trades-content').innerHTML = '<div class="no-data">Error loading trades</div>';
            }
        }
        
        function displayMessages(messages) {
            const chatContent = document.getElementById('chat-content');
            
            if (messages.length === 0) {
                chatContent.innerHTML = '<div class="no-data">No messages found</div>';
                return;
            }
            
            const messagesHtml = messages.map(msg => `
                <div class="message ${msg.has_signal ? 'has-signal' : ''}">
                    <div class="message-header">
                        <strong>${msg.first_name || msg.username || 'Unknown'}</strong>
                        <span class="timestamp">${formatDate(msg.message_date)}</span>
                        ${msg.has_signal ? '<span style="color: #3498db;">🔔 Signal</span>' : ''}
                    </div>
                    <div class="message-text">${msg.message_text || 'No text'}</div>
                </div>
            `).join('');
            
            chatContent.innerHTML = messagesHtml;
        }
        
        function displayTrades(trades) {
            const tradesContent = document.getElementById('trades-content');
            
            if (trades.length === 0) {
                tradesContent.innerHTML = '<div class="no-data">No trades found</div>';
                return;
            }
            
            const tradesHtml = trades.map(trade => {
                const profit = calculateProfit(trade);
                const profitClass = profit > 0 ? 'positive' : profit < 0 ? 'negative' : '';
                
                return `
                    <div class="trade-card ${trade.trade_type.toLowerCase()}">
                        <div class="trade-header">
                            <span class="trade-type ${trade.trade_type.toLowerCase()}">${trade.trade_type}</span>
                            <span class="timestamp">${formatDate(trade.timestamp)}</span>
                        </div>
                        <div class="trade-details">
                            <div><strong>Token:</strong> ${trade.token_name || 'Unknown'}</div>
                            <div class="trade-amount">
                                <strong>Amount:</strong> ${formatAmount(trade.amount_sol)} SOL
                                ${trade.amount_tokens ? `(${formatAmount(trade.amount_tokens, 0)} tokens)` : ''}
                            </div>
                            <div><strong>Price:</strong> ${formatAmount(trade.price, 8)} SOL</div>
                            <div><strong>Slippage:</strong> ${formatAmount(trade.slippage, 2)}%</div>
                            <div><strong>Status:</strong> 
                                <span style="color: ${trade.status === 'success' ? '#27ae60' : trade.status === 'failed' ? '#e74c3c' : '#f39c12'}">
                                    ${trade.status}
                                </span>
                            </div>
                            ${profit !== null ? `
                                <div><strong>Estimated Profit:</strong> 
                                    <span class="profit ${profitClass}">${profit > 0 ? '+' : ''}${formatAmount(profit)} SOL</span>
                                </div>
                            ` : ''}
                            ${trade.transaction_hash ? `
                                <div><strong>TX:</strong> 
                                    <a href="https://solscan.io/tx/${trade.transaction_hash}" target="_blank" style="color: #3498db;">
                                        ${trade.transaction_hash.substring(0, 8)}...
                                    </a>
                                </div>
                            ` : ''}
                            ${trade.error_message ? `
                                <div style="color: #e74c3c;"><strong>Error:</strong> ${trade.error_message}</div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }).join('');
            
            tradesContent.innerHTML = tradesHtml;
        }
        
        function refreshChatLog() {
            document.getElementById('chat-content').innerHTML = '<div class="loading">Loading messages...</div>';
            document.getElementById('trades-content').innerHTML = '<div class="loading">Loading trades...</div>';
            loadChatLog();
        }
        
        // Initial load
        loadChatLog();
        
        // Auto-refresh every 30 seconds
        setInterval(loadChatLog, 30000);
    </script>
</body>
</html>
        """
        
        with open(template_file, 'w') as f:
            f.write(html_content.strip())
        
        logger.info("Created chat log template")

# Initialize templates on import
create_dashboard_template()
create_chat_log_template() 