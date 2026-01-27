"""
源太AI🤖ハゲタカSCOPE - 統合版
- 出来高急動モニター（GitHub Actionsで自動更新）
- 利用者ごとのメール通知機能
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

# ==========================================
# 定数
# ==========================================
JST = pytz.timezone("Asia/Tokyo")
RATIO_HIGH = 3.0
RATIO_MEDIUM = 1.5
MARKET_CAP_MIN = 300
MARKET_CAP_MAX = 2000

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

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #C41E3A 0%, #E63946 100%) !important;
    color: #FFF !important;
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

/* ボタン：赤グラデーション */
.stButton > button {
    background: linear-gradient(135deg, #C41E3A 0%, #E63946 100%) !important;
    color: #FFF !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(196, 30, 58, 0.3) !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #A01830 0%, #C41E3A 100%) !important;
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

/* 設定セクション */
.settings-section {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #F0F0F0;
}
</style>
""", unsafe_allow_html=True)


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
            lines.extend([
                f"{marker} {s['ticker']} ({s.get('name', '')[:10]})",
                f"   倍率: {s['ratio']}x | ¥{s.get('price', 0):,.0f} | {s.get('market_cap_oku', 0)}億円",
                "",
            ])
        
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
                <span style="font-size:0.75rem;color:#888;margin-left:6px;">{str(d.get('name',''))[:12]}</span>
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
# メイン
# ==========================================
st.title("🦅 源太AI ハゲタカSCOPE")
st.markdown(f'<p class="subtitle">中型株（{MARKET_CAP_MIN}億〜{MARKET_CAP_MAX}億円）の出来高急動を自動検知</p>', unsafe_allow_html=True)

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
            st.success("✅ 保存しました")
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
        🔒 設定はあなたのブラウザにのみ保存されます
    </div>
    """, unsafe_allow_html=True)
