"""
N8N Webhook Integration for Solanagram
Sends real-time notifications to N8N workflows when crypto addresses are extracted
"""

import requests
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class N8NWebhookSender:
    """Sends webhooks to N8N workflows for real-time processing"""
    
    def __init__(self, base_url: str = "http://localhost:5679"):
        self.base_url = base_url
        self.timeout = 10
        
    def send_crypto_alert(self, 
                         address: str,
                         address_type: str,
                         message_text: str,
                         sender_name: str,
                         chat_title: str,
                         extracted_at: datetime,
                         rule_name: str = "crypto_address") -> bool:
        """
        Send crypto address alert to N8N workflow
        
        Args:
            address: The extracted crypto address
            address_type: Type of address (bitcoin, ethereum, solana, etc.)
            message_text: Original message containing the address
            sender_name: Name of the message sender
            chat_title: Title of the source chat
            extracted_at: When the address was extracted
            rule_name: Extraction rule name
            
        Returns:
            bool: True if webhook was sent successfully
        """
        
        webhook_url = f"{self.base_url}/webhook/solanagram-crypto-alert"
        
        payload = {
            "event": "crypto_address_extracted",
            "timestamp": extracted_at.isoformat(),
            "data": {
                "address": address,
                "address_type": address_type,
                "rule_name": rule_name,
                "source": {
                    "chat_title": chat_title,
                    "sender_name": sender_name,
                    "message_text": message_text[:500]  # Limit message size
                },
                "metadata": {
                    "extracted_at": extracted_at.isoformat(),
                    "system": "solanagram",
                    "version": "1.0"
                }
            }
        }
        
        try:
            logger.info(f"Sending crypto alert webhook to N8N: {address}")
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Solanagram/1.0"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Webhook sent successfully to N8N for address: {address}")
                return True
            else:
                logger.warning(f"⚠️ N8N webhook returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ N8N webhook timeout for address: {address}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to N8N webhook endpoint: {webhook_url}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending N8N webhook: {e}")
            return False
    
    def send_system_alert(self, 
                         alert_type: str,
                         message: str,
                         level: str = "info",
                         data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send system alert to N8N workflow
        
        Args:
            alert_type: Type of alert (error, warning, info, etc.)
            message: Alert message
            level: Alert level (info, warning, critical)
            data: Additional data
            
        Returns:
            bool: True if webhook was sent successfully
        """
        
        webhook_url = f"{self.base_url}/webhook/solanagram-system-alert"
        
        payload = {
            "event": "system_alert",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "alert_type": alert_type,
                "level": level,
                "message": message,
                "additional_data": data or {},
                "metadata": {
                    "system": "solanagram",
                    "version": "1.0"
                }
            }
        }
        
        try:
            logger.info(f"Sending system alert webhook to N8N: {alert_type}")
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Solanagram/1.0"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ System alert webhook sent successfully to N8N")
                return True
            else:
                logger.warning(f"⚠️ N8N system alert webhook returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending N8N system alert webhook: {e}")
            return False
    
    def send_message_batch(self, messages: list) -> bool:
        """
        Send batch of messages to N8N for processing
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            bool: True if webhook was sent successfully
        """
        
        webhook_url = f"{self.base_url}/webhook/solanagram-message-batch"
        
        payload = {
            "event": "message_batch",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "messages": messages,
                "batch_size": len(messages),
                "metadata": {
                    "system": "solanagram",
                    "version": "1.0"
                }
            }
        }
        
        try:
            logger.info(f"Sending message batch webhook to N8N: {len(messages)} messages")
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.timeout * 2,  # Longer timeout for batch operations
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Solanagram/1.0"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Message batch webhook sent successfully to N8N")
                return True
            else:
                logger.warning(f"⚠️ N8N message batch webhook returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending N8N message batch webhook: {e}")
            return False
    
    def health_check(self) -> bool:
        """
        Check if N8N webhook endpoint is available
        
        Returns:
            bool: True if N8N is reachable
        """
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=5)
            return response.status_code == 200
        except:
            return False

# Global instance
n8n_webhook = N8NWebhookSender()

def notify_crypto_extraction(address: str, 
                           address_type: str,
                           message_text: str,
                           sender_name: str,
                           chat_title: str,
                           extracted_at: datetime,
                           rule_name: str = "crypto_address") -> bool:
    """
    Convenience function to notify N8N of crypto address extraction
    """
    if not n8n_webhook.health_check():
        logger.warning("N8N webhook endpoint not available, skipping notification")
        return False
        
    return n8n_webhook.send_crypto_alert(
        address=address,
        address_type=address_type,
        message_text=message_text,
        sender_name=sender_name,
        chat_title=chat_title,
        extracted_at=extracted_at,
        rule_name=rule_name
    )

def notify_system_event(alert_type: str, message: str, level: str = "info", data: Optional[Dict] = None) -> bool:
    """
    Convenience function to notify N8N of system events
    """
    if not n8n_webhook.health_check():
        logger.warning("N8N webhook endpoint not available, skipping notification")
        return False
        
    return n8n_webhook.send_system_alert(
        alert_type=alert_type,
        message=message,
        level=level,
        data=data
    ) 