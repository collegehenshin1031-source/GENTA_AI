"""
源太AI🤖ハゲタカSCOPE - 統合版
- ログイン機能
- 出来高急動モニター（GitHub Actionsで自動更新）
- 利用者ごとのメール通知機能（LocalStorage永続化）
"""

import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List
from pathlib import Path
import streamlit as st
from datetime import datetime
import pytz
import base64
from streamlit.components.v1 import html

# ==========================================
# 定数
# ==========================================
JST = pytz.timezone("Asia/Tokyo")
RATIO_HIGH = 3.0
RATIO_MEDIUM = 1.5
MARKET_CAP_MIN = 300
MARKET_CAP_MAX = 2000

# ログインパスワード
LOGIN_PASSWORD = "88888"

# ==========================================
# 日本語銘柄名辞書
# ==========================================
TICKER_NAMES_JP = {
    "3923.T": "ラクス",
    "4443.T": "Sansan",
    "4478.T": "フリー",
    "3994.T": "マネーフォワード",
    "4165.T": "プレイド",
    "4169.T": "ENECHANGE",
    "4449.T": "ギフティ",
    "4475.T": "HENNGE",
    "4431.T": "スマレジ",
    "4057.T": "インターファクトリー",
    "3697.T": "SHIFT",
    "4194.T": "ビジョナル",
    "4180.T": "Appier",
    "3655.T": "ブレインパッド",
    "4751.T": "サイバーエージェント",
    "3681.T": "ブイキューブ",
    "6035.T": "IRジャパン",
    "4384.T": "ラクスル",
    "9558.T": "ジャパニアス",
    "4441.T": "トビラシステムズ",
    "6315.T": "TOWA",
    "6323.T": "ローツェ",
    "6890.T": "フェローテック",
    "7735.T": "SCREENホールディングス",
    "6146.T": "ディスコ",
    "6266.T": "タツモ",
    "3132.T": "マクニカホールディングス",
    "6920.T": "レーザーテック",
    "4565.T": "そーせいグループ",
    "4587.T": "ペプチドリーム",
    "4582.T": "シンバイオ製薬",
    "4583.T": "カイオム・バイオ",
    "4563.T": "アンジェス",
    "2370.T": "メディネット",
    "4593.T": "ヘリオス",
    "3064.T": "MonotaRO",
    "3092.T": "ZOZO",
    "3769.T": "GMOペイメント",
    "4385.T": "メルカリ",
    "7342.T": "ウェルスナビ",
    "4480.T": "メドレー",
    "6560.T": "LTS",
    "3182.T": "オイシックス",
    "9166.T": "GENDA",
    "3765.T": "ガンホー",
    "3659.T": "ネクソン",
    "3656.T": "KLab",
    "3932.T": "アカツキ",
    "4071.T": "プラスアルファ",
    "4485.T": "JTOWER",
    "7095.T": "Macbee Planet",
    "4054.T": "日本情報クリエイト",
    "6095.T": "メドピア",
    "4436.T": "ミンカブ",
    "4477.T": "BASE",
}

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
# CSS
# ==========================================
st.markdown("""
<style>
#MainMenu, footer, header, .stDeployButton {display: none !important;}

/* 背景：白ベース */
div[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #FFF5F5 100%) !important;
}

.main .block-container {
    max-width: 800px !important;
    padding: 1rem 1rem 3rem 1rem !important;
}

/* タイトル：赤 */
h1 {
    text-align: center !important;
    font-size: 1.6rem !important;
    color: #C41E3A !important;
    font-weight: 800 !important;
}

.subtitle {
    text-align: center;
    color: #666;
    font-size: 0.8rem;
    margin-bottom: 1rem;
}

/* タブ */
.stTabs [data-baseweb="tab-list"] {
    justify-content: center !important;
    background-color: #FFF !important;
    padding: 0.3rem !important;
    border-radius: 10px !important;
    margin-bottom: 1rem !important;
    box-shadow: 0 2px 8px rgba(196, 30, 58, 0.1) !important;
}

.stTabs [data-baseweb="tab"] {
    padding: 0.5rem 1rem !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    color: #666 !important;
}

/* 選択中のタブ - 白文字 */
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #C41E3A 0%, #E63946 100%) !important;
    color: #FFFFFF !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] p {
    color: #FFFFFF !important;
}

/* カード：白背景・赤ボーダー */
.spike-card {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 0.9rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid #C41E3A;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.spike-card.high {
    border-left-color: #C41E3A;
    background: linear-gradient(90deg, rgba(196,30,58,0.08) 0%, #FFFFFF 100%);
}

.spike-card.medium {
    border-left-color: #FFB347;
    background: linear-gradient(90deg, rgba(255,179,71,0.08) 0%, #FFFFFF 100%);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.4rem;
}

.ticker-name {
    font-size: 1rem;
    font-weight: bold;
    color: #333;
}

.ticker-name a { color: inherit; text-decoration: none; }
.ticker-name a:hover { color: #C41E3A; }

.ratio-badge {
    font-size: 1.3rem;
    font-weight: bold;
}

.ratio-badge.high { color: #C41E3A; }
.ratio-badge.medium { color: #FF8C00; }
.ratio-badge.normal { color: #28a745; }

.card-body {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.4rem;
    font-size: 0.8rem;
}

.info-label { color: #888; font-size: 0.7rem; }
.info-value { color: #333; }

/* 統計ボックス */
.stat-box {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 0.8rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #F0F0F0;
}

.stat-value { font-size: 1.6rem; font-weight: bold; }
.stat-value.high { color: #C41E3A; }
.stat-value.medium { color: #FF8C00; }
.stat-value.total { color: #C41E3A; }
.stat-label { font-size: 0.7rem; color: #666; }

/* ボタン：赤グラデーション・白文字 */
.stButton > button {
    background: linear-gradient(135deg, #C41E3A 0%, #E63946 100%) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(196, 30, 58, 0.3) !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #A01830 0%, #C41E3A 100%) !important;
    color: #FFFFFF !important;
}

.stButton > button:active {
    color: #FFFFFF !important;
}

.stButton > button p {
    color: #FFFFFF !important;
}

/* テキスト色 */
p, span, label, div { color: #333; }

/* 更新情報ボックス */
.update-info {
    text-align: center;
    padding: 0.8rem;
    background: linear-gradient(135deg, #FFF5F5 0%, #FFFFFF 100%);
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.8rem;
    border: 1px solid #FFE0E0;
    color: #333;
}

.cap-badge {
    display: inline-block;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.65rem;
    margin-left: 4px;
}
.cap-badge.in { background: rgba(196,30,58,0.1); color: #C41E3A; }
.cap-badge.out { background: rgba(128,128,128,0.1); color: #888; }

/* チェックボックス */
.stCheckbox label span { color: #333 !important; }

/* ラジオボタン */
.stRadio label span { color: #333 !important; }

/* 入力フィールド */
.stTextInput input {
    background: #FFFFFF !important;
    color: #333 !important;
    border: 1px solid #DDD !important;
}

/* expander */
.streamlit-expanderHeader {
    background: #FFF5F5 !important;
    color: #333 !important;
}

/* ログイン画面 */
.login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background: #FFFFFF;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(196, 30, 58, 0.15);
    text-align: center;
}

.login-title {
    color: #C41E3A;
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 1.5rem;
}

.login-error {
    color: #C41E3A;
    background: #FFE0E0;
    padding: 0.5rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# ロゴ画像を読み込み
# ==========================================
def get_logo_base64():
    try:
        with open("logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


# ==========================================
# データ読み込み
# ==========================================
@st.cache_data(ttl=60)
def load_data() -> Dict:
    """JSONからデータを読み込み"""
    data_path = Path("data/ratios.json")
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ==========================================
# LocalStorage連携（JavaScript）
# ==========================================
def load_from_localstorage():
    """LocalStorageから設定を読み込むJavaScriptを実行"""
    html("""
    <script>
    // LocalStorageから読み込み
    const email = localStorage.getItem('hagetaka_email') || '';
    const appPassword = localStorage.getItem('hagetaka_app_password') || '';
    
    // Streamlitに送信（URLパラメータ経由）
    if (email || appPassword) {
        const currentUrl = new URL(window.parent.location.href);
        let needReload = false;
        
        if (email && !currentUrl.searchParams.has('email')) {
            currentUrl.searchParams.set('email', email);
            needReload = true;
        }
        if (appPassword && !currentUrl.searchParams.has('app_pw')) {
            currentUrl.searchParams.set('app_pw', appPassword);
            needReload = true;
        }
        
        if (needReload) {
            window.parent.history.replaceState({}, '', currentUrl.toString());
            window.parent.location.reload();
        }
    }
    </script>
    """, height=0)


def save_to_localstorage(email: str, app_password: str):
    """LocalStorageに設定を保存するJavaScriptを実行"""
    html(f"""
    <script>
    localStorage.setItem('hagetaka_email', '{email}');
    localStorage.setItem('hagetaka_app_password', '{app_password}');
    </script>
    """, height=0)


def clear_localstorage():
    """LocalStorageをクリアするJavaScriptを実行"""
    html("""
    <script>
    localStorage.removeItem('hagetaka_email');
    localStorage.removeItem('hagetaka_app_password');
    </script>
    """, height=0)


# ==========================================
# メール送信
# ==========================================
def send_test_email(email: str, app_password: str) -> tuple[bool, str]:
    try:
        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = email
        msg["Subject"] = "🦅 ハゲタカSCOPE - テスト通知"
        body = "メール設定が正常に完了しました！\n\n出来高急動が検知された際に通知が届きます。"
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email, app_password)
            server.send_message(msg)
        return True, "テストメール送信成功！"
    except smtplib.SMTPAuthenticationError:
        return False, "認証エラー: アプリパスワードを確認してください"
    except Exception as e:
        return False, f"送信エラー: {str(e)}"


def send_spike_alert(email: str, app_password: str, stocks: List[Dict], updated_at: str) -> bool:
    if not stocks:
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = email
        msg["Subject"] = f"🚀 出来高急動アラート: {len(stocks)}件 - {updated_at[:10]}"
        
        lines = [
            "━" * 30,
            "📊 出来高急動モニター",
            "━" * 30,
            f"更新日時: {updated_at}",
            f"検知銘柄: {len(stocks)}件",
            "",
        ]
        
        for s in stocks:
            marker = "🔴" if s["ratio"] >= RATIO_HIGH else "🟠"
            name_jp = TICKER_NAMES_JP.get(s["ticker"], s.get("name", "")[:10])
            lines.extend([
                f"{marker} {s['ticker']} ({name_jp})",
                f"   倍率: {s['ratio']}x | ¥{s.get('price', 0):,.0f} | {s.get('market_cap_oku', 0)}億円",
                "",
            ])
        
        lines.append("━" * 30)
        lines.append("源太AI ハゲタカSCOPE")
        lines.append("━" * 30)
        msg.attach(MIMEText("\n".join(lines), "plain", "utf-8"))
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email, app_password)
            server.send_message(msg)
        return True
    except:
        return False


# ==========================================
# カード表示
# ==========================================
def render_card(ticker: str, d: Dict, show_cap_badge: bool = False):
    ratio = d["ratio"]
    card_class = "high" if ratio >= RATIO_HIGH else ("medium" if ratio >= RATIO_MEDIUM else "")
    ratio_class = "high" if ratio >= RATIO_HIGH else ("medium" if ratio >= RATIO_MEDIUM else "normal")
    
    code = ticker.replace(".T", "")
    url = f"https://finance.yahoo.co.jp/quote/{code}.T"
    
    # 日本語名を優先、なければ英語名、なければ銘柄コード
    name_jp = TICKER_NAMES_JP.get(ticker, d.get('name', code))
    
    cap_badge = ""
    if show_cap_badge:
        if d.get("in_cap_range"):
            cap_badge = '<span class="cap-badge in">対象</span>'
        else:
            cap_badge = '<span class="cap-badge out">範囲外</span>'
    
    st.markdown(f"""
    <div class="spike-card {card_class}">
        <div class="card-header">
            <div class="ticker-name">
                <a href="{url}" target="_blank">{ticker}</a>
                <span style="font-size:0.75rem;color:#888;margin-left:6px;">{str(name_jp)[:12]}</span>
            </div>
            <div class="ratio-badge {ratio_class}">{ratio}x</div>
        </div>
        <div class="card-body">
            <div><span class="info-label">現在値</span><br><span class="info-value" style="color:#C41E3A;font-weight:600;">¥{d['price']:,.0f}</span></div>
            <div><span class="info-label">時価総額</span><br><span class="info-value">{d['market_cap_oku']:,}億円{cap_badge}</span></div>
            <div><span class="info-label">当日出来高</span><br><span class="info-value">{d['volume']:,}</span></div>
            <div><span class="info-label">252日平均</span><br><span class="info-value">{d['avg_volume']:,}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# ログイン画面
# ==========================================
def show_login_page():
    """ログイン画面を表示"""
    logo_base64 = get_logo_base64()
    
    st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)
    
    # ログインコンテナ
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # ロゴ表示
        if logo_base64:
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <img src="data:image/png;base64,{logo_base64}" style="max-width: 280px; width: 90%;">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align:center;'>🦅 源太AI ハゲタカSCOPE</h1>", unsafe_allow_html=True)
        
        # ログインフォーム
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1rem;">
            <p style="color: #666; font-size: 0.9rem;">ログインしてください</p>
        </div>
        """, unsafe_allow_html=True)
        
        # エラーメッセージ表示
        if st.session_state.get("login_error"):
            st.markdown(f"""
            <div class="login-error">
                ❌ パスワードが正しくありません
            </div>
            """, unsafe_allow_html=True)
        
        # パスワード入力
        password = st.text_input(
            "パスワード",
            type="password",
            placeholder="パスワードを入力",
            key="login_password_input"
        )
        
        # ログインボタン
        if st.button("ログイン", use_container_width=True):
            if password == LOGIN_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["login_error"] = False
                st.rerun()
            else:
                st.session_state["login_error"] = True
                st.rerun()
        
        # フッター
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #aaa; font-size: 0.75rem;">
            先乗り株カレッジ会員専用ツール
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# メイン画面
# ==========================================
def show_main_page():
    """メインアプリ画面を表示"""
    logo_base64 = get_logo_base64()
    
    # URLパラメータからメール設定を取得
    query_params = st.query_params
    if "email" in query_params and not st.session_state.get("email_loaded"):
        st.session_state["email_address"] = query_params["email"]
        st.session_state["email_loaded"] = True
    if "app_pw" in query_params and not st.session_state.get("pw_loaded"):
        st.session_state["app_password"] = query_params["app_pw"]
        st.session_state["pw_loaded"] = True
    
    # ヘッダー表示
    if logo_base64:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 0.5rem;">
            <img src="data:image/png;base64,{logo_base64}" style="max-width: 320px; width: 80%;">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.title("🦅 源太AI ハゲタカSCOPE")
    
    st.markdown(f'<p class="subtitle">中型株（{MARKET_CAP_MIN}億〜{MARKET_CAP_MAX}億円）の出来高急動を自動検知</p>', unsafe_allow_html=True)
    
    # LocalStorageから読み込み試行（初回のみ）
    if not st.session_state.get("localstorage_loaded"):
        load_from_localstorage()
        st.session_state["localstorage_loaded"] = True
    
    # データ読み込み
    data = load_data()
    
    # タブ
    tab1, tab2 = st.tabs(["📊 出来高急動", "🔔 通知設定"])
    
    # ==========================================
    # タブ1: 出来高急動
    # ==========================================
    with tab1:
        if data:
            updated_at = data.get("updated_at", "不明")
            st.markdown(f"""
            <div class="update-info">
                📡 最終更新: <strong>{updated_at}</strong><br>
                <span style="font-size:0.7rem;color:#666;">毎日 16:30 JST に自動更新されます</span>
            </div>
            """, unsafe_allow_html=True)
            
            # レジェンド
            st.markdown("""
            <div style="display:flex;justify-content:center;gap:1.2rem;margin-bottom:0.8rem;font-size:0.75rem;color:#666;">
                <span>🔴 3倍以上</span>
                <span>🟠 1.5倍以上</span>
            </div>
            """, unsafe_allow_html=True)
            
            # フィルター切替
            show_all = st.checkbox("全銘柄を表示（時価総額フィルターOFF）", value=False)
            
            if show_all:
                display_data = data.get("all_data", {})
            else:
                display_data = data.get("data", {})
            
            # 統計
            spike_high = len([v for v in display_data.values() if v["ratio"] >= RATIO_HIGH])
            spike_medium = len([v for v in display_data.values() if v["ratio"] >= RATIO_MEDIUM])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="stat-box"><div class="stat-value high">{spike_high}</div><div class="stat-label">🔴 3倍以上</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="stat-box"><div class="stat-value medium">{spike_medium}</div><div class="stat-label">🟠 1.5倍以上</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="stat-box"><div class="stat-value total">{len(display_data)}</div><div class="stat-label">銘柄数</div></div>', unsafe_allow_html=True)
            
            st.markdown("")
            
            # 表示フィルター
            filter_opt = st.radio("", ["すべて", "🔴 3倍以上", "🟠 1.5倍以上"], horizontal=True, label_visibility="collapsed")
            
            if filter_opt == "🔴 3倍以上":
                display_data = {k: v for k, v in display_data.items() if v["ratio"] >= RATIO_HIGH}
            elif filter_opt == "🟠 1.5倍以上":
                display_data = {k: v for k, v in display_data.items() if v["ratio"] >= RATIO_MEDIUM}
            
            # カード表示
            if display_data:
                for ticker, d in display_data.items():
                    render_card(ticker, d, show_cap_badge=show_all)
            else:
                st.info("該当する銘柄がありません")
            
            # メール送信
            email = st.session_state.get("email_address", "")
            app_password = st.session_state.get("app_password", "")
            
            notify_stocks = [{"ticker": k, **v} for k, v in display_data.items() if v["ratio"] >= RATIO_MEDIUM]
            
            if notify_stocks and email and app_password:
                st.markdown("---")
                if st.button(f"📧 検知銘柄（{len(notify_stocks)}件）をメール送信"):
                    with st.spinner("送信中..."):
                        if send_spike_alert(email, app_password, notify_stocks, updated_at):
                            st.success(f"✅ 送信しました！")
                        else:
                            st.error("❌ 送信失敗。通知設定を確認してください。")
        else:
            st.markdown("""
            <div style="text-align:center;padding:2rem;color:#666;">
                <p style="font-size:2.5rem;">📊</p>
                <p>データがありません</p>
                <p style="font-size:0.8rem;color:#888;">GitHub Actionsで初回実行してください</p>
            </div>
            """, unsafe_allow_html=True)
    
    # ==========================================
    # タブ2: 通知設定
    # ==========================================
    with tab2:
        st.markdown("### 🔔 メール通知設定")
        st.markdown('<p style="color:#666;font-size:0.8rem;">出来高急動（1.5倍以上）を検知した際に通知を受け取れます</p>', unsafe_allow_html=True)
        
        email = st.text_input("Gmailアドレス", value=st.session_state.get("email_address", ""), placeholder="example@gmail.com")
        app_password = st.text_input("アプリパスワード（16桁）", value=st.session_state.get("app_password", ""), type="password", placeholder="xxxx xxxx xxxx xxxx")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存", use_container_width=True):
                st.session_state["email_address"] = email
                st.session_state["app_password"] = app_password
                # LocalStorageに保存
                save_to_localstorage(email, app_password)
                st.success("✅ 保存しました（この端末に記憶されます）")
        with col2:
            if st.button("🧪 テスト送信", use_container_width=True):
                if email and app_password:
                    ok, msg = send_test_email(email, app_password)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("入力してください")
        
        # 設定クリアボタン
        if st.button("🗑️ 保存した設定をクリア", use_container_width=True):
            st.session_state["email_address"] = ""
            st.session_state["app_password"] = ""
            clear_localstorage()
            st.success("✅ 設定をクリアしました")
            st.rerun()
        
        with st.expander("📖 アプリパスワードの取得方法"):
            st.markdown("""
            1. [myaccount.google.com](https://myaccount.google.com/) にアクセス
            2. **セキュリティ** → **2段階認証** を有効化
            3. [アプリパスワード](https://myaccount.google.com/apppasswords) で生成
            4. 16桁のパスワードを上のフォームに入力
            
            ⚠️ 通常のGmailパスワードでは動作しません
            """)
        
        st.markdown("""
        <div style="background:#FFF5F5;border-radius:8px;padding:0.8rem;margin-top:1rem;font-size:0.75rem;color:#666;border:1px solid #FFE0E0;">
            🔒 設定はこの端末のブラウザに保存されます（他の人からは見えません）
        </div>
        """, unsafe_allow_html=True)
        
        # ログアウトボタン
        st.markdown("---")
        if st.button("🚪 ログアウト", use_container_width=True):
            st.session_state["logged_in"] = False
            st.rerun()


# ==========================================
# メイン処理
# ==========================================
# セッション初期化
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "login_error" not in st.session_state:
    st.session_state["login_error"] = False

# ページ表示
if st.session_state.get("logged_in"):
    show_main_page()
else:
    show_login_page()
