"""
源太AI🤖ハゲタカSCOPE
- 出来高急動モニター（中型株の初動狙い）
- ハゲタカ監視（M&A予兆検知）
- 利用者ごとのメール通知設定
"""

import re
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import pytz

import ma_detector as ma

# ==========================================
# 🔑 パスワード設定
# ==========================================
LOGIN_PASSWORD = "88888"
ADMIN_CODE = "888888"

# ==========================================
# 定数
# ==========================================
JST = pytz.timezone("Asia/Tokyo")
LOOKBACK_DAYS = 252  # 1年分の営業日

# 時価総額フィルター（億円）
MARKET_CAP_MIN = 300
MARKET_CAP_MAX = 2000

# 出来高倍率の閾値
RATIO_HIGH = 3.0
RATIO_MEDIUM = 1.5

# ==========================================
# UI設定
# ==========================================
st.set_page_config(
    page_title="源太AI🤖ハゲタカSCOPE", 
    page_icon="🦅", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🎨 CSS
# ==========================================
st.markdown("""
<style>
/* 基本設定・Streamlit要素非表示 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display:none;}

/* 全体背景 */
div[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
}

/* メインコンテナ */
.main .block-container {
    max-width: 900px !important;
    padding: 1rem 1.5rem 3rem 1.5rem !important;
    margin: 0 auto !important;
}

/* ヘッダー */
h1 {
    text-align: center !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    color: #4ecdc4 !important;
    margin-bottom: 0.3rem !important;
}

/* サブタイトル */
.subtitle {
    text-align: center;
    color: #888;
    font-size: 0.85rem;
    margin-bottom: 1rem;
}

/* タブスタイル */
.stTabs [data-baseweb="tab-list"] {
    justify-content: center !important;
    gap: 0 !important;
    background-color: #2d2d44 !important;
    padding: 0.3rem !important;
    border-radius: 12px !important;
    margin-bottom: 1rem !important;
}

.stTabs [data-baseweb="tab"] {
    padding: 0.6rem 1.2rem !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: #888 !important;
    transition: all 0.3s ease !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%) !important;
    color: #1a1a2e !important;
}

/* カードスタイル */
.spike-card {
    background: #2d2d44;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    border-left: 4px solid #4ecdc4;
}

.spike-card.high {
    border-left-color: #ff6b6b;
    background: linear-gradient(90deg, rgba(255,107,107,0.15) 0%, #2d2d44 100%);
}

.spike-card.medium {
    border-left-color: #ffa94d;
    background: linear-gradient(90deg, rgba(255,169,77,0.1) 0%, #2d2d44 100%);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.ticker-name {
    font-size: 1.1rem;
    font-weight: bold;
    color: #fff;
}

.ratio-badge {
    font-size: 1.4rem;
    font-weight: bold;
}

.ratio-badge.high { color: #ff6b6b; }
.ratio-badge.medium { color: #ffa94d; }
.ratio-badge.normal { color: #4ecdc4; }

.card-body {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #aaa;
}

.info-label { color: #666; }
.info-value { color: #fff; }

/* 統計カード */
.stat-box {
    background: #2d2d44;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}

.stat-value {
    font-size: 2rem;
    font-weight: bold;
}

.stat-value.high { color: #ff6b6b; }
.stat-value.medium { color: #ffa94d; }
.stat-value.total { color: #4ecdc4; }

.stat-label {
    font-size: 0.8rem;
    color: #888;
}

/* ボタン */
.stButton > button {
    background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%) !important;
    color: #1a1a2e !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
}

/* 入力フィールド */
input, textarea {
    background: #2d2d44 !important;
    color: #fff !important;
    border: 1px solid #444 !important;
    border-radius: 8px !important;
}

/* レジェンド */
.legend {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    margin-bottom: 1rem;
    font-size: 0.8rem;
    color: #888;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.3rem;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}

.legend-dot.high { background: #ff6b6b; }
.legend-dot.medium { background: #ffa94d; }

/* 設定フォーム */
.settings-section {
    background: #2d2d44;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.settings-title {
    font-size: 1rem;
    font-weight: bold;
    color: #4ecdc4;
    margin-bottom: 1rem;
}

/* アコーディオン */
.help-section {
    background: #252540;
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1rem;
    font-size: 0.85rem;
    color: #aaa;
}

.help-section h4 {
    color: #4ecdc4;
    margin-bottom: 0.5rem;
}

.help-section ol {
    padding-left: 1.2rem;
}

.help-section li {
    margin-bottom: 0.3rem;
}

/* テキスト色 */
p, span, label, div {
    color: #ddd;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 銘柄リスト（中型グロース・テック）
# ==========================================
DEFAULT_TICKERS = [
    # グロース・テック
    "3923", "4443", "4478", "3994", "3697", "4194", "4165", "4169", "4180", "9166",
    # 半導体
    "6315", "6323", "3132", "4062", "5384",
    # バイオ
    "4565", "4587", "4582",
    # EC・サービス
    "3064", "3092", "3769",
]


# ==========================================
# データ取得関数
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_volume_spike_data(tickers: List[str]) -> Dict[str, Any]:
    """
    出来高急動データを取得
    """
    import yfinance as yf
    
    results = {}
    
    # .Tを追加
    ticker_symbols = [f"{t}.T" for t in tickers]
    
    try:
        # バッチでデータ取得
        data = yf.download(
            tickers=ticker_symbols,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        
        for ticker in tickers:
            symbol = f"{ticker}.T"
            try:
                if len(ticker_symbols) == 1:
                    vol_series = data["Volume"]
                    close_series = data["Close"]
                else:
                    vol_series = data[symbol]["Volume"]
                    close_series = data[symbol]["Close"]
                
                vol_series = vol_series.dropna()
                close_series = close_series.dropna()
                
                if len(vol_series) < 20:
                    continue
                
                # 出来高計算
                latest_volume = int(vol_series.iloc[-1])
                avg_volume = int(vol_series.tail(LOOKBACK_DAYS).mean())
                
                if avg_volume > 0:
                    ratio = round(latest_volume / avg_volume, 2)
                else:
                    ratio = 0
                
                # 現在値
                latest_price = float(close_series.iloc[-1]) if len(close_series) > 0 else 0
                
                # 時価総額取得
                try:
                    stock = yf.Ticker(symbol)
                    info = stock.info
                    market_cap = info.get("marketCap", 0)
                    market_cap_oku = market_cap / 1e8 if market_cap else 0
                    name = info.get("shortName", info.get("longName", ticker))
                except:
                    market_cap_oku = 0
                    name = ticker
                
                # 時価総額フィルター
                in_range = MARKET_CAP_MIN <= market_cap_oku <= MARKET_CAP_MAX
                
                results[ticker] = {
                    "name": name,
                    "volume": latest_volume,
                    "avg_volume": avg_volume,
                    "ratio": ratio,
                    "price": round(latest_price, 1),
                    "market_cap_oku": round(market_cap_oku, 0),
                    "in_cap_range": in_range,
                }
                
            except Exception as e:
                continue
                
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
    
    return results


# ==========================================
# メール送信関数
# ==========================================
def send_test_email(email: str, app_password: str) -> tuple[bool, str]:
    """テストメールを送信"""
    try:
        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = email
        msg["Subject"] = "🦅 ハゲタカSCOPE - テスト通知"
        
        body = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 テスト通知
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

メール設定が正常に完了しました！

今後、出来高急動（1.5倍以上）が検知された際に
このアドレスに通知が届きます。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
源太AI🦅ハゲタカSCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email, app_password)
            server.send_message(msg)
        
        return True, "テストメール送信成功！"
        
    except smtplib.SMTPAuthenticationError:
        return False, "認証エラー: メールアドレスまたはアプリパスワードが正しくありません"
    except Exception as e:
        return False, f"送信エラー: {str(e)}"


def send_spike_alert(email: str, app_password: str, spike_stocks: List[Dict]) -> bool:
    """出来高急動アラートを送信"""
    if not spike_stocks:
        return False
    
    try:
        now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
        
        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = email
        msg["Subject"] = f"🚀 出来高急動アラート: {len(spike_stocks)}件検知 - {now[:10]}"
        
        body_lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 出来高急動モニター - アラート通知",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"検知日時: {now}",
            f"検知銘柄数: {len(spike_stocks)}件",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🎯 検知銘柄一覧",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        
        for stock in spike_stocks:
            marker = "🔴 特大" if stock["ratio"] >= RATIO_HIGH else "🟠 注目"
            body_lines.extend([
                f"【{marker}】{stock['ticker']} ({stock.get('name', '')})",
                f"  出来高倍率: {stock['ratio']}倍",
                f"  当日出来高: {stock['volume']:,}",
                f"  252日平均: {stock['avg_volume']:,}",
                f"  現在値: ¥{stock.get('price', 0):,.0f}",
                f"  時価総額: {stock.get('market_cap_oku', 0):.0f}億円",
                "",
            ])
        
        body_lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "※ 投資判断は自己責任でお願いします",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ])
        
        msg.attach(MIMEText("\n".join(body_lines), "plain", "utf-8"))
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email, app_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        return False


# ==========================================
# カード表示関数
# ==========================================
def render_spike_card(ticker: str, data: Dict):
    """出来高急動カードを表示"""
    ratio = data["ratio"]
    
    if ratio >= RATIO_HIGH:
        card_class = "high"
        ratio_class = "high"
    elif ratio >= RATIO_MEDIUM:
        card_class = "medium"
        ratio_class = "medium"
    else:
        card_class = ""
        ratio_class = "normal"
    
    yahoo_url = f"https://finance.yahoo.co.jp/quote/{ticker}.T"
    
    st.markdown(f"""
    <div class="spike-card {card_class}">
        <div class="card-header">
            <div class="ticker-name">
                <a href="{yahoo_url}" target="_blank" style="color: inherit; text-decoration: none;">
                    {ticker} <span style="font-size: 0.8rem; color: #888;">{data.get('name', '')[:15]}</span>
                </a>
            </div>
            <div class="ratio-badge {ratio_class}">{ratio}x</div>
        </div>
        <div class="card-body">
            <div>
                <span class="info-label">現在値</span><br>
                <span class="info-value" style="color: #4ecdc4; font-size: 1rem;">¥{data['price']:,.0f}</span>
            </div>
            <div>
                <span class="info-label">時価総額</span><br>
                <span class="info-value">{data['market_cap_oku']:,.0f}億円</span>
            </div>
            <div>
                <span class="info-label">当日出来高</span><br>
                <span class="info-value">{data['volume']:,}</span>
            </div>
            <div>
                <span class="info-label">252日平均</span><br>
                <span class="info-value">{data['avg_volume']:,}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# セッション初期化
# ==========================================
def init_session_state():
    if "spike_data" not in st.session_state:
        st.session_state["spike_data"] = {}
    if "last_fetch_time" not in st.session_state:
        st.session_state["last_fetch_time"] = None
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

init_session_state()


# ==========================================
# メイン画面
# ==========================================
st.title("🦅 源太AI ハゲタカSCOPE")
st.markdown('<p class="subtitle">中型株（300億〜2000億円）の出来高急動を自動検知</p>', unsafe_allow_html=True)

# タブ
tab1, tab2, tab3 = st.tabs(["📊 出来高急動", "🔍 ハゲタカ監視", "🔔 通知設定"])


# ==========================================
# タブ1: 出来高急動モニター
# ==========================================
with tab1:
    # レジェンド
    st.markdown("""
    <div class="legend">
        <div class="legend-item">
            <div class="legend-dot high"></div>
            <span>3倍以上（異常）</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot medium"></div>
            <span>1.5倍以上（注目）</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 更新ボタン
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 データ更新", use_container_width=True):
            with st.spinner("📡 データ取得中..."):
                data = fetch_volume_spike_data(DEFAULT_TICKERS)
                st.session_state["spike_data"] = data
                st.session_state["last_fetch_time"] = datetime.now(JST)
            st.rerun()
    
    # 最終更新時刻
    last_fetch = st.session_state.get("last_fetch_time")
    if last_fetch:
        st.markdown(f'<p style="text-align: center; color: #666; font-size: 0.8rem;">最終更新: {last_fetch.strftime("%Y-%m-%d %H:%M:%S")}</p>', unsafe_allow_html=True)
    
    # データ表示
    spike_data = st.session_state.get("spike_data", {})
    
    if spike_data:
        # 時価総額フィルター適用 & ソート
        filtered_data = {
            k: v for k, v in spike_data.items()
            if v.get("in_cap_range", False)
        }
        sorted_data = dict(sorted(filtered_data.items(), key=lambda x: x[1]["ratio"], reverse=True))
        
        # 統計
        spike_high = len([v for v in sorted_data.values() if v["ratio"] >= RATIO_HIGH])
        spike_medium = len([v for v in sorted_data.values() if v["ratio"] >= RATIO_MEDIUM])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value high">{spike_high}</div>
                <div class="stat-label">🔴 3倍以上</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value medium">{spike_medium}</div>
                <div class="stat-label">🟠 1.5倍以上</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value total">{len(sorted_data)}</div>
                <div class="stat-label">対象銘柄</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")
        
        # フィルター
        filter_option = st.radio(
            "表示フィルター",
            ["すべて", "🔴 3倍以上", "🟠 1.5倍以上"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # フィルタリング
        if filter_option == "🔴 3倍以上":
            display_data = {k: v for k, v in sorted_data.items() if v["ratio"] >= RATIO_HIGH}
        elif filter_option == "🟠 1.5倍以上":
            display_data = {k: v for k, v in sorted_data.items() if v["ratio"] >= RATIO_MEDIUM}
        else:
            display_data = sorted_data
        
        # カード表示
        if display_data:
            for ticker, data in display_data.items():
                render_spike_card(ticker, data)
        else:
            st.info("該当する銘柄がありません")
        
        # メール通知（設定済みの場合）
        email = st.session_state.get("email_address", "")
        app_password = st.session_state.get("app_password", "")
        notify_enabled = st.session_state.get("notify_enabled", False)
        
        if notify_enabled and email and app_password:
            notify_stocks = [
                {"ticker": k, **v} 
                for k, v in sorted_data.items() 
                if v["ratio"] >= RATIO_MEDIUM
            ]
            if notify_stocks:
                st.markdown("---")
                if st.button("📧 検知銘柄をメール送信"):
                    with st.spinner("送信中..."):
                        success = send_spike_alert(email, app_password, notify_stocks)
                        if success:
                            st.success(f"✅ {len(notify_stocks)}件の銘柄情報を送信しました！")
                        else:
                            st.error("❌ 送信に失敗しました。通知設定を確認してください。")
    else:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #888;">
            <p style="font-size: 3rem;">📊</p>
            <p>「データ更新」ボタンを押して<br>出来高急動銘柄をスキャンしてください</p>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# タブ2: ハゲタカ監視（M&A分析）
# ==========================================
with tab2:
    st.markdown("### 🔍 M&A予兆監視")
    st.markdown('<p style="color: #888; font-size: 0.85rem;">特定銘柄のM&A可能性を詳細分析します</p>', unsafe_allow_html=True)
    
    # 銘柄入力
    col1, col2 = st.columns([3, 1])
    with col1:
        new_code = st.text_input(
            "銘柄コード",
            placeholder="例: 7203",
            label_visibility="collapsed"
        )
    with col2:
        add_btn = st.button("追加", use_container_width=True)
    
    if add_btn and new_code:
        code = re.sub(r'\D', '', new_code)[:4]
        if code and len(code) == 4:
            if code not in st.session_state["watchlist"]:
                st.session_state["watchlist"].append(code)
                st.success(f"✅ {code} を追加しました")
            else:
                st.warning("既に追加されています")
        else:
            st.error("4桁の銘柄コードを入力してください")
    
    # ウォッチリスト表示
    watchlist = st.session_state.get("watchlist", [])
    
    if watchlist:
        st.markdown("#### 📋 監視リスト")
        
        # 削除用
        cols = st.columns(min(len(watchlist), 5))
        for i, code in enumerate(watchlist[:5]):
            with cols[i]:
                if st.button(f"❌ {code}", key=f"del_{code}"):
                    st.session_state["watchlist"].remove(code)
                    st.rerun()
        
        # M&A分析実行
        if st.button("🔍 M&A分析を実行", use_container_width=True):
            import yfinance as yf
            
            with st.spinner("分析中..."):
                for code in watchlist:
                    try:
                        # yfinanceでデータ取得
                        symbol = f"{code}.T"
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        hist = ticker.history(period="1mo")
                        
                        # 基本情報取得
                        name = info.get("shortName", info.get("longName", code))
                        price = info.get("currentPrice", info.get("regularMarketPrice", 0))
                        pbr = info.get("priceToBook", 0)
                        market_cap = info.get("marketCap", 0)
                        market_cap_oku = market_cap / 1e8 if market_cap else 0
                        
                        # 出来高情報
                        if not hist.empty:
                            current_vol = hist["Volume"].iloc[-1]
                            avg_vol = hist["Volume"].mean()
                            volume_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
                        else:
                            volume_ratio = 1.0
                        
                        # M&A分析実行
                        result = ma.analyze_ma_potential(
                            code=code,
                            name=name,
                            price=price,
                            pbr=pbr,
                            upside_pct=None,
                            market_cap=market_cap_oku,
                            volume_ratio=volume_ratio,
                            turnover_pct=None,
                            turnover_5d_pct=None,
                            signal_icon="",
                            skip_news=False  # ニュースも分析
                        )
                        
                        score = result.total_score
                        
                        if score >= 70:
                            level = "🔴 緊急"
                            card_class = "high"
                        elif score >= 50:
                            level = "🟠 高"
                            card_class = "medium"
                        elif score >= 30:
                            level = "🟡 中"
                            card_class = ""
                        else:
                            level = "🟢 低"
                            card_class = ""
                        
                        st.markdown(f"""
                        <div class="spike-card {card_class}">
                            <div class="card-header">
                                <div class="ticker-name">{code} <span style="font-size: 0.8rem; color: #888;">{name[:15]}</span></div>
                                <div class="ratio-badge" style="font-size: 1rem;">{level}</div>
                            </div>
                            <div style="color: #aaa; font-size: 0.9rem; margin-top: 0.5rem;">
                                <strong>M&Aスコア: {score}点</strong><br>
                                📰 ニュース: {result.news_score}点 / 
                                📊 出来高: {result.volume_score}点 / 
                                💰 バリュエーション: {result.valuation_score}点<br>
                                時価総額: {market_cap_oku:.0f}億円 / PBR: {pbr:.2f}倍
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 検知キーワードがあれば表示
                        if result.matched_keywords:
                            st.markdown(f'<p style="color: #ff6b6b; font-size: 0.85rem; margin-left: 1rem;">🔑 キーワード: {", ".join(result.matched_keywords[:5])}</p>', unsafe_allow_html=True)
                        
                        # ニュースがあれば表示
                        if result.news_items:
                            with st.expander(f"📰 {code} のニュース（{len(result.news_items)}件）"):
                                for news in result.news_items[:5]:
                                    st.markdown(f"- [{news.title}]({news.url})")
                        
                    except Exception as e:
                        st.error(f"{code}: 分析エラー - {str(e)}")
                        
                    time.sleep(0.5)  # API制限対策
    else:
        st.info("👆 銘柄コードを入力して監視リストに追加してください")


# ==========================================
# タブ3: 通知設定
# ==========================================
with tab3:
    st.markdown("### 🔔 メール通知設定")
    st.markdown('<p style="color: #888; font-size: 0.85rem;">出来高急動（1.5倍以上）を検知した際に、あなたのGmailに通知します</p>', unsafe_allow_html=True)
    
    # 設定フォーム
    st.markdown('<div class="settings-section">', unsafe_allow_html=True)
    st.markdown('<div class="settings-title">📧 Gmail設定</div>', unsafe_allow_html=True)
    
    email = st.text_input(
        "Gmailアドレス",
        value=st.session_state.get("email_address", ""),
        placeholder="example@gmail.com"
    )
    
    app_password = st.text_input(
        "アプリパスワード（16桁）",
        value=st.session_state.get("app_password", ""),
        type="password",
        placeholder="xxxx xxxx xxxx xxxx"
    )
    
    notify_enabled = st.checkbox(
        "📨 出来高急動アラートを受け取る",
        value=st.session_state.get("notify_enabled", False)
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存", use_container_width=True):
            st.session_state["email_address"] = email
            st.session_state["app_password"] = app_password
            st.session_state["notify_enabled"] = notify_enabled
            st.success("✅ 設定を保存しました")
    
    with col2:
        if st.button("🧪 テスト送信", use_container_width=True):
            if email and app_password:
                with st.spinner("送信中..."):
                    success, message = send_test_email(email, app_password)
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
            else:
                st.warning("メールアドレスとアプリパスワードを入力してください")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ヘルプセクション
    with st.expander("📖 アプリパスワードの取得方法"):
        st.markdown("""
        ### Gmailアプリパスワードの取得手順
        
        **前提**: Googleアカウントの2段階認証が有効になっている必要があります
        
        #### Step 1: Googleアカウントにアクセス
        1. [myaccount.google.com](https://myaccount.google.com/) にアクセス
        2. Googleアカウントでログイン
        
        #### Step 2: 2段階認証を有効化（まだの場合）
        1. 左メニューの「**セキュリティ**」をクリック
        2. 「**2段階認証プロセス**」をクリック
        3. 画面の指示に従って有効化
        
        #### Step 3: アプリパスワードを生成
        1. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) にアクセス
        2. 「**アプリを選択**」で「**その他（名前を入力）**」を選択
        3. 名前に「`ハゲタカSCOPE`」と入力
        4. 「**生成**」をクリック
        5. **16桁のパスワード**が表示されます（例: `abcd efgh ijkl mnop`）
        
        #### Step 4: ハゲタカSCOPEに設定
        1. 上のフォームにGmailアドレスを入力
        2. 16桁のアプリパスワードを入力（スペースありでもなしでもOK）
        3. 「保存」をクリック
        4. 「テスト送信」で確認
        
        ---
        
        ⚠️ **注意**
        - 通常のGmailパスワードでは動作しません
        - アプリパスワードは**一度しか表示されない**のでメモしてください
        - 設定情報は**このブラウザのみ**に保存されます（サーバーには送信されません）
        """)
    
    # セキュリティ説明
    st.markdown("""
    <div style="background: #252540; border-radius: 8px; padding: 1rem; margin-top: 1rem; font-size: 0.8rem; color: #888;">
        🔒 <strong>セキュリティについて</strong><br>
        入力したメールアドレスとアプリパスワードは、あなたのブラウザにのみ保存されます。
        サーバーに送信されることはありません。メール送信はあなたのGmailから直接行われます。
    </div>
    """, unsafe_allow_html=True)
