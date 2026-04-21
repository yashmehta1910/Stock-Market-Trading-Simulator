import random
import json
from collections import deque
from datetime import datetime

from dash import Dash, html, dcc, Input, Output, State, ctx, no_update
import plotly.graph_objects as go

# ═══════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════

MAX_HIST = 40

STOCKS_META = [
    ("RELIANCE",   "Reliance Industries", 2847.50, "Energy"),
    ("TCS",        "Tata Consultancy",    3912.00, "Tech"),
    ("INFY",       "Infosys Ltd",         1423.80, "Tech"),
    ("HDFCBANK",   "HDFC Bank",           1678.40, "Finance"),
    ("WIPRO",      "Wipro Ltd",            521.30, "Tech"),
    ("TATAMOTORS", "Tata Motors",          924.60, "Auto"),
    ("SUNPHARMA",  "Sun Pharma",          1285.90, "Health"),
    ("ONGC",       "ONGC Ltd",             278.40, "Energy"),
    ("ICICIBANK",  "ICICI Bank",          1134.20, "Finance"),
    ("BAJFINANCE", "Bajaj Finance",       7234.10, "Finance"),
]

SECTOR_DRIFT = {"Tech": 0.0015, "Energy": -0.001, "Finance": 0.001, "Health": 0.002, "Auto": -0.0015}

class MarketEngine:
    """Hash Map + Graph + Circular Buffer all in one engine"""
    def __init__(self):
        # Hash Map: symbol -> stock data
        self.stocks = {}
        # Circular Buffer: price history per stock (deque)
        self.history = {}
        # Graph: adjacency list for sector peers
        self.graph = {}

        for sym, name, price, sector in STOCKS_META:
            self.stocks[sym] = {"sym": sym, "name": name, "price": price,
                                "sector": sector, "chg": 0.0, "vol": 0, "prev": price}
            self.history[sym] = deque([price] * MAX_HIST, maxlen=MAX_HIST)
            self.graph[sym] = []

        # Build graph edges (same sector = connected)
        sector_map = {}
        for sym, _, _, sector in STOCKS_META:
            sector_map.setdefault(sector, []).append(sym)
        for peers in sector_map.values():
            for i in range(len(peers)):
                for j in range(i + 1, len(peers)):
                    self.graph[peers[i]].append(peers[j])
                    self.graph[peers[j]].append(peers[i])

    def tick(self):
        """Update all prices with random walk + sector drift"""
        for sym, s in self.stocks.items():
            r = (random.random() - 0.48) * 0.032
            d = SECTOR_DRIFT.get(s["sector"], 0)
            s["prev"]  = s["price"]
            s["price"] = round(max(10, s["price"] * (1 + r + d)), 2)
            s["chg"]   = round((s["price"] - s["prev"]) / s["prev"] * 100, 2)
            s["vol"]   = random.randint(10000, 500000)
            self.history[sym].append(s["price"])

    def bfs_peers(self, sym):
        """BFS traversal on stock graph to find sector peers"""
        visited, queue, result = {sym}, deque([sym]), []
        while queue:
            node = queue.popleft()
            for nb in self.graph.get(node, []):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
                    result.append(nb)
        return result


class Portfolio:
    """OOP portfolio with Stack for transaction history"""
    def __init__(self, cash=100000):
        self.cash      = cash
        self.holdings  = {}   # Hash Map: sym -> qty
        self.tx_stack  = []   # Stack: transaction history

    def buy(self, sym, qty, price):
        cost = price * qty
        if cost > self.cash:
            return False, f"Need ₹{cost:,.2f} but only have ₹{self.cash:,.2f}"
        self.cash -= cost
        self.holdings[sym] = self.holdings.get(sym, 0) + qty
        self.tx_stack.append({"type": "BUY", "sym": sym, "qty": qty,
                               "price": price, "time": datetime.now().strftime("%H:%M:%S")})
        return True, f"Bought {qty}× {sym} @ ₹{price:,.2f}"

    def sell(self, sym, qty, price):
        owned = self.holdings.get(sym, 0)
        if owned < qty:
            return False, f"Only own {owned} shares of {sym}"
        self.cash += price * qty
        self.holdings[sym] -= qty
        if self.holdings[sym] == 0:
            del self.holdings[sym]
        self.tx_stack.append({"type": "SELL", "sym": sym, "qty": qty,
                               "price": price, "time": datetime.now().strftime("%H:%M:%S")})
        return True, f"Sold {qty}× {sym} @ ₹{price:,.2f}"

    def total_value(self, market):
        invested = sum(market[s]["price"] * q for s, q in self.holdings.items() if s in market)
        return self.cash + invested

    def pnl(self, market, init=100000):
        return self.total_value(market) - init

    def avg_buy_price(self, sym):
        buys = [t["price"] for t in self.tx_stack if t["type"] == "BUY" and t["sym"] == sym]
        return sum(buys) / len(buys) if buys else 0

    def to_json(self):
        return json.dumps({"cash": self.cash, "holdings": self.holdings, "tx_stack": self.tx_stack})

    @staticmethod
    def from_json(s):
        d = json.loads(s)
        p = Portfolio(cash=d["cash"])
        p.holdings = d["holdings"]
        p.tx_stack = d["tx_stack"]
        return p


