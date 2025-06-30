#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Test script for unified menu system
"""

from menu_utils import get_unified_menu, get_logout_script

def test_menu_generation():
    """Test menu generation for different pages"""
    
    print("🧪 Testing Unified Menu System")
    print("=" * 50)
    
    # Test menu for different pages
    pages = ['dashboard', 'profile', 'chats', 'configured-channels', 'find']
    
    for page in pages:
        print(f"\n📄 Menu for {page}:")
        menu_html = get_unified_menu(page)
        print(menu_html)
        print("-" * 30)
    
    # Test logout script
    print("\n🔧 Logout Script:")
    logout_script = get_logout_script()
    print(logout_script[:200] + "..." if len(logout_script) > 200 else logout_script)
    
    print("\n✅ Menu system test completed!")

if __name__ == "__main__":
    test_menu_generation() 