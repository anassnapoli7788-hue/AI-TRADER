"""
LIVE PUMP.FUN WHOLE-MARKET SCANNER
==================================
Feeds your system live market data for the WHOLE pump.fun market:

1. PumpPortal WebSocket (wss://pumpportal.fun/api/data)
   - subscribeNewToken  -> EVERY new token created on pump.fun, real time
   - subscribeMigration -> every token graduating to PumpSwap
   - (optional) subscribeTokenTrade -> every trade, whole market (flag: --trades)

2. DexScreener enrichment (free, no key)
   - price, liquidity, volume 5m/1h, buys/sells, market cap

3. Scanner score (0-100): liquidity + momentum + buy pressure

4. Output
   - console live feed
   - pumpfun_live_feed.jsonl  (drop-in data file for the rest of your system)

Usage:
  py pumpfun_live_scanner.py                 # runs forever
  py pumpfun_live_scanner.py --seconds 120   # demo run, stops after 120s
  py pumpfun_live_scanner.py --trades        # also stream every trade (noisy)
"""

import asyncio
import json
import sys
import time
import argparse
from datetime import datetime, timezone

# Live, unbuffered, unicode-safe console output (token names contain emoji)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

import httpx
import websockets

PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"
DEXSCREENER = "https://api.dexscreener.com"
FEED_FILE = "pumpfun_live_feed.jsonl"

ENRICH_INTERVAL = 1.0          # seconds between DexScreener calls (rate-limit safe)
WS_RECONNECT_SECONDS = 10
SUMMARY_EVERY = 20             # seconds between market summaries


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def clock() -> str:
    return now_utc().strftime("%H:%M:%S")


def short(addr: str) -> str:
    return f"{addr[:4]}..{addr[-4:]}" if addr and len(addr) > 12 else str(addr)


def fmt_usd(v) -> str:
    if v is None:
        return "-"
    v = float(v)
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.1f}k"
    return f"${v:.2f}"


def score_token(rec: dict) -> int:
    """Transparent 0-100 scan score: liquidity + momentum + buy pressure."""
    liq = float(rec.get("liquidity_usd") or 0)
    vol5 = float(rec.get("volume_5m_usd") or 0)
    buys = int(rec.get("buys_5m") or 0)
    sells = int(rec.get("sells_5m") or 0)
    total = buys + sells

    liq_pts = 40.0 * min(liq / 10_000, 1.0)          # $10k+ liq = full marks
    vol_pts = 30.0 * min(vol5 / 5_000, 1.0)          # $5k 5m volume = full marks
    buy_ratio = (buys / total) if total else 0.5
    buy_pts = 30.0 * buy_ratio
    return round(liq_pts + vol_pts + buy_pts)