# ─── Singleton engine ───────────────────────────────────
engine = MarketEngine()
engine.tick()

# ═══════════════════════════════════════════════════════
#  STYLES
# ═══════════════════════════════════════════════════════

DARK = {
    "bg_base":    "#060912",
    "bg_surface": "#0b0f1e",
    "bg_card":    "#0f1629",
    "bg_hover":   "#141b35",
    "border":     "rgba(59,130,246,0.14)",
    "border_med": "rgba(59,130,246,0.28)",
    "text_pri":   "#e8eeff",
    "text_sec":   "#7b93c8",
    "text_mut":   "#3d5280",
    "accent":     "#3b82f6",
    "accent_hi":  "#60a5fa",
    "green":      "#10d9a0",
    "red":        "#f43f5e",
    "green_bg":   "rgba(16,217,160,0.08)",
    "red_bg":     "rgba(244,63,94,0.08)",
    "blue_glow":  "rgba(59,130,246,0.1)",
    "plot_bg":    "#060912",
    "plot_paper": "#060912",
    "grid_col":   "rgba(59,130,246,0.07)",
    "tick_col":   "#3d5280",
}

LIGHT = {
    "bg_base":    "#f0f4ff",
    "bg_surface": "#ffffff",
    "bg_card":    "#ffffff",
    "bg_hover":   "#f5f8ff",
    "border":     "rgba(59,130,246,0.14)",
    "border_med": "rgba(59,130,246,0.3)",
    "text_pri":   "#0f1e45",
    "text_sec":   "#3d5a9a",
    "text_mut":   "#8fa4cc",
    "accent":     "#2563eb",
    "accent_hi":  "#3b82f6",
    "green":      "#059669",
    "red":        "#e11d48",
    "green_bg":   "rgba(5,150,105,0.08)",
    "red_bg":     "rgba(225,29,72,0.08)",
    "blue_glow":  "rgba(59,130,246,0.07)",
    "plot_bg":    "#f0f4ff",
    "plot_paper": "#f0f4ff",
    "grid_col":   "rgba(59,130,246,0.1)",
    "tick_col":   "#8fa4cc",
}

FONTS = {
    "display": "Syne, sans-serif",
    "mono":    "JetBrains Mono, monospace",
}

def T(theme): return DARK if theme == "dark" else LIGHT

def card_style(t):
    return {
        "background": T(t)["bg_card"],
        "border": f"1px solid {T(t)['border']}",
        "borderRadius": "12px",
        "padding": "14px",
        "position": "relative",
        "overflow": "hidden",
        "transition": "border-color .2s",
    }

def label_style(t):
    return {"fontSize": "9px", "letterSpacing": "2px", "color": T(t)["text_mut"],
            "textTransform": "uppercase", "fontWeight": "600", "marginBottom": "5px",
            "fontFamily": FONTS["mono"]}

def mono(t, size="13px", color=None, weight="400"):
    return {"fontFamily": FONTS["mono"], "fontSize": size,
            "color": color or T(t)["text_pri"], "fontWeight": weight}

# ═══════════════════════════════════════════════════════
#  LAYOUT BUILDERS
# ═══════════════════════════════════════════════════════

def build_header(t):
    th = T(t)
    return html.Div([
        # Logo
        html.Div([
            html.Div("▲", style={
                "width":"30px","height":"30px","borderRadius":"8px",
                "background": th["accent"],"color":"#fff",
                "display":"flex","alignItems":"center","justifyContent":"center",
                "fontSize":"13px","fontWeight":"700",
            }),
            html.Span(["APEX", html.Span("MKT", style={"color": th["accent_hi"]})],
                      style={"fontFamily": FONTS["display"],"fontWeight":"700",
                             "fontSize":"17px","letterSpacing":"0.08em"}),
        ], style={"display":"flex","alignItems":"center","gap":"10px","flexShrink":"0"}),

        # Ticker tape
        html.Div(html.Div(id="tape", style={
            "display":"flex","gap":"28px","whiteSpace":"nowrap",
            "animation":"scrollTape 35s linear infinite",
        }), style={"flex":"1","overflow":"hidden","position":"relative"}),

        # Right side
        html.Div([
            html.Div(id="htime", style={**mono(t,"11px",th["text_mut"]),"flexShrink":"0"}),
            html.Div([
                html.Div("PORTFOLIO", style=label_style(t)),
                html.Div(id="hbal", children="₹1,00,000",
                         style={**mono(t,"15px",th["accent_hi"],"500")}),
            ], style={"textAlign":"right"}),
            # Theme toggle
            html.Button(
                "🌙" if t=="dark" else "☀️",
                id="theme-toggle",
                style={
                    "background": th["bg_card"],
                    "border": f"1px solid {th['border_med']}",
                    "borderRadius":"20px","padding":"5px 14px",
                    "cursor":"pointer","color": th["accent_hi"],
                    "fontFamily": FONTS["mono"],"fontSize":"12px",
                    "transition":"all .3s","flexShrink":"0",
                }
            ),
        ], style={"display":"flex","alignItems":"center","gap":"14px","flexShrink":"0"}),
    ], style={
        "display":"flex","alignItems":"center","gap":"16px",
        "padding":"0 20px","height":"58px",
        "background": th["bg_surface"],
        "borderBottom": f"1px solid {th['border_med']}",
        "position":"sticky","top":"0","zIndex":"100",
        "backdropFilter":"blur(20px)",
    })


