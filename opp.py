import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import streamlit.components.v1 as components

# ==========================================
# 1. 페이지 설정 및 데이터 유지
# ==========================================
st.set_page_config(page_title="S-ATM 🏧", page_icon="🏧", layout="wide")

if 'seed' not in st.session_state: st.session_state.seed = 37000.0
if 'qty' not in st.session_state: st.session_state.qty = 77
if 'avg' not in st.session_state: st.session_state.avg = 115.76
if 'step' not in st.session_state: st.session_state.step = 2

st.sidebar.markdown("### 🏧 나의 계좌 정보")
seed = st.sidebar.number_input("1. 총 투자 원금 ($)", value=st.session_state.seed, step=100.0)
qty = st.sidebar.number_input("2. 현재 보유 수량 (주)", value=st.session_state.qty, step=1)
avg = st.sidebar.number_input("3. 나의 현재 평단가 ($)", value=st.session_state.avg, step=0.01)
step = st.sidebar.select_slider("4. 다음 매수 회차", options=[1, 2, 3], value=st.session_state.step)

st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    tickers = [TICKER, "USDKRW=X"]
    try:
        raw_data = yf.download(tickers, period="30d", progress=False)['Close']
        return raw_data.dropna() if not raw_data.empty else None
    except: return None

data = get_market_data()

# ==========================================
# 3. 실시간 계산 (구글 시트 방식 ddof=0 적용)
# ==========================================
if data is not None and not data.empty and len(data) >= 2:
    last_close = float(data[TICKER].iloc[-1])
    rate = float(data['USDKRW=X'].iloc[-1])
    
    used_cash_usd = qty * avg
    profit_loss_usd = (last_close - avg) * qty
    profit_loss_krw = profit_loss_usd * rate
    return_rate = (profit_loss_usd / used_cash_usd * 100) if used_cash_usd > 0 else 0
    
    # [핵심 수정] ddof=0을 사용하여 구글 시트와 100% 일치 시킴 (16년 백테스트 우승 로직)
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std(ddof=0) if len(returns) >= N_SIGMA else 0
    
    buy_loc = last_close * (1 + BUY_MULT * sigma)
    sell_loc = last_close * (1 + SELL_MULT * sigma)
    
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining_usd = seed - used_cash_usd
    buy_qty = int(min(target_usd, remaining_usd) / buy_loc) if buy_loc > 0 else 0

    # ------------------------------------------
    # 💸 [수익 잭팟 효과] 지폐 비 & 황금 글로우
    # ------------------------------------------
    if profit_loss_krw >= 100000:
        components.html(
            """
            <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
            <script>
                function rain() {
                    var end = Date.now() + (3 * 1000);
                    var ems = ['💸', '💵', '💰', '🏧'];
                    (function frame() {
                        confetti({particleCount: 5, angle: 60, spread: 55, origin: { x: 0, y: 0.5 }, shapes: ['text'], shapeOptions: { text: { value: ems[Math.floor(Math.random() * ems.length)] } }, scalar: 3});
                        confetti({particleCount: 5, angle: 120, spread: 55, origin: { x: 1, y: 0.5 }, shapes: ['text'], shapeOptions: { text: { value: ems[Math.floor(Math.random() * ems.length)] } }, scalar: 3});
                        if (Date.now() < end) requestAnimationFrame(frame);
                    }());
                }
                setTimeout(rain, 500);
            </script>
            """, height=300,
        )
        st.markdown("<style>@keyframes glow {0%{border-color:#FFD700;box-shadow:0 0 10px #FFD700;}50%{border-color:#FFA500;box-shadow:0 0 30px #FFA500;}100%{border-color:#FFD700;box-shadow:0 0 10px #FFD700;}}[data-testid='stAppViewContainer']{border:10px solid #FFD700;animation:glow 2s infinite alternate;box-sizing:border-box;}</style>", unsafe_allow_html=True)
        st.success(f"🏆 **수익금 {profit_loss_krw:,.0f}원 돌파!** 🏧 돈 비가 내립니다! 💸")

    # ==========================================
    # 4. 화면 구성
    # ==========================================
    st.title("📟 UPRO 실전 매매 터미널")
    st.divider()
    o1, o2 = st.columns(2)
    with o1:
        st.markdown(f"""<div style="background-color:rgba(255,75,75,0.1);padding:20px;border-radius:10px;border-left:10px solid #FF4B4B;">
            <h3 style="color:#FF4B4B;margin:0;">🔵 매수 LOC (Step {step})</h3>
            <h1 style="margin:10px 0;">${buy_loc:.2f}</h1>
            <h4>주문 수량: {buy_qty}주 <small>(약 {buy_loc*rate*buy_qty:,.0f}원)</small></h4>
        </div>""", unsafe_allow_html=True)
    with o2:
        st.markdown(f"""<div style="background-color:rgba(27,107,255,0.1);padding:20px;border-radius:10px;border-left:10px solid #1B6BFF;">
            <h3 style="color:#1B6BFF;margin:0;">🔴 매도 LOC (전량)</h3>
            <h1 style="margin:10px 0;">${sell_loc:.2f}</h1>
            <h4>주문 수량: {qty}주 <small>(약 {sell_loc*rate*qty:,.0f}원)</small></h4>
        </div>""", unsafe_allow_html=True)

    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"${last_close:,.2f}", f"{rate:,.1f}원")
    c2.metric("원화 수익금", f"{profit_loss_krw:+,.0f}원", f"{return_rate:+.2f}%")
    c3.metric("남은 현금", f"${remaining_usd:,.2f}", f"{remaining_usd*rate:,.0f}원")

    st.divider()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index[-15:], y=data[TICKER].tail(15), mode='lines+markers', name='현재가', line=dict(color='#00FF00', width=2)))
    
    for l in [{"y": sell_loc, "c": "#1B6BFF", "t": "매도 LOC"}, {"y": avg, "c": "white", "t": "내 평단가"}, {"y": buy_loc, "c": "#FF4B4B", "t": "매수 LOC"}]:
        fig.add_hline(y=l['y'], line_dash="dot", line_color=l['c'], line_width=2)
        fig.add_annotation(x=1.02, y=l['y'], xref="paper", yref="y", text=f"<b>{l['t']}<br>${l['y']:.2f}</b>", showarrow=False, font=dict(size=13, color=l['c']), align="left", xanchor="left")

    fig.update_layout(template="plotly_dark", height=550, margin=dict(l=10, r=120, t=50, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("데이터 로딩 중...")