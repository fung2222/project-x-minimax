"""
Project X — 止損 / 止盈 / 加倉 邏輯模組
ATR-based 止損，固定 % 止盈
"""
import json, os

PORTFOLIO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio.json")
SIGNALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals.json")


def load_portfolio():
    with open(PORTFOLIO_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(pf):
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(pf, f, ensure_ascii=False, indent=2)


def get_position_with_indicators(ticker):
    """取得持倉 + 對應股票嘅技術指標（RSI、MACD、ATR）"""
    with open(SIGNALS_PATH, encoding="utf-8") as f:
        sig_data = json.load(f)
    today = list({s["date"] for s in sig_data.get("signals", [])})[-1] if sig_data.get("signals") else None
    if not today:
        return None, None
    sig_today = next((s for s in sig_data["signals"] if s.get("date") == today and s.get("ticker") == ticker), None)
    return sig_today, today


def check_stop_loss(position, current_price, atr):
    """ATR-based 止損：跌穿 entry_price - 2*ATR 即觸發"""
    rules = load_portfolio()["rules"]
    atr_mult = rules.get("stop_loss_atr_mult", 2.0)
    entry = position["entry_price"]
    stop_price = entry - (atr * atr_mult)
    stop_pct = (stop_price - entry) / entry * 100
    distance_to_stop = (current_price - stop_price) / current_price * 100
    triggered = current_price <= stop_price
    return {
        "stop_price": round(stop_price, 2),
        "stop_pct": round(stop_pct, 1),
        "current_price": current_price,
        "distance_to_stop_pct": round(distance_to_stop, 1),
        "triggered": triggered,
        "atr": atr,
        "atr_mult": atr_mult
    }


def check_take_profit(position, current_price):
    """固定 % 止盈：升 +10% 即觸發"""
    rules = load_portfolio()["rules"]
    tp_pct = rules.get("take_profit_pct", 0.10)
    entry = position["entry_price"]
    target_price = entry * (1 + tp_pct)
    triggered = current_price >= target_price
    return {
        "target_price": round(target_price, 2),
        "target_pct": round(tp_pct * 100, 0),
        "current_price": current_price,
        "triggered": triggered,
        "pnl_pct": round((current_price - entry) / entry * 100, 2)
    }


def check_add_position(position, current_price, indicators):
    """加倉規則：RSI 仍然 < 45 + MACD 仍然睇漲 + 倉位 < 30% 持倉上限"""
    pf = load_portfolio()
    rules = pf["rules"]
    max_pos_pct = rules.get("max_position_pct", 0.30)
    cash_usd = pf["account"].get("cash_usd", 0)
    equity = pf["account"].get("equity_usd", 641)
    current_pos_pct = (position["current_price"] * position["shares"]) / equity
    can_add = current_pos_pct < max_pos_pct * 0.7  # 已用少於 70% 上限先可以加
    rsi = indicators.get("rsi") if indicators else None
    macd_bull = indicators.get("macd_bullish") if indicators else None
    condition_met = rsi is not None and rsi < 45 and macd_bull
    # 加倉金額 = min(cash * 0.3, equity * (max_pos - current))
    target_add_usd = min(cash_usd * 0.5, equity * max_pos_pct - current_pos_pct * equity)
    shares_to_add = int(target_add_usd / current_price) if current_price else 0
    return {
        "current_pos_pct": round(current_pos_pct * 100, 1),
        "max_pos_pct": round(max_pos_pct * 100, 1),
        "can_add": can_add,
        "rsi": rsi,
        "macd_bullish": macd_bull,
        "condition_met": condition_met,
        "cash_usd": round(cash_usd, 2),
        "shares_to_add": shares_to_add,
        "add_amount_usd": round(shares_to_add * current_price, 2)
    }


def evaluate_all_positions(current_prices):
    """評估所有持倉：止損 / 止盈 / 加倉"""
    pf = load_portfolio()
    results = []
    for pos in pf.get("positions", []):
        ticker = pos["ticker"]
        cur = current_prices.get(ticker, pos["current_price"])
        sig, _ = get_position_with_indicators(ticker)
        atr = sig.get("atr", pos["entry_price"] * 0.03) if sig else pos["entry_price"] * 0.03
        sl = check_stop_loss(pos, cur, atr)
        tp = check_take_profit(pos, cur)
        add = check_add_position(pos, cur, sig or {})
        pnl_pct = (cur - pos["entry_price"]) / pos["entry_price"] * 100
        pnl_usd = (cur - pos["entry_price"]) * pos["shares"]
        action = None
        if sl["triggered"]:
            action = "STOP_LOSS"
        elif tp["triggered"]:
            action = "TAKE_PROFIT"
        elif add["condition_met"] and add["can_add"] and add["shares_to_add"] > 0:
            action = "ADD_POSITION"
        results.append({
            "ticker": ticker,
            "shares": pos["shares"],
            "entry_price": pos["entry_price"],
            "current_price": cur,
            "pnl_usd": round(pnl_usd, 2),
            "pnl_pct": round(pnl_pct, 2),
            "stop_loss": sl,
            "take_profit": tp,
            "add_position": add,
            "recommended_action": action
        })
    return results


def execute_action(ticker, action, current_price):
    """執行交易動作（止損/止盈/加倉），更新 portfolio.json"""
    import datetime as dt
    pf = load_portfolio()
    positions = pf.get("positions", [])
    trade_log = pf.get("trade_log", [])
    # 模擬交易費 1%（買 + 賣各 0.5%）
    FEE_RATE = 0.005

    if action == "STOP_LOSS" or action == "TAKE_PROFIT":
        # 平倉
        pos = next((p for p in positions if p["ticker"] == ticker), None)
        if not pos:
            return False, "持倉不存在"
        gross_pnl_usd = (current_price - pos["entry_price"]) * pos["shares"]
        fee_usd = current_price * pos["shares"] * FEE_RATE
        net_pnl_usd = gross_pnl_usd - fee_usd
        gross_pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"] * 100
        net_pnl_pct = net_pnl_usd / (pos["entry_price"] * pos["shares"]) * 100
        proceeds_usd = current_price * pos["shares"] - fee_usd
        proceeds_hkd = round(proceeds_usd * 7.8, 2)
        trade = {
            "id": f"T{len(trade_log)+1:03d}",
            "date": dt.date.today().isoformat(),
            "timestamp": dt.datetime.now().isoformat(),
            "ticker": ticker,
            "action": "SELL",
            "reason": action,
            "shares": pos["shares"],
            "entry_price": pos["entry_price"],
            "exit_price": round(current_price, 2),
            "entry_date": pos.get("entry_date"),
            "exit_date": dt.date.today().isoformat(),
            "gross_proceeds_usd": round(current_price * pos["shares"], 2),
            "fee_usd": round(fee_usd, 2),
            "proceeds_usd": round(proceeds_usd, 2),
            "proceeds_hkd": proceeds_hkd,
            "gross_pnl_usd": round(gross_pnl_usd, 2),
            "gross_pnl_pct": round(gross_pnl_pct, 2),
            "net_pnl_usd": round(net_pnl_usd, 2),
            "net_pnl_pct": round(net_pnl_pct, 2),
            "status": "closed"
        }
        trade_log.append(trade)
        # 移除持倉
        pf["positions"] = [p for p in positions if p["ticker"] != ticker]
        # 更新現金（已扣手續費）
        pf["account"]["cash_usd"] = round(pf["account"].get("cash_usd", 0) + proceeds_usd, 2)
        pf["account"]["cash_hkd"] = round(pf["account"]["cash_usd"] * 7.8, 2)
        pf["account"]["total_fees_usd"] = round(pf["account"].get("total_fees_usd", 0) + fee_usd, 2)
        # 更新交易統計（用 net）
        update_performance_stats(pf, trade)
        save_portfolio(pf)
        return True, trade

    elif action == "ADD_POSITION":
        pos = next((p for p in positions if p["ticker"] == ticker), None)
        if not pos:
            return False, "持倉不存在"
        sig, _ = get_position_with_indicators(ticker)
        add = check_add_position(pos, current_price, sig or {})
        shares_to_add = add["shares_to_add"]
        if shares_to_add <= 0:
            return False, "無足夠現金加倉"
        cost_usd = shares_to_add * current_price
        fee_usd = cost_usd * FEE_RATE
        cost_hkd = round((cost_usd + fee_usd) * 7.8, 2)
        trade = {
            "id": f"T{len(trade_log)+1:03d}",
            "date": dt.date.today().isoformat(),
            "timestamp": dt.datetime.now().isoformat(),
            "ticker": ticker,
            "action": "BUY",
            "reason": "ADD_POSITION",
            "shares": shares_to_add,
            "entry_price": round(current_price, 2),
            "entry_date": dt.date.today().isoformat(),
            "cost_usd": round(cost_usd, 2),
            "fee_usd": round(fee_usd, 2),
            "total_cost_usd": round(cost_usd + fee_usd, 2),
            "cost_hkd": cost_hkd,
            "status": "open"
        }
        trade_log.append(trade)
        # 加倉平均成本
        total_shares = pos["shares"] + shares_to_add
        avg_cost = (pos["entry_price"] * pos["shares"] + current_price * shares_to_add) / total_shares
        pos["shares"] = total_shares
        pos["entry_price"] = round(avg_cost, 2)
        pos["entry_date"] = dt.date.today().isoformat()
        pos["current_price"] = current_price
        pf["account"]["cash_usd"] = round(pf["account"].get("cash_usd", 0) - cost_usd - fee_usd, 2)
        pf["account"]["cash_hkd"] = round(pf["account"]["cash_usd"] * 7.8, 2)
        pf["account"]["total_fees_usd"] = round(pf["account"].get("total_fees_usd", 0) + fee_usd, 2)
        save_portfolio(pf)
        return True, trade

    return False, "不支援嘅動作"


def update_performance_stats(pf, trade):
    """更新命中率統計"""
    signals_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals.json")
    with open(signals_path, encoding="utf-8") as f:
        sig_data = json.load(f)
    perf = sig_data.get("performance", {})
    total = perf.get("total_signals", 0) + 1
    pnl_pct = trade.get("pnl_pct", 0)
    if pnl_pct >= 2:
        perf["hits"] = perf.get("hits", 0) + 1
    elif pnl_pct >= 0:
        perf["partials"] = perf.get("partials", 0) + 1
    elif pnl_pct <= -2:
        perf["misses"] = perf.get("misses", 0) + 1
    else:
        perf["neutrals"] = perf.get("neutrals", 0) + 1
    perf["total_signals"] = total
    perf["hit_rate_pct"] = round(perf.get("hits", 0) / total * 100, 1) if total else 0
    sig_data["performance"] = perf
    with open(signals_path, "w", encoding="utf-8") as f:
        json.dump(sig_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 測試：假設 NVDA 今日收 $200
    res = evaluate_all_positions({"NVDA": 200.0})
    print(json.dumps(res, ensure_ascii=False, indent=2))