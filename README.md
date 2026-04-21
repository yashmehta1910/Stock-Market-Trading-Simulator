# Apex Markets — Stock Market Trading Simulator

A real-time, browser-based stock market trading simulator built entirely in Python using Dash and Plotly. Simulates live NSE stock prices, buy/sell trading, portfolio tracking, and sector peer discovery using Graph BFS — no JavaScript required.

---

## Features

- Live price updates every 2 seconds for 10 NSE stocks
- Interactive Plotly price chart with tight Y-axis range
- Buy and Sell trading with cash validation and P&L tracking
- Portfolio panel with real-time profit/loss per holding
- Sector peer discovery using Graph + BFS traversal
- Transaction log displayed as a Stack (newest trade first)
- Scrolling ticker tape in the header
- Dark and Light theme toggle
- 100% Python — no HTML, CSS, or JavaScript files

---

## Data Structures Used

| Structure | Implementation | Used For |
|---|---|---|
| Hash Map | `dict` | Stock data lookup O(1) |
| Graph | Adjacency list | Sector relationships |
| BFS | `bfs_peers()` | Peer stock discovery |
| Stack | `list` | Transaction history |
| Circular Buffer | `deque(maxlen=40)` | Price chart history |
| OOP | Classes | MarketEngine, Portfolio |

---

## Installation

**Step 1 — Make sure Python is installed:**
```bash
python --version
# Should show Python 3.10 or higher
```

**Step 2 — Install dependencies:**
```bash
pip install dash plotly
```

Or using the requirements file:
```bash
pip install -r requirements.txt
```

**Step 3 — Run the app:**
```bash
python apex_markets.py
```

**Step 4 — Open in browser:**