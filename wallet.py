"""
Solana wallet management module.
Handles wallet operations, balance checks, and transaction signing.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import transfer as create_transfer_instruction
from solders.transaction import Transaction as SoldersTransaction
from solders.message import Message
from solders.instruction import Instruction
from solana.rpc.types import TxOpts
from cryptography.fernet import Fernet

from config import config

logger = logging.getLogger(__name__)

class SolanaWallet:
    """Solana wallet manager with encryption support"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or config.data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.wallet_file = self.data_dir / 'wallet.json'
        self.keypair: Optional[Keypair] = None
        
        # Initialize Solana RPC client
        rpc_url = config.get('solana.rpc_url')
        self.client = Client(rpc_url)
        
        # Load or create wallet
        self._load_or_create_wallet()
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key from environment or create new one"""
        key_file = self.data_dir / 'wallet.key'
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Secure the key file (Unix only)
            try:
                import os
                os.chmod(key_file, 0o600)
            except:
                pass
            
            logger.warning("Generated new wallet encryption key. Keep wallet.key file secure!")
            return key
    
    def _load_or_create_wallet(self) -> None:
        """Load existing wallet or create a new one"""
        if self.wallet_file.exists():
            self._load_wallet()
        else:
            self._create_new_wallet()
    
    def _create_new_wallet(self) -> None:
        """Create a new Solana wallet"""
        try:
            # Generate new keypair
            self.keypair = Keypair()
            
            # Save encrypted wallet
            self._save_wallet()
            
            logger.info(f"Created new wallet: {self.get_address()}")
            logger.warning("IMPORTANT: Save your private key backup securely!")
            
        except Exception as e:
            logger.error(f"Failed to create wallet: {e}")
            raise
    
    def _load_wallet(self) -> None:
        """Load wallet from encrypted file"""
        try:
            # Get encryption key
            encryption_key = self._generate_encryption_key()
            fernet = Fernet(encryption_key)
            
            # Load and decrypt wallet
            with open(self.wallet_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = fernet.decrypt(encrypted_data)
            wallet_data = json.loads(decrypted_data.decode())
            
            # Restore keypair from private key
            private_key_bytes = bytes(wallet_data['private_key'])
            self.keypair = Keypair.from_bytes(private_key_bytes)
            
            logger.info(f"Loaded wallet: {self.get_address()}")
            
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")
            raise
    
    def _save_wallet(self) -> None:
        """Save wallet to encrypted file"""
        try:
            if not self.keypair:
                raise ValueError("No keypair to save")
            
            # Get encryption key
            encryption_key = self._generate_encryption_key()
            fernet = Fernet(encryption_key)
            
            # Prepare wallet data
            wallet_data = {
                'public_key': str(self.keypair.pubkey()),
                'private_key': list(bytes(self.keypair))
            }
            
            # Encrypt and save
            data_to_encrypt = json.dumps(wallet_data).encode()
            encrypted_data = fernet.encrypt(data_to_encrypt)
            
            with open(self.wallet_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Secure the wallet file (Unix only)
            try:
                import os
                os.chmod(self.wallet_file, 0o600)
            except:
                pass
            
            logger.info("Wallet saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save wallet: {e}")
            raise
    
    def get_address(self) -> str:
        """Get wallet public address"""
        if not self.keypair:
            raise ValueError("Wallet not initialized")
        return str(self.keypair.pubkey())
    
    def get_balance(self) -> float:
        """Get SOL balance in the wallet"""
        try:
            if not self.keypair:
                raise ValueError("Wallet not initialized")
            
            response = self.client.get_balance(self.keypair.pubkey())
            
            # Handle response properly for solders
            if hasattr(response, 'value'):
                # Convert lamports to SOL (1 SOL = 1e9 lamports)
                balance_lamports = response.value
                balance_sol = balance_lamports / 1e9
                return balance_sol
            elif isinstance(response, dict) and 'result' in response:
                # Handle dict response format
                balance_lamports = response['result']['value']
                balance_sol = balance_lamports / 1e9
                return balance_sol
            else:
                logger.error(f"Failed to get balance: {response}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    def get_token_balance(self, token_mint: str) -> float:
        """Get balance of a specific SPL token"""
        try:
            if not self.keypair:
                raise ValueError("Wallet not initialized")
            
            # Get token accounts by owner
            token_accounts = self.client.get_token_accounts_by_owner(
                self.keypair.pubkey(),
                {"mint": Pubkey.from_string(token_mint)}
            )
            
            # Handle response properly
            if hasattr(token_accounts, 'value'):
                accounts = token_accounts.value
            elif isinstance(token_accounts, dict) and 'result' in token_accounts:
                accounts = token_accounts['result']['value']
            else:
                return 0.0
            
            if accounts:
                # Get the first token account
                token_account = accounts[0]
                if hasattr(token_account, 'account'):
                    account_info = token_account.account.data.parsed.info
                else:
                    account_info = token_account['account']['data']['parsed']['info']
                
                # Get token amount and decimals
                token_amount = int(account_info['tokenAmount']['amount'])
                decimals = int(account_info['tokenAmount']['decimals'])
                
                # Convert to human readable format
                balance = token_amount / (10 ** decimals)
                return balance
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting token balance for {token_mint}: {e}")
            return 0.0
    
    def send_sol(self, to_address: str, amount: float, dry_run: bool = True) -> Dict[str, Any]:
        """
        Send SOL to another address.
        
        Args:
            to_address: Recipient address
            amount: Amount in SOL
            dry_run: If True, only simulate the transaction
            
        Returns:
            Transaction result dictionary
        """
        try:
            if not self.keypair:
                raise ValueError("Wallet not initialized")
            
            # Convert SOL to lamports
            lamports = int(amount * 1e9)
            
            # Create transfer instruction using solders
            transfer_instruction = create_transfer_instruction(
                from_pubkey=self.keypair.pubkey(),
                to_pubkey=Pubkey.from_string(to_address),
                lamports=lamports
            )
            
            # Get latest blockhash
            recent_blockhash_resp = self.client.get_latest_blockhash()
            
            # Handle blockhash response properly
            if hasattr(recent_blockhash_resp, 'value'):
                recent_blockhash = recent_blockhash_resp.value.blockhash
            elif isinstance(recent_blockhash_resp, dict) and 'result' in recent_blockhash_resp:
                recent_blockhash = recent_blockhash_resp['result']['value']['blockhash']
            else:
                raise ValueError("Failed to get recent blockhash")
            
            # Create message and transaction
            message = Message([transfer_instruction], self.keypair.pubkey())
            transaction = SoldersTransaction([self.keypair], message, recent_blockhash)
            
            if dry_run:
                # Simulate transaction
                result = self.client.simulate_transaction(transaction)
                return {
                    'success': True,
                    'dry_run': True,
                    'simulation': result,
                    'amount': amount,
                    'to_address': to_address
                }
            else:
                # Send actual transaction
                result = self.client.send_transaction(
                    transaction,
                    opts=TxOpts(skip_preflight=False)
                )
                
                # Handle transaction result properly
                if hasattr(result, 'value'):
                    tx_hash = result.value
                elif isinstance(result, dict) and 'result' in result:
                    tx_hash = result['result']
                else:
                    tx_hash = str(result)
                
                return {
                    'success': True,
                    'dry_run': False,
                    'transaction_hash': tx_hash,
                    'amount': amount,
                    'to_address': to_address
                }
                
        except Exception as e:
            logger.error(f"Failed to send SOL: {e}")
            return {
                'success': False,
                'error': str(e),
                'amount': amount,
                'to_address': to_address
            }
    
    def get_transaction_history(self, limit: int = 10) -> list:
        """Get recent transaction history"""
        try:
            if not self.keypair:
                raise ValueError("Wallet not initialized")
            
            # Get signatures for address
            signatures = self.client.get_signatures_for_address(
                self.keypair.pubkey(),
                limit=limit
            )
            
            # Handle signatures response properly
            if hasattr(signatures, 'value'):
                sig_list = signatures.value
            elif isinstance(signatures, dict) and 'result' in signatures:
                sig_list = signatures['result']
            else:
                return []
            
            transactions = []
            for sig_info in sig_list:
                try:
                    # Get full transaction details
                    tx_details = self.client.get_transaction(sig_info.signature if hasattr(sig_info, 'signature') else sig_info['signature'])
                    
                    # Handle transaction details response
                    if hasattr(tx_details, 'value') and tx_details.value:
                        tx_data = tx_details.value
                        transactions.append({
                            'signature': sig_info.signature if hasattr(sig_info, 'signature') else sig_info['signature'],
                            'slot': sig_info.slot if hasattr(sig_info, 'slot') else sig_info['slot'],
                            'block_time': sig_info.block_time if hasattr(sig_info, 'block_time') else sig_info['blockTime'],
                            'status': 'success' if not (sig_info.err if hasattr(sig_info, 'err') else sig_info['err']) else 'failed',
                            'fee': tx_data.meta.fee / 1e9 if hasattr(tx_data, 'meta') else 0,  # Convert to SOL
                        })
                    elif isinstance(tx_details, dict) and tx_details.get('result'):
                        tx_data = tx_details['result']
                        transactions.append({
                            'signature': sig_info['signature'],
                            'slot': sig_info['slot'],
                            'block_time': sig_info['blockTime'],
                            'status': 'success' if not sig_info['err'] else 'failed',
                            'fee': tx_data['meta']['fee'] / 1e9,  # Convert to SOL
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to get transaction details for {sig_info.signature if hasattr(sig_info, 'signature') else sig_info['signature']}: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return []
    
    def export_private_key(self) -> str:
        """Export private key as base58 string (for backup)"""
        if not self.keypair:
            raise ValueError("Wallet not initialized")
        
        import base58
        return base58.b58encode(bytes(self.keypair)).decode()
    
    def import_private_key(self, private_key_b58: str) -> None:
        """Import wallet from base58 private key"""
        try:
            import base58
            private_key_bytes = base58.b58decode(private_key_b58)
            self.keypair = Keypair.from_bytes(private_key_bytes)
            
            # Save the imported wallet
            self._save_wallet()
            
            logger.info(f"Imported wallet: {self.get_address()}")
            
        except Exception as e:
            logger.error(f"Failed to import private key: {e}")
            raise
    
    def get_wallet_info(self) -> Dict[str, Any]:
        """Get comprehensive wallet information"""
        if not self.keypair:
            return {"error": "Wallet not initialized"}
        
        try:
            balance = self.get_balance()
            
            return {
                'address': self.get_address(),
                'balance_sol': balance,
                'balance_usd': balance * self._get_sol_price(),  # Approximate
                'network': 'mainnet-beta' if 'mainnet' in config.get('solana.rpc_url') else 'devnet',
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            return {"error": str(e)}
    
    def _get_sol_price(self) -> float:
        """Get SOL price in USD (simple implementation)"""
        try:
            import requests
            response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd', timeout=5)
            if response.status_code == 200:
                return response.json()['solana']['usd']
        except:
            pass
        return 100.0  # Fallback price

# Global wallet instance
wallet = SolanaWallet() 