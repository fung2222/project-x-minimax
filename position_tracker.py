"""
Project X — 即時持倉追蹤 (每小時 21:00-04:00 HKT)
美股交易時段自動更新持倉價格，唔推送 Telegram，只更新 dashboard
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
    """取得實時報價"""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        return info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
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
    for pos in positions:
        ticker = pos["ticker"]
        price = fetch_latest_quote(ticker)
        if price:
            pos["current_price"] = price
            pos["value_usd"] = round(price * pos["shares"], 2)
            pos["pnl_usd"] = round((price - pos["entry_price"]) * pos["shares"], 2)
            pos["pnl_pct"] = round((price - pos["entry_price"]) / pos["entry_price"] * 100, 2)
            pos["last_updated"] = datetime.datetime.now().isoformat()
            total_value += pos["value_usd"]
            total_pnl += pos["pnl_usd"]
            updates.append(f"{ticker} ${price:.2f} ({pos['pnl_pct']:+.2f}%)")
    pf["account"]["equity_usd"] = round(total_value + pf["account"].get("cash_usd", 0), 2)
    pf["account"]["total_pnl_usd"] = round(total_pnl, 2)
    pf["account"]["total_pnl_pct"] = round(total_pnl / (pf["account"]["equity_usd"] - total_pnl) * 100, 2) if (pf["account"]["equity_usd"] - total_pnl) else 0
    pf["last_tracker_update"] = datetime.datetime.now().isoformat()
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(pf, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.datetime.now()}] 更新 {len(positions)} 持倉: {' '.join(updates)}")


if __name__ == "__main__":
    update_positions()