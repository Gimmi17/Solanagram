#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for crypto signal parser
"""

from backend.crypto.parser import CryptoSignalParser

# Test messages
buy_message = """💸 New smart holder entry

🔎 Address: 4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk
💰 Name: BaoBao
📈 MCap: 396.6K

💯 TradeScore: 1

🦚 7 smart holders 
🟢 Cousey  ($936) (06/23/2025, 15:50:00)
🟢 NewTokenSpecialist  ($405) (06/23/2025, 16:38:54)
🟢 OOO  ($675) (06/23/2025, 15:52:29)
🟢 Solkcrow  ($2673) (06/23/2025, 15:52:40)
🟢 Loopierr  ($3341) (06/23/2025, 16:47:50)
🟢 James Corleone  ($4050) (06/23/2025, 16:46:47)
🟢 Casino  ($825) (06/23/2025, 16:01:45)

❗ 0 close

⚡ Jupiter (https://jup.ag/swap/4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk-SOL)
🐸 Gmgn (https://gmgn.ai/sol/token/4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk)
🚀 Photon (https://photon-sol.tinyastro.io/en/lp/4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk)
🐂 Bullx (https://neo.bullx.io/terminal?chainId=1399811149&address=4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk)"""

sell_message = """💸 New smart holder entry

🔎 Address: 4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk
💰 Name: BaoBao
📈 MCap: 3.5M

💯 TradeScore: 2

🦚 5 smart holders 
🟢 Cousey  ($1005) (06/23/2025, 15:50:00)
🟢 Latuche  ($2871) (06/24/2025, 16:29:27)
🟢 Solkcrow  ($2871) (06/23/2025, 15:52:40)
🟢 James Corleone  ($18852) (06/24/2025, 15:46:46)
🟢 Casino  ($886) (06/23/2025, 16:01:45)

❗ 3 close
🔴 NewTokenSpecialist
🔴 OOO
🔴 Loopierr

⚡ Jupiter (https://jup.ag/swap/4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk-SOL)
🐸 Gmgn (https://gmgn.ai/sol/token/4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk)
🚀 Photon (https://photon-sol.tinyastro.io/en/lp/4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk)
🐂 Bullx (https://neo.bullx.io/terminal?chainId=1399811149&address=4bXCaDUciWA5Qj1zmcZ9ryJsoqv4rahKD4r8zYYsbonk)"""

def test_parser():
    parser = CryptoSignalParser()
    
    print("🧪 Testing Crypto Signal Parser\n")
    print("=" * 60)
    
    # Test buy signal
    print("\n📈 Testing BUY Signal:")
    buy_result = parser.parse_signal(buy_message)
    print(parser.format_signal_summary(buy_result))
    print("\nParsed Data:")
    print(f"- Type: {buy_result['type']}")
    print(f"- Token: {buy_result['name']} ({buy_result['address'][:8]}...)")
    print(f"- Market Cap: ${buy_result['mcap']:,.0f}")
    print(f"- Smart Holders: {len(buy_result['smart_holders'])}")
    print(f"- Total Holdings: ${buy_result['total_holdings']:,.0f}")
    
    print("\n" + "=" * 60)
    
    # Test sell signal
    print("\n📉 Testing SELL Signal:")
    sell_result = parser.parse_signal(sell_message)
    print(parser.format_signal_summary(sell_result))
    print("\nParsed Data:")
    print(f"- Type: {sell_result['type']}")
    print(f"- Token: {sell_result['name']} ({sell_result['address'][:8]}...)")
    print(f"- Market Cap: ${sell_result['mcap']:,.0f}")
    print(f"- Smart Holders: {len(sell_result['smart_holders'])}")
    print(f"- Closed Positions: {sell_result['closed_positions']}")
    
    print("\n✅ Parser test completed!")

if __name__ == "__main__":
    test_parser() 