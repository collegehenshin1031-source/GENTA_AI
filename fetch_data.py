"""
出来高急動（Volume Spike）検知スクリプト
- GitHub Actionsで毎日16:30 JSTに自動実行
- 時価総額フィルター: 300億〜2000億円
- ratio = 当日出来高 / 252日平均出来高
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz
import yfinance as yf

# ==========================================
# 設定
# ==========================================
LOOKBACK_DAYS = 252  # 1年分の営業日
JST = pytz.timezone("Asia/Tokyo")

# 時価総額フィルター（億円）
MARKET_CAP_MIN = 300   # 300億円以上
MARKET_CAP_MAX = 2000  # 2000億円以下

# 出来高倍率の閾値
RATIO_HIGH = 3.0
RATIO_MEDIUM = 1.5

# 監視対象銘柄（約60銘柄）
TICKERS = [
    # SaaS / クラウド
    "3923.T", "4443.T", "4478.T", "3994.T", "4165.T", "4169.T", 
    "4449.T", "4475.T", "4431.T", "4057.T",
    # IT / テック
    "3697.T", "4194.T", "4180.T", "3655.T", "4751.T", "3681.T", 
    "6035.T", "4384.T", "9558.T", "4441.T",
    # 半導体関連
    "6315.T", "6323.T", "6890.T", "7735.T", "6146.T", "6266.T", 
    "3132.T", "6920.T",
    # バイオ / ヘルスケア
    "4565.T", "4587.T", "4582.T", "4583.T", "4563.T", "2370.T", "4593.T",
    # EC / サービス
    "3064.T", "3092.T", "3769.T", "4385.T", "7342.T", "4480.T", 
    "6560.T", "3182.T",
    # エンタメ / ゲーム
    "9166.T", "3765.T", "3659.T", "3656.T", "3932.T",
    # その他成長株
    "4071.T", "4485.T", "7095.T", "4054.T", "6095.T", "4436.T", "4477.T",
]


def fetch_volume_data(tickers: list[str], chunk_size: int = 20) -> dict:
    """銘柄の出来高データを取得"""
    results = {}
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        print(f"📥 取得中: {i+1}〜{min(i+chunk_size, len(tickers))} / {len(tickers)}")
        
        try:
            data = yf.download(
                tickers=chunk,
                period="1y",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            
            for ticker in chunk:
                try:
                    if len(chunk) == 1:
                        vol_series = data["Volume"]
                        close_series = data["Close"]
                    else:
                        vol_series = data[ticker]["Volume"]
                        close_series = data[ticker]["Close"]
                    
                    vol_series = vol_series.dropna()
                    close_series = close_series.dropna()
                    
                    if len(vol_series) < 20:
                        continue
                    
                    latest_volume = int(vol_series.iloc[-1])
                    avg_volume = int(vol_series.tail(LOOKBACK_DAYS).mean())
                    ratio = round(latest_volume / avg_volume, 2) if avg_volume > 0 else 0
                    latest_price = float(close_series.iloc[-1]) if len(close_series) > 0 else 0
                    
                    # 時価総額取得
                    market_cap_oku = 0
                    name = ticker.replace(".T", "")
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        market_cap = info.get("marketCap", 0)
                        if market_cap:
                            market_cap_oku = round(market_cap / 1e8, 0)
                        name = info.get("shortName", info.get("longName", name))
                    except:
                        pass
                    
                    in_range = MARKET_CAP_MIN <= market_cap_oku <= MARKET_CAP_MAX
                    
                    results[ticker] = {
                        "name": name,
                        "volume": latest_volume,
                        "avg_volume": avg_volume,
                        "ratio": ratio,
                        "price": round(latest_price, 1),
                        "market_cap_oku": int(market_cap_oku),
                        "in_cap_range": in_range,
                    }
                    
                    status = "✅" if in_range else f"⚠️範囲外"
                    print(f"  {ticker}: {ratio}倍, {market_cap_oku:.0f}億円 {status}")
                    
                except Exception as e:
                    print(f"  ⚠️ {ticker}: {e}")
                    
        except Exception as e:
            print(f"  ❌ チャンク取得エラー: {e}")
    
    return results


def main():
    print("=" * 50)
    print("📊 出来高急動検知 - 自動更新")
    print("=" * 50)
    
    now_jst = datetime.now(JST)
    updated_at = now_jst.strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ 実行時刻: {updated_at} JST")
    print(f"📋 対象銘柄数: {len(TICKERS)}")
    
    # データ取得
    results = fetch_volume_data(TICKERS)
    print(f"\n✅ 取得成功: {len(results)}銘柄")
    
    # フィルター通過銘柄
    filtered = {k: v for k, v in results.items() if v.get("in_cap_range", False)}
    print(f"✅ 時価総額フィルター通過: {len(filtered)}銘柄")
    
    # ソート
    sorted_filtered = dict(sorted(filtered.items(), key=lambda x: x[1]["ratio"], reverse=True))
    sorted_all = dict(sorted(results.items(), key=lambda x: x[1]["ratio"], reverse=True))
    
    # 統計
    spike_high = len([r for r in sorted_filtered.values() if r["ratio"] >= RATIO_HIGH])
    spike_medium = len([r for r in sorted_filtered.values() if r["ratio"] >= RATIO_MEDIUM])
    
    # 出力
    output = {
        "updated_at": updated_at,
        "date": now_jst.strftime("%Y-%m-%d"),
        "market_cap_range": f"{MARKET_CAP_MIN}億〜{MARKET_CAP_MAX}億円",
        "total_count": len(sorted_filtered),
        "all_count": len(results),
        "spike_high_count": spike_high,
        "spike_medium_count": spike_medium,
        "data": sorted_filtered,
        "all_data": sorted_all,
    }
    
    os.makedirs("data", exist_ok=True)
    with open("data/ratios.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"💾 保存完了: data/ratios.json")
    
    # サマリー
    print("\n📈 上位10件（フィルター通過）:")
    for ticker, info in list(sorted_filtered.items())[:10]:
        marker = "🔴" if info["ratio"] >= 3.0 else ("🟠" if info["ratio"] >= 1.5 else "⚪")
        print(f"  {marker} {ticker}: {info['ratio']}倍 | {info['market_cap_oku']}億円")


if __name__ == "__main__":
    main()