def build_market_panel(t):
    th = T(t)
    rows = []
    for sym, name, _, sector in STOCKS_META:
        s = engine.stocks[sym]
        up = s["chg"] >= 0
        rows.append(html.Div([
            # Symbol + name
            html.Div([
                html.Div(sym, style={**mono(t,"12px",th["accent_hi"],"500")}),
                html.Div(name[:16]+"…" if len(name)>16 else name,
                         style={"fontSize":"9px","color":th["text_mut"],"marginTop":"1px"}),
            ], style={"flex":"1"}),
            # Price
            html.Div(f"₹{s['price']:,.2f}",
                     style={**mono(t,"11px",th["text_pri"]),"textAlign":"right","minWidth":"72px"}),
            # Change
            html.Div(f"{'▲' if up else '▼'}{abs(s['chg']):.2f}%",
                     style={**mono(t,"10px",th["green"] if up else th["red"]),
                            "textAlign":"right","minWidth":"60px"}),
        ], id={"type":"mkt-row","sym":sym}, n_clicks=0,
           style={
               "display":"flex","alignItems":"center","gap":"8px",
               "padding":"9px 12px","cursor":"pointer",
               "borderBottom": f"1px solid {th['border']}",
               "transition":"background .15s",
           }
        ))

    return html.Div([
        _panel_header("Market Watch", t, right=html.Span("● LIVE", style={
            "fontSize":"9px","color":th["green"],"fontFamily":FONTS["mono"],"letterSpacing":"1px"
        })),
        html.Div(rows, id="mkt-rows", style={"overflowY":"auto","flex":"1"}),
    ], style={"display":"flex","flexDirection":"column","background":th["bg_surface"],
              "borderRight":f"1px solid {th['border']}","overflow":"hidden"})


def build_chart_panel(t):
    th = T(t)
    sym = "TCS"
    s = engine.stocks[sym]
    up = s["chg"] >= 0
    return html.Div([
        _panel_header("Price Chart", t, right=html.Span(
            s["sector"], style={
                "fontSize":"9px","fontWeight":"600","letterSpacing":"2px",
                "padding":"3px 10px","borderRadius":"20px",
                "background":th["blue_glow"],"border":f"1px solid {th['border_med']}",
                "color":th["accent_hi"],"textTransform":"uppercase",
                "fontFamily":FONTS["mono"],
            }
        )),
        html.Div([
            html.Div([
                html.Div(sym, id="c-sym",
                         style={**mono(t,"12px",th["text_mut"],"500"),"letterSpacing":"1px"}),
                html.Div(s["name"], id="c-name",
                         style={"fontSize":"11px","color":th["text_mut"],"marginBottom":"4px"}),
                html.Div(f"₹{s['price']:,.2f}", id="c-price",
                         style={"fontFamily":FONTS["display"],"fontSize":"22px",
                                "fontWeight":"700","color":th["text_pri"],"lineHeight":"1"}),
                html.Div(f"{'+'if up else ''}{s['chg']}%", id="c-chg",
                         style={**mono(t,"13px",th["green"] if up else th["red"]),"marginTop":"4px"}),
            ]),
            html.Div(f"VOL: {s['vol']:,}", id="c-vol",
                     style={**mono(t,"10px",th["text_mut"]),"alignSelf":"flex-start"}),
        ], style={"display":"flex","justifyContent":"space-between",
                  "alignItems":"flex-start","padding":"8px 16px 0"}),
        html.Div(
            dcc.Graph(id="main-chart", config={"displayModeBar":False},
                      style={"height":"160px"}),
            style={"height":"160px","flexShrink":"0","overflow":"hidden"},
        ),
    ], style={"display":"flex","flexDirection":"column","overflow":"hidden",
              "background":th["bg_surface"],"minHeight":"0"})


