import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import pytz
import numpy as np
import streamlit.components.v1 as components

# ==========================================
# 1. 페이지 설정 및 디자인 (전문 대시보드 스타일)
# ==========================================
st.set_page_config(page_title="S-ATM 🏧", page_icon="🏧", layout="wide")

# [고급 CSS 주입]
st.markdown("""
<style>
    /* 배경 및 전역 폰트 */
    .stApp { background: #0f172a; color: #FFFFFF; font-family: 'Pretendard', sans-serif; }
    [data-testid="stSidebar"] { background-color: #020617; border-right: 1px solid #1e293b; }
    
    /* 카드 디자인: Glassmorphism 스타일 */
    .glass-panel {
        background: rgba(30, 41, 59, 0.7);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 20px;
    }
    
    /* 주문 박스 강조 */
    .order-box {
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        border: 2px solid;
        transition: transform 0.3s ease;
    }
    .order-box:hover { transform: translateY(-5px); }
    
    /* 가격 텍스트 네온 효과 */
    .neon-text {
        font-size: 72px !important;
        font-weight: 900 !important;
        text-shadow: 0 0 10px rgba(255,255,255,0.3);
        margin: 10px 0;
    }
    
    /* 상단 상태 바 */
    .status-bar {
        padding: 8px 15px;
        border-radius: 50px;
        font-size: 14px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# [세션 관리]
if 'seed' not in st.session_state: st.session_state.seed = 37000.0
if 'qty' not in st.session_state: st.session_state.qty = 77
if 'avg' not in st.session_state: st.session_state.avg = 115.76
if 'step' not in st.session_state: st.session_state.step = 2

# [사이드바]
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🏧</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>계좌 정보 설정</h2>", unsafe_allow_html=True)
    st.divider()
    seed = st.number_input("💰 총 원금 (달러)", value=st.session_state.seed, step=100.0)
    qty = st.number_input("📦 보유 수량 (주)", value=st.session_state.qty, step=1)
    avg = st.number_input("🏷️ 나의 평단 ($)", value=st.session_state.avg, step=0.01)
    step = st.select_slider("🎯 매수 회차", options=[1, 2, 3], value=st.session_state.step)
    st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집 및 '확정 종가' 추출 로직 (유지)
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    try:
        raw = yf.download([TICKER, "USDKRW=X"], period="60d", progress=False)
        if raw.empty: return None
        df = raw['Close'] if isinstance(raw.columns, pd.MultiIndex) else raw[['Close']]
        df = df.dropna()
        now_ny = datetime.now(pytz.timezone('America/New_York'))
        last_date = df.index[-1].date()
        if last_date >= now_ny.date():
            if now_ny.hour < 16: df_final = df.iloc[:-1]
            else: df_final = df
        else: df_final = df
        return df_final, df
    except: return None

market_result = get_market_data()

# ==========================================
# 3. 메인 화면 구성
# ==========================================
if market_result:
    final_data, full_data = market_result
    base_price = float(final_data[TICKER].iloc[-1])
    live_price = float(full_data[TICKER].iloc[-1])
    rate = float(full_data['USDKRW=X'].iloc[-1])
    
    # 시그마 계산 (ddof=0)
    returns = final_data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std(ddof=0)
    
    buy_loc = base_price * (1 + BUY_MULT * sigma)
    sell_loc = base_price * (1 + SELL_MULT * sigma)
    
    # 지표 계산
    profit_loss_krw = (live_price - avg) * qty * rate
    return_rate = ((live_price - avg) / avg * 100) if avg > 0 else 0
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining_usd = seed - (qty * avg)
    buy_qty = int(min(target_usd, remaining_usd) / buy_loc) if buy_loc > 0 else 0

    # [헤더 영역]
    now_ny = datetime.now(pytz.timezone('America/New_York'))
    is_open = 9 <= now_ny.hour < 16 # 단순화된 장중 체크
    status_color = "#22c55e" if is_open else "#94a3b8"
    status_text = "MARKET OPEN" if is_open else "MARKET CLOSED"

    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.markdown(f"<h1 style='color: #38bdf8; margin:0;'>UPRO SIGNAL</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #94a3b8;'>산출 기준: {final_data.index[-1].strftime('%Y-%m-%d')} 확정 데이터</p>", unsafe_allow_html=True)
    with col_status:
        st.markdown(f"<div class='status-bar' style='background: {status_color}22; color: {status_color}; border: 1px solid {status_color};'>● {status_text}</div>", unsafe_allow_html=True)

    # [주문 카드 영역]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="order-box" style="background-color: rgba(239, 68, 68, 0.15); border-color: #ef4444;">
            <p style="color: #fca5a5 !important; font-weight: 600; font-size: 18px; margin: 0;">🔴 매수 LOC 구매 ({step}회차)</p>
            <div class="neon-text">${buy_loc:.2f}</div>
            <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 10px;">
                <span style="font-size: 24px; font-weight: 800; color: white;">{buy_qty}주 구매</span>
                <span style="color: #cbd5e1;"> (약 {buy_loc*rate*buy_qty:,.0f}원)</span>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("📋 매수 주문 정보 복사", key="b_cp", use_container_width=True):
            st.toast("클립보드에 복사되었습니다!")

    with c2:
        st.markdown(f"""<div class="order-box" style="background-color: rgba(59, 130, 246, 0.15); border-color: #3b82f6;">
            <p style="color: #93c5fd !important; font-weight: 600; font-size: 18px; margin: 0;">🔵 매도 LOC 판매 (전량)</p>
            <div class="neon-text">${sell_loc:.2f}</div>
            <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 10px;">
                <span style="font-size: 24px; font-weight: 800; color: white;">{qty}주 판매</span>
                <span style="color: #cbd5e1;"> (약 {sell_loc*rate*qty:,.0f}원)</span>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("📋 매도 주문 정보 복사", key="s_cp", use_container_width=True):
            st.toast("클립보드에 복사되었습니다!")

    # [가격 위치 게이지]
    st.write("")
    total_range = sell_loc - buy_loc
    price_pos = (live_price - buy_loc) / total_range if total_range != 0 else 0.5
    price_pos = max(0, min(1, price_pos))
    
    st.markdown(f"<p style='text-align: center; color: #94a3b8; font-size: 14px; margin-bottom: 5px;'>현재가 위치: 매수선 ↔ 매도선</p>", unsafe_allow_html=True)
    st.progress(price_pos)

    # [대시보드 메트릭 패널]
    st.write("")
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💹 현재가", f"${live_price:,.2f}", f"{rate:,.1f}원")
    m2.metric("💰 원화 수익", f"{profit_loss_krw:+,.0f}원", f"{return_rate:+.2f}%")
    m3.metric("💵 가용 예수금", f"${remaining_usd:,.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

    # [차트 섹션]
    st.subheader("📉 실시간 가격 가이드라인")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=full_data.index[-25:], y=full_data[TICKER].tail(25), 
                             mode='lines+markers', line=dict(color='#22c55e', width=3),
                             marker=dict(size=6, color='#0f172a', line=dict(width=2, color='#22c55e'))))
    
    for l in [{"y": sell_loc, "color": "#3b82f6", "text": "매도선"}, {"y": avg, "color": "#FFFFFF", "text": "평단선"}, {"y": buy_loc, "color": "#ef4444", "text": "매수선"}]:
        fig.add_hline(y=l['y'], line_dash="solid", line_color=l['color'], line_width=2, opacity=0.8)
        fig.add_annotation(x=1, y=l['y'], xref="paper", yref="y", text=f"<b>{l['text']} ${l['y']:.2f}</b>", 
                           showarrow=False, font=dict(color=l['color'], size=13), bgcolor="rgba(15, 23, 42, 0.9)", bordercolor=l['color'], borderwidth=1, borderpad=4)

    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10), 
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      xaxis=dict(showgrid=False), yaxis=dict(gridcolor='rgba(255,255,255,0.05)'))
    st.plotly_chart(fig, use_container_width=True)

    # 잭팟 효과
    if profit_loss_krw >= 100000:
        components.html("""<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script><script>function rain(){var end=Date.now()+(3*1000);var ems=['💸','💵','💰','🏧'];(function frame(){confetti({particleCount:5,angle:60,spread:55,origin:{x:0,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});confetti({particleCount:5,angle:120,spread:55,origin:{x:1,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});if(Date.now()<end)requestAnimationFrame(frame);}());}setTimeout(rain, 500);</script>""", height=0)

else:
    st.markdown("<div style='text-align: center; padding: 100px;'><h2 style='color: #94a3b8;'>📡 시장 데이터를 연결 중입니다...</h2></div>", unsafe_allow_html=True)