class PumpFunLiveScanner:
    def __init__(self, stream_trades: bool, enrich_all: bool):
        self.tokens: dict[str, dict] = {}
        self.stream_trades = stream_trades
        self.enrich_all = enrich_all
        self.http = httpx.AsyncClient(timeout=15.0)
        self.enrich_queue: asyncio.Queue = asyncio.Queue()
        self.stats = {"new_tokens": 0, "trades": 0, "migrations": 0, "enriched": 0, "ws_errors": 0}
        self.debug_left = 3   # print first raw events to confirm the schema
        self.t0 = time.time()
        self.feed = open(FEED_FILE, "a", encoding="utf-8")

    # ------------------------------------------------------------ dexscreener
    async def enrich(self, mint: str):
        try:
            r = await self.http.get(f"{DEXSCREENER}/tokens/v1/solana/{mint}")
            if r.status_code == 429:
                await asyncio.sleep(3)
                return
            if r.status_code >= 400:
                return
            pairs = r.json()
            if not isinstance(pairs, list) or not pairs:
                return
            best = max(pairs, key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0))
            rec = self.tokens.get(mint)
            if rec is None:
                return
            tx5 = ((best.get("txns") or {}).get("m5") or {})
            rec.update({
                "price_usd": float(best.get("priceUsd") or 0),
                "liquidity_usd": float((best.get("liquidity") or {}).get("usd") or 0),
                "fdv_usd": float(best.get("fdv") or 0),
                "volume_5m_usd": float(((best.get("volume") or {}).get("m5")) or 0),
                "volume_1h_usd": float(((best.get("volume") or {}).get("h1")) or 0),
                "buys_5m": int(tx5.get("buys") or 0),
                "sells_5m": int(tx5.get("sells") or 0),
                "dex": best.get("dexId"),
                "dex_url": best.get("url"),
                "enriched_at": clock(),
            })
            rec["score"] = score_token(rec)
            self.stats["enriched"] += 1
            self.feed.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.feed.flush()
            print(f"[{clock()}] SCAN  ${rec['symbol']:<10} "
                  f"px={rec['price_usd']:.10f}  liq={fmt_usd(rec['liquidity_usd']):>8}  "
                  f"vol5m={fmt_usd(rec['volume_5m_usd']):>8}  "
                  f"tx5m={rec['buys_5m']}b/{rec['sells_5m']}s  "
                  f"mc={fmt_usd(rec['fdv_usd']):>8}  score={rec['score']:>3}")
        except Exception as e:
            print(f"[{clock()}] WARN  enrich failed {short(mint)}: {e}")

    async def enrich_worker(self):
        while True:
            mint = await self.enrich_queue.get()
            await self.enrich(mint)
            await asyncio.sleep(ENRICH_INTERVAL)

    # --------------------------------------------------------- startup board
    async def startup_board(self, queries=("pump", "pumpfun", "pump fun")):
        """Immediate live snapshot of current pump.fun tokens via DexScreener search."""
        print(f"[{clock()}] BOARD pulling current pump.fun market snapshot...")
        seen = set()
        collected = []
        for q in queries:
            try:
                r = await self.http.get(f"{DEXSCREENER}/latest/dex/search", params={"q": q})
                if r.status_code >= 400:
                    continue
                for p in r.json().get("pairs") or []:
                    if p.get("chainId") != "solana":
                        continue
                    base = p.get("baseToken") or {}
                    mint = base.get("address")
                    if not mint or mint in seen:
                        continue
                    seen.add(mint)
                    tx5 = ((p.get("txns") or {}).get("m5") or {})
                    rec = {
                        "mint": mint,
                        "type": "market_board",
                        "seen_at": clock(),
                        "source": "dexscreener_search",
                        "pump_url": f"https://pump.fun/coin/{mint}",
                        "symbol": (base.get("symbol") or "?")[:10],
                        "name": (base.get("name") or "")[:40],
                        "price_usd": float(p.get("priceUsd") or 0),
                        "liquidity_usd": float((p.get("liquidity") or {}).get("usd") or 0),
                        "volume_5m_usd": float(((p.get("volume") or {}).get("m5")) or 0),
                        "volume_1h_usd": float(((p.get("volume") or {}).get("h1")) or 0),
                        "buys_5m": int(tx5.get("buys") or 0),
                        "sells_5m": int(tx5.get("sells") or 0),
                        "fdv_usd": float(p.get("fdv") or 0),
                        "dex": p.get("dexId"),
                        "dex_url": p.get("url"),
                    }
                    rec["score"] = score_token(rec)
                    collected.append(rec)
            except Exception as e:
                print(f"[{clock()}] WARN  search '{q}' failed: {e}")
        collected.sort(key=lambda t: t["liquidity_usd"], reverse=True)
        print(f"[{clock()}] BOARD {len(collected)} current pump.fun tokens — top by liquidity:")
        for rec in collected[:20]:
            self.tokens[rec["mint"]] = rec
            self.feed.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[{clock()}] BOARD  ${rec['symbol']:<10} px={rec['price_usd']:.10f}  "
                  f"liq={fmt_usd(rec['liquidity_usd']):>8}  "
                  f"vol5m={fmt_usd(rec['volume_5m_usd']):>8}  "
                  f"tx5m={rec['buys_5m']}b/{rec['sells_5m']}s  "
                  f"mc={fmt_usd(rec['fdv_usd']):>8}  score={rec['score']:>3}")
        self.feed.flush()
        for rec in collected[:15]:
            self.enrich_queue.put_nowait(rec["mint"])

    # ------------------------------------------------------------- pumpportal
    def handle_event(self, evt: dict):
        if self.debug_left > 0:
            self.debug_left -= 1
            print(f"[{clock()}] DEBUG raw event sample: {json.dumps(evt)[:400]}")

        mint = evt.get("mint") or evt.get("token") or evt.get("ca")
        tx_type = str(evt.get("txType") or "").lower()
        msg_type = str(evt.get("messageType") or "").lower()

        # --- new token creation (whole pump.fun market) ---
        if tx_type == "create" or ("new" in msg_type and "token" in msg_type and mint):
            if not mint or mint in self.tokens:
                return
            rec = {
                "type": "new_token",
                "seen_at": clock(),
                "mint": mint,
                "symbol": (evt.get("symbol") or "?")[:10],
                "name": (evt.get("name") or "")[:40],
                "creator": evt.get("traderPublicKey"),
                "sol_initial": evt.get("solAmount"),
                "initial_mc": evt.get("marketCap"),
                "pump_url": f"https://pump.fun/coin/{mint}",
                "source": "pumpportal_ws",
            }
            self.tokens[mint] = rec
            self.stats["new_tokens"] += 1
            self.feed.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.feed.flush()
            print(f"[{clock()}] NEW   ${rec['symbol']:<10} {rec['name']:<40} mint={short(mint)}")
            if self.enrich_all or len(self.tokens) <= 80:
                self.enrich_queue.put_nowait(mint)
            return

        # --- migration to PumpSwap ---
        if "migration" in tx_type or "migration" in msg_type:
            self.stats["migrations"] += 1
            if not mint:
                return
            if mint not in self.tokens:
                self.tokens[mint] = {
                    "mint": mint,
                    "type": "migration",
                    "seen_at": clock(),
                    "symbol": (evt.get("symbol") or "?")[:10],
                    "name": (evt.get("name") or "")[:40],
                    "pump_url": f"https://pump.fun/coin/{mint}",
                    "source": "pumpportal_ws",
                }
            rec = self.tokens[mint]
            rec["migrated_at"] = clock()
            print(f"[{clock()}] MIGR  ${rec['symbol']:<10} mint={short(mint)} graduated to PumpSwap")
            self.enrich_queue.put_nowait(mint)
            return

        # --- trades ---
        if tx_type in ("buy", "sell") or "trade" in msg_type:
            self.stats["trades"] += 1
            if self.stream_trades and mint:
                rec = self.tokens.get(mint) or {}
                print(f"[{clock()}] TRADE {tx_type or '?':<4} ${rec.get('symbol', '?'):<10} "
                      f"sol={evt.get('solAmount')} mc={evt.get('marketCap')} mint={short(mint)}")
            rec = self.tokens.get(mint)
            if rec is not None:
                rec["last_trade"] = {"side": tx_type or "?", "sol": evt.get("solAmount"), "at": clock()}

    async def ws_loop(self):
        backoff = WS_RECONNECT_SECONDS
        while True:
            try:
                async with websockets.connect(PUMPPORTAL_WS, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(json.dumps({"method": "subscribeNewToken"}))
                    await ws.send(json.dumps({"method": "subscribeMigration"}))
                    print(f"[{clock()}] OK    PumpPortal connected — WHOLE pump.fun market live "
                          f"(new tokens + migrations)")
                    if self.stream_trades:
                        await ws.send(json.dumps({"method": "subscribeTokenTrade"}))
                        print(f"[{clock()}] OK    also streaming every trade (whole market)")
                    backoff = WS_RECONNECT_SECONDS
                    async for raw in ws:
                        try:
                            evt = json.loads(raw)
                        except Exception:
                            continue
                        self.handle_event(evt)
            except Exception as e:
                self.stats["ws_errors"] += 1
                print(f"[{clock()}] ERR   PumpPortal WS: {e} — retry in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    # ---------------------------------------------------------------- rest fallback
    async def rest_fallback(self, queries=("pump", "pumpfun")):
        """Used only if the WebSocket is unreachable."""
        print(f"[{clock()}] FALLBACK  DexScreener REST polling mode")
        seen: set[str] = set()
        while True:
            for q in queries:
                try:
                    r = await self.http.get(f"{DEXSCREENER}/latest/dex/search", params={"q": q})
                    if r.status_code >= 400:
                        continue
                    for p in r.json().get("pairs") or []:
                        if p.get("chainId") != "solana":
                            continue
                        mint = (p.get("baseToken") or {}).get("address")
                        if not mint or mint in seen:
                            continue
                        seen.add(mint)
                        self.handle_event({"txType": "create", "mint": mint,
                                           "symbol": (p.get("baseToken") or {}).get("symbol"),
                                           "name": (p.get("baseToken") or {}).get("name")})
                except Exception as e:
                    print(f"[{clock()}] ERR   REST search '{q}': {e}")
            await asyncio.sleep(20)

    # ---------------------------------------------------------------- summary
    async def summary_loop(self):
        while True:
            await asyncio.sleep(SUMMARY_EVERY)
            live = [t for t in self.tokens.values() if t.get("score") is not None]
            live.sort(key=lambda t: t.get("score") or 0, reverse=True)
            mins = (time.time() - self.t0) / 60
            print("-" * 100)
            print(f"[{clock()}] SUMMARY  up {mins:.1f}m | new: {self.stats['new_tokens']} | "
                  f"migrations: {self.stats['migrations']} | trades: {self.stats['trades']} | "
                  f"enriched: {self.stats['enriched']} | feed: {FEED_FILE}")
            for t in live[:5]:
                print(f"   TOP  ${t['symbol']:<10} score={t['score']:>3}  "
                      f"px={t.get('price_usd', 0):.10f}  liq={fmt_usd(t.get('liquidity_usd'))}  "
                      f"vol5m={fmt_usd(t.get('volume_5m_usd'))}")
            print("-" * 100)

    # ---------------------------------------------------------------- run
    async def run(self, max_seconds: float):
        await self.startup_board()
        probe_ok = await self._probe_ws()
        tasks = [
            asyncio.create_task(self.enrich_worker()),
            asyncio.create_task(self.summary_loop()),
            asyncio.create_task(self.ws_loop() if probe_ok else self.rest_fallback()),
        ]
        try:
            if max_seconds > 0:
                await asyncio.sleep(max_seconds)
            else:
                await asyncio.Event().wait()
        finally:
            for t in tasks:
                t.cancel()
            mins = (time.time() - self.t0) / 60
            print("\n" + "=" * 100)
            print(f"SCANNER STOPPED after {mins:.1f}m")
            print(f"  new pump.fun tokens seen : {self.stats['new_tokens']}")
            print(f"  migrations seen          : {self.stats['migrations']}")
            print(f"  trades seen              : {self.stats['trades']}")
            print(f"  enriched w/ market data   : {self.stats['enriched']}")
            print(f"  live feed saved to        : {FEED_FILE}")
            print("=" * 100)
            await self.http.aclose()

    async def _probe_ws(self) -> bool:
        try:
            async with websockets.connect(PUMPPORTAL_WS, ping_interval=20, ping_timeout=20,
                                           open_timeout=12) as ws:
                await ws.send(json.dumps({"method": "subscribeNewToken"}))
            return True
        except Exception as e:
            print(f"[{clock()}] WARN  WebSocket unreachable ({e}) — using REST fallback")
            return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0, help="stop after N seconds (0 = run forever)")
    ap.add_argument("--trades", action="store_true", help="also stream every trade (very noisy)")
    ap.add_argument("--enrich-all", action="store_true", help="enrich every token, not just first 80")
    args = ap.parse_args()

    scanner = PumpFunLiveScanner(stream_trades=args.trades, enrich_all=args.enrich_all)
    try:
        asyncio.run(scanner.run(max_seconds=args.seconds))
    except KeyboardInterrupt:
        print("\nStopped by user.")