def build_portfolio_panel(t):
    th = T(t)
    return html.Div([
        _panel_header("Portfolio", t),
        html.Div([
            # Stats grid
            html.Div([
                _stat_card("Cash",        "pf-cash",    "₹1,00,000", th["accent_hi"], t),
                _stat_card("Invested",    "pf-inv",     "₹0",        th["text_pri"],  t),
                _stat_card("Total Value", "pf-total",   "₹1,00,000", th["accent_hi"], t, full=True),
                _stat_card("P&L",         "pf-pnl",     "₹0.00",     th["text_pri"],  t, full=True),
            ], style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"8px","marginBottom":"14px"}),

            _section_label("Holdings", t),
            html.Div(
                html.Div("No holdings yet.\nStart trading!", style={
                    "color":th["text_mut"],"fontSize":"11px","textAlign":"center","padding":"16px 0","lineHeight":"1.7"
                }),
                id="hold-list"
            ),

            _section_label("Sector Peers (Graph BFS)", t),
            html.Div(id="peers-wrap", style={"display":"flex","flexWrap":"wrap","gap":"6px","marginTop":"4px"}),

        ], style={"overflowY":"auto","flex":"1","padding":"12px"}),
    ], style={"display":"flex","flexDirection":"column","background":th["bg_surface"],
              "borderLeft":f"1px solid {th['border']}","overflow":"hidden",
              "gridColumn":"3","gridRow":"1/3"})


def build_trade_panel(t):
    th = T(t)
    syms = [(sym, f"{sym} — {name}") for sym, name, _, _ in STOCKS_META]
    return html.Div([
        _panel_header("Trade Desk", t),
        html.Div([
            # Buy/Sell tabs
            html.Div([
                html.Button("BUY", id="tab-buy", n_clicks=0, style={
                    "flex":"1","padding":"7px","borderRadius":"8px",
                    "border":f"1px solid {th['green']}","background":th["green_bg"],
                    "color":th["green"],"fontFamily":FONTS["display"],
                    "fontSize":"11px","fontWeight":"700","letterSpacing":"1.5px",
                    "cursor":"pointer","transition":"all .2s",
                }),
                html.Button("SELL", id="tab-sell", n_clicks=0, style={
                    "flex":"1","padding":"7px","borderRadius":"8px",
                    "border":f"1px solid {th['border']}","background":"transparent",
                    "color":th["text_mut"],"fontFamily":FONTS["display"],
                    "fontSize":"11px","fontWeight":"700","letterSpacing":"1.5px",
                    "cursor":"pointer","transition":"all .2s",
                }),
            ], style={"display":"flex","gap":"6px","marginBottom":"12px"}),

            # Symbol
            html.Div([
                html.Div("SYM", style={**label_style(t),"width":"28px","marginBottom":"0","flexShrink":"0"}),
                dcc.Dropdown(
                    id="t-sym",
                    options=[{"label":lbl,"value":sym} for sym,lbl in syms],
                    value="TCS", clearable=False,
                    style={"flex":"1","fontFamily":FONTS["mono"],"fontSize":"11px"},
                ),
            ], style={"display":"flex","alignItems":"center","gap":"8px","marginBottom":"8px"}),

            # Quantity
            html.Div([
                html.Div("QTY", style={**label_style(t),"width":"28px","marginBottom":"0","flexShrink":"0"}),
                dcc.Input(id="t-qty", type="number", value=1, min=1,
                          style={
                              "flex":"1","background":th["bg_card"],
                              "border":f"1px solid {th['border_med']}",
                              "borderRadius":"7px","padding":"7px 10px",
                              "fontFamily":FONTS["mono"],"fontSize":"11px",
                              "color":th["text_pri"],"outline":"none","width":"100%",
                          }),
            ], style={"display":"flex","alignItems":"center","gap":"8px","marginBottom":"8px"}),

            # Cost bar
            html.Div(id="t-cost", children="Total: ₹0.00 · Available: ₹1,00,000",
                     style={
                         **mono(t,"10px",th["text_mut"]),
                         "textAlign":"center","padding":"6px",
                         "background":th["blue_glow"],"border":f"1px solid {th['border']}",
                         "borderRadius":"6px","marginBottom":"8px",
                     }),

            html.Button("EXECUTE BUY", id="exec-btn", n_clicks=0, style={
                "width":"100%","padding":"10px","border":"none","borderRadius":"8px",
                "fontFamily":FONTS["display"],"fontSize":"11px","fontWeight":"700",
                "letterSpacing":"2px","cursor":"pointer","transition":"all .2s",
                "background":th["green"],"color":"#021a10",
                "boxShadow":f"0 0 20px {th['green_bg']}",
            }),

            html.Div(id="trade-msg", style={
                **mono(t,"11px"),"textAlign":"center","marginTop":"8px","minHeight":"18px"
            }),
        ], style={"padding":"12px","display":"flex","flexDirection":"column","gap":"0"}),
    ], style={"display":"flex","flexDirection":"column","background":th["bg_surface"],
              "borderRight":f"1px solid {th['border']}","borderTop":f"1px solid {th['border']}"})


