# Six-Agent AI Trading Desk — START HERE

The complete, working version is in **`solana-ai-desk`**.
Website: **http://127.0.0.1:8020** (served directly by the backend — no separate frontend server needed).

The six agents: **Nova** (scout), **Axiom** (charts), **Pulse** (social), **Onyx** (on-chain),
**Orion** (strategy), **Veto** (red-team). Paper trading only — never real money.

How they work together: every candidate goes through the full pipeline — Nova finds it, Axiom/Pulse/Onyx
analyze independently, Orion proposes, Veto attacks it, then the desk **argues it out in rounds**
(peers answer Veto, then rebut each other while Veto counters). Right before voting, market data is
**refreshed** so the team always decides on current prices, never data that went stale mid-argument.
When 5/6 vote APPROVE *and* the Risk Gate passes, the trade fills on the **one shared wallet**.

### Light speed: the six brains work AT THE SAME TIME

All independent model calls fire in parallel, so the wall-clock time of a cycle is close to the
critical path instead of the sum of every call:

- **Independent analysis** — Axiom, Pulse and Onyx think simultaneously.
- **Debate rounds** — every responder in a round answers simultaneously.
- **Voting** — all six final votes are cast simultaneously.
- **Market data** — all ~10 enrichment fetches per candidate (DexScreener, Pump.fun, candles,
  Solana RPC, Jupiter price + profile, RugCheck, Fear & Greed, social, web search) and the
  discovery sweeps run concurrently.
- **Model layer** — up to 6 brain calls are in flight at once (tune with the
  `MODEL_MAX_CONCURRENT` env var), with a tiny breather to keep the endpoint happy and automatic
  key rotation + retries on rate limits.

### Where each agent lives (independent folders)

Every agent owns its own folder with its identity, system prompt, and a README improvement
guide (role, brain, data, output schema, verification steps, house rules):

| Agent | Folder |
|---|---|
| Nova (scout) | `solana-ai-desk\backend\app\agents\nova` |
| Axiom (charts) | `solana-ai-desk\backend\app\agents\axiom` |
| Pulse (social) | `solana-ai-desk\backend\app\agents\pulse` |
| Onyx (on-chain) | `solana-ai-desk\backend\app\agents\onyx` |
| Orion (strategy) | `solana-ai-desk\backend\app\agents\orion` |
| Veto (red-team) | `solana-ai-desk\backend\app\agents\veto` |

To improve one agent, work only inside that agent's folder — its README explains exactly how.
The old `app\agents\definitions.py` still works; it just assembles the roster from the folders.

---

## FASTEST WAY — one click

Double-click:

```
C:\Users\Anas\Desktop\ai trader\start-trading-desk.bat
```

It opens a backend window, waits for it, and opens the website at http://127.0.0.1:8020.
Keep the backend window open while using the desk. Close it to stop.

---

## Manual way (PowerShell)

```powershell
cd "C:\Users\Anas\Desktop\ai trader\solana-ai-desk\backend"
py -3.12 run.py --port 8020
```

Then open **http://127.0.0.1:8020** in your browser.

One-time setup (already done on this machine):
- `py -3.12 -m pip install -r requirements.txt` — DONE
- `Copy-Item config.example.json config.json` — DONE (safe defaults, `mode: auto`)
- Frontend is pre-built in `frontend\dist` — the backend serves it

Optional frontend development with hot reload:
```powershell
cd "C:\Users\Anas\Desktop\ai trader\solana-ai-desk\frontend"
npm run dev      # opens on http://localhost:5173, proxies /api and /ws to :8020
```

---

## Models: real, not mock

