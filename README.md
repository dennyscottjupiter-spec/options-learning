# options-learning 📈

A tool for **learning** US stock options by watching real ones get analyzed.

You give it a ticker and a strategy. It pulls a live option chain, evaluates every
sensible contract, picks the best one — and then explains, in plain English, *why*
that contract won, what could go wrong, and exactly which formula produced every
number on the page.

It never places a trade. It cannot place a trade. See [Safety](#safety-what-this-cannot-do).

> **📄 See a real report first:** [live demo on GitHub Pages](https://dennyscottjupiter-spec.github.io/options-learning/)
> — a frozen AAPL example in English/Portuguese and Learn/Pro modes, no setup required.

---

## Table of contents

- [Options in five minutes](#options-in-five-minutes)
- [The four strategies](#the-four-strategies)
- [What the report tells you](#what-the-report-tells-you)
- [Setup](#setup)
- [Running it](#running-it)
- [How it works inside](#how-it-works-inside)
- [Safety: what this *cannot* do](#safety-what-this-cannot-do)
- [Configuration](#configuration)
- [Testing](#testing)
- [FAQ / troubleshooting](#faq--troubleshooting)

---

## Options in five minutes

An **option** is a contract that gives you the *right*, but not the *obligation*, to
buy or sell 100 shares of a stock at a fixed price, before a fixed date. You pay for
that right. The person on the other side gets paid, and takes on the obligation.

Five words unlock almost everything:

| Word | What it means | Example |
|---|---|---|
| **Call** | The right to **buy** 100 shares at the strike | A call on AAPL lets you buy AAPL at $200 |
| **Put** | The right to **sell** 100 shares at the strike | A put on AAPL lets you sell AAPL at $200 |
| **Strike** | The fixed price the contract locks in | $200 |
| **Expiration** | The date the right disappears | 2027-01-15 |
| **Premium** | What the contract costs (per share — multiply by 100) | $6.40 → **$640** for the contract |

**One contract = 100 shares.** This trips up every beginner. A "$6.40 option" costs
$640. Every dollar figure in this project's reports is already multiplied out to the
real, whole-contract amount — no mental math required.

### The Greeks, in one line each

The Greeks measure how the option's price *reacts* to the world changing:

- **Delta** — how much the option moves when the stock moves $1. A delta of `0.75`
  means the option gains ~$0.75 per $1 of stock. It doubles as a rough gut-check on
  "what are the odds this finishes in the money?" (~75%).
- **Gamma** — how fast delta itself changes. High gamma = the position's character
  shifts quickly.
- **Theta** — how much value bleeds away per calendar day. Options are melting ice
  cubes; theta is the melt rate. Negative when you *own* an option.
- **Vega** — sensitivity to volatility. Options get more expensive when the market
  expects turbulence.
- **Rho** — sensitivity to interest rates. Usually the least important of the five.

### Two ideas this project takes seriously

**1. Breakeven ≠ strike.** A very common beginner error is computing the odds of
finishing past the *strike*. But you paid a premium, so you only actually profit past
**strike + premium** (for a call). Every probability in this project is measured at the
true breakeven. That difference is often several percentage points of "probability" that
beginners quietly gift themselves.

**2. Finishing there ≠ touching there.** *Probability of profit* asks where the price
ends up on expiration day. *Probability of touch* asks whether it ever gets there along
the way — which is roughly **twice** as likely, and is what actually matters if you plan
to close early or if you might get assigned. The report shows both, side by side.

---

## The four strategies

All four are bullish or neutral-bullish — they're the strategies that pair naturally
with "I want to own good companies at good prices."

### 1. Long Call (LEAPS) — *"acquire it cheaper, later"*
**Buy** a call, typically 6–24 months out. You control 100 shares for a fraction of
their price. If the stock rises, your percentage gain dwarfs owning shares outright.
- **Max loss:** the premium — and nothing more. 💸
- **Max profit:** unlimited.
- **You need:** conviction and time.

### 2. Cash-Secured Put — *"get paid to set your buy price"*
**Sell** a put and set aside the cash to buy the shares if assigned. You collect a
premium today. Worst case, you're forced to buy a stock you already wanted, at a price
*you* chose.
- **Max profit:** the premium collected. 💰
- **Max loss:** large — the stock could fall to zero while you're obligated to buy.
- **You need:** the full cash amount (strike × 100) genuinely set aside.

### 3. Covered Call — *"rent out shares you already own"*
**Sell** a call against 100 shares you hold. The premium is income on stock that would
otherwise just sit there. The trade-off: if the stock rockets past the strike, your
shares get called away and you miss the run.
- **Max profit:** premium + gains up to the strike. 🧢 (capped)
- **Max loss:** the stock falling, minus the premium cushion.
- **You need:** 100 shares already owned.

### 4. Protective Put — *"insurance on shares you own"*
**Buy** a put against 100 shares you hold. It guarantees a minimum sale price, no matter
how badly things go. Upside stays fully open.
- **Max loss:** floored at the strike, minus the premium. 🛡️
- **Max profit:** unlimited.
- **You need:** 100 shares, plus willingness to pay for peace of mind.

---

## What the report tells you

Every report has two modes and two languages, toggled at the top of the page:

- **Learn mode** 🎓 — full explanations, analogies, and the reasoning behind each choice.
- **Pro mode** ⚡ — the same numbers, stripped of the teaching text.
- **English / Português (BR)** 🌐 — a full translation, not a machine pass.

What's on the page:

| Section | What you get |
|---|---|
| **The pick** | The chosen contract, its strike, expiration, premium, and full Greeks |
| **Why this one** | An explicit comparison against the runner-up, with the score margin |
| **Payoff diagram** | Profit/loss at expiry, with the **probability distribution drawn behind it** as a ribbon — so you can *see* how much likelihood sits over the profitable region |
| **Probabilities** | POP (closed-form), POP (Monte Carlo), and probability of touch |
| **Risk numbers** | Max profit, max loss, breakeven, capital required, average win/loss |
| **Context** | SMA 20/50/200, RSI(14), historical volatility with its 1-year percentile, 52-week range, directional bias |
| **Warnings** | ⚠️ Earnings before expiration, thin liquidity, unaffordable position, disagreeing probability engines |
| **Methodology** | Every metric, its exact formula, and the file + function that computes it |

That last row is the point of the whole project: **no number is asserted, every number
is checkable.** You can open the named function and read the math yourself.

Reports export to PDF (archived under `archive/`) using the exact same HTML and CSS the
browser renders — so the PDF can never silently drift from the web page.

---

## Setup

**Requirements:** Windows, Python 3.11+, and a free [Alpaca](https://alpaca.markets)
**paper trading** account (the API keys are free; the account trades fake money).

```powershell
# 1. Create and populate a virtual environment
python3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .

# 2. Install the headless browser used for PDF export
.venv\Scripts\python.exe -m playwright install chromium

# 3. Store your Alpaca paper keys (typed hidden, never written to a file)
.venv\Scripts\python.exe scripts\set_credentials.py

# 4. Confirm the keys work — prints your paper balance, never your keys
.venv\Scripts\python.exe scripts\check_account.py
```

Step 3 writes your keys into **Windows Credential Manager**, encrypted by DPAPI against
your Windows login. They never touch a `.env` file, a config file, or the repository.

---

## Running it

```powershell
.venv\Scripts\python.exe scripts\run_web.py
```

Then open **<http://127.0.0.1:8420>**. You get a dashboard with your watchlist and a box
to analyze any ticker. From a report page you can switch strategy, mode, and language, or
export to PDF.

Other entry points:

```powershell
.venv\Scripts\python.exe scripts\export_static_demo.py   # rebuild the docs/ demo site
.venv\Scripts\python.exe scripts\run_mcp.py              # read-only Alpaca MCP server
```

The MCP server lets Claude Code query your paper account and market data conversationally.
Register it once:

```powershell
claude mcp add options-learning-alpaca -- <path-to>\.venv\Scripts\python.exe scripts\run_mcp.py
```

---

## How it works inside

Data flows in exactly one direction — each layer only knows about the ones above it:

```
config.toml + Credential Manager
        │
        ▼
   market.py ──────► cache.py        Alpaca chains, bars, account
   fundamentals.py                   (market cap, sector, earnings — via yfinance)
        │
        ▼
   bs.py + pop.py                    Black-Scholes, Greeks, IV solver,
        │                            two independent probability engines
        ▼
   strategies.py                     the four payoff shapes
        │
        ▼
   select.py                         the decision: which contract wins, and why
        │
        ▼
   report.py + i18n.py + svg.py      words, translation, payoff diagram
        │
        ▼
   web.py  ──►  browser  ──►  PDF
```

A few design choices worth knowing:

- **Two probability engines, deliberately.** A closed-form `N(d2)` calculation and a
  100,000-path Monte Carlo simulation compute the same number independently. When they
  disagree by more than a configured threshold, the report *says so* rather than quietly
  picking one — the disagreement itself is a signal that the lognormal assumption is
  straining.
- **Two-phase evaluation.** Simulating every candidate at full precision is wasteful, so
  the 12 strikes nearest the target delta get a fast, low-path screening run; only the top
  two get the full-precision simulation the report displays.
- **Local Greeks as a labelled fallback.** When Alpaca returns no Greeks or IV (zero
  quotes, same-day expirations), they're solved locally via Black-Scholes — and tagged
  `calculated locally` so the report can tell you which numbers came from the market and
  which came from our model.
- **Liquidity is flagged, never hidden.** A contract nobody is trading still appears in
  your results, marked with a warning. Silently filtering would teach you nothing.
- **Reproducibility.** The Monte Carlo seed is fixed in `config.toml`, so the same inputs
  always produce the same report.

---

## Safety: what this *cannot* do

This is a **learning** tool, and the constraints are structural, not just promises:

| Guarantee | How it's enforced |
|---|---|
| Never places an order | No order-placement code exists anywhere in the repo |
| Never touches a live account | `TradingClient(..., paper=True)` is hardcoded |
| The MCP server can't trade either | `scripts/run_mcp.py` strips the `trading` toolset and forces paper mode |
| Keys never hit the disk | Windows Credential Manager only, read through a single module (`creds.py`) |
| Keys never reach the published site | The static export renders with no credentials and no local paths |

**None of this is financial advice.** The reports explain mechanics and probabilities;
they don't tell you what to buy. Real options trading can lose more than you put in —
that's exactly why this project runs on paper money.

---

## Configuration

Everything tunable lives in [`config.toml`](config.toml) — no code edits needed:

| Setting | What it changes |
|---|---|
| `risk_free_rate` | The interest rate used in Black-Scholes |
| `monte_carlo_paths` / `monte_carlo_seed` | Simulation precision and reproducibility |
| `pop_disagreement_flag_pp` | How far the two probability engines may drift before you're warned |
| `leaps_*_dte` / `premium_*_dte` | Default expiration windows per strategy |
| `min_quote_size` / `max_bid_ask_spread_pct` | The liquidity warning thresholds |
| `data_feed` | `indicative` (free) or `opra` (paid, real-time) |
| `watchlist.tickers` | Seeds your dashboard on first run |

---

## Testing

```powershell
.venv\Scripts\python.exe -m pytest -q                     # everything
.venv\Scripts\python.exe -m pytest tests\test_pop.py -q   # one file
.venv\Scripts\python.exe -m pytest -q -k payoff           # one test by name
```

The suite is fully offline — the math is checked against hand-computed values, and the
selection pipeline runs against a stubbed market layer. No API key needed to run it.

---

## FAQ / troubleshooting

**"Alpaca credentials are not set"** — run `scripts\set_credentials.py`. If you already
did, confirm you're launching with the same Windows user account that stored them; DPAPI
ties the encryption to your login.

**"Alpaca rate limit exceeded"** — the free plan allows 200 requests/minute and this
project stops you *before* you hit it. Responses are cached to `cache/` (15 min for price
bars, 2 min for chains, 24 h for fundamentals); wait a moment and retry.

**"No usable contracts found"** — the ticker may have no options, or none inside that
strategy's default expiration window. Try a large-cap ticker, or pass an explicit
expiration date.

**PDF export fails** — run `.venv\Scripts\python.exe -m playwright install chromium`.

**Prices look stale** — that's the cache. Delete the `cache/` folder to force fresh data.

---

Built for learning. Trade paper until the numbers on these pages feel obvious. 🎯
