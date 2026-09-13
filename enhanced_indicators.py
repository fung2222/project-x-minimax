"""
Project X — 增強版指標模組
包含資深投資者建議嘅所有優化：
1. 真正 MACD Histogram 計算（修正版）
2. RSI 背馳偵測
3. 多時框分析（日線 + 週線）
4. 板塊輪動
5. 宏觀經濟指標
6. 行業特定指標
"""
import yfinance as yf
import datetime as dt
import pandas as pd


# ── 1. 真正 MACD 計算（修正版） ──

def calc_real_macd(closes, fast=12, slow=26, signal_period=9):
    """真正 MACD：EMA(12) - EMA(26)，Signal = EMA(9) of MACD"""
    closes_series = pd.Series(closes)
    ema_fast = closes_series.ewm(span=fast, adjust=False).mean()
    ema_slow = closes_series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        'macd': float(macd_line.iloc[-1]),
        'signal': float(signal_line.iloc[-1]),
        'histogram': float(histogram.iloc[-1]),
        'histogram_prev': float(histogram.iloc[-2]) if len(histogram) > 1 else 0,
        'macd_bullish': float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]),
        'histogram_rising': float(histogram.iloc[-1]) > float(histogram.iloc[-2]) if len(histogram) > 1 else False,
        'crossover': 'golden' if (float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]) and float(macd_line.iloc[-2]) <= float(signal_line.iloc[-2])) else 'death' if (float(macd_line.iloc[-1]) < float(signal_line.iloc[-1]) and float(macd_line.iloc[-2]) >= float(signal_line.iloc[-2])) else None,
        'ema_fast': float(ema_fast.iloc[-1]),
        'ema_slow': float(ema_slow.iloc[-1])
    }


# ── 2. RSI 背馳偵測 ──

def detect_rsi_divergence(closes, rsi_values, lookback=20):
    """RSI 背馳偵測：
    - 看漲背馳：股價新低，但 RSI 唔破前低 → 反轉向上信號
    - 看跌背馳：股價新高，但 RSI 唔破前高 → 反轉向下信號
    """
    if len(closes) < lookback or len(rsi_values) < lookback:
        return {'divergence': None, 'strength': 0, 'description': '數據不足'}
    recent_closes = closes[-lookback:]
    recent_rsi = rsi_values[-lookback:]
    # 找最近 5 日最低 / 最高
    mid = lookback // 2
    first_half_close = recent_closes[:mid]
    second_half_close = recent_closes[mid:]
    first_half_rsi = recent_rsi[:mid]
    second_half_rsi = recent_rsi[mid:]
    first_low = min(first_half_close)
    first_low_rsi = min(first_half_rsi)
    second_low = min(second_half_close)
    second_low_rsi = min(second_half_rsi)
    first_high = max(first_half_close)
    first_high_rsi = max(first_half_rsi)
    second_high = max(second_half_close)
    second_high_rsi = max(second_half_rsi)
    # 看漲背馳：股價新低 + RSI 唔新低
    if second_low < first_low and second_low_rsi > first_low_rsi:
        return {'divergence': 'bullish', 'strength': abs(second_low_rsi - first_low_rsi), 'description': f'看漲背馳：股價新低 ${second_low:.2f}，但 RSI 唔破前低（{second_low_rsi:.1f} > {first_low_rsi:.1f}）'}
    # 看跌背馳：股價新高 + RSI 唔新高
    if second_high > first_high and second_high_rsi < first_high_rsi:
        return {'divergence': 'bearish', 'strength': abs(first_high_rsi - second_high_rsi), 'description': f'看跌背馳：股價新高 ${second_high:.2f}，但 RSI 唔破前高（{second_high_rsi:.1f} < {first_high_rsi:.1f}）'}
    return {'divergence': None, 'strength': 0, 'description': '無背馳'}


# ── 3. 多時框分析 ──

def multi_timeframe_analysis(ticker):
    """日線 + 週線共振分析"""
    tk = yf.Ticker(ticker)
    daily = tk.history(period="3mo", interval="1d")
    weekly = tk.history(period="2y", interval="1wk")
    if daily.empty or weekly.empty or len(daily) < 26 or len(weekly) < 26:
        return {'alignment': 'unknown', 'daily_trend': None, 'weekly_trend': None}
    daily_close = daily["Close"].values
    weekly_close = weekly["Close"].values
    # 日線 MACD
    daily_macd = calc_real_macd(daily_close)
    weekly_macd = calc_real_macd(weekly_close)
    daily_bullish = daily_macd['macd_bullish']
    weekly_bullish = weekly_macd['macd_bullish']
    if daily_bullish and weekly_bullish:
        alignment = 'strong_bullish'
    elif daily_bullish and not weekly_bullish:
        alignment = 'daily_only_bullish'
    elif not daily_bullish and weekly_bullish:
        alignment = 'weekly_only_bullish'
    else:
        alignment = 'bearish'
    return {
        'alignment': alignment,
        'daily_trend': 'bullish' if daily_bullish else 'bearish',
        'weekly_trend': 'bullish' if weekly_bullish else 'bearish',
        'daily_macd_histogram': daily_macd['histogram'],
        'weekly_macd_histogram': weekly_macd['histogram']
    }


# ── 4. 板塊輪動 ──

SECTOR_ETFS = {
    'XLK': '科技',
    'XLF': '金融',
    'XLE': '能源',
    'XLV': '健康護理',
    'XLY': '非必需消費',
    'XLP': '必需消費',
    'XLI': '工業',
    'XLB': '原材料',
    'XLU': '公用事業',
    'XLRE': '房地產',
    'ARKK': '創新科技',
    'SOXX': '半導體',
}


