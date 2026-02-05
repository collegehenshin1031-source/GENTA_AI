"""
出来高急動（Volume Spike）検知スクリプト
- GitHub Actionsで毎日16:30 JSTに自動実行
- 東証全銘柄から時価総額300億〜2000億円の中型株を自動検出
- ratio = 当日出来高 / 252日平均出来高
"""

import json
import os
from datetime import datetime
from pathlib import Path
import time

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


def get_all_tse_tickers() -> list[str]:
    """
    東証上場銘柄のリストを取得
    JPX（日本取引所グループ）の公開データから取得
    """
    print("📋 東証銘柄リストを取得中...")
    
    try:
        # JPXの上場銘柄一覧（Excel）を取得
        url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
        df = pd.read_excel(url)
        
        # 銘柄コードを取得（東証の銘柄のみ）
        # カラム名は「コード」
        if 'コード' in df.columns:
            codes = df['コード'].dropna().astype(int).astype(str).tolist()
        else:
            # カラム名が異なる場合の対応
            codes = df.iloc[:, 0].dropna().astype(int).astype(str).tolist()
        
        # yfinance形式に変換（例: 7203 → 7203.T）
        tickers = [f"{code}.T" for code in codes if code.isdigit() and len(code) == 4]
        
        print(f"✅ 取得完了: {len(tickers)}銘柄")
        return tickers
        
    except Exception as e:
        print(f"⚠️ JPXからの取得に失敗: {e}")
        print("📋 バックアップリストを使用します...")
        return get_backup_tickers()


def get_backup_tickers() -> list[str]:
    """
    バックアップ用の銘柄リスト
    主要な銘柄コード範囲をカバー
    """
    tickers = []
    
    # 東証の主要な銘柄コード範囲
    # 1000番台〜9000番台
    ranges = [
        (1300, 1999),  # 水産・農林・鉱業など
        (2000, 2999),  # 食品など
        (3000, 3999),  # 繊維・パルプ・化学など
        (4000, 4999),  # 医薬品・化学など
        (5000, 5999),  # 石油・ゴム・ガラスなど
        (6000, 6999),  # 機械・電気機器など
        (7000, 7999),  # 輸送用機器・精密機器など
        (8000, 8999),  # 銀行・証券・保険など
        (9000, 9999),  # 不動産・運輸・情報通信など
    ]
    
    for start, end in ranges:
        for code in range(start, end + 1):
            tickers.append(f"{code}.T")
    
    print(f"📋 バックアップリスト: {len(tickers)}銘柄")
    return tickers


def filter_midcap_tickers(tickers: list[str], chunk_size: int = 50) -> list[str]:
    """
    時価総額で中型株（300億〜2000億円）をフィルタリング
    """
    print(f"\n📊 中型株フィルタリング中（{MARKET_CAP_MIN}億〜{MARKET_CAP_MAX}億円）...")
    
    midcap_tickers = []
    processed = 0
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        processed += len(chunk)
        
        if processed % 500 == 0 or processed == len(tickers):
            print(f"  処理中: {processed}/{len(tickers)}銘柄...")
        
        for ticker in chunk:
            try:
                stock = yf.Ticker(ticker)
                info = stock.fast_info
                
                # 時価総額を取得（円）
                market_cap = getattr(info, 'market_cap', None)
                
                if market_cap is None:
                    continue
                
                # 億円に変換
                market_cap_oku = market_cap / 1e8
                
                # 中型株の範囲内かチェック
                if MARKET_CAP_MIN <= market_cap_oku <= MARKET_CAP_MAX:
                    midcap_tickers.append(ticker)
                    
            except Exception:
                continue
        
        # API制限対策（少し待機）
        time.sleep(0.1)
    
    print(f"✅ 中型株: {len(midcap_tickers)}銘柄を検出")
    return midcap_tickers


