"""Live PUMPFUN Market Data Scanner using DexScreener"""
import httpx
import asyncio
from datetime import datetime, timezone


BASE = "https://api.dexscreener.com"


async def get_json(client, url, **params):
    """Fetch JSON from DexScreener API"""
    r = await client.get(url, params=params, timeout=15.0)
    if r.status_code >= 400:
        return None
    return r.json()


async def scan_pumpfun_market():
    """Scan and display live PUMPFUN market data"""
    async with httpx.AsyncClient(base_url=BASE, timeout=15.0) as client:
        # Step 1: Discover PUMPFUN tokens using "pump" query
        print("=" * 60)
        print("Step 1: Discovering PUMPFUN tokens via DexScreener")
        print("=" * 60)
        data = await get_json(client, "/latest/dex/search", q="pump")
        
        if data and "pairs" in data:
            pumpfun_pairs = [p for p in data["pairs"] if p.get("chainId") == "solana"]
            print(f"Found {len(pumpfun_pairs)} SOLana PUMPFUN pairs\n")
            
            # Step 2: Fetch market stats for each token
            print("=" * 60)
            print("Step 2: Fetching live market data (Top 20 by liquidity)")
            print("=" * 60)
            
            results = []
            seen = set()
            for pair in pumpfun_pairs[:30]:  # Limit to first 30
                base = pair.get("baseToken") or {}
                mint = base.get("address")
                if not mint or mint in seen:
                    continue
                seen.add(mint)
                
                # Extract market data
                txns = pair.get("txns") or {}
                vol = pair.get("volume") or {}
                chg = pair.get("priceChange") or {}
                
                price_usd = float(pair.get("priceUsd", 0) or 0)
                liquidity_usd = float((pair.get("liquidity") or {}).get("usd") or 0)
                volume_24h = float(vol.get("h24", 0) or 0)
                volume_1h = float(vol.get("h1", 0) or 0)
                price_change_24h = float(chg.get("h24", 0) or 0)
                price_change_1h = float(chg.get("h1", 0) or 0)
                market_cap = float(pair.get("marketCap") or pair.get("fdv") or 0)
                
                results.append({
                    "mint": mint,
                    "symbol": base.get("symbol", ""),
                    "name": base.get("name", ""),
                    "price_usd": price_usd,
                    "liquidity_usd": liquidity_usd,
                    "volume_24h_usd": volume_24h,
                    "volume_1h_usd": volume_1h,
                    "price_change_24h_pct": price_change_24h,
                    "price_change_1h_pct": price_change_1h,
                    "market_cap": market_cap,
                    "txns_24h_buys": txns.get("buys", 0),
                    "txns_24h_sells": txns.get("sells", 0),
                    "pair_address": pair.get("pairAddress", ""),
                    "url": pair.get("url", ""),
                    "dexId": pair.get("dexId", ""),
                })
            
            # Sort by liquidity (highest first)
            results.sort(key=lambda x: x["liquidity_usd"], reverse=True)
            
            # Display results
            print(f"\nTop {len(results)} PUMPFUN tokens by liquidity:\n")
            for i, token in enumerate(results, 1):
                print(f"{i}. {token['symbol']} ({token['name']})")
                print(f"   📦 Mint: {token['mint'][:8]}...")
                print(f"   💰 Price: ${token['price_usd']:.6f}")
                print(f"   💧 Liquidity: ${token['liquidity_usd']:,.2f}")
                print(f"   📊 24h Volume: ${token['volume_24h_usd']:,.2f}")
                print(f"   📈 24h Change: {token['price_change_24h_pct']:.2f}%")
                print(f"   ⏱ 1h Change: {token['price_change_1h_pct']:.2f}%")
                print(f"   🏆 Market Cap: ${token['market_cap']:,.2f}")
                print(f"   📤 TXNs 24h: {token['txns_24h_buys']} buys / {token['txns_24h_sells']} sells")
                print(f"   🔗 Pair: {token['pair_address'][:8]}...")
                print(f"   🌐 URL: {token['url']}")
                print()
        else:
            print("No PUMPFUN data found from DexScreener search")
            print("Trying direct token lookup...")
            
            # Step 3: Try direct token lookup
            print("\nStep 3: Direct token lookup")
            test_mints = [
                "FsQp8CjqrqRDLQJMusingzN6k3Q9jGcdau8a671NPUzQG",  # Example PUMPFUN mint
            ]
            for mint in test_mints:
                print(f"\nLooking up mint: {mint[:8]}...")
                try:
                    data = await get_json(client, f"/tokens/v1/solana/{mint}")
                    if data and isinstance(data, list) and data:
                        token = data[0]
                        print(f"  Symbol: {token.get('baseToken', {}).get('symbol', 'N/A')}")
                        print(f"  Price: {token.get('priceUsd', 'N/A')}")
                        print(f"  Liquidity: {token.get('liquidity', {}).get('usd', 'N/A')}")
                    else:
                        print("  No data returned (mint may be inactive or private)")
                except Exception as e:
                    print(f"  Error: {e}")


if __name__ == "__main__":
    asyncio.run(scan_pumpfun_market())