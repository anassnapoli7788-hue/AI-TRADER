# Solana AI Trading Desk 🛰️

A local-first web application where **six specialized AI agents** scout Solana meme coins, analyze them independently, debate each other, red-team the trade, vote, and — only when consensus AND a deterministic risk gate agree — execute **paper** trades. Everything streams live into a premium dark dashboard over WebSocket.

**This app never signs, sends, or even constructs real blockchain transactions. Real trading is disabled at the schema level and is out of scope.**

---

## The six agents

| Agent | Specialty | Personality |
|---|---|---|
| 🟣 **Nova — The Scout** | Discovery: candidates, age/liquidity/volume, wash-trade detection | Curious, fast, opportunistic, hype-skeptical |
| 🔵 **Axiom — The Chart Analyst** | Technicals from supplied candles only; never invents data | Disciplined, evidence-focused; observations vs hypotheses |
| 🩷 **Pulse — X & Social Intelligence** | Narratives, engagement quality, coordinated-shill detection | Socially perceptive, influencer-skeptical |
| 🟢 **Onyx — The On-Chain Detective** | Mint identity, mint/freeze authority, holders, liquidity forensics | Suspicious by default; verified facts vs heuristics |
| 🟡 **Orion — The Strategist** | Scenarios, entries, stops, targets, R:R | Patient, decisive only when evidence earns it |
| 🔴 **Veto — The Red-Team Auditor** | Challenges every assumption; independent APPROVE/REJECT verdict | Adversarial, rigorous, never a rubber stamp |

Each agent is a **separate orchestrated model call** with its own system prompt, its own dataset, and a strict JSON output contract validated by Pydantic. Phase B analysts never see each other's conclusions before their independent reports are recorded.

## The workflow (every cycle)

1. **Discovery** — Nova ranks real candidates from the discovery feed (DexScreener live search, or labeled demo tokens).
2. **Independent analysis** — Axiom, Pulse and Onyx each get only their own dataset.
3. **Strategy** — Orion reads all reports → TRADE or NO_TRADE with entry/invalidation/stop/targets/sizing.
4. **Red-team** — Veto challenges claims by name and returns a verdict.
5. **Debate** — targeted responses/objections/revisions (max 2 rounds, hard-capped).
6. **Voting** — exactly one final vote per agent: APPROVE / REJECT / INSUFFICIENT_DATA (revisions preserved in an append-only audit log).
7. **Decision** — consensus requires **≥5 of 6 APPROVE**. Then the **deterministic Python Risk Gate** re-validates 16 mandatory conditions (freshness, integrity, liquidity, slippage, size, capital, positions, daily loss, stop validity, duplicates, kill switch…). Only then does the paper broker fill a simulated order with fees and slippage.

No AI component can bypass the risk gate. Failed agent calls become `INSUFFICIENT_DATA` — never approvals.

## Quick start (Windows PowerShell)

```powershell
cd "C:\Users\Anas\Desktop\ai trader"
.\start-desk.ps1
```

Then open **http://127.0.0.1:8765** (the script opens it for you).

### Manual commands (equivalent)

```powershell
# One-time setup
py -3.14 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend; npm install; npm run build; cd ..

# Run the backend (serves the built dashboard)
backend\.venv\Scripts\python.exe backend\run.py --port 8765

# Run the test suite
cd backend
.venv\Scripts\python.exe -m pytest tests -q

# Frontend dev mode (optional, hot reload) — in a second terminal
cd frontend
npm run dev     # http://localhost:5173 (proxies /api and /ws to :8765)

# Stop the backend
.\stop-desk.ps1
```

## Model providers (Settings page, hot-swappable)

| Provider | How it works | Secrets needed? |
|---|---|---|
| **`opencode_cli`** (default) | Spawns `opencode run --format json -m <provider/model>` via the **OpenCode Desktop bundled CLI (v2.1.1)** — the official programmatic interface that reuses the providers already configured in OpenCode (your NVIDIA NIM models, etc.). Verified working on this machine with `nvidia/z-ai/glm-5.3-flash`. | **None** — auth is handled by OpenCode |
| `openai_compatible` | Direct HTTP to any OpenAI-compatible endpoint (NVIDIA NIM, DeepSeek, GLM, Ollama…). You set the **name** of an environment variable that holds the key (e.g. `TRADING_DESK_API_KEY` in `.env`); the app reads it at runtime. Keys are never stored or displayed. | API key in env var only |
| `mock` | Deterministic rule-based outputs computed from the actual data, **explicitly labeled** on every message, with a persistent DEMO MODE banner. For pipeline testing with zero dependencies. | None |

