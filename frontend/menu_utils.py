#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Corporate Menu System for Solanagram
Modern unified menu with SVG icons and professional design
Enhanced with advanced animations and hover effects
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
    
    # Menu items configuration with SVG icons - Simplified menu
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
        }
    ]
    
    # Build modern menu HTML with enhanced structure
    menu_html = '''
    <nav class="corporate-nav" role="navigation" aria-label="Main navigation">
        <div class="nav-container">
            <div class="nav-brand">
                <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7v10c0 5.55 3.84 9.74 9 11 5.16-1.26 9-5.45 9-11V7l-10-5z"/>
                </svg>
                <span class="brand-text">Solanagram</span>
            </div>
            
            <div class="nav-menu" id="nav-menu">
                <div class="nav-menu-backdrop"></div>'''
    
    for item in menu_items:
        # Determine if this is the active page
        is_active = current_page == item["id"]
        active_class = ' nav-link--active' if is_active else ''
        
        menu_html += f'''
                <a href="{item["url"]}" class="nav-link{active_class}" data-menu-item="{item["id"]}">
                    <div class="nav-link-content">
                        <span class="nav-icon">{item["icon"]}</span>
                        <span class="nav-text">{item["text"]}</span>
                    </div>
                    <div class="nav-link-hover-effect"></div>
                </a>'''
    
    menu_html += '''
                <div class="nav-link nav-logout" onclick="logout()" role="button" tabindex="0">
                    <div class="nav-link-content">
                        <span class="nav-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                                <polyline points="16,17 21,12 16,7"></polyline>
                                <line x1="21" y1="12" x2="9" y2="12"></line>
                            </svg>
                        </span>
                        <span class="nav-text">Logout</span>
                    </div>
                    <div class="nav-link-hover-effect"></div>
                </div>
            </div>
            
            <button class="nav-toggle" onclick="toggleMobileMenu()" aria-label="Toggle navigation menu" aria-expanded="false">
                <div class="hamburger">
                    <span class="hamburger-line"></span>
                    <span class="hamburger-line"></span>
                    <span class="hamburger-line"></span>
                </div>
            </button>
        </div>
    </nav>'''
    
    return menu_html

