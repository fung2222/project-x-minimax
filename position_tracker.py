"""
Project X — 即時持倉追蹤 (每小時 21:00-04:00 HKT)
美股交易時段自動更新持倉價格；報價失敗唔會清零 equity
"""
import json, os, sys, datetime
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finnhub_api
import risk_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_PATH = os.path.join(BASE_DIR, "portfolio.json")
PROFILES_PATH = os.path.join(BASE_DIR, "profiles.json")


def fetch_latest_quote(ticker):
    """取得實時／最近報價：Finnhub 優先，再 yfinance"""
    try:
        q = finnhub_api.get_quote(ticker)
        if isinstance(q, dict):
            price = q.get("price") or q.get("c") or q.get("current")
            if price:
                return float(price)
    except Exception:
        pass
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price:
            return float(price)
    except Exception:
        pass
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if len(hist):
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def update_positions():
    """更新所有持倉嘅當前價格"""
    with open(PORTFOLIO_PATH, encoding="utf-8") as f:
        pf = json.load(f)
    positions = pf.get("positions", [])
    if not positions:
        print(f"[{datetime.datetime.now()}] 無持倉，跳過")
        return
    updates = []
    total_value = 0
    total_pnl = 0
    got_any = False
    for pos in positions:
        ticker = pos["ticker"]
        price = fetch_latest_quote(ticker)
        if price:
            got_any = True
            pos["current_price"] = price
            pos["value_usd"] = round(price * pos["shares"], 2)
            pos["pnl_usd"] = round((price - pos["entry_price"]) * pos["shares"], 2)
            pos["pnl_pct"] = round((price - pos["entry_price"]) / pos["entry_price"] * 100, 2)
            pos["last_updated"] = datetime.datetime.now().isoformat()
            updates.append(f"{ticker} ${price:.2f} ({pos['pnl_pct']:+.2f}%)")
        # 用現有／成本價計市值，避免報價全失敗時 equity 被清成純現金
        px = pos.get("current_price") or pos["entry_price"]
        val = round(px * pos["shares"], 2)
        pos["value_usd"] = val
        pos["pnl_usd"] = round((px - pos["entry_price"]) * pos["shares"], 2)
        pos["pnl_pct"] = round((px - pos["entry_price"]) / pos["entry_price"] * 100, 2)
        total_value += val
        total_pnl += pos["pnl_usd"]
    if not got_any:
        print(f"[{datetime.datetime.now()}] 報價失敗，保留舊價；持倉市值 ${total_value:.2f}")
    pf["account"]["equity_usd"] = round(total_value + pf["account"].get("cash_usd", 0), 2)
    pf["account"]["total_pnl_usd"] = round(total_pnl, 2)
    cost = sum(p["entry_price"] * p["shares"] for p in positions) or 1
    pf["account"]["total_pnl_pct"] = round(total_pnl / cost * 100, 2)
    pf["account"]["total_invested_usd"] = round(cost, 2)
    pf["last_tracker_update"] = datetime.datetime.now().isoformat()
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(pf, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.datetime.now()}] 更新 {len(positions)} 持倉: {' '.join(updates) if updates else '(no fresh quotes)'}")


if __name__ == "__main__":
    update_positions()