Notes:
- OpenCode Desktop must be **running** for `opencode_cli` calls (its background service owns the sessions/auth). Use *Settings → Test model connection* to preflight.
- Your available models are exactly the ones OpenCode shows you, in `provider/model` form (e.g. `nvidia/z-ai/glm-5.3-flash`, `nvidia/deepseek-ai/deepseek-v4.1-flash`, `nvidia/moonshotai/kimi-k2.6`).
- The npm-installed `opencode` CLI (1.19.4) on this machine is older than the desktop's 2.x database and errors with *"Database is not empty and has no session table"* — the app deliberately uses the **desktop-bundled CLI** instead, which works.

## Market & social data sources

| Source | Used for | Key needed | Status |
|---|---|---|---|
| **DexScreener public API** | Candidate discovery + live quotes (price, liquidity, volume, txns, price-change buckets) | No | ✅ verified working |
| **Solana public RPC** | On-chain forensics: mint account existence, mint/freeze authority decoded from raw account data, top holders (best-effort) | No | ✅ verified (rate-limited → degrades honestly) |
| OHLCV candles | Technical history | — | ⚠️ **UNAVAILABLE in live mode** (GeckoTerminal OHLCV failed from this machine; Birdeye needs a key). Axiom marks data insufficient instead of inventing candles. Configure a provider to enable. |
| X / social | Pulse's dataset | — | ❌ **No free authorized X API exists** → honestly reported UNAVAILABLE; Pulse abstains with INSUFFICIENT_DATA. Demo mode ships labeled synthetic posts. |

Every dataset carries a mode badge: **LIVE / CACHED / DEMO / UNAVAILABLE**. Demo data never mixes with live data silently.

## Paper trading engine

- Simulated buys/sells with **0.85% fee per side** and **impact-based slippage** (`0.25% + order/pool-depth`), all configurable.
- Orders >40% of pool liquidity are **refused**; orders >15% are **partially filled** — exactly like reality would punish you.
- Stop-loss monitoring, TP1/TP2 ladders, breakeven stop after TP1, realized/unrealized P&L, equity curve, daily-loss circuit breaker.
- Win rate is hidden until ≥5 closed trades exist (no fabricated stats).
- Global **kill switch** (halts analysis + monitoring) and **pause** controls, both enforced server-side.

## Safety & honesty guarantees

- `real_trading_enabled` is `Literal[False]` — the config schema **cannot** represent real trading.
- The broker has no signing/sending/wallet APIs at all (asserted by tests).
- Mock outputs are labeled on every message and report; a persistent DEMO MODE banner appears whenever the mock provider or demo market data is active.
- All external data is wrapped in UNTRUSTED markers and the agents are instructed to treat it as data, never instructions.
- No secrets in source control: `.env` is git-ignored; only the **name** of the key env var is configurable.

## Project layout

```
backend/
  app/
    config.py            # pydantic config (backend/data/config.json), hot-reloaded
    db.py                # SQLite (WAL) + migrations + audit-log queries
    schemas.py           # strict pydantic schemas for everything
    events.py            # event bus -> WebSocket fan-out
    state.py             # runtime state (statuses, kill switch)
    providers/           # opencode_cli, openai_compatible, mock (labeled)
    marketdata/          # dexscreener, solana_rpc, demo, social adapters + manager
    agents/              # six agents: prompts, schemas, task builders
    orchestrator.py      # the debate engine (phases A-E, voting, gate, execution)
    voting.py            # 5-of-6 protocol, audit-log revisions
    riskgate.py          # deterministic gate (16 checks)
    paperbroker.py       # paper fills, fees, slippage, SL/TP, equity
    api/routes.py        # REST; main.py adds /ws
  tests/                 # 41 tests covering the acceptance criteria
frontend/                # React + TypeScript + Vite (hand-rolled dark UI)
.opencode/agents/tradingdesk.md   # tool-less programmatic agent for opencode run
```

## REST/WS API (see /docs for the full schema)

- `GET /api/state` — full snapshot (agents, messages, votes, decisions, portfolio, health)
- `POST /api/analysis/start|stop|pause|resume|run-once` · `POST /api/kill-switch[/release]`
- `GET /api/agents`, `GET /api/agents/{id}/reports`, `GET /api/runs`, `GET /api/runs/{id}`
- `GET /api/portfolio`, `GET /api/trades`, `POST /api/positions/{id}/close`, `POST /api/positions/close-all`
- `GET /api/risk`, `GET /api/sources`, `GET /api/scanner`
- `GET/PUT /api/settings`, `POST /api/provider/test`
- `WS /ws` — live event stream (`agent_status`, `message`, `vote`, `phase`, `decision`, `portfolio`, `system`, …)
