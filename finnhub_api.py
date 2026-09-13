"""
股價數據整合 — Project X
使用 yfinance（完全免費，無需 API Key）
實時讀取 Yahoo Finance 數據
+ Finnhub API（新聞 + 詳細分析師評級）
"""
import yfinance as yf
import json, os, datetime, requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 觀察名單（AI + 太空 + 馬斯克生態）
WATCH_PRIMARY = ["NVDA", "TSLA", "RKLB"]     # 核心3隻
WATCH_SECONDARY = ["AMD", "MSFT", "GOOGL", "META", "PLTR", "ARM"]  # 擴展觀察
WATCH_INDEX = ["SPY", "QQQ", "^VIX"]

# Finnhub API 配置
FINNHUB_CONFIG_PATH = os.path.join(BASE_DIR, "finnhub_config.json")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")


def load_finnhub_key():
    """由 config 文件或環境變數載入 Finnhub API key"""
    global FINNHUB_API_KEY
    if FINNHUB_API_KEY:
        return FINNHUB_API_KEY
    try:
        if os.path.exists(FINNHUB_CONFIG_PATH):
            cfg = json.load(open(FINNHUB_CONFIG_PATH, encoding="utf-8"))
            FINNHUB_API_KEY = cfg.get("api_key", "")
            return FINNHUB_API_KEY
    except Exception:
        pass
    return ""
ALL_TICKERS = WATCH_PRIMARY + WATCH_SECONDARY + WATCH_INDEX