def sector_rotation():
    """板塊輪動強度（20日回報）"""
    results = {}
    end = dt.date.today()
    start = end - dt.timedelta(days=30)
    for etf, name in SECTOR_ETFS.items():
        try:
            tk = yf.Ticker(etf)
            hist = tk.history(start=start, end=end)
            if not hist.empty and len(hist) > 1:
                first = float(hist["Close"].iloc[0])
                last = float(hist["Close"].iloc[-1])
                ret = (last - first) / first * 100
                results[name] = round(ret, 2)
        except Exception:
            pass
    return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))


# ── 5. 宏觀經濟指標 ──

MACRO_INDICATORS = {
    '^TNX': '10年期美債孳息率',
    '^IRX': '3個月美債孳息率',
    'DX-Y.NYB': '美元指數 DXY',
    'GC=F': '黃金期貨',
    'CL=F': '原油期貨',
    'BTC-USD': '比特幣',
}


def macro_indicators():
    """取得主要宏觀指標"""
    results = {}
    for symbol, name in MACRO_INDICATORS.items():
        try:
            tk = yf.Ticker(symbol)
            hist = tk.history(period="5d")
            if not hist.empty and len(hist) >= 2:
                last = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = (last - prev) / prev * 100
                results[name] = {
                    'value': round(last, 2),
                    'change_pct': round(chg, 2)
                }
        except Exception:
            pass
    return results


def get_fomc_next_date():
    """下次 FOMC 開會日（簡化版）"""
    # FOMC 2026 開會日（預定）
    return '2026-07-29'  # 暫定


# ── 6. 行業特定指標 ──

def industry_specific(ticker):
    """股票行業特定指標"""
    indicators = {}
    if ticker == 'NVDA' or ticker == 'AMD':
        # 半導體
        try:
            soxx = yf.Ticker('SOXX').history(period="5d")
            if not soxx.empty and len(soxx) >= 2:
                chg = (float(soxx["Close"].iloc[-1]) - float(soxx["Close"].iloc[-2])) / float(soxx["Close"].iloc[-2]) * 100
                indicators['半導體 ETF (SOXX) 5日變動'] = f"{chg:+.2f}%"
        except Exception:
            pass
        indicators['AI 晶片需求指標'] = 'SMCI / DELL 季度出貨量'
    elif ticker == 'TSLA':
        try:
            ark = yf.Ticker('ARKK').history(period="5d")
            if not ark.empty and len(ark) >= 2:
                chg = (float(ark["Close"].iloc[-1]) - float(ark["Close"].iloc[-2])) / float(ark["Close"].iloc[-2]) * 100
                indicators['ARKK 創新科技 5日變動'] = f"{chg:+.2f}%"
        except Exception:
            pass
        indicators['電動車交付追蹤'] = '季度報告'
    elif ticker == 'RKLB':
        indicators['太空指數追蹤'] = 'UFO / SPCE ETF'
        try:
            # SPCE 維珍銀河
            spce = yf.Ticker('SPCE').history(period="5d")
            if not spce.empty and len(spce) >= 2:
                chg = (float(spce["Close"].iloc[-1]) - float(spce["Close"].iloc[-2])) / float(spce["Close"].iloc[-2]) * 100
                indicators['SPCE 維珍銀河 5日變動'] = f"{chg:+.2f}%"
        except Exception:
            pass
    return indicators


# ── 整合：取得全部增強指標 ──

def get_enhanced_indicators(ticker):
    """單一股票嘅全部增強指標"""
    try:
        tk = yf.Ticker(ticker)
        daily = tk.history(period="3mo", interval="1d")
        if daily.empty or len(daily) < 30:
            return None
        closes = daily["Close"].values
        # RSI
        gains = [max(0, closes[-i] - closes[-i-1]) for i in range(1, 15)]
        losses = [abs(min(0, closes[-i] - closes[-i-1])) for i in range(1, 15)]
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = round(100 - (100 / (1 + rs)), 2)
        rsi_series = []
        for end_i in range(20, len(closes)):
            g = [max(0, closes[-i] - closes[-i-1]) for i in range(1, 15) if end_i - i >= 0]
            l = [abs(min(0, closes[-i] - closes[-i-1])) for i in range(1, 15) if end_i - i >= 0]
            ag = sum(g) / 14 if g else 0
            al = sum(l) / 14 if l else 0
            r = ag / al if al > 0 else 100
            rsi_series.append(round(100 - (100 / (1 + r)), 2))
        return {
            'ticker': ticker,
            'rsi': rsi,
            'macd': calc_real_macd(closes),
            'rsi_divergence': detect_rsi_divergence(closes, rsi_series),
            'multi_timeframe': multi_timeframe_analysis(ticker),
            'industry_specific': industry_specific(ticker)
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}


if __name__ == '__main__':
    # 測試
    for t in ['NVDA', 'TSLA', 'RKLB']:
        result = get_enhanced_indicators(t)
        if result:
            print(f'\n=== {t} ===')
            print(f'RSI: {result.get("rsi")}')
            print(f'MACD Histogram: {result.get("macd", {}).get("histogram")}')
            print(f'Divergence: {result.get("rsi_divergence", {}).get("divergence")}')
            print(f'Multi-TF: {result.get("multi_timeframe", {}).get("alignment")}')
            print(f'Industry: {result.get("industry_specific")}')
    print('\n=== 板塊輪動 ===')
    print(sector_rotation())
    print('\n=== 宏觀指標 ===')
    print(macro_indicators())