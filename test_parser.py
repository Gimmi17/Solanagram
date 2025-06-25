#!/usr/bin/env python3
"""
Test script for the Telegram message parser.
Use this to test and debug the parser with example messages.
"""

from parser import parser, TradingSignal
from datetime import datetime

# Example BUY message
buy_message = """
BONK
❗ 0 close

Market Cap: $2.1M
TradeScore: 88

🟢 Assassin.eth ($45K)
🟢 SmartTrader.sol ($32K)
🟢 WhaleAlert ($78K)
🟢 CryptoGuru ($15K)

https://jup.ag/swap/SOL-DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
"""

# Example SELL message
sell_message = """
PEPE
❗ 1 close

🔴 Assassin.eth
🔴 SmartTrader.sol
🔴 WhaleAlert
"""

# Another BUY example with different format
buy_message_2 = """
SAMO
❗ 0 close
Market Cap: $850K
TradeScore: 72
🟢 DegenKing ($25K)
🟢 SolanaMax ($40K)
🟢 TokenHunter ($18K)
Jupiter: https://jup.ag/swap/SOL-7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
"""

def test_parser():
    """Test the parser with example messages"""
    
    print("🧪 Testing Solanagram Parser")
    print("=" * 50)
    
    test_cases = [
        ("BUY Signal #1", buy_message),
        ("SELL Signal", sell_message),
        ("BUY Signal #2", buy_message_2),
    ]
    
    for name, message in test_cases:
        print(f"\n📝 Testing: {name}")
        print("-" * 30)
        
        # Parse the message
        signal = parser.parse_message(message)
        
        if signal:
            print(f"✅ Signal parsed successfully!")
            print(f"   Type: {signal.signal_type}")
            print(f"   Token: {signal.token_name}")
            print(f"   Address: {signal.token_address}")
            print(f"   Market Cap: ${signal.market_cap:,.0f}" if signal.market_cap else "   Market Cap: N/A")
            print(f"   Trade Score: {signal.trade_score}" if signal.trade_score else "   Trade Score: N/A")
            print(f"   Smart Holders: {len(signal.smart_holders)}")
            
            for i, holder in enumerate(signal.smart_holders):
                holder_info = f"{holder['name']}"
                if holder.get('amount'):
                    holder_info += f" ({holder['amount']})"
                print(f"     {i+1}. {holder_info}")
            
            print(f"   Jupiter Link: {signal.jupiter_link or 'N/A'}")
            
            # Validate the signal
            is_valid = parser.validate_signal(signal)
            print(f"   Valid: {'✅ Yes' if is_valid else '❌ No'}")
            
        else:
            print("❌ No signal detected")
    
    print("\n" + "=" * 50)
    print("🎯 Parser Test Complete")

def test_edge_cases():
    """Test edge cases and malformed messages"""
    
    print("\n🔍 Testing Edge Cases")
    print("=" * 50)
    
    edge_cases = [
        ("Empty message", ""),
        ("No signal markers", "Just a regular message about crypto"),
        ("BUY without holders", "DOGE\n❗ 0 close\nMarket Cap: $1M"),
        ("Invalid format", "Random text with ❗ somewhere"),
        ("SELL without red holders", "TOKEN\n❗ 1 close\nSome other text"),
    ]
    
    for name, message in edge_cases:
        print(f"\n📝 Testing: {name}")
        print("-" * 30)
        
        signal = parser.parse_message(message)
        
        if signal:
            print(f"⚠️  Signal detected (unexpected): {signal.signal_type} - {signal.token_name}")
            is_valid = parser.validate_signal(signal)
            print(f"   Valid: {'✅ Yes' if is_valid else '❌ No'}")
        else:
            print("✅ No signal detected (expected)")

def test_regex_patterns():
    """Test individual regex patterns"""
    
    print("\n🔧 Testing Regex Patterns")
    print("=" * 50)
    
    # Test address pattern
    test_addresses = [
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Valid
        "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",   # Valid
        "So11111111111111111111111111111111111111112",    # SOL address
        "invalid_address",                                  # Invalid
        "123",                                             # Too short
    ]
    
    print("\n🔗 Address Pattern:")
    for addr in test_addresses:
        matches = parser.address_pattern.findall(addr)
        print(f"   {addr}: {'✅' if matches else '❌'} {matches}")
    
    # Test market cap pattern
    test_mcaps = [
        "$1.2M", "$500K", "$2.5B", "$100", "$1,234K", "$0.5M"
    ]
    
    print("\n💰 Market Cap Pattern:")
    for mcap in test_mcaps:
        matches = parser.mcap_pattern.findall(mcap)
        if matches:
            value, unit = matches[0]
            multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
            actual_value = float(value) * multipliers.get(unit.upper(), 1)
            print(f"   {mcap}: ✅ ${actual_value:,.0f}")
        else:
            print(f"   {mcap}: ❌")
    
    # Test holder pattern
    test_holders = [
        "🟢 Assassin.eth ($45K)",
        "🟢 SmartTrader.sol ($32K)",
        "🔴 WhaleAlert",
        "🟢 User123 ($100)",
    ]
    
    print("\n👥 Holder Patterns:")
    for holder in test_holders:
        green_matches = parser.holder_pattern.findall(holder)
        red_matches = parser.red_holder_pattern.findall(holder)
        
        if green_matches:
            name, amount = green_matches[0]
            print(f"   {holder}: ✅ Green - {name} ({amount})")
        elif red_matches:
            name = red_matches[0]
            print(f"   {holder}: ✅ Red - {name}")
        else:
            print(f"   {holder}: ❌")

if __name__ == "__main__":
    test_parser()
    test_edge_cases()
    test_regex_patterns()
    
    print("\n🎉 All tests completed!")
    print("\nTo test your own messages, modify the test cases in this file.") 