def get_quote(ticker):
    """取得單一股票報價"""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")
        info = tk.info

        if hist.empty:
            return None

        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        high = float(hist["High"].iloc[-1])
        low = float(hist["Low"].iloc[-1])
        volume = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
        change_pct = round(((price - prev) / prev) * 100, 2)

        return {
            "symbol": ticker,
            "price": round(price, 2),
            "change": round(price - prev, 2),
            "change_pct": change_pct,
            "high": round(high, 2),
            "low": round(low, 2),
            "open": round(float(hist["Open"].iloc[-1]), 2),
            "prev_close": round(prev, 2),
            "volume": volume,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "source": "yfinance",
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        return {"symbol": ticker, "error": str(e)}


def get_all_quotes():
    """一次過取得所有股票報價"""
    result = {}
    for ticker in ALL_TICKERS:
        q = get_quote(ticker)
        if q:
            result[ticker] = q
    return result


def get_vix_regime():
    """根據 VIX 水準返回市場狀態"""
    vix_data = get_quote("^VIX")
    if not vix_data or "error" in vix_data:
        return "NORMAL", 18.0

    vix = vix_data["price"]

    if vix < 20:
        regime = "NORMAL"
    elif vix < 30:
        regime = "CAUTION"
    else:
        regime = "DEFENSIVE"

    return regime, vix


def get_tech_indicators(ticker):
    """計算簡單技術指標"""
    try:
        tk = yf.Ticker(ticker)
        # 取最近 20 個交易日
        hist = tk.history(period="1mo")

        if hist.empty or len(hist) < 15:
            return None

        closes = hist["Close"].values
        highs = hist["High"].values
        lows = hist["Low"].values
        volumes = hist["Volume"].values if "Volume" in hist.columns else [1000000] * len(closes)

        # 現價
        price = closes[-1]

        # ── RSI (14日) ──────────────────────────────────────────────
        gains = []
        losses = []
        for i in range(1, min(15, len(closes))):
            diff = closes[-i] - closes[-i-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(abs(diff) if diff < 0 else 0)
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = round(100 - (100 / (1 + rs)), 1)

        # ── MACD (12 EMA / 26 EMA / Signal 9) ─────────────────────
        def ema(data, period):
            k = 2 / (period + 1)
            ema_val = data[0]
            for d in data[1:]:
                ema_val = d * k + ema_val * (1 - k)
            return ema_val

        ema12 = ema(closes, 12) if len(closes) >= 12 else closes[-1]
        ema26 = ema(closes, 26) if len(closes) >= 26 else closes[-1]
        macd_line = ema12 - ema26
        # Signal line = 9-period EMA of MACD (simplified: use last 9 closes)
        signal_val = macd_line * 0.8  # simplified fallback
        if len(closes) >= 9:
            macd_hist_vals = []
            for i in range(9):
                e12 = ema(closes[:len(closes)-i], 12) if len(closes[:len(closes)-i]) >= 12 else closes[0]
                e26 = ema(closes[:len(closes)-i], 26) if len(closes[:len(closes)-i]) >= 26 else closes[0]
                macd_hist_vals.append(e12 - e26)
            signal_val = ema(macd_hist_vals, 9) if len(macd_hist_vals) >= 9 else sum(macd_hist_vals)/len(macd_hist_vals)
        macd_histogram = round(macd_line - signal_val, 4)
        macd_bullish = macd_histogram > 0  # MACD above signal = bullish

        # ── 成交量確認 ──────────────────────────────────────────────
        avg_vol = sum(volumes[-20:]) / min(20, len(volumes)) if len(volumes) >= 5 else sum(volumes)/len(volumes)
        vol_ratio = round(volumes[-1] / avg_vol, 2) if avg_vol > 0 else 1.0
        vol_confirmed = vol_ratio >= 0.8  # Volume at least 80% of average

        # ── 50日均線 ──────────────────────────────────────────────
        ma50 = sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 50 else sum(closes) / len(closes)

        # ── ATR 估算 ──────────────────────────────────────────────
        trs = []
        for i in range(1, min(15, len(closes))):
            hl = highs[-i] - lows[-i]
            hc = abs(highs[-i] - closes[-i-1])
            lc = abs(lows[-i] - closes[-i-1])
            trs.append(max(hl, hc, lc))
        atr = round(sum(trs) / len(trs), 2) if trs else round(price * 0.02, 2)

        # 方向
        price_vs_ma = price - ma50
        regime = "bullish" if price_vs_ma > 0 else "bearish"

        # ── 信號生成（含 MACD + 成交量確認）───────────────────────
        signal = "HOLD"
        action = "觀望"
        confidence = 50
        signal_reasons = []

        # RSI 評估
        if rsi < 30:
            signal = "BUY"
            action = "超賣區域，強烈買入信號"
            confidence = min(90, 70 + (30 - rsi) * 2)
            signal_reasons.append(f"RSI {rsi:.0f} 超賣")
        elif rsi < 40:
            signal = "BUY"
            action = "偏低，買入機會"
            confidence = min(80, 60 + (40 - rsi))
            signal_reasons.append(f"RSI {rsi:.0f} 偏低")
        elif rsi < 45:
            signal = "HOLD"
            action = "中性偏低，觀望"
            confidence = 55
            signal_reasons.append(f"RSI {rsi:.0f} 中性")
        elif rsi > 75:
            signal = "SELL"
            action = "嚴重超買，止盈"
            confidence = min(90, 60 + (rsi - 75) * 2)
            signal_reasons.append(f"RSI {rsi:.0f} 嚴重超買")
        elif rsi > 68:
            signal = "SELL"
            action = "超買，考慮止盈"
            confidence = min(80, 55 + (rsi - 68))
            signal_reasons.append(f"RSI {rsi:.0f} 超買")
        elif rsi > 62:
            signal = "HOLD"
            action = "偏高，觀望"
            confidence = 55
            signal_reasons.append(f"RSI {rsi:.0f} 偏高")
        else:
            confidence = 50
            signal_reasons.append(f"RSI {rsi:.0f} 中性")

        # MACD 調整（MACD 高於信號線 = 額外確認）
        if macd_bullish and signal == "BUY":
            confidence = min(95, confidence + 8)
            signal_reasons.append("MACD 看漲確認")
        elif not macd_bullish and signal == "BUY":
            confidence = max(35, confidence - 10)
            signal_reasons.append("⚠️ MACD 尚在看跌")
        elif not macd_bullish and signal == "SELL":
            confidence = min(95, confidence + 5)
            signal_reasons.append("MACD 看跌確認")

        # 成交量調整
        if vol_ratio >= 1.2 and signal == "BUY":
            confidence = min(95, confidence + 5)
            signal_reasons.append(f"放量確認 (vol×{vol_ratio:.1f})")
        elif vol_ratio < 0.5 and signal == "BUY":
            confidence = max(30, confidence - 8)
            signal_reasons.append("⚠️ 成交量不足")

        # MA50 調整
        if price > ma50 and signal == "BUY":
            confidence = min(95, confidence + 5)
            signal_reasons.append("價格高於 MA50")
        elif price < ma50 and signal == "BUY":
            confidence = max(30, confidence - 5)
            signal_reasons.append("⚠️ 價格低於 MA50")

        # PLTR 特殊調整
        if ticker == "PLTR" and signal == "BUY":
            confidence = min(confidence, 75)
            action = action + "（PLTR波動大，控制注碼）"

        # 低VIX環境加成
        confidence = min(95, confidence + 5)

        return {
            "symbol": ticker,
            "price": round(price, 2),
            "rsi": rsi,
            "macd": round(macd_line, 4),
            "macd_signal": round(signal_val, 4),
            "macd_histogram": macd_histogram,
            "macd_bullish": macd_bullish,
            "vol_ratio": vol_ratio,
            "vol_confirmed": vol_confirmed,
            "ma50": round(ma50, 2),
            "atr": atr,
            "signal": signal,
            "action": action,
            "confidence": confidence,
            "regime": regime,
            "above_ma50": price > ma50,
            "change_pct": round(((price - closes[-2]) / closes[-2]) * 100, 2) if len(closes) > 1 else 0,
            "signal_reasons": signal_reasons,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        return {"symbol": ticker, "error": str(e)}


def get_full_tech_batch():
    """一次過計算所有股票的技術指標"""
    results = {}
    for ticker in WATCH_PRIMARY + WATCH_SECONDARY:
        results[ticker] = get_tech_indicators(ticker)
    return results


def get_market_snapshot():
    """取得完整市場快照"""
    quotes = get_all_quotes()
    regime, vix = get_vix_regime()

    snapshot = {
        "timestamp": datetime.datetime.now().isoformat(),
        "vix": {"value": vix, "regime": regime},
        "indices": {},
        "stocks": {},
        "regime_changed": False
    }

    for t in WATCH_INDEX:
        if t in quotes:
            snapshot["indices"][t] = quotes[t]

    for t in WATCH_PRIMARY + WATCH_SECONDARY:
        if t in quotes:
            snapshot["stocks"][t] = quotes[t]

    return snapshot


def get_stock_profile(ticker):
    """取得基本面資料（分析師評級、目標價、業績日期、新聞）"""
    import datetime as dt
    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        # 分析師評級（簡化顯示）
        rec_key = info.get("recommendationKey", "")
        rec_map = {
            "strong_buy": ("強烈買入", "🟢"),
            "buy": ("買入", "🟢"),
            "hold": ("觀望", "🟡"),
            "sell": ("賣出", "🔴"),
            "strong_sell": ("強烈賣出", "🔴"),
        }
        rec_label, rec_emoji = rec_map.get(rec_key, ("未知", "⚪"))
        num_analysts = info.get("numberOfAnalystOpinions", 0) or 0

        # 目標價
        current = info.get("currentPrice") or info.get("regularMarketPrice")
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        upside = None
        if current and target_mean:
            upside = round((target_mean - current) / current * 100, 1)

        # 業績日期
        earn_ts = info.get("earningsTimestamp")
        earnings_date = None
        earnings_days = None
        if earn_ts:
            earn_dt = dt.datetime.fromtimestamp(earn_ts, tz=dt.timezone.utc)
            earnings_date = earn_dt.strftime("%Y-%m-%d")
            now = dt.datetime.now(dt.timezone.utc)
            delta = earn_dt - now
            earnings_days = delta.days
            if earnings_days < 0:
                earnings_days = None  # 已過期不顯示
                earnings_date = None

        # 估值指標（新手友好）
        pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        profit_margin = info.get("profitMargins")
        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")

        # 行業
        industry = info.get("industry", "")
        sector = info.get("sector", "")

        # 新聞（保留英文真實標題 + 中文 sentiment 分析 + 中文章節描述）
        news_list = []
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=72)
        for item in (tk.news or [])[:8]:
            content = item.get("content", {})
            title = content.get("title", "")
            summary = content.get("summary", "")
            pub_str = content.get("pubDate", "")
            if not title:
                continue
            # Sentiment 分析（基於真實標題 + 摘要）
            title_lower = (title + " " + summary).lower()
            sentiment_score = 0
            positive_keywords = ["beat", "surge", "jump", "soar", "rally", "buy", "bull", "upgrade",
                                 "growth", "profit", "record", "high", "strong", "win", "gain", "boost",
                                 "rise", "climb", "advance", "outperform"]
            negative_keywords = ["miss", "fall", "drop", "crash", "downgrade", "sell", "bear", "concern",
                                 "loss", "low", "weak", "decline", "cut", "warn", "fear", "risk",
                                 "slump", "tumble", "sink", "plunge", "underperform"]
            for kw in positive_keywords:
                if kw in title_lower:
                    sentiment_score += 1
            for kw in negative_keywords:
                if kw in title_lower:
                    sentiment_score -= 1
            sentiment_label = "利好" if sentiment_score > 0 else "利淡" if sentiment_score < 0 else "中性"
            sentiment_emoji = "🟢" if sentiment_score > 0 else "🔴" if sentiment_score < 0 else "⚪"
            # 中文章節描述（保留真實英文標題 + 中文一句解讀）
            ticker_zh = {
                "NVDA": "英偉達", "AMD": "AMD超微", "MSFT": "微軟", "GOOGL": "谷歌",
                "META": "Meta", "AMZN": "亞馬遜", "PLTR": "Palantir",
                "ARM": "ARM", "TSLA": "特斯拉", "RKLB": "Rocket Lab"
            }.get(ticker, ticker)
            if sentiment_score > 0:
                desc_zh = f"{ticker_zh} 相關利好消息"
            elif sentiment_score < 0:
                desc_zh = f"{ticker_zh} 相關負面消息"
            else:
                # 主題分類
                if any(k in title_lower for k in ["earnings", "revenue", "profit", "guidance", "quarter"]):
                    desc_zh = f"{ticker_zh} 業績／財務相關"
                elif any(k in title_lower for k in ["ai", "chip", "gpu", "data"]):
                    desc_zh = f"{ticker_zh} AI／晶片板塊"
                elif any(k in title_lower for k in ["space", "rocket", "launch", "satellite"]):
                    desc_zh = f"{ticker_zh} 太空業務"
                elif any(k in title_lower for k in ["musk", "tesla", "robotaxi", "cybertruck"]):
                    desc_zh = f"{ticker_zh} 馬斯克／電車"
                else:
                    desc_zh = f"{ticker_zh} 市場動態"
            pub_date = None
            try:
                pub_dt = dt.datetime.fromisoformat(pub_str.replace("Z", "+00:00")).replace(tzinfo=dt.timezone.utc)
                if pub_dt < cutoff:
                    continue
                pub_date = pub_dt.strftime("%m/%d")
            except Exception:
                pass
            news_list.append({
                "title": title[:120],  # 保留英文真實標題
                "title_en": title[:120],
                "desc_zh": desc_zh,  # 中文一句解讀
                "sentiment": sentiment_label,
                "sentiment_emoji": sentiment_emoji,
                "sentiment_score": sentiment_score,
                "date": pub_date
            })
            if len(news_list) >= 3:
                break

        return {
            "symbol": ticker,
            "analyst_consensus": rec_label,
            "analyst_emoji": rec_emoji,
            "recommendation_key": rec_key,
            "num_analysts": num_analysts,
            "analyst_rating_str": f"{rec_emoji} {rec_label}（{num_analysts}位分析師）",
            "current_price": current,
            "target_mean": target_mean,
            "target_high": target_high,
            "target_low": target_low,
            "upside_pct": upside,
            "earnings_date": earnings_date,
            "earnings_days": earnings_days,
            "pe_ratio": round(pe, 1) if pe else None,
            "forward_pe": round(forward_pe, 1) if forward_pe else None,
            "profit_margin_pct": round(profit_margin * 100, 1) if profit_margin else None,
            "revenue_growth_pct": round(revenue_growth * 100, 1) if revenue_growth else None,
            "earnings_growth_pct": round(earnings_growth * 100, 1) if earnings_growth else None,
            "industry": industry,
            "sector": sector,
            "news": news_list,
            "timestamp": dt.datetime.now().isoformat()
        }
    except Exception as e:
        return {"symbol": ticker, "error": str(e)}


def get_all_profiles():
    """一次過取得所有股票的基本面資料"""
    result = {}
    for ticker in WATCH_PRIMARY + WATCH_SECONDARY:
        p = get_stock_profile(ticker)
        if p:
            result[ticker] = p
    return result


# ── FINNHUB API 整合 ──

def fetch_finnhub_company_news(ticker, days_back=3):
    """Finnhub 公司新聞（真實新聞 + sentiment + 中文分類）"""
    key = load_finnhub_key()
    if not key:
        return []
    try:
        end = datetime.date.today()
        start = end - datetime.timedelta(days=days_back)
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start}&to={end}&token={key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        news = resp.json()
        result = []
        ticker_zh = {
            "NVDA": "英偉達", "AMD": "AMD超微", "MSFT": "微軟", "GOOGL": "谷歌",
            "META": "Meta", "AMZN": "亞馬遜", "PLTR": "Palantir",
            "ARM": "ARM", "TSLA": "特斯拉", "RKLB": "Rocket Lab"
        }.get(ticker, ticker)
        for item in news[:5]:
            headline = item.get("headline", "")
            summary = item.get("summary", "")
            source = item.get("source", "")
            dt_ts = item.get("datetime", 0)
            pub_date = datetime.datetime.fromtimestamp(dt_ts).strftime("%m/%d") if dt_ts else ""
            url_link = item.get("url", "")
            # Finnhub 唔提供 sentiment 分數，用關鍵詞推斷
            sentiment_score = 0
            text_lower = (headline + " " + summary).lower()
            positive_keywords = ["beat", "surge", "jump", "soar", "rally", "upgrade", "growth",
                                 "record", "high", "strong", "win", "gain", "boost", "rise", "outperform"]
            negative_keywords = ["miss", "fall", "drop", "crash", "downgrade", "concern",
                                 "loss", "low", "weak", "decline", "cut", "warn", "fear", "slump", "plunge"]
            for kw in positive_keywords:
                if kw in text_lower:
                    sentiment_score += 1
            for kw in negative_keywords:
                if kw in text_lower:
                    sentiment_score -= 1
            sentiment_label = "利好" if sentiment_score > 0 else "利淡" if sentiment_score < 0 else "中性"
            sentiment_emoji = "🟢" if sentiment_score > 0 else "🔴" if sentiment_score < 0 else "⚪"
            # 中文章節分類
            if sentiment_score > 0:
                desc_zh = f"{ticker_zh} 相關利好消息"
            elif sentiment_score < 0:
                desc_zh = f"{ticker_zh} 相關負面消息"
            else:
                if any(k in text_lower for k in ["earnings", "revenue", "profit", "guidance", "quarter"]):
                    desc_zh = f"{ticker_zh} 業績／財務相關"
                elif any(k in text_lower for k in ["ai", "chip", "gpu", "data"]):
                    desc_zh = f"{ticker_zh} AI／晶片板塊"
                elif any(k in text_lower for k in ["space", "rocket", "launch", "satellite"]):
                    desc_zh = f"{ticker_zh} 太空業務"
                elif any(k in text_lower for k in ["musk", "tesla", "robotaxi", "cybertruck"]):
                    desc_zh = f"{ticker_zh} 馬斯克／電車"
                else:
                    desc_zh = f"{ticker_zh} 市場動態"
            result.append({
                "title": headline,
                "summary": summary[:200],
                "source": source,
                "date": pub_date,
                "url": url_link,
                "sentiment": sentiment_label,
                "sentiment_emoji": sentiment_emoji,
                "sentiment_score": sentiment_score,
                "desc_zh": desc_zh,
                "provider": "finnhub"
            })
        return result
    except Exception as e:
        return []


def fetch_finnhub_recommendation(ticker):
    """Finnhub 分析師推薦詳細分佈"""
    key = load_finnhub_key()
    if not key:
        return None
    try:
        url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        latest = data[0]
        return {
            "period": latest.get("period"),
            "strong_buy": latest.get("strongBuy", 0),
            "buy": latest.get("buy", 0),
            "hold": latest.get("hold", 0),
            "sell": latest.get("sell", 0),
            "strong_sell": latest.get("strongSell", 0),
            "total": sum([latest.get(k, 0) for k in ["strongBuy", "buy", "hold", "sell", "strongSell"]])
        }
    except Exception:
        return None


def fetch_finnhub_company_news_general(category="general", count=10):
    """Finnhub 通用市場新聞"""
    key = load_finnhub_key()
    if not key:
        return []
    try:
        url = f"https://finnhub.io/api/v1/news?category={category}&token={key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        news = resp.json()[:count]
        result = []
        for item in news:
            headline = item.get("headline", "")
            summary = item.get("summary", "")
            source = item.get("source", "")
            dt_ts = item.get("datetime", 0)
            pub_date = datetime.datetime.fromtimestamp(dt_ts).strftime("%m/%d %H:%M") if dt_ts else ""
            url_link = item.get("url", "")
            result.append({
                "title": headline,
                "summary": summary[:150],
                "source": source,
                "date": pub_date,
                "url": url_link,
                "category": category,
                "provider": "finnhub"
            })
        return result
    except Exception:
        return []


# ── MARKETAUX API 整合 ──

MARKETAUX_CONFIG_PATH = os.path.join(BASE_DIR, "marketaux_config.json")
MARKETAUX_API_KEY = os.environ.get("MARKETAUX_API_KEY", "")


def load_marketaux_key():
    """由 config 文件或環境變數載入 Marketaux API key"""
    global MARKETAUX_API_KEY
    if MARKETAUX_API_KEY:
        return MARKETAUX_API_KEY
    try:
        if os.path.exists(MARKETAUX_CONFIG_PATH):
            cfg = json.load(open(MARKETAUX_CONFIG_PATH, encoding="utf-8"))
            MARKETAUX_API_KEY = cfg.get("api_key", "")
            return MARKETAUX_API_KEY
    except Exception:
        pass
    return ""


def fetch_marketaux_news(ticker, limit=5, days_back=3):
    """Marketaux 新聞（真實新聞 + sentiment 標註）"""
    key = load_marketaux_key()
    if not key:
        return []
    try:
        end = datetime.date.today().isoformat()
        start = (datetime.date.today() - datetime.timedelta(days=days_back)).isoformat()
        url = (
            f"https://api.marketaux.com/v1/news/all"
            f"?symbols={ticker}&language=en"
            f"&published_after={start}&published_before={end}"
            f"&filter_entities=true"
            f"&limit={limit}"
            f"&api_token={key}"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        result = []
        for item in data.get("data", []):
            title = item.get("title", "")
            description = item.get("description", "")
            source = item.get("source", "")
            url_link = item.get("url", "")
            published = item.get("published_at", "")[:10]
            # Marketaux sentiment
            sentiment_score = item.get("sentiment", 0)
            if sentiment_score is None:
                sentiment_score = 0
            sentiment_label = "利好" if sentiment_score > 0.1 else "利淡" if sentiment_score < -0.1 else "中性"
            sentiment_emoji = "🟢" if sentiment_score > 0.1 else "🔴" if sentiment_score < -0.1 else "⚪"
            # Entities（識別到嘅股票）
            entities = [e.get("symbol") for e in item.get("entities", []) if e.get("symbol")]
            result.append({
                "title": title[:150],
                "summary": description[:200] if description else "",
                "source": source,
                "date": published,
                "url": url_link,
                "sentiment_score": sentiment_score,
                "sentiment": sentiment_label,
                "sentiment_emoji": sentiment_emoji,
                "entities": entities[:5],
                "provider": "marketaux"
            })
        return result
    except Exception as e:
        return []


def fetch_marketaux_market_overview(limit=10):
    """Marketaux 通用市場新聞"""
    key = load_marketaux_key()
    if not key:
        return []
    try:
        url = (
            f"https://api.marketaux.com/v1/news/all"
            f"?language=en&filter_entities=true&limit={limit}&api_token={key}"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        result = []
        for item in data.get("data", []):
            title = item.get("title", "")
            source = item.get("source", "")
            published = item.get("published_at", "")[:10]
            entities = [e.get("symbol") for e in item.get("entities", []) if e.get("symbol")]
            sentiment_score = item.get("sentiment") or 0
            result.append({
                "title": title[:150],
                "source": source,
                "date": published,
                "entities": entities[:5],
                "sentiment_score": sentiment_score,
                "provider": "marketaux"
            })
        return result
    except Exception:
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("Project X — 真實市場數據測試")
    print("=" * 60)

    regime, vix = get_vix_regime()
    print(f"\nVIX: {vix:.2f} → {regime}")

    print("\n📊 觀察股票：")
    for ticker in WATCH_PRIMARY:
        q = get_quote(ticker)
        if q and "error" not in q:
            print(f"  {ticker:6} ${q['price']:8.2f}  {q['change_pct']:+.2f}%  {q.get('name','')}")
        t = get_tech_indicators(ticker)
        if t and "error" not in t:
            sig_emoji = "🟢" if t["signal"] == "BUY" else "🔴" if t["signal"] == "SELL" else "🟡"
            print(f"         RSI:{t['rsi']:5.1f}  {sig_emoji} {t['signal']}  信心:{t['confidence']:.0f}%")

    print("\n📈 指數：")
    for ticker in WATCH_INDEX:
        q = get_quote(ticker)
        if q and "error" not in q:
            print(f"  {ticker:6} ${q['price']:8.2f}  {q['change_pct']:+.2f}%")
