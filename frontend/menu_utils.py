#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 Menu Utilities for Solanagram
Unified menu management system
"""

import os
from typing import Optional

def get_unified_menu(current_page: Optional[str] = None) -> str:
    """
    Returns the unified menu HTML for all pages
    
    Args:
        current_page: Current page identifier for active state
        
    Returns:
        HTML string for the unified menu
    """
    
    # Menu items configuration
    menu_items = [
        {"url": "/dashboard", "icon": "🏠", "text": "Dashboard", "id": "dashboard"},
        {"url": "/profile", "icon": "👤", "text": "Profilo", "id": "profile"},
        {"url": "/chats", "icon": "💬", "text": "Le mie Chat", "id": "chats"},
        {"url": "/message-manager", "icon": "📨", "text": "Gestione Messaggi", "id": "message-manager"},
        {"url": "/configured-channels", "icon": "🔄", "text": "Tutti i Reindirizzamenti", "id": "configured-channels"},
        {"url": "/crypto-dashboard", "icon": "🚀", "text": "Crypto", "id": "crypto-dashboard"},
        {"url": "/find", "icon": "🔍", "text": "Trova Chat", "id": "find"},
        {"url": "/security", "icon": "🔐", "text": "Sicurezza", "id": "security"},
        {"url": "#", "icon": "🚪", "text": "Logout", "id": "logout", "onclick": "logout()"}
    ]
    
    # Build menu HTML
    menu_html = '<div class="nav">'
    
    for item in menu_items:
        # Determine if this is the active page
        is_active = current_page == item["id"]
        active_class = ' active' if is_active else ''
        
        # Build onclick attribute if present
        onclick_attr = f' onclick="{item["onclick"]}"' if "onclick" in item else ""
        
        menu_html += f'''
        <a href="{item["url"]}" class="nav-link{active_class}"{onclick_attr}>
            {item["icon"]} {item["text"]}
        </a>'''
    
    menu_html += '</div>'
    
    return menu_html

def get_logout_script() -> str:
    """
    Returns the logout JavaScript function
    
    Returns:
        JavaScript string for logout functionality
    """
    return """
    async function logout() {
        if (confirm('Sei sicuro di voler uscire?')) {
            try {
                const result = await makeRequest('/api/auth/logout', {
                    method: 'POST'
                });
                
                // Reindirizza al login
                if (result && result.redirect) {
                    window.location.href = result.redirect;
                } else {
                    window.location.href = '/login';
                }
            } catch (error) {
                console.error('Errore durante logout:', error);
                // Anche in caso di errore, reindirizza al login
                window.location.href = '/login';
            }
        }
    }
    """ 