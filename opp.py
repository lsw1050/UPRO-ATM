import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import pytz
import numpy as np
import streamlit.components.v1 as components

# ==========================================
# 1. 페이지 설정 및 디자인 (네이비 배경 + 흰색 글씨)
# ==========================================
st.set_page_config(page_title="S-ATM 🏧", page_icon="🏧", layout="wide")

# [고대비 네이비 디자인 CSS]
st.markdown("""
<style>
    /* 배경: 깊은 네이비 그라데이션 */
    .stApp { 
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
        color: #FFFFFF; 
    }
    
    /* 사이드바: 더 어두운 네이비 */
    [data-testid="stSidebar"] { 
        background-color: #020617; 
        border-right: 1px solid #334155; 
    }
    
    /* 모든 글자를 선명한 흰색으로 */
    h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown { 
        color: #FFFFFF !important; 
        font-family: 'Pretendard', -apple-system, sans-serif;
    }
    
    /* 주문 카드: 선명한 테두리와 배경 */
    .order-box {
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 20px;
        text-align: center;
        border: 2px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    }
    
    /* 가격 숫자: 압도적 크기와 선명도 */
    .big-price {
        font-size: 68px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        margin: 10px 0;
    }

    /* 지표(Metric) 글자색 보정 */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 36px !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #CBD5E1 !important; font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

# [세션 관리]
if 'seed' not in st.session_state: st.session_state.seed = 37000.0
if 'qty' not in st.session_state: st.session_state.qty = 77
if 'avg' not in st.session_state: st.session_state.avg = 115.76
if 'step' not in st.session_state: st.session_state.step = 2

# [사이드바 설정]
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🏧</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>계좌 설정</h2>", unsafe_allow_html=True)
    st.divider()
    seed = st.number_input("💰 총 원금 ($)", value=st.session_state.seed, step=100.0)
    qty = st.number_input("📦 보유 수량 (주)", value=st.session_state.qty, step=1)
    avg = st.number_input("🏷️ 나의 평단 ($)", value=st.session_state.avg, step=0.01)
    step = st.select_slider("🎯 매수 회차", options=[1, 2, 3], value=st.session_state.step)
    st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    try:
        raw_data = yf.download([TICKER, "USDKRW=X"], period="30d", progress=False)
        if raw_data.empty: return None
        data_close = raw_data['Close'] if isinstance(raw_data.columns, pd.MultiIndex) else raw_data[['Close']]
        return data_close.dropna()
    except: return None

data = get_market_data()

# ==========================================
# 3. 메인 화면 구성
# ==========================================
if data is not None and not data.empty and len(data) >= 2:
    # 계산 로직
    last_close = float(data[TICKER].iloc[-1])
    rate = float(data['USDKRW=X'].iloc[-1])
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std(ddof=0)
    
    buy_loc = last_close * (1 + BUY_MULT * sigma)
    sell_loc = last_close * (1 + SELL_MULT * sigma)
    
    profit_loss_krw = (last_close - avg) * qty * rate
    return_rate = ((last_close - avg) / avg * 100) if avg > 0 else 0
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining_usd = seed - (qty * avg)
    buy_qty = int(min(target_usd, remaining_usd) / buy_loc) if buy_loc > 0 else 0

    # 제목
    st.markdown("<h1 style='text-align: center; color: #38bdf8; font-size: 48px;'>UPRO 매매 터미널</h1>", unsafe_allow_html=True)
    st.write("")

    # [1단계] 주문 카드 (네이비 배경과 대비되는 선명한 색상)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="order-box" style="background-color: rgba(220, 38, 38, 0.2); border-color: #ef4444;">
            <h2 style="color: #fca5a5 !important; margin: 0;">🔵 매수 LOC ({step}회차)</h2>
            <div class="big-price">${buy_loc:.2f}</div>
            <p style="font-size: 24px; font-weight: bold;">주문 수량: {buy_qty}주</p>
            <p style="color: #e2e8f0 !important;">(약 {buy_loc*rate*buy_qty:,.0f}원)</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("📋 매수 정보 복사", key="b_cp", use_container_width=True)

    with c2:
        st.markdown(f"""
        <div class="order-box" style="background-color: rgba(37, 99, 235, 0.2); border-color: #3b82f6;">
            <h2 style="color: #93c5fd !important; margin: 0;">🔴 매도 LOC (전량)</h2>
            <div class="big-price">${sell_loc:.2f}</div>
            <p style="font-size: 24px; font-weight: bold;">주문 수량: {qty}주</p>
            <p style="color: #e2e8f0 !important;">(약 {sell_loc*rate*qty:,.0f}원)</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("📋 매도 정보 복사", key="s_cp", use_container_width=True)

    # [2단계] 계좌 지표 (선명한 흰색 수치)
    st.write("")
    st.divider()
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("💹 실시간 현재가", f"${last_close:,.2f}", f"{rate:,.1f}원")
    with m2:
        st.metric("💰 원화 수익", f"{profit_loss_krw:+,.0f}원", f"{return_rate:+.2f}%")
    with m3:
        st.metric("💵 가용 예수금", f"${remaining_usd:,.2f}", f"약 {remaining_usd*rate:,.0f}원", delta_color="off")

    # [3단계] 가격 가이드 차트
    st.write("")
    st.subheader("📈 가격선 가이드")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index[-20:], y=data[TICKER].tail(20), mode='lines+markers', line=dict(color='#22c55e', width=4)))
    
    # 가이드라인 (차트에서도 글씨가 잘 보이게 설정)
    for l in [{"y": sell_loc, "color": "#3b82f6", "text": "매도선"}, {"y": avg, "color": "#FFFFFF", "text": "평단선"}, {"y": buy_loc, "color": "#ef4444", "text": "매수선"}]:
        fig.add_hline(y=l['y'], line_dash="solid", line_color=l['color'], line_width=2)
        fig.add_annotation(x=1, y=l['y'], xref="paper", yref="y", text=f"<b>{l['text']}</b>", showarrow=False, font=dict(color=l['color'], size=14), bgcolor="rgba(0,0,0,0.5)")

    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # 수익 잭팟 효과 (기존 유지)
    if profit_loss_krw >= 100000:
        components.html("""<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script><script>function rain(){var end=Date.now()+(3*1000);var ems=['💸','💵','💰','🏧'];(function frame(){confetti({particleCount:5,angle:60,spread:55,origin:{x:0,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});confetti({particleCount:5,angle:120,spread:55,origin:{x:1,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});if(Date.now()<end)requestAnimationFrame(frame);}());}setTimeout(rain, 500);</script>""", height=0)
        st.markdown("<style>[data-testid='stAppViewContainer']{border:10px solid #FFD700; box-sizing:border-box;}</style>", unsafe_allow_html=True)

else:
    st.markdown("<div style='text-align: center; padding-top: 100px;'><h2 style='color: white;'>📡 데이터를 연결 중입니다...</h2></div>", unsafe_allow_html=True)