def get_menu_styles() -> str:
    """
    Returns the CSS styles for the corporate menu with enhanced animations
    
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
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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
            transition: transform 0.3s ease;
        }
        
        .nav-brand:hover {
            transform: scale(1.05);
        }
        
        .brand-icon {
            width: 32px;
            height: 32px;
            color: rgba(255, 255, 255, 0.9);
            transition: transform 0.3s ease;
        }
        
        .nav-brand:hover .brand-icon {
            transform: rotate(5deg);
        }
        
        .brand-text {
            font-family: 'Segoe UI', system-ui, sans-serif;
            letter-spacing: -0.5px;
        }
        
        .nav-menu {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            position: relative;
        }
        
        .nav-link {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            border-radius: 12px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-weight: 500;
            font-size: 0.95rem;
            position: relative;
            overflow: hidden;
            cursor: pointer;
            background: transparent;
            border: 1px solid transparent;
        }
        
        .nav-link-content {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            position: relative;
            z-index: 2;
        }
        
        .nav-link-hover-effect {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
            border-radius: 12px;
            transform: scale(0.8);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
        }
        
        .nav-link:hover {
            color: white;
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        
        .nav-link:hover .nav-link-hover-effect {
            transform: scale(1);
            opacity: 1;
        }
        
        .nav-link:active {
            transform: translateY(0);
            transition: transform 0.1s ease;
        }
        
        .nav-link--active {
            color: white;
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            border-color: rgba(255, 255, 255, 0.3);
        }
        
        .nav-link--active::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 50%;
            transform: translateX(-50%);
            width: 8px;
            height: 8px;
            background: white;
            border-radius: 50%;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: translateX(-50%) scale(1); opacity: 1; }
            50% { transform: translateX(-50%) scale(1.2); opacity: 0.7; }
        }
        
        .nav-icon {
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .nav-icon svg {
            width: 18px;
            height: 18px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .nav-link:hover .nav-icon {
            transform: scale(1.1) rotate(5deg);
        }
        
        .nav-link:hover .nav-icon svg {
            transform: scale(1.1);
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
        }
        
        .nav-text {
            white-space: nowrap;
            font-family: 'Segoe UI', system-ui, sans-serif;
            transition: transform 0.3s ease;
        }
        
        .nav-link:hover .nav-text {
            transform: translateX(2px);
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
            border-color: rgba(239, 68, 68, 0.3);
        }
        
        .nav-logout:hover .nav-link-hover-effect {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
        }
        
        /* Enhanced Hamburger Menu */
        .nav-toggle {
            display: none;
            background: none;
            border: none;
            cursor: pointer;
            padding: 0.5rem;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .nav-toggle:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .hamburger {
            width: 24px;
            height: 18px;
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .hamburger-line {
            width: 100%;
            height: 2px;
            background: white;
            border-radius: 1px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            transform-origin: center;
        }
        
        .nav-toggle:hover .hamburger-line {
            background: rgba(255, 255, 255, 0.8);
        }
        
        /* Hamburger Animation */
        .nav-toggle[aria-expanded="true"] .hamburger-line:nth-child(1) {
            transform: translateY(8px) rotate(45deg);
        }
        
        .nav-toggle[aria-expanded="true"] .hamburger-line:nth-child(2) {
            opacity: 0;
            transform: scale(0);
        }
        
        .nav-toggle[aria-expanded="true"] .hamburger-line:nth-child(3) {
            transform: translateY(-8px) rotate(-45deg);
        }
        
        /* Adjust main content to account for fixed nav */
        .main-content {
            margin-top: 70px;
        }
        
        /* Mobile responsiveness with enhanced animations */
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
                transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                max-height: calc(100vh - 60px);
                overflow-y: auto;
            }
            
            .nav-menu-backdrop {
                position: fixed;
                top: 60px;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(4px);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: -1;
            }
            
            .nav-menu.nav-menu--open {
                transform: translateY(0);
            }
            
            .nav-menu.nav-menu--open + .nav-menu-backdrop {
                opacity: 1;
                visibility: visible;
            }
            
            .nav-link {
                width: 100%;
                justify-content: flex-start;
                padding: 1rem;
                border-radius: 12px;
                margin-bottom: 0.25rem;
                animation: slideInFromTop 0.3s ease forwards;
                opacity: 0;
                transform: translateY(-20px);
            }
            
            .nav-menu--open .nav-link {
                animation: slideInFromTop 0.3s ease forwards;
            }
            
            .nav-menu--open .nav-link:nth-child(1) { animation-delay: 0.1s; }
            .nav-menu--open .nav-link:nth-child(2) { animation-delay: 0.15s; }
            .nav-menu--open .nav-link:nth-child(3) { animation-delay: 0.2s; }
            .nav-menu--open .nav-link:nth-child(4) { animation-delay: 0.25s; }
            
            @keyframes slideInFromTop {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
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
                max-height: calc(100vh - 55px);
            }
            
            .nav-menu-backdrop {
                top: 55px;
            }
            
            .main-content {
                margin-top: 55px;
            }
            
            .nav-text {
                font-size: 0.9rem;
            }
        }
        
        /* Focus styles for accessibility */
        .nav-link:focus,
        .nav-toggle:focus {
            outline: 2px solid rgba(255, 255, 255, 0.5);
            outline-offset: 2px;
        }
        
        /* Reduced motion support */
        @media (prefers-reduced-motion: reduce) {
            .nav-link,
            .nav-icon,
            .nav-text,
            .hamburger-line,
            .nav-menu {
                transition: none;
            }
            
            .nav-link:hover {
                transform: none;
            }
            
            .nav-link:hover .nav-icon {
                transform: none;
            }
            
            .nav-link:hover .nav-text {
                transform: none;
            }
        }
    </style>
    '''

def get_menu_scripts() -> str:
    """
    Returns the JavaScript for menu functionality with enhanced interactions
    
    Returns:
        JavaScript string for menu interactions
    """
    return '''
    <script>
        let isMenuOpen = false;
        
        function toggleMobileMenu() {
            const menu = document.querySelector('.nav-menu');
            const toggle = document.querySelector('.nav-toggle');
            const backdrop = document.querySelector('.nav-menu-backdrop');
            
            isMenuOpen = !isMenuOpen;
            
            if (isMenuOpen) {
                menu.classList.add('nav-menu--open');
                toggle.setAttribute('aria-expanded', 'true');
                document.body.style.overflow = 'hidden';
                
                // Add backdrop click handler
                backdrop.addEventListener('click', closeMobileMenu);
            } else {
                closeMobileMenu();
            }
        }
        
        function closeMobileMenu() {
            const menu = document.querySelector('.nav-menu');
            const toggle = document.querySelector('.nav-toggle');
            const backdrop = document.querySelector('.nav-menu-backdrop');
            
            menu.classList.remove('nav-menu--open');
            toggle.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = '';
            isMenuOpen = false;
            
            // Remove backdrop click handler
            backdrop.removeEventListener('click', closeMobileMenu);
        }
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(event) {
            const nav = document.querySelector('.corporate-nav');
            const menu = document.querySelector('.nav-menu');
            
            if (!nav.contains(event.target) && menu.classList.contains('nav-menu--open')) {
                closeMobileMenu();
            }
        });
        
        // Close mobile menu on escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && isMenuOpen) {
                closeMobileMenu();
            }
        });
        
        // Enhanced hover effects for desktop
        document.addEventListener('DOMContentLoaded', function() {
            const navLinks = document.querySelectorAll('.nav-link');
            
            navLinks.forEach(link => {
                // Add ripple effect on click
                link.addEventListener('click', function(e) {
                    if (window.innerWidth > 768) {
                        const ripple = document.createElement('div');
                        const rect = this.getBoundingClientRect();
                        const size = Math.max(rect.width, rect.height);
                        const x = e.clientX - rect.left - size / 2;
                        const y = e.clientY - rect.top - size / 2;
                        
                        ripple.style.cssText = `
                            position: absolute;
                            width: ${size}px;
                            height: ${size}px;
                            left: ${x}px;
                            top: ${y}px;
                            background: rgba(255, 255, 255, 0.3);
                            border-radius: 50%;
                            transform: scale(0);
                            animation: ripple-animation 0.6s ease-out;
                            pointer-events: none;
                            z-index: 1;
                        `;
                        
                        this.appendChild(ripple);
                        
                        setTimeout(() => {
                            ripple.remove();
                        }, 600);
                    }
                });
                
                // Add keyboard navigation
                link.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        if (this.classList.contains('nav-logout')) {
                            logout();
                        } else {
                            this.click();
                        }
                    }
                });
            });
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
        
        // Smooth scroll effect for nav with enhanced performance
        let lastScroll = 0;
        let ticking = false;
        
        function updateNavVisibility() {
            const nav = document.querySelector('.corporate-nav');
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > lastScroll && currentScroll > 100) {
                nav.style.transform = 'translateY(-100%)';
            } else {
                nav.style.transform = 'translateY(0)';
            }
            
            lastScroll = currentScroll;
            ticking = false;
        }
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateNavVisibility);
                ticking = true;
            }
        });
        
        // Add ripple animation CSS
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple-animation {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    </script>
    '''

def get_logout_script() -> str:
    """
    Returns the logout JavaScript function for backward compatibility
    
    Returns:
        JavaScript string for logout functionality
    """
    return get_menu_scripts() 