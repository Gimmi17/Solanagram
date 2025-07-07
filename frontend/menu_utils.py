#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Corporate Menu System for Solanagram
Modern unified menu with SVG icons and professional design
"""

import os
from typing import Optional

def get_unified_menu(current_page: Optional[str] = None) -> str:
    """
    Returns the unified modern menu HTML for all pages
    
    Args:
        current_page: Current page identifier for active state
        
    Returns:
        HTML string for the unified corporate menu
    """
    
    # Menu items configuration with SVG icons
    menu_items = [
        {
            "url": "/dashboard", 
            "icon": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
            </svg>''', 
            "text": "Dashboard", 
            "id": "dashboard"
        },
        {
            "url": "/profile", 
            "icon": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>''', 
            "text": "Profilo", 
            "id": "profile"
        },
        {
            "url": "/chats", 
            "icon": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>''', 
            "text": "Le mie Chat", 
            "id": "chats"
        },
        {
            "url": "/configured-channels", 
            "icon": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="17,1 21,5 17,9"></polyline>
                <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
                <polyline points="7,23 3,19 7,15"></polyline>
                <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
            </svg>''', 
            "text": "Reindirizzamenti", 
            "id": "configured-channels"
        },
        {
            "url": "/find", 
            "icon": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="M21 21l-4.35-4.35"></path>
            </svg>''', 
            "text": "Trova Chat", 
            "id": "find"
        },
        {
            "url": "/security", 
            "icon": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>''', 
            "text": "Sicurezza", 
            "id": "security"
        }
    ]
    
    # Build modern menu HTML
    menu_html = '''
    <nav class="corporate-nav">
        <div class="nav-container">
            <div class="nav-brand">
                <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7v10c0 5.55 3.84 9.74 9 11 5.16-1.26 9-5.45 9-11V7l-10-5z"/>
                </svg>
                <span class="brand-text">Solanagram</span>
            </div>
            
            <div class="nav-menu">'''
    
    for item in menu_items:
        # Determine if this is the active page
        is_active = current_page == item["id"]
        active_class = ' nav-link--active' if is_active else ''
        
        menu_html += f'''
                <a href="{item["url"]}" class="nav-link{active_class}">
                    <span class="nav-icon">{item["icon"]}</span>
                    <span class="nav-text">{item["text"]}</span>
                </a>'''
    
    menu_html += '''
                <div class="nav-link nav-logout" onclick="logout()">
                    <span class="nav-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                            <polyline points="16,17 21,12 16,7"></polyline>
                            <line x1="21" y1="12" x2="9" y2="12"></line>
                        </svg>
                    </span>
                    <span class="nav-text">Logout</span>
                </div>
            </div>
            
            <button class="nav-toggle" onclick="toggleMobileMenu()">
                <span></span>
                <span></span>
                <span></span>
            </button>
        </div>
    </nav>'''
    
    return menu_html

def get_menu_styles() -> str:
    """
    Returns the CSS styles for the corporate menu
    
    Returns:
        CSS string for the modern menu styling
    """
    return '''
    <style>
        .corporate-nav {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            height: 70px;
        }
        
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            color: white;
            text-decoration: none;
            font-size: 1.5rem;
        }
        
        .brand-icon {
            width: 32px;
            height: 32px;
            color: rgba(255, 255, 255, 0.9);
        }
        
        .brand-text {
            font-family: 'Segoe UI', system-ui, sans-serif;
            letter-spacing: -0.5px;
        }
        
        .nav-menu {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .nav-link {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-weight: 500;
            font-size: 0.95rem;
            position: relative;
            overflow: hidden;
        }
        
        .nav-link::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s ease;
        }
        
        .nav-link:hover::before {
            left: 100%;
        }
        
        .nav-link:hover {
            color: white;
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }
        
        .nav-link--active {
            color: white;
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }
        
        .nav-link--active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 6px;
            height: 6px;
            background: white;
            border-radius: 50%;
        }
        
        .nav-icon {
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .nav-icon svg {
            width: 18px;
            height: 18px;
            transition: transform 0.3s ease;
        }
        
        .nav-link:hover .nav-icon svg {
            transform: scale(1.1);
        }
        
        .nav-text {
            white-space: nowrap;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        
        .nav-logout {
            cursor: pointer;
            margin-left: 1rem;
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            padding-left: 1.5rem;
        }
        
        .nav-logout:hover {
            background: rgba(239, 68, 68, 0.2);
            color: #fecaca;
        }
        
        .nav-toggle {
            display: none;
            flex-direction: column;
            background: none;
            border: none;
            cursor: pointer;
            padding: 0.5rem;
            gap: 4px;
        }
        
        .nav-toggle span {
            width: 25px;
            height: 3px;
            background: white;
            border-radius: 2px;
            transition: all 0.3s ease;
        }
        
        .nav-toggle:hover span {
            background: rgba(255, 255, 255, 0.8);
        }
        
        /* Adjust main content to account for fixed nav */
        .main-content {
            margin-top: 70px;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .nav-container {
                padding: 0 1rem;
                height: 60px;
            }
            
            .nav-brand {
                font-size: 1.25rem;
            }
            
            .brand-icon {
                width: 28px;
                height: 28px;
            }
            
            .nav-menu {
                position: fixed;
                top: 60px;
                left: 0;
                right: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                backdrop-filter: blur(15px);
                flex-direction: column;
                padding: 1rem;
                gap: 0.5rem;
                transform: translateY(-100%);
                transition: transform 0.3s ease;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            }
            
            .nav-menu.nav-menu--open {
                transform: translateY(0);
            }
            
            .nav-link {
                width: 100%;
                justify-content: flex-start;
                padding: 1rem;
                border-radius: 12px;
            }
            
            .nav-logout {
                margin-left: 0;
                border-left: none;
                border-top: 1px solid rgba(255, 255, 255, 0.2);
                padding-left: 1rem;
                margin-top: 0.5rem;
            }
            
            .nav-toggle {
                display: flex;
            }
            
            .main-content {
                margin-top: 60px;
            }
        }
        
        /* Small devices */
        @media (max-width: 480px) {
            .nav-container {
                height: 55px;
            }
            
            .nav-brand {
                font-size: 1.1rem;
            }
            
            .brand-icon {
                width: 24px;
                height: 24px;
            }
            
            .nav-menu {
                top: 55px;
            }
            
            .main-content {
                margin-top: 55px;
            }
            
            .nav-text {
                font-size: 0.9rem;
            }
        }
    </style>
    '''

def get_menu_scripts() -> str:
    """
    Returns the JavaScript for menu functionality
    
    Returns:
        JavaScript string for menu interactions
    """
    return '''
    <script>
        function toggleMobileMenu() {
            const menu = document.querySelector('.nav-menu');
            menu.classList.toggle('nav-menu--open');
        }
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(event) {
            const nav = document.querySelector('.corporate-nav');
            const menu = document.querySelector('.nav-menu');
            const toggle = document.querySelector('.nav-toggle');
            
            if (!nav.contains(event.target) && menu.classList.contains('nav-menu--open')) {
                menu.classList.remove('nav-menu--open');
            }
        });
        
        // Enhanced logout function with confirmation
        async function logout() {
            if (confirm('Sei sicuro di voler uscire?')) {
                try {
                    const result = await makeRequest('/api/auth/logout', {
                        method: 'POST'
                    });
                    
                    // Clear local storage
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('session_token');
                    
                    // Redirect
                    if (result && result.redirect) {
                        window.location.href = result.redirect;
                    } else {
                        window.location.href = '/login';
                    }
                } catch (error) {
                    console.error('Logout error:', error);
                    // Force redirect even on error
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('session_token');
                    window.location.href = '/login';
                }
            }
        }
        
        // Smooth scroll effect for nav
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const nav = document.querySelector('.corporate-nav');
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > lastScroll && currentScroll > 100) {
                nav.style.transform = 'translateY(-100%)';
            } else {
                nav.style.transform = 'translateY(0)';
            }
            
            lastScroll = currentScroll;
        });
    </script>
    '''

def get_logout_script() -> str:
    """
    Returns the logout JavaScript function for backward compatibility
    
    Returns:
        JavaScript string for logout functionality
    """
    return get_menu_scripts() 