`config.json` uses `"mode": "openai_compat"` — the six agents call NVIDIA NIM directly
through env vars (`MODEL_BASE_URL`, `MODEL_API_KEY` in the backend's `.env`).

**Every agent has his own brain** (all verified live on 2026-10-23 via `scripts/probe_brains.py --bench`,
real prompt + real schema per seat, 90s timeout):

| Agent | Brain | Bench result |
|---|---|---|
| Nova (scout) | `minimaxai/minimax-m3.1-flash` | 27.8s — correct 1-of-3 triage pick |
| Axiom (charts) | `meta/muse-glimmer-30b` | 25.3s — correct uptrend + sufficient-data call |
| Pulse (social) | `nvidia/ising-calibration-1.5-31b` | 8.5s — honest unavailable reporting |
| Onyx (on-chain) | `nvidia/nemotron-3-ultra-550b-a55b` | 32.7s — 4 real risk flags (flagship seat) |
| Orion (strategy) | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 34.5s — reasoning strategist |
| Veto (red-team) | `nvidia/nemotron-3.5-lightning-30b-a3b` | 36.5s — REJECT + 4 real challenges |

Every seat stayed comfortably under the 90s timeout. Dropped by bench evidence:
`poolside/laguna-xs-2.1` (503/empty on every seat), `z-ai/glm-5.3-flash` (429 rate-limited + ~97s),
`meta/llama-3.2-11b-vision-instruct` (unstable 1.8s-120s), `openai/gpt-oss-20b` (276s),
`stepfun-ai/step-5-preview` (235s), `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` on Nova
(307s — too slow; used by Orion instead), `nvidia/ising-calibration-1.5-31b` on Veto
(0 challenges — too shallow).

The agent `agent_thinking` config is `false` for all seats — thinking mode exhausted token
budgets on Nova's big discovery prompt (all candidates returned "empty completion"). The adapter
now auto-retries with thinking off on the same brain when that happens.

Every brain also keeps a **fallback safety net**: if an agent's primary model fails all retries,
the global fallback (`nvidia/nemotron-3.5-lightning-30b-a3b`) answers and the event feed notes it.
Report rows always record the exact model used.

Re-verify the whole roster any time:
```powershell
cd "C:\Users\Anas\Desktop\ai trader\solana-ai-desk\backend"
py -3.12 scripts/probe_agent_models.py
```

## Web data sources added (no API key needed)

| Source | What it feeds | Cost |
|---|---|---|
| Reddit public search (`reddit_social`) | Real Reddit posts about the token → Pulse's social posts (labeled `source="reddit"`) | Free, key-less |
| Crypto news RSS (`news_feeds`) | CoinDesk / CoinTelegraph / Decrypt headlines → every agent's DATA block | Free, key-less |

Both are on by default, degrade honestly (unavailable, never fabricated), and appear in the
desk's source health feed alongside DexScreener, Jupiter, RugCheck, Fear & Greed, and DuckDuckGo web search.

Change models in the app's **Settings** page or in `config.json` (`agents`, `default_model`).
To list every model this NVIDIA account offers: `py -3.12 scripts/probe_catalog.py`

---

## Market data

Live and working (no API key needed): GeckoTerminal (discovery + candles), DexScreener
(enrichment), Solana JSON-RPC (mint checks), and **internet web search** — every analyzed token
is searched live on the web (DuckDuckGo, keyless) and the results go into each agent's DATA block.
X/Twitter: the desk **tells you when it wants an account** — since no X provider is configured,
the Data Sources page, the health table and Pulse's reports all show **NEEDS ACCOUNT** with the
exact steps (authorized provider + `SOCIAL_X_API_KEY` in the backend's `.env`). Until then Pulse
analyzes web evidence only and never invents posts. Every data point is
labeled LIVE / CACHED / DEMO / UNAVAILABLE in the UI.

---

## Agent Wallets — one shared wallet, attributed per agent

All six agents trade **one shared demo wallet** ($10,000 starting capital). When
consensus + the Risk Gate approve a trade, every agent that voted APPROVE commits its
own **budget slice** of that trade (weighted by its vote confidence). When the position
closes (stop-loss, take-profit, or manual), the gain or loss is attributed back to
those agents' slices.

See it under **Agent Wallets** in the site: a leaderboard of who is winning and losing
(realized, unrealized, win/loss counts, best/worst trade per agent) plus each agent's
budget-slice history. The Live Agent Room also shows each agent's funding P&L on its
card. Weighting mode: `paper.wallet_weighting` in config.json (`confidence` | `equal`).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Browser shows nothing | Backend window must stay open; check it for errors |
| Port 8020 busy | Use another: `py -3.12 run.py --port 8030` |
| DEMO MODE banner shows | MODEL_BASE_URL / MODEL_API_KEY / MODEL_ID env vars missing; check `solana-ai-desk\backend\.env` and `scripts/probe_agent_models.py` |
| Want a fresh start | Stop backend, delete `solana-ai-desk\backend\data\trading_desk.db` |
| Tests | `cd solana-ai-desk\backend; py -3.12 -m pytest tests -q` (58 tests) |

---

## Other folders in this workspace (older copies — not needed to run)

| Folder | What it is |
|---|---|
| `ai-trading-desk` | Earlier version (demo-only models, separate dev server). Contains a broken `backend\index.js` (Node) — ignore it. |
| `solana-ai-trading-desk` | Backend-only copy, no website |
| `backend` (root) | Partial backend copy, no website |
| `pumpfun-ai-trading-bot-main`, `pumpfun-auto-trader-ai-agent-main` | Downloaded reference bots, unrelated to the desk |

Full details: `solana-ai-desk\README.md`
