import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정 및 세션 상태 초기화 (로컬 유지용)
# ==========================================
st.set_page_config(page_title="UPRO 실전 매매 터미널", page_icon="🏦", layout="wide")

# [중요] 사용자님의 현재 데이터를 기본값으로 설정 (여기만 고치면 매번 입력 안 해도 됩니다)
DEFAULT_SEED = 37000.0
DEFAULT_QTY = 77
DEFAULT_AVG = 115.76
DEFAULT_STEP = 2

# 세션 상태에 저장 (새로고침 시 값 유지)
if 'seed' not in st.session_state: st.session_state.seed = DEFAULT_SEED
if 'qty' not in st.session_state: st.session_state.qty = DEFAULT_QTY
if 'avg' not in st.session_state: st.session_state.avg = DEFAULT_AVG
if 'step' not in st.session_state: st.session_state.step = DEFAULT_STEP

# 사이드바 입력
st.sidebar.header("⚙️ My Portfolio")
seed = st.sidebar.number_input("Total Seed ($)", value=st.session_state.seed, step=100.0)
qty = st.sidebar.number_input("Holding Qty", value=st.session_state.qty, step=1)
avg = st.sidebar.number_input("Avg Price ($)", value=st.session_state.avg, step=0.01)
step = st.sidebar.select_slider("Current Step", options=[1, 2, 3], value=st.session_state.step)

# 입력값 세션 업데이트
st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집 및 계산
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    tickers = [TICKER, "USDKRW=X"]
    try:
        raw_data = yf.download(tickers, period="30d", progress=False)['Close']
        return raw_data.dropna() if not raw_data.empty else None
    except: return None

data = get_market_data()

if data is not None and len(data) >= 2:
    last_close = float(data[TICKER].iloc[-1])
    prev_close = float(data[TICKER].iloc[-2])
    rate = float(data['USDKRW=X'].iloc[-1])
    
    # 수익 계산
    p_l_usd = (last_close - avg) * qty
    p_l_krw = p_l_usd * rate
    ret_rate = (p_l_usd / (qty * avg) * 100) if qty > 0 else 0
    
    # LOC 계산
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std()
    buy_loc = last_close * (1 + BUY_MULT * sigma)
    sell_loc = last_close * (1 + SELL_MULT * sigma)
    
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining_usd = seed - (qty * avg)
    buy_qty = int(min(target_usd, remaining_usd) / buy_loc) if buy_loc > 0 else 0

    # ==========================================
    # 3. UI 구성 (주문표 상단 배치 + 효과)
    # ==========================================
    
    # [효과] 수익 10만원 이상 시 폭죽 및 황금 테두리
    if p_l_krw >= 100000:
        st.balloons()
        st.markdown("<style>.stApp {border: 6px solid #FFD700;}</style>", unsafe_allow_html=True)
        st.success(f"🎊 목표 달성! 수익 {p_l_krw:,.0f}원 돌파! 🎊")

    st.title("📟 UPRO 실전 매매 터미널")
    st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 환율: {rate:,.2f}원")

    # --- [상단 섹션] 핵심 주문 정보 ---
    st.divider()
    o1, o2 = st.columns(2)
    with o1:
        st.markdown(f"""
        <div style="background-color:rgba(255, 75, 75, 0.1); padding:20px; border-radius:10px; border-left: 8px solid #FF4B4B;">
            <h3 style="color:#FF4B4B; margin:0;">🔵 매수 LOC (Step {step})</h3>
            <h1 style="margin:10px 0;">${buy_loc:.2f}</h1>
            <h4 style="margin:0;">주문 수량: {buy_qty}주 <span style="font-size:14px; color:gray;">(약 {buy_loc*rate*buy_qty:,.0f}원)</span></h4>
        </div>
        """, unsafe_allow_html=True)
    with o2:
        st.markdown(f"""
        <div style="background-color:rgba(27, 107, 255, 0.1); padding:20px; border-radius:10px; border-left: 8px solid #1B6BFF;">
            <h3 style="color:#1B6BFF; margin:0;">🔴 매도 LOC (전량)</h3>
            <h1 style="margin:10px 0;">${sell_loc:.2f}</h1>
            <h4 style="margin:0;">주문 수량: {qty}주 <span style="font-size:14px; color:gray;">(약 {sell_loc*rate*qty:,.0f}원)</span></h4>
        </div>
        """, unsafe_allow_html=True)

    # --- [중단 섹션] 자산 현황 KPI ---
    st.write("")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재가", f"${last_close:,.2f}", f"{((last_close-prev_close)/prev_close*100):+.2f}%")
    m2.metric("원화 수익금", f"{p_l_krw:+,.0f}원", f"{ret_rate:+.2f}%")
    m3.metric("남은 현금", f"${remaining_usd:,.2f}", f"{remaining_usd*rate:,.0f}원", delta_color="off")
    m4.metric("내 평단가", f"${avg:,.2f}", delta_color="off")

    # --- [하단 섹션] 고도화된 차트 (라벨 우측 정렬) ---
    st.divider()
    st.subheader("📈 가격 위치 가이드")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index[-15:], y=data[TICKER].tail(15), mode='lines+markers', name='현재가', line=dict(color='#00FF00')))
    
    # 우측 라벨 가이드라인 설정 (글씨 굵게 + 색상 지정)
    guides = [
        {"y": sell_loc, "color": "#1B6BFF", "name": "매도 LOC"},
        {"y": avg, "color": "white", "name": "내 평단가"},
        {"y": buy_loc, "color": "#FF4B4B", "name": "매수 LOC"}
    ]
    for g in guides:
        fig.add_hline(y=g['y'], line_dash="dot", line_color=g['color'], line_width=2)
        fig.add_annotation(
            x=1.02, y=g['y'], xref="paper", yref="y",
            text=f"<b>{g['name']}<br>${g['y']:.2f}</b>",
            showarrow=False, font=dict(color=g['color'], size=13), align="left", xanchor="left"
        )

    fig.update_layout(template="plotly_dark", height=500, margin=dict(r=120, l=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("데이터 로딩 실패")