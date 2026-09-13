"""
Project X — 每日分析引擎 v2（使用 yfinance 真實數據）
完整流程：VIX Guardrail → 真實報價 → 技術分析 → 生成信號 → 記錄命中率
"""
import json, os, datetime, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import finnhub_api   # 整合了 yfinance 的股價模組
import vix_guardrail

PORTFOLIO_PATH = os.path.join(BASE_DIR, "portfolio.json")
SIGNALS_PATH  = os.path.join(BASE_DIR, "signals.json")
REPORT_PATH   = os.path.join(BASE_DIR, "daily_report.json")

STOCK_NAMES = {
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "RKLB": "Rocket Lab",
    "AMD":  "Adv. Micro Devices",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "META": "Meta Platforms",
    "AMZN": "Amazon",
    "PLTR": "Palantir",
    "ARM":  "Arm Holdings",
    # Opportunity scan (small capital)
    "SOUN": "SoundHound AI",
    "BBAI": "BigBear.ai",
    "IONQ": "IonQ",
    "ASTS": "AST SpaceMobile",
    "LUNR": "Intuitive Machines",
    "SOFI": "SoFi Technologies",
    "HOOD": "Robinhood",
    "RIVN": "Rivian",
    "JOBY": "Joby Aviation",
    "SMCI": "Super Micro Computer",
}

# Max price for 1 share ≈ 25% of ~USD 1280 capital
OPP_MAX_PRICE = 320.0
OPP_MIN_CONFIDENCE = 70.0


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sanitize(obj):
    """將 numpy/Python3 類型轉為 JSON 可序列化類型"""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    import numpy as np
    if isinstance(obj, (np.bool_, np.int64, np.float64)):
        return obj.item()
    return obj


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sanitize(data), f, ensure_ascii=False, indent=2)


def get_owned_tickers():
    """取得已持倉的股票列表"""
    try:
        pf = load_json(PORTFOLIO_PATH)
        return [p.get("ticker") for p in pf.get("positions", [])]
    except Exception:
        return []


def generate_signal(ticker, quote, tech, gr):
    """根據真實數據生成信號（整合持倉）"""
    if not tech or "error" in tech:
        return None

    rsi = tech["rsi"]
    price = tech["price"]
    chg = tech["change_pct"]
    regime = gr["regime"]
    min_conf = gr["min_confidence"]
    owned = get_owned_tickers()

    # 使用 finnhub_api 計算的信心度
    confidence = tech.get("confidence", 50)

    # VIX Guardrail 調整
    if regime == "DEFENSIVE":
        confidence -= 20
    elif regime == "CAUTION":
        confidence -= 10

    confidence = max(20, min(95, confidence))

    # 最終信號
    signal = tech["signal"]
    action = tech["action"]
    reasons = list(tech.get("signal_reasons", []))

    # 已持倉調整
    if ticker in owned:
        if signal == "BUY":
            signal = "HOLD"
            action = "已持有，觀望"
            confidence = 50
            reasons = [f"{ticker} 已在持倉中，不重複買入"]
        elif signal == "SELL":
            reasons.append("已持倉，考慮止盈")

    # 信心度門檻
    if signal == "BUY" and confidence < min_conf * 100:
        signal = "HOLD"
        action = "信心度不足，觀望"
        confidence = max(30, confidence)
        reasons.append(f"信心度 {confidence:.0f}% < 門檻 {min_conf*100:.0f}%")

    return {
        "ticker": ticker,
        "name": STOCK_NAMES.get(ticker, ticker),
        "signal": signal,
        "action": action,
        "confidence": round(confidence, 1),
        "price": price,
        "change_pct": chg,
        "rsi": rsi,
        "macd": tech.get("macd"),
        "macd_histogram": tech.get("macd_histogram"),
        "macd_bullish": tech.get("macd_bullish"),
        "vol_ratio": tech.get("vol_ratio"),
        "ma50": tech.get("ma50"),
        "atr": tech.get("atr"),
        "regime": regime,
        "above_ma50": tech.get("above_ma50", False),
        "reasons": reasons,
        "signal_reasons": tech.get("signal_reasons", []),
        "is_owned": ticker in owned,
        "timestamp": datetime.datetime.now().isoformat()
    }



