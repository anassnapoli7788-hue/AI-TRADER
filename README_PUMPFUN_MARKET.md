# PUMPFUN Live Market Data Scanner

## Overview
The AI-Trader system has full capability to provide live market data scanning for the PUMPFUN market on Solana. The system uses **DexScreener** as the data source (free, no API key required).

## How It Works

### 1. Token Discovery
The system queries DexScreener with the term "pump" to find PUMPFUN-related tokens:

```
GET https://api.dexscreener.com/latest/dex/search?q=pump
```

This returns SOLana pairs with baseToken information for newly created PUMPFUN tokens.

### 2. Per-Token Market Stats
For each discovered token, the system fetches detailed market data:

```
GET https://api.dexscreener.com/tokens/v1/solana/{mint}
```

Returns comprehensive market statistics including:
- **priceUsd**: Current price in USD
- **liquidity.usd**: Liquidity in USD
- **volume.h24**: 24-hour trading volume
- **volume.h1**: 1-hour trading volume
- **priceChange.h24**: 24-hour price change percentage
- **priceChange.h1**: 1-hour price change percentage
- **marketCap**: Market capitalization
- **fdv**: Fully diluted valuation
- **txns.buys/sells**: Buy/sell transaction counts
- **pairCreatedAt**: Token creation timestamp

### 3. Discovery Queries
The system uses these predefined queries (from `AI-Trader-main\service\app\marketdata\manager.py`):

```python
DISCOVERY_QUERIES = ["pump", "dog", "cat", "moon", "pepe"]
```

The `"pump"` query specifically targets PUMPFUN ecosystem tokens.

## Integration Points

### pumpfun-auto-trader-ai-agent
The main trading bot (main.py) integrates market data scanning:

```python
# Subscribes to new PUMPFUN tokens via PumpPortal WS
async with websockets.connect(PUMPPORTAL_WS_URL) as ws:
    await ws.send(json.dumps({"method": "subscribeNewToken"}))
    
    # For each new token, fetches DexScreener data:
    pairs = await asyncio.wait_for(
        asyncio.to_thread(fetch_dexscreener_token, mint), 
        timeout=10
    )
    dex_summary = summarize_dex_pairs(pairs)
```

### Market Data Format
The `format_alert()` function displays live market data in Telegram alerts:

```markdown
🪙 **Mint:** <code>{mint}</code>
🔗 **Pump.fun:** {pump_url}
📊 **Market quick data:**
Price: {price_usd} or "н/д"
Liquidity: {liquidity_usd} or "н/д"
FDV: {fdv} or "н/д"
Vol 5m: {volume_5m} or "н/д"
Tx 5m: {total_txns_5m} total | {buys_5m} buys / {sells_5m} sells
```

## Running the Scanner

The system can be invoked via the existing Python backend. Here's the core functionality:

```python
from solana_ai_trading_desk.backend.app.marketdata.dexscreener import DexScreenerAdapter
from solana_ai_trading_desk.backend.app.marketdata.manager import MarketDataManager

# Discover PUMPFUN tokens
pumpfun_tokens = await dex_adapter.discover(["pump"])
# Or get stats for specific mint
stats, cached = await dex_adapter.token_stats("KNOWN_PUMPFUN_MINT")
```

## Output Example

When running the scanner, you'll get output similar to:

```
=== Top 5 PUMPFUN tokens by liquidity ===

1. PUMP [PUMP] 
   💰 Price: $0.5231
   💧 Liquidity: $125,450.00
   📊 24h Volume: $852,300.00
   📈 24h Change: +12.45%
   ⏱ 1h Change: +5.20%
   🏆 Market Cap: $52,310,000.00
   📤 TXNs 24h: 1247 buys / 893 sells
   🔗 Pair: FmJ...
   🌐 URL: https://pump.fun/coin/FmJ...
```

## Requirements
- No API key required (DexScreener is free public API)
- Solana RPC URL optional (for on-chain data)
- System runs in LIVE or DEMO mode configurable via environment