def build_log_panel(t):
    th = T(t)
    return html.Div([
        _panel_header("Transaction Log", t,
                      right=html.Span(id="log-count", children="0 trades",
                                      style={**mono(t,"10px",th["text_mut"])})),
        html.Div(
            html.Div("No transactions yet…", style={"color":th["text_mut"],"fontSize":"11px","padding":"12px 0"}),
            id="log-list",
            style={"overflowY":"auto","flex":"1","padding":"0 14px"},
        ),
    ], style={"display":"flex","flexDirection":"column","background":th["bg_surface"],
              "borderTop":f"1px solid {th['border']}","borderLeft":f"1px solid {th['border']}",
              "overflow":"hidden"})


def _panel_header(title, t, right=None):
    th = T(t)
    return html.Div([
        html.Div([
            html.Span(style={
                "width":"5px","height":"5px","borderRadius":"50%",
                "background":th["accent"],"display":"inline-block",
                "boxShadow":f"0 0 6px {th['accent']}","marginRight":"7px",
                "animation":"blink 2s ease-in-out infinite",
            }),
            html.Span(title, style=label_style(t)),
        ], style={"display":"flex","alignItems":"center"}),
        right or html.Div(),
    ], style={
        "display":"flex","alignItems":"center","justifyContent":"space-between",
        "padding":"11px 16px 10px","borderBottom":f"1px solid {th['border']}","flexShrink":"0",
    })


def _stat_card(label, id_, value, color, t, full=False):
    th = T(t)
    style = card_style(t)
    if full:
        style["gridColumn"] = "1/-1"
    return html.Div([
        html.Div(label, style=label_style(t)),
        html.Div(value, id=id_, style={**mono(t,"13px",color,"500")}),
    ], style=style)


def _section_label(text, t):
    th = T(t)
    return html.Div(text, style={
        "fontSize":"9px","letterSpacing":"2.5px","color":th["text_mut"],
        "textTransform":"uppercase","fontWeight":"600",
        "margin":"14px 0 8px","fontFamily":FONTS["mono"],
        "borderBottom":f"1px solid {th['border']}","paddingBottom":"6px",
    })


# ═══════════════════════════════════════════════════════
#  CHART BUILDER
# ═══════════════════════════════════════════════════════

def make_chart(sym, theme):
    th    = T(theme)
    s     = engine.stocks[sym]
    hist  = list(engine.history[sym])
    up    = s["chg"] >= 0
    color = th["green"] if up else th["red"]
    fill_color = "rgba(16,217,160,0.09)" if up else "rgba(244,63,94,0.09)"

    # Tight Y-axis: pad only 0.3% so line fills the whole chart area
    lo  = min(hist)
    hi  = max(hist)
    pad = (hi - lo) * 0.3 if hi != lo else lo * 0.002
    y_min = lo - pad
    y_max = hi + pad

    x_vals = list(range(len(hist)))
    # Closed polygon for fill (avoids "tozeroy" which fills down to 0)
    x_fill = x_vals + x_vals[::-1]
    y_fill  = hist  + [y_min] * len(hist)

    fig = go.Figure()
    # Shaded fill area
    fig.add_trace(go.Scatter(
        x=x_fill, y=y_fill, mode="lines",
        line=dict(width=0), fill="toself",
        fillcolor=fill_color,
        hoverinfo="skip", showlegend=False,
    ))
    # Price line
    fig.add_trace(go.Scatter(
        x=x_vals, y=hist, mode="lines",
        line=dict(color=color, width=2, shape="spline", smoothing=0.5),
        hovertemplate="Rs %{y:,.2f}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        height=160,
        autosize=False,
        margin=dict(l=4, r=58, t=6, b=6),
        paper_bgcolor=th["plot_paper"],
        plot_bgcolor=th["plot_bg"],
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False,
                   range=[0, len(hist)-1]),
        yaxis=dict(
            range=[y_min, y_max],
            gridcolor=th["grid_col"],
            tickfont=dict(family=FONTS["mono"], size=10, color=th["tick_col"]),
            tickformat=",.0f", side="right", zeroline=False, nticks=4,
        ),
        hoverlabel=dict(bgcolor=th["bg_card"], bordercolor=th["border_med"],
                        font=dict(family=FONTS["mono"], size=11, color=th["text_pri"])),
        showlegend=False,
    )
    return fig

# ═══════════════════════════════════════════════════════
#  APP INIT
# ═══════════════════════════════════════════════════════

GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; font-family: 'Syne', sans-serif; }
body { overflow-x: hidden; transition: background .35s, color .35s; }
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(59,130,246,0.4); border-radius:2px; }
@keyframes scrollTape { from{transform:translateX(0);} to{transform:translateX(-50%);} }
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
@keyframes fadeSlide { from{opacity:0;transform:translateY(-6px);} to{opacity:1;transform:translateY(0);} }
.mkt-row-item:hover { background: rgba(59,130,246,0.06) !important; }
.mkt-row-sel { background: rgba(59,130,246,0.1) !important; border-left: 2px solid #3b82f6 !important; }
"""

app = Dash(__name__, suppress_callback_exceptions=True,
           index_string=f"""<!DOCTYPE html>
<html>
  <head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    {{%css%}}
    <style>{GLOBAL_CSS}</style>
  </head>
  <body>
    {{%app_entry%}}
    <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
  </body>
</html>""")
app.title = "Apex Markets"

app.layout = html.Div([
    dcc.Store(id="theme-store",    data="dark"),
    dcc.Store(id="portfolio-store",data=Portfolio().to_json()),
    dcc.Store(id="sel-sym-store",  data="TCS"),
    dcc.Store(id="trade-mode",     data="BUY"),
    dcc.Interval(id="interval",    interval=2000, n_intervals=0),
    html.Div(id="root-layout"),
], style={"height":"100vh","display":"flex","flexDirection":"column"})


# ═══════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════

@app.callback(Output("root-layout","children"),
              Input("theme-store","data"))
def render_layout(theme):
    th = T(theme)
    return html.Div([
        build_header(theme),
        html.Div([
            build_market_panel(theme),
            build_chart_panel(theme),
            build_portfolio_panel(theme),
            build_trade_panel(theme),
            build_log_panel(theme),
        ], style={
            "display":"grid",
            "gridTemplateColumns":"250px 1fr 290px",
            "gridTemplateRows":"calc(100vh - 58px - 210px) 210px",
            "flex":"1","gap":"1px","background":th["border"],
            "overflow":"hidden",
        }),
    ], style={"display":"flex","flexDirection":"column","height":"100vh",
              "background":th["bg_base"],"color":th["text_pri"]})


@app.callback(Output("theme-store","data"),
              Input("theme-toggle","n_clicks"),
              State("theme-store","data"),
              prevent_initial_call=True)
def toggle_theme(n, current):
    return "light" if current == "dark" else "dark"


@app.callback(
    [Output("tape","children"),
     Output("mkt-rows","children"),
     Output("main-chart","figure"),
     Output("c-sym","children"),   Output("c-name","children"),
     Output("c-price","children"), Output("c-chg","children"),
     Output("c-chg","style"),      Output("c-vol","children"),
     Output("htime","children"),   Output("hbal","children"),
     Output("pf-cash","children"), Output("pf-inv","children"),
     Output("pf-total","children"),Output("pf-pnl","children"),
     Output("pf-pnl","style"),     Output("hold-list","children"),
     Output("peers-wrap","children"),
     Output("t-cost","children"),  Output("log-list","children"),
     Output("log-count","children")],
    [Input("interval","n_intervals"),
     Input("sel-sym-store","data")],
    [State("theme-store","data"),
     State("portfolio-store","data"),
     State("t-sym","value"),
     State("t-qty","value")],
)
def refresh_all(n, sel_sym, theme, pf_json, t_sym, t_qty):
    engine.tick()
    th  = T(theme)
    pf  = Portfolio.from_json(pf_json)
    sym = sel_sym or "TCS"
    s   = engine.stocks[sym]

    # ── Ticker tape ──
    tape_items = []
    for stk_sym, _, _, _ in STOCKS_META:
        stk = engine.stocks[stk_sym]
        up  = stk["chg"] >= 0
        tape_items.append(html.Span([
            html.Span(stk_sym, style={**mono(theme,"11px",th["accent_hi"],"500"),"marginRight":"6px"}),
            html.Span(f"₹{stk['price']:,.2f}", style=mono(theme,"11px",th["text_pri"])),
            html.Span(f"{'+'if up else ''}{stk['chg']}%", style={
                **mono(theme,"10px",th["green"] if up else th["red"]),
                "background": th["green_bg"] if up else th["red_bg"],
                "padding":"1px 5px","borderRadius":"3px","marginLeft":"5px",
            }),
        ], style={"display":"inline-flex","alignItems":"center","gap":"2px","marginRight":"28px"}))
    tape = tape_items + tape_items  # duplicate for seamless loop

    # ── Market rows ──
    rows = []
    for stk_sym, name, _, _ in STOCKS_META:
        stk = engine.stocks[stk_sym]
        up  = stk["chg"] >= 0
        is_sel = stk_sym == sym
        rows.append(html.Div([
            html.Div([
                html.Div(stk_sym, style={**mono(theme,"12px",th["accent_hi"],"500")}),
                html.Div(name[:16]+"…" if len(name)>16 else name,
                         style={"fontSize":"9px","color":th["text_mut"],"marginTop":"1px"}),
            ], style={"flex":"1"}),
            html.Div(f"₹{stk['price']:,.2f}",
                     style={**mono(theme,"11px",th["text_pri"]),"textAlign":"right","minWidth":"72px"}),
            html.Div(f"{'▲'if up else '▼'}{abs(stk['chg']):.2f}%",
                     style={**mono(theme,"10px",th["green"] if up else th["red"]),
                            "textAlign":"right","minWidth":"60px"}),
        ], id={"type":"mkt-row","sym":stk_sym}, n_clicks=0,
           className="mkt-row-item" + (" mkt-row-sel" if is_sel else ""),
           style={
               "display":"flex","alignItems":"center","gap":"8px",
               "padding":"9px 12px","cursor":"pointer",
               "borderBottom":f"1px solid {th['border']}","transition":"background .15s",
               "borderLeft": f"2px solid {th['accent']}" if is_sel else "2px solid transparent",
           }
        ))

    # ── Chart ──
    up   = s["chg"] >= 0
    fig  = make_chart(sym, theme)
    chg_style = {**mono(theme,"13px",th["green"] if up else th["red"]),"marginTop":"4px"}

    # ── Portfolio stats ──
    invested = sum(engine.stocks[sm]["price"]*q for sm,q in pf.holdings.items() if sm in engine.stocks)
    total    = pf.cash + invested
    pnl      = total - 100000
    pnl_pos  = pnl >= 0
    pnl_style = {**mono(theme,"13px",th["green"] if pnl_pos else th["red"],"500")}

    # ── Holdings ──
    if not pf.holdings:
        hold_children = html.Div("No holdings yet.\nStart trading!", style={
            "color":th["text_mut"],"fontSize":"11px","textAlign":"center","padding":"16px 0","lineHeight":"1.7"
        })
    else:
        hold_children = html.Div([
            html.Div([
                html.Div([
                    html.Div(sm, style={**mono(theme,"12px",th["accent_hi"],"500")}),
                    html.Div(f"{q} shares · avg ₹{pf.avg_buy_price(sm):.0f}",
                             style={"fontSize":"10px","color":th["text_mut"],"marginTop":"2px"}),
                ]),
                html.Div(
                    ("▲ " if (engine.stocks[sm]["price"]-pf.avg_buy_price(sm))*q>=0 else "▼ ") +
                    f"₹{abs((engine.stocks[sm]['price']-pf.avg_buy_price(sm))*q):.0f}",
                    style={**mono(theme,"12px",
                                  th["green"] if (engine.stocks[sm]["price"]-pf.avg_buy_price(sm))*q>=0 else th["red"],
                                  "500")}
                ),
            ], style={
                "display":"flex","justifyContent":"space-between","alignItems":"center",
                "background":th["bg_card"],"border":f"1px solid {th['border']}",
                "borderRadius":"10px","padding":"10px 12px","marginBottom":"7px",
            })
            for sm, q in pf.holdings.items() if q > 0 and sm in engine.stocks
        ])

    # ── Peers (BFS) ──
    peers = engine.bfs_peers(sym)
    peer_chips = [
        html.Span(p, style={
            **mono(theme,"10px",th["accent_hi"],"500"),
            "padding":"3px 9px","borderRadius":"5px","cursor":"pointer",
            "background":th["blue_glow"],"border":f"1px solid {th['border_med']}",
            "letterSpacing":"0.5px",
        }) for p in peers
    ]

    # ── Trade cost ──
    try:
        qty = int(t_qty) if t_qty else 0
    except:
        qty = 0
    t_s = engine.stocks.get(t_sym or sym)
    cost_txt = f"Total ₹{t_s['price']*qty:,.2f} · Cash ₹{pf.cash:,.2f}" if t_s else ""

    # ── Transaction log ──
    if not pf.tx_stack:
        log_children = html.Div("No transactions yet…",
                                style={"color":th["text_mut"],"fontSize":"11px","padding":"12px 0"})
    else:
        log_children = html.Div([
            html.Div([
                html.Span(tx["time"], style={**mono(theme,"10px",th["text_mut"]),"minWidth":"54px"}),
                html.Span(tx["type"], style={
                    "fontSize":"9px","fontWeight":"700","letterSpacing":"1px",
                    "padding":"2px 6px","borderRadius":"4px","flexShrink":"0",
                    "background": th["green_bg"] if tx["type"]=="BUY" else th["red_bg"],
                    "color": th["green"] if tx["type"]=="BUY" else th["red"],
                    "fontFamily": FONTS["mono"],
                }),
                html.Span(tx["sym"],  style={**mono(theme,"11px",th["accent_hi"],"500"),"minWidth":"82px"}),
                html.Span(f"{tx['qty']}× ₹{tx['price']:,.2f}",
                          style={**mono(theme,"10px",th["text_mut"]),"flex":"1"}),
                html.Span(f"₹{tx['price']*tx['qty']:,.0f}",
                          style=mono(theme,"11px",th["text_pri"])),
            ], style={
                "display":"flex","alignItems":"center","gap":"10px",
                "padding":"7px 0","borderBottom":f"1px solid {th['border']}",
                "animation":"fadeSlide .3s ease",
            })
            for tx in reversed(pf.tx_stack[-15:])
        ])

    now = datetime.now().strftime("%H:%M:%S")

    return (
        tape,
        rows,
        fig,
        sym, s["name"],
        f"₹{s['price']:,.2f}",
        f"{'+'if up else ''}{s['chg']}%", chg_style,
        f"VOL: {s['vol']:,}",
        now,
        f"₹{total:,.0f}",
        f"₹{pf.cash:,.0f}",
        f"₹{invested:,.0f}",
        f"₹{total:,.0f}",
        f"{'+'if pnl_pos else '−'}₹{abs(pnl):,.2f}", pnl_style,
        hold_children,
        peer_chips,
        cost_txt,
        log_children,
        f"{len(pf.tx_stack)} trade{'s' if len(pf.tx_stack)!=1 else ''}",
    )


@app.callback(
    [Output("portfolio-store","data"),
     Output("trade-msg","children"),
     Output("trade-msg","style")],
    Input("exec-btn","n_clicks"),
    [State("t-sym","value"),
     State("t-qty","value"),
     State("trade-mode","data"),
     State("portfolio-store","data"),
     State("theme-store","data")],
    prevent_initial_call=True,
)
def execute_trade(n, sym, qty, mode, pf_json, theme):
    th = T(theme)
    if not n or not sym: return no_update, no_update, no_update
    pf = Portfolio.from_json(pf_json)
    try: qty = int(qty)
    except: qty = 0
    s = engine.stocks.get(sym)
    if not s or qty <= 0:
        return no_update, "Invalid quantity", {**mono(theme,"11px",th["red"]),"textAlign":"center","marginTop":"8px"}

    if mode == "BUY":
        ok, msg = pf.buy(sym, qty, s["price"])
    else:
        ok, msg = pf.sell(sym, qty, s["price"])

    color = th["green"] if ok else th["red"]
    return (
        pf.to_json(),
        msg,
        {**mono(theme,"11px",color),"textAlign":"center","marginTop":"8px"},
    )


@app.callback(
    [Output("trade-mode","data"),
     Output("tab-buy","style"),
     Output("tab-sell","style"),
     Output("exec-btn","children"),
     Output("exec-btn","style")],
    [Input("tab-buy","n_clicks"), Input("tab-sell","n_clicks")],
    State("theme-store","data"),
    prevent_initial_call=True,
)
def switch_mode(buy_n, sell_n, theme):
    th    = T(theme)
    mode  = "BUY" if ctx.triggered_id == "tab-buy" else "SELL"
    base  = {"flex":"1","padding":"7px","borderRadius":"8px","fontFamily":FONTS["display"],
             "fontSize":"11px","fontWeight":"700","letterSpacing":"1.5px","cursor":"pointer","transition":"all .2s"}
    buy_s  = {**base,"border":f"1px solid {th['green']}","background":th["green_bg"],"color":th["green"]} \
              if mode=="BUY" else {**base,"border":f"1px solid {th['border']}","background":"transparent","color":th["text_mut"]}
    sell_s = {**base,"border":f"1px solid {th['red']}","background":th["red_bg"],"color":th["red"]} \
              if mode=="SELL" else {**base,"border":f"1px solid {th['border']}","background":"transparent","color":th["text_mut"]}
    btn_s  = {"width":"100%","padding":"10px","border":"none","borderRadius":"8px",
              "fontFamily":FONTS["display"],"fontSize":"11px","fontWeight":"700",
              "letterSpacing":"2px","cursor":"pointer","transition":"all .2s",
              "background":th["green"] if mode=="BUY" else th["red"],
              "color":"#021a10" if mode=="BUY" else "#fff"}
    return mode, buy_s, sell_s, f"EXECUTE {mode}", btn_s


@app.callback(
    Output("sel-sym-store","data"),
    Input({"type":"mkt-row","sym": "__all__"}, "n_clicks"),
    prevent_initial_call=True,
)
def select_sym(_):
    if ctx.triggered_id:
        return ctx.triggered_id["sym"]
    return no_update


if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════╗")
    print("  ║   APEX MARKETS — Starting up…   ║")
    print("  ║   Open: http://localhost:8050    ║")
    print("  ╚══════════════════════════════════╝\n")
    app.run(debug=False, port=8050)