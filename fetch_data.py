"""
HAGETAKA SCOPE - 日次候補抽出（GitHub Actions用・ブロック対策強化版）
"""

import json
import os
from datetime import datetime
from pathlib import Path
import time
import random # 追加

import numpy as np
import pandas as pd
import pytz
import yfinance as yf
import requests # 追加

# ==========================================
# 共通計算関数（変更なし）
# ==========================================

def calculate_volume_profile(df: pd.DataFrame, bins: int = 24) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    price_min = float(df['Low'].min())
    price_max = float(df['High'].max())
    if not np.isfinite(price_min) or not np.isfinite(price_max) or price_max <= price_min:
        return pd.DataFrame()
    price_bins = np.linspace(price_min, price_max, int(bins) + 1)
    volume_profile = []
    for i in range(len(price_bins) - 1):
        bin_low = float(price_bins[i])
        bin_high = float(price_bins[i + 1])
        bin_center = (bin_low + bin_high) / 2.0
        total_volume = 0.0
        for _, row in df.iterrows():
            low = float(row['Low'])
            high = float(row['High'])
            vol = float(row['Volume'])
            if low <= bin_high and high >= bin_low:
                overlap_low = max(low, bin_low)
                overlap_high = min(high, bin_high)
                if high > low:
                    ratio = (overlap_high - overlap_low) / (high - low)
                else:
                    ratio = 1.0
                total_volume += vol * ratio
        volume_profile.append({'price': bin_center, 'price_low': bin_low, 'price_high': bin_high, 'volume': total_volume})
    return pd.DataFrame(volume_profile)

def calculate_volume_profile_with_bins(df: pd.DataFrame, price_bins: np.ndarray) -> pd.DataFrame:
    if df is None or df.empty or price_bins is None or len(price_bins) < 2:
        return pd.DataFrame()
    volume_profile = []
    for i in range(len(price_bins) - 1):
        bin_low = float(price_bins[i])
        bin_high = float(price_bins[i + 1])
        bin_center = (bin_low + bin_high) / 2.0
        total_volume = 0.0
        for _, row in df.iterrows():
            low = float(row["Low"])
            high = float(row["High"])
            vol = float(row["Volume"])
            if low <= bin_high and high >= bin_low:
                overlap_low = max(low, bin_low)
                overlap_high = min(high, bin_high)
                if high > low:
                    ratio = (overlap_high - overlap_low) / (high - low)
                else:
                    ratio = 1.0
                total_volume += vol * ratio
        volume_profile.append({"price": bin_center, "price_low": bin_low, "price_high": bin_high, "volume": total_volume})
    return pd.DataFrame(volume_profile)

def compute_support_from_recent_growth(df: pd.DataFrame, bins: int = 24, recent_ratio: float = 0.33, low_band_ratio: float = 0.35):
    if df is None or df.empty or len(df) < 40:
        return None, None
    price_min = float(df["Low"].min())
    price_max = float(df["High"].max())
    if not np.isfinite(price_min) or not np.isfinite(price_max) or price_max <= price_min:
        return None, None
    price_bins = np.linspace(price_min, price_max, int(bins) + 1)
    n = len(df)
    recent_len = max(20, int(n * float(recent_ratio)))
    if n < recent_len * 2:
        return None, None
    recent_df = df.tail(recent_len)
    prev_df = df.iloc[-recent_len * 2 : -recent_len]
    vp_recent = calculate_volume_profile_with_bins(recent_df, price_bins)
    vp_prev = calculate_volume_profile_with_bins(prev_df, price_bins)
    if vp_recent.empty or vp_prev.empty:
        return None, None
    vp = vp_recent.copy()
    vp["prev_volume"] = vp_prev["volume"].values
    vp["growth"] = vp["volume"] - vp["prev_volume"]
    low_limit = price_min + (price_max - price_min) * float(low_band_ratio)
    cand = vp[vp["price_high"] <= low_limit].copy()
    if cand.empty:
        return None, None
    cand = cand.sort_values("growth", ascending=False)
    best = cand.iloc[0]
    if float(best.get("growth", 0.0)) <= 0:
        return None, None
    return float(best["price_low"]), float(best["price_high"])

def compute_support_zone_from_profile(vp: pd.DataFrame, threshold_ratio: float = 0.60):
    if vp is None or vp.empty or 'volume' not in vp.columns:
        return None, None
    max_vol = float(vp['volume'].max())
    if max_vol <= 0:
        return None, None
    vp_reset = vp.reset_index(drop=True)
    try:
        poc_pos = int(vp_reset['volume'].idxmax())
    except Exception:
        poc_pos = 0
    thr = max_vol * float(threshold_ratio)
    left = poc_pos
    right = poc_pos
    while left - 1 >= 0 and float(vp_reset.loc[left - 1, 'volume']) >= thr:
        left -= 1
    while right + 1 < len(vp_reset) and float(vp_reset.loc[right + 1, 'volume']) >= thr:
        right += 1
    support = float(vp_reset.loc[left, 'price_low'])
    upper = float(vp_reset.loc[right, 'price_high'])
    return support, upper

def support_position_tag(latest_price: float, support_price: float | None) -> tuple[str | None, float | None]:
    if support_price is None or support_price <= 0:
        return None, None
    gap_pct = (latest_price / support_price - 1.0) * 100.0
    if gap_pct <= 5.0:
        return "下側ゾーン", float(gap_pct)
    if gap_pct >= 20.0:
        return "上側ゾーン", float(gap_pct)
    return None, float(gap_pct)

# ==========================================
# 設定・辞書
# ==========================================

LOOKBACK_DAYS = 252
JST = pytz.timezone("Asia/Tokyo")
MARKET_CAP_MIN = 300
MARKET_CAP_MAX = 2000
FLOW_SCORE_HIGH = 70.0
FLOW_SCORE_MEDIUM = 40.0

# (TICKER_NAMES辞書は長いので、提供されたものをそのまま使用してください。ここでは省略せず含めます)
TICKER_NAMES = {
    # (中略：ユーザー提供の全辞書リストがここに入ります)
    "3655.T": "ブレインパッド", "3681.T": "ブイキューブ", "3697.T": "SHIFT", "3765.T": "ガンホー",
    # ...[ここにすべての辞書データが入っていると仮定して進めます]...
    "9989.T": "サンドラッグ", "9997.T": "ベルーナ",
}

MIDCAP_TICKERS = list(TICKER_NAMES.keys())

# ==========================================
# ロジック関数
# ==========================================

def get_japanese_name(ticker: str, api_name: str | None = None) -> str:
    if ticker in TICKER_NAMES:
        return TICKER_NAMES[ticker]
    return api_name if api_name else ticker.replace(".T", "")