def fetch_volume_data(tickers: list[str], chunk_size: int = 20) -> dict:
    """銘柄の出来高データを取得"""
    results = {}
    total = len(tickers)
    
    for i in range(0, total, chunk_size):
        chunk = tickers[i:i + chunk_size]
        print(f"📥 出来高データ取得中: {i+1}〜{min(i+chunk_size, total)} / {total}")
        
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
                        if ticker not in data.columns.get_level_values(0):
                            continue
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
                    
                    # 時価総額と銘柄名を取得
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
                    
                    # 再度時価総額チェック（データ取得時点での確認）
                    in_range = MARKET_CAP_MIN <= market_cap_oku <= MARKET_CAP_MAX
                    
                    if in_range:  # 中型株のみ保存
                        results[ticker] = {
                            "name": name,
                            "volume": latest_volume,
                            "avg_volume": avg_volume,
                            "ratio": ratio,
                            "price": round(latest_price, 1),
                            "market_cap_oku": int(market_cap_oku),
                            "in_cap_range": True,
                        }
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"  ❌ チャンク取得エラー: {e}")
        
        # API制限対策
        time.sleep(0.2)
    
    return results


def main():
    print("=" * 60)
    print("📊 出来高急動検知 - 東証中型株全銘柄スキャン")
    print("=" * 60)
    
    now_jst = datetime.now(JST)
    updated_at = now_jst.strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ 実行時刻: {updated_at} JST")
    print(f"🎯 対象: 時価総額 {MARKET_CAP_MIN}億〜{MARKET_CAP_MAX}億円")
    
    # Step 1: 東証全銘柄を取得
    all_tickers = get_all_tse_tickers()
    
    # Step 2: 中型株をフィルタリング
    midcap_tickers = filter_midcap_tickers(all_tickers)
    
    if not midcap_tickers:
        print("⚠️ 中型株が見つかりませんでした")
        midcap_tickers = []
    
    print(f"\n📋 スキャン対象: {len(midcap_tickers)}銘柄")
    
    # Step 3: 出来高データを取得
    results = fetch_volume_data(midcap_tickers)
    print(f"\n✅ データ取得成功: {len(results)}銘柄")
    
    # ソート（出来高倍率の高い順）
    sorted_results = dict(sorted(results.items(), key=lambda x: x[1]["ratio"], reverse=True))
    
    # 統計
    spike_high = len([r for r in sorted_results.values() if r["ratio"] >= RATIO_HIGH])
    spike_medium = len([r for r in sorted_results.values() if r["ratio"] >= RATIO_MEDIUM])
    
    # 出力
    output = {
        "updated_at": updated_at,
        "date": now_jst.strftime("%Y-%m-%d"),
        "market_cap_range": f"{MARKET_CAP_MIN}億〜{MARKET_CAP_MAX}億円",
        "total_count": len(sorted_results),
        "all_count": len(sorted_results),
        "spike_high_count": spike_high,
        "spike_medium_count": spike_medium,
        "scanned_tickers": len(midcap_tickers),
        "data": sorted_results,
        "all_data": sorted_results,
    }
    
    os.makedirs("data", exist_ok=True)
    with open("data/ratios.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 保存完了: data/ratios.json")
    
    # サマリー
    print("\n" + "=" * 60)
    print("📈 検知結果サマリー")
    print("=" * 60)
    print(f"  スキャン銘柄数: {len(midcap_tickers)}")
    print(f"  中型株データ取得: {len(sorted_results)}銘柄")
    print(f"  🔴 3倍以上: {spike_high}銘柄")
    print(f"  🟠 1.5倍以上: {spike_medium}銘柄")
    
    print("\n📈 上位10件:")
    for ticker, info in list(sorted_results.items())[:10]:
        marker = "🔴" if info["ratio"] >= 3.0 else ("🟠" if info["ratio"] >= 1.5 else "⚪")
        print(f"  {marker} {ticker} {info['name']}: {info['ratio']}倍 | {info['market_cap_oku']}億円")


if __name__ == "__main__":
    main()