def enrich_signal_with_profile(sig, prof):
    """合併基本面欄位到信號（缺失資料時安全跳過）"""
    if not sig or not prof or "error" in prof:
        return sig
    for key in (
        "analyst_consensus", "analyst_emoji", "analyst_rating_str", "num_analysts",
        "target_mean", "target_high", "target_low", "upside_pct",
        "earnings_date", "earnings_days", "pe_ratio", "forward_pe",
        "profit_margin_pct", "revenue_growth_pct", "earnings_growth_pct",
        "industry", "sector",
    ):
        if key in prof:
            sig[key] = prof.get(key)
    if "news" in prof:
        sig["analyst_news"] = prof.get("news", [])
    return sig


def build_opportunity_picks(quotes, tech_batch, profiles, gr):
    """
    機會掃描：產生信號但不寫入核心 signals.json / 不觸發自動入倉邏輯。
    僅將 BUY 且信心≥70、股價適合小資金者寫入 daily_report.opportunity_picks。
    """
    picks = []
    for ticker in getattr(finnhub_api, "WATCH_OPPORTUNITY", []):
        tech = tech_batch.get(ticker, {})
        if not tech or "error" in tech:
            continue
        quote = quotes.get(ticker, {})
        try:
            sig = generate_signal(ticker, quote, tech, gr)
        except Exception:
            continue
        if not sig:
            continue
        enrich_signal_with_profile(sig, profiles.get(ticker, {}))
        price = sig.get("price") or 0
        conf = sig.get("confidence") or 0
        if sig.get("signal") != "BUY":
            continue
        if conf < OPP_MIN_CONFIDENCE:
            continue
        if price <= 0 or price > OPP_MAX_PRICE:
            continue
        picks.append({
            "ticker": ticker,
            "name": sig.get("name", ticker),
            "price": price,
            "signal": sig.get("signal"),
            "confidence": conf,
            "change_pct": sig.get("change_pct"),
            "reasons": sig.get("reasons") or sig.get("signal_reasons") or [],
            "upside_pct": sig.get("upside_pct"),
            "rsi": sig.get("rsi"),
            "action": sig.get("action"),
        })
    picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return picks


def get_cached_report(max_age_minutes=30):
    """如果今日報告存在且不超過 max_age_minutes，返回緩存的報告"""
    try:
        if not os.path.exists(REPORT_PATH):
            return None
        report = load_json(REPORT_PATH)
        if report.get("date") != datetime.date.today().isoformat():
            return None
        ts = report.get("timestamp", "")
        if ts:
            try:
                report_time = datetime.datetime.fromisoformat(ts)
                age = datetime.datetime.now() - report_time
                if age.total_seconds() > max_age_minutes * 60:
                    return None
                return report
            except Exception:
                return None
        return None
    except Exception:
        return None


def analyze_day(quiet=False):
    """Execute full daily analysis"""
    if quiet:
        import io, sys as _sys
        _old = _sys.stdout
        _sys.stdout = io.StringIO()
        try:
            return _analyze_impl()
        finally:
            _sys.stdout = _old
    return _analyze_impl()