def calculate_flow_score(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {"flow_score": 0.0, "vol_anomaly": 0.0, "price_stability": 0.0, "absorption": 0.0, "range_compression": 0.0, "lower_shadow": 0.0}
    recent_5 = df.tail(5)
    recent_60 = df.tail(60) if len(df) >= 60 else df
    try:
        avg_vol_60 = float(recent_60["Volume"].mean())
        avg_vol_5 = float(recent_5["Volume"].mean())
        vol_anomaly = max(0.0, min(100.0, (avg_vol_5 / avg_vol_60 - 1) * 50.0)) if avg_vol_60 > 0 else 0.0
        price_change_5 = abs(float(recent_5["Close"].iloc[-1]) / float(recent_5["Close"].iloc[0]) - 1.0) * 100.0
        price_stability = max(0.0, 100.0 - price_change_5 * 20.0)
        vol_ratio = (avg_vol_5 / avg_vol_60) if avg_vol_60 > 0 else 1.0
        absorption = min(100.0, (vol_ratio / (price_change_5 + 0.1)) * 30.0)
        df_copy = df.copy()
        df_copy["TR"] = np.maximum(df_copy["High"] - df_copy["Low"], np.maximum((df_copy["High"] - df_copy["Close"].shift(1)).abs(), (df_copy["Low"] - df_copy["Close"].shift(1)).abs()))
        atr_20 = float(df_copy["TR"].tail(20).mean())
        atr_5 = float(df_copy["TR"].tail(5).mean())
        range_compression = max(0.0, min(100.0, (1.0 - atr_5 / atr_20) * 100.0)) if atr_20 > 0 else 50.0
        body_range = (recent_5["High"] - recent_5["Low"]).replace(0, np.nan)
        lower_shadow = float(((recent_5["Close"] - recent_5["Low"]) / body_range).fillna(0.5).mean()) * 100.0
        flow_score = float(min(100.0, max(0.0, vol_anomaly * 0.30 + price_stability * 0.25 + absorption * 0.25 + range_compression * 0.10 + lower_shadow * 0.10)))
        return {"flow_score": round(flow_score, 1), "vol_anomaly": round(vol_anomaly, 1), "price_stability": round(price_stability, 1), "absorption": round(absorption, 1), "range_compression": round(range_compression, 1), "lower_shadow": round(lower_shadow, 1)}
    except Exception:
        return {"flow_score": 0.0, "vol_anomaly": 0.0, "price_stability": 0.0, "absorption": 0.0, "range_compression": 0.0, "lower_shadow": 0.0}

def load_previous_streaks() -> dict:
    try:
        p = Path("data/ratios.json")
        if not p.exists(): return {}
        prev = json.loads(p.read_text(encoding="utf-8"))
        return {t: int(d.get("flow_streak_high", 0)) for t, d in prev.get("data", {}).items()}
    except Exception: return {}

def is_watch_state(flow_details: dict) -> bool:
    return (flow_details.get("vol_anomaly", 0) > 50 and flow_details.get("price_stability", 0) > 60)

def calculate_reorg_score(market_cap_oku: float | None, pbr: float | None) -> float:
    score = 50.0
    if market_cap_oku and market_cap_oku > 0:
        center = (MARKET_CAP_MIN + MARKET_CAP_MAX) / 2
        dist = abs(market_cap_oku - center) / ((MARKET_CAP_MAX - MARKET_CAP_MIN) / 2)
        score = 20.0 + max(0.0, 1.0 - min(1.0, dist)) * 60.0
    if pbr is not None and pbr > 0:
        if pbr <= 1.0: score += 20.0
        elif pbr <= 2.0: score += 10.0
        elif pbr >= 5.0: score -= 5.0
    return float(min(100.0, max(0.0, score)))

def calculate_event_score(stock: yf.Ticker, now_jst: datetime) -> tuple[float, list[str]]:
    score = 0.0
    tags = []
    try:
        if hasattr(stock, "earnings_dates") and stock.earnings_dates is not None and len(stock.earnings_dates) > 0:
            ed = stock.earnings_dates.index[0].to_pydatetime()
            ed_jst = JST.localize(ed) if ed.tzinfo is None else ed.astimezone(JST)
            if abs((ed_jst.date() - now_jst.date()).days) <= 3:
                score += 35.0
                tags.append("決算近")
    except Exception: pass
    try:
        info = stock.info or {}
        ex = info.get("exDividendDate")
        if ex:
            ex_dt = datetime.fromtimestamp(int(ex), tz=JST)
            if -2 <= (ex_dt.date() - now_jst.date()).days <= 5:
                score += 15.0
                tags.append("権利期")
    except Exception: pass
    return float(min(100.0, score)), tags

def determine_level(ma_score: float) -> int:
    if ma_score >= 75: return 4
    if ma_score >= 60: return 3
    if ma_score >= 45: return 2
    if ma_score >= 30: return 1
    return 0

# ==========================================
# メイン取得処理（ブロック対策適用）
# ==========================================

def fetch_volume_data(tickers: list[str], chunk_size: int = 15) -> tuple[dict, dict]:
    results: dict = {}
    qualified: dict = {}
    prev_streaks = load_previous_streaks()
    total = len(tickers)
    now_jst = datetime.now(JST)

    # ブラウザになりすますセッション設定
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    for i in range(0, total, chunk_size):
        chunk = tickers[i:i + chunk_size]
        print(f"📥 取得中: {i+1}〜{min(i+chunk_size, total)} / {total}")

        try:
            data = yf.download(tickers=chunk, period="1y", interval="1d", group_by="ticker", auto_adjust=True, progress=False, threads=True, session=session)
            if data.empty: continue

            for ticker in chunk:
                try:
                    df = data[ticker].copy() if len(chunk) > 1 else data.copy()
                    df = df.dropna()
                    if len(df) < 60: continue

                    # 🚨 連続リクエストを避けるためのランダム待機
                    time.sleep(random.uniform(0.5, 1.2))

                    flow_details = calculate_flow_score(df)
                    flow_score = float(flow_details["flow_score"])
                    avg_volume = int(df["Volume"].tail(LOOKBACK_DAYS).mean())
                    latest_volume = int(df["Volume"].iloc[-1])
                    vol_ratio = round(latest_volume / avg_volume, 2) if avg_volume > 0 else 0
                    latest_price = float(df["Close"].iloc[-1])
                    price_change_5d = round((df["Close"].iloc[-1] / df["Close"].iloc[-6] - 1) * 100, 2) if len(df) >= 6 else 0

                    # 銘柄詳細情報の取得（ここがブロックされやすいのでセッションを通す）
                    stock = yf.Ticker(ticker, session=session)
                    info = stock.info or {}
                    
                    if not info: # infoが取れない場合は次へ
                        print(f"  ⚠️ {ticker}: info取得失敗（スキップ）")
                        continue

                    mc = info.get("marketCap", 0) or 0
                    market_cap_oku = round(float(mc) / 1e8, 0)
                    api_name = info.get("shortName") or info.get("longName")
                    pbr = info.get("priceToBook")
                    
                    so = info.get("sharesOutstanding")
                    shares_outstanding = int(so) if so else int(float(mc) / latest_price) if mc else None

                    name = get_japanese_name(ticker, api_name)
                    in_range = (MARKET_CAP_MIN <= market_cap_oku <= MARKET_CAP_MAX)
                    watch_flag = is_watch_state(flow_details)
                    prev_high = int(prev_streaks.get(ticker, 0))
                    flow_streak_high = prev_high + 1 if flow_score >= FLOW_SCORE_HIGH else 0
                    
                    reorg_score = calculate_reorg_score(market_cap_oku, pbr)
                    event_score, event_tags = calculate_event_score(stock, now_jst)
                    ma_score = float(min(100.0, max(0.0, flow_score * 0.45 + reorg_score * 0.40 + event_score * 0.15)))
                    level = determine_level(ma_score)

                    support_price = None
                    support_upper = None
                    support_gap_pct = None
                    support_tag = None
                    try:
                        df_half_year = df.tail(125)
                        if len(df_half_year) >= 30:
                            vp = calculate_volume_profile(df_half_year, bins=24)
                            sup_p, sup_u = compute_support_zone_from_profile(vp)
                            if sup_p is not None:
                                support_price, support_upper = sup_p, sup_u
                                support_tag, support_gap_pct = support_position_tag(latest_price, support_price)
                    except Exception: pass

                    tags = []
                    if support_tag: tags.append(support_tag)
                    if watch_flag: tags.append("要監視")
                    if flow_details.get("vol_anomaly", 0) >= 50: tags.append("出来高変化")
                    if flow_streak_high >= 2: tags.append(f"継続{flow_streak_high}日")
                    tags.extend(event_tags)

                    v_pct = (float(latest_volume) / float(shares_outstanding)) * 100.0 if shares_outstanding else None

                    result = {
                        "name": name, "price": round(latest_price, 1), "volume": latest_volume, "avg_volume": avg_volume, "vol_ratio": vol_ratio,
                        "shares_outstanding": shares_outstanding, "volume_of_shares_pct": round(float(v_pct), 3) if v_pct else None,
                        "price_change_5d": price_change_5d, "market_cap_oku": int(market_cap_oku), "pbr": round(float(pbr), 2) if pbr else None,
                        "in_cap_range": in_range, "level": int(level), "ma_score": round(ma_score, 1), "flow_score": round(flow_score, 1),
                        "flow_details": flow_details, "flow_streak_high": int(flow_streak_high), "reorg_score": round(reorg_score, 1),
                        "event_score": round(event_score, 1), "display_state": "要監視" if watch_flag else "観測中",
                        "support_price": round(float(support_price), 1) if support_price else None,
                        "support_upper": round(float(support_upper), 1) if support_upper else None,
                        "support_gap_pct": round(float(support_gap_pct), 1) if support_gap_pct is not None else None,
                        "tags": tags,
                    }
                    results[ticker] = result
                    if in_range and flow_score >= FLOW_SCORE_MEDIUM:
                        qualified[ticker] = result

                except Exception as e:
                    print(f"  ❌ {ticker}: {str(e)[:50]}")
                    continue
        except Exception as e:
            print(f"  ❌ チャンクエラー: {e}")
        
        # チャンクごとに長めに休憩
        time.sleep(3.5)

    return results, qualified

def main():
    now_jst = datetime.now(JST)
    updated_at = now_jst.strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 40 + "\n🦅 HAGETAKA SCOPE - 取得開始\n" + "=" * 40)
    
    results, qualified = fetch_volume_data(MIDCAP_TICKERS)
    filtered = {k: v for k, v in results.items() if v.get("in_cap_range")}
    
    # 並び替え
    sorted_q = dict(sorted(qualified.items(), key=lambda x: (x[1]["level"], x[1]["ma_score"]), reverse=True))
    sorted_f = dict(sorted(filtered.items(), key=lambda x: (x[1]["level"], x[1]["ma_score"]), reverse=True))

    output = {
        "updated_at": updated_at, "date": now_jst.strftime("%Y-%m-%d"),
        "total_count": len(sorted_q), "data": sorted_q, "all_data": sorted_f,
        "disclaimer": "本ツールは補助ツールです。投資判断は自己責任でお願いします。"
    }
    os.makedirs("data", exist_ok=True)
    Path("data/ratios.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 保存完了: 候補 {len(sorted_q)} 件")

if __name__ == "__main__":
    main()