def _analyze_impl():
    """Actual analysis logic"""
    print("=" * 60)
    print("Project X — 每日分析引擎 v2")
    print(f"時間：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("數據來源：Yahoo Finance (yfinance)")
    print("=" * 60)

    print("\n1️⃣ VIX Guardrail 檢查...")
    regime, vix = finnhub_api.get_vix_regime()
    gr = vix_guardrail.check_guardrail(vix_value=vix, regime=regime)
    print(vix_guardrail.format_guardrail_report(gr))

    print("\n2️⃣ 取得真實報價（Yahoo Finance）...")
    quotes = finnhub_api.get_all_quotes()

    print("\n3️⃣ 技術指標計算...")
    tech_batch = finnhub_api.get_full_tech_batch()

    print("\n4️⃣ 基本面資料（分析師評級、目標價、業績日期）...") 
    profiles = finnhub_api.get_all_profiles()
    for ticker, prof in profiles.items():
        if "error" not in prof:
            print(f"  {prof['analyst_emoji']} {ticker}: {prof['analyst_consensus']}（{prof['num_analysts']}位分析師）")

    print("\n5️⃣ 信號生成...")
    signals = []
    all_tickers = finnhub_api.WATCH_PRIMARY + finnhub_api.WATCH_SECONDARY

    for ticker in all_tickers:
        quote = quotes.get(ticker, {})
        tech = tech_batch.get(ticker, {})
        if "error" in tech:
            print(f"  ⚠️ {ticker}: {tech['error']}")
            continue
        sig = generate_signal(ticker, quote, tech, gr)
        if sig:
            # 合併基本面資料
            prof = profiles.get(ticker, {})
            if prof and "error" not in prof:
                sig["analyst_consensus"] = prof.get("analyst_consensus", "")
                sig["analyst_emoji"] = prof.get("analyst_emoji", "")
                sig["analyst_rating_str"] = prof.get("analyst_rating_str", "")
                sig["num_analysts"] = prof.get("num_analysts", 0)
                sig["target_mean"] = prof.get("target_mean")
                sig["target_high"] = prof.get("target_high")
                sig["target_low"] = prof.get("target_low")
                sig["upside_pct"] = prof.get("upside_pct")
                sig["earnings_date"] = prof.get("earnings_date")
                sig["earnings_days"] = prof.get("earnings_days")
                sig["pe_ratio"] = prof.get("pe_ratio")
                sig["forward_pe"] = prof.get("forward_pe")
                sig["profit_margin_pct"] = prof.get("profit_margin_pct")
                sig["revenue_growth_pct"] = prof.get("revenue_growth_pct")
                sig["earnings_growth_pct"] = prof.get("earnings_growth_pct")
                sig["industry"] = prof.get("industry", "")
                sig["sector"] = prof.get("sector", "")
                sig["analyst_news"] = prof.get("news", [])
            signals.append(sig)
        sig_icon = "🟢" if sig["signal"] == "BUY" else "🔴" if sig["signal"] == "SELL" else "🟡"
        ma_arrow = "↑" if sig["above_ma50"] else "↓"
        macd_icon = "↗" if tech.get("macd_bullish") else "↘"
        vol = tech.get("vol_ratio", 1.0)
        vol_icon = "▲" if vol >= 1.2 else "▼" if vol < 0.7 else "▬"
        print(f"  {sig_icon} {ticker:4} | ${sig['price']:7.2f} | RSI:{sig['rsi']:5.1f} | MACD:{macd_icon} | vol:{vol_icon}{vol:.1f} | {sig['confidence']:3.0f}% | {sig['action']}")

    print("\n6️⃣ 機會掃描（小資金，不入核心自動邏輯）...")
    opportunity_picks = build_opportunity_picks(quotes, tech_batch, profiles, gr)
    for p in opportunity_picks:
        print(f"  💡 {p['ticker']:4} | ${p['price']:7.2f} | conf:{p['confidence']:3.0f}% | {p.get('action','')}")
    if not opportunity_picks:
        print("  （今日無符合條件的機會標的）")

    print("\n7️⃣ 保存信號記錄...")
    sig_data = load_json(SIGNALS_PATH)
    today_str = datetime.date.today().isoformat()
    # Core only — opportunity tickers stay out of signals.json / hit-rate / auto portfolio
    sig_data["signals"] = [s for s in sig_data["signals"] if s.get("date") != today_str]
    for sig in signals:
        sig["date"] = today_str
        sig_data["signals"].append(sig)
    sig_data["last_updated"] = datetime.datetime.now().isoformat()
    sig_data["vix_regime"] = gr["title"]
    sig_data["vix_value"] = round(vix, 2)
    save_json(SIGNALS_PATH, sig_data)

    print("\n8️⃣ 生成每日報告...")
    core_tickers = set(finnhub_api.WATCH_PRIMARY + finnhub_api.WATCH_SECONDARY)
    profiles_clean = {t: p for t, p in profiles.items() if "error" not in p and t in core_tickers}
    # Keep opportunity profiles available under report but not required for core dashboard profiles.json
    report = generate_report(signals, quotes, gr, vix, regime, profiles_clean, opportunity_picks=opportunity_picks)
    save_json(REPORT_PATH, report)
    save_json(os.path.join(BASE_DIR, "profiles.json"), profiles_clean)

    update_hit_rate()

    print("\n" + "=" * 60)
    print("📋 每日摘要")
    print("=" * 60)
    print(f"VIX: {vix:.2f} → {gr['title']}")
    buys = [s for s in signals if s["signal"] == "BUY"]
    holds = [s for s in signals if s["signal"] == "HOLD"]
    sells = [s for s in signals if s["signal"] == "SELL"]
    print(f"\n📡 信號摘要：")
    print(f"   買入候選：{len(buys)} 隻")
    print(f"   觀望：{len(holds)} 隻")
    print(f"   考慮止盈：{len(sells)} 隻")
    perf = sig_data["performance"]
    total = perf.get("total_signals", 0)
    if total > 0:
        print(f"\n📊 命中率：{perf.get('hit_rate_pct',0):.0f}%（{total}筆交易）")
    print(f"\n💡 機會掃描候選：{len(opportunity_picks)} 隻")
    print("\n✅ 分析完成！")
    return report


def generate_report(signals, quotes, gr, vix, regime, profiles=None, opportunity_picks=None):
    """生成完整的中文每日報告"""
    buys = [s for s in signals if s["signal"] == "BUY"]
    holds = [s for s in signals if s["signal"] == "HOLD"]
    sells = [s for s in signals if s["signal"] == "SELL"]

    spy = quotes.get("SPY", {})
    qqq = quotes.get("QQQ", {})

    report = {
        "date": datetime.date.today().isoformat(),
        "timestamp": datetime.datetime.now().isoformat(),
        "source": "Yahoo Finance (yfinance)",
        "market": {
            "vix": round(vix, 2),
            "regime": gr["title"],
            "regime_emoji": gr["emoji"],
            "spy_price": spy.get("price"),
            "spy_change": spy.get("change_pct"),
            "qqq_price": qqq.get("price"),
            "qqq_change": qqq.get("change_pct"),
        },
        "guardrail": gr,
        "signals": signals,
        "all_quotes": quotes,
        "profiles": profiles or {},
        "summary": {
            "total_stocks": len(signals),
            "buy_signals": len(buys),
            "hold_signals": len(holds),
            "sell_signals": len(sells),
        },
        "top_picks": [
            {
                "ticker": s["ticker"],
                "name": s["name"],
                "action": s["action"],
                "confidence": s["confidence"],
                "price": s["price"],
                "change_pct": s["change_pct"],
                "rsi": s["rsi"],
                "macd_bullish": s.get("macd_bullish"),
                "vol_ratio": s.get("vol_ratio"),
                "above_ma50": s.get("above_ma50"),
                "reasons": s.get("reasons", []),
                "signal_reasons": s.get("signal_reasons", []),
                "is_owned": s.get("is_owned", False),
                "analyst_emoji": (profiles or {}).get(s["ticker"], {}).get("analyst_emoji", ""),
                "analyst_consensus": (profiles or {}).get(s["ticker"], {}).get("analyst_consensus", ""),
                "upside_pct": (profiles or {}).get(s["ticker"], {}).get("upside_pct"),
                "earnings_days": (profiles or {}).get(s["ticker"], {}).get("earnings_days"),
                "earnings_date": (profiles or {}).get(s["ticker"], {}).get("earnings_date"),
            }
            for s in sorted(buys, key=lambda x: x["confidence"], reverse=True)
        ],
        "opportunity_picks": opportunity_picks or [],
        "quotes_ts": datetime.datetime.now().isoformat()
    }
    return report


def update_hit_rate():
    """更新命中率統計"""
    sig_data = load_json(SIGNALS_PATH)
    signals = sig_data.get("signals", [])
    if len(signals) < 2:
        return

    # 按日期分組
    by_date = {}
    for s in signals:
        d = s.get("date")
        if d:
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(s)

    dates = sorted(by_date.keys())
    if len(dates) < 2:
        return

    hits = partials = misses = neutrals = 0

    for i in range(len(dates) - 1):
        day_signals = by_date[dates[i]]
        next_day_signals = {s["ticker"]: s for s in by_date[dates[i + 1]]}

        for sig in day_signals:
            if sig["signal"] != "BUY":
                continue

            ticker = sig["ticker"]
            entry_price = sig["price"]

            result_sig = next_day_signals.get(ticker)
            if not result_sig:
                continue

            exit_price = result_sig.get("price", entry_price)
            pct_chg = (exit_price - entry_price) / entry_price * 100 if entry_price else 0

            if pct_chg >= 2:
                hits += 1
            elif pct_chg >= 0:
                partials += 1
            elif pct_chg <= -2:
                misses += 1
            else:
                neutrals += 1

    total = hits + partials + misses
    if total > 0:
        sig_data["performance"]["total_signals"] = total
        sig_data["performance"]["hits"] = hits
        sig_data["performance"]["partials"] = partials
        sig_data["performance"]["misses"] = misses
        sig_data["performance"]["neutrals"] = neutrals
        sig_data["performance"]["hit_rate_pct"] = round(hits / total * 100, 1)
        sig_data["performance"]["partial_rate_pct"] = round(partials / total * 100, 1)
        sig_data["performance"]["miss_rate_pct"] = round(misses / total * 100, 1)
        save_json(SIGNALS_PATH, sig_data)


if __name__ == "__main__":
    report = analyze_day()
