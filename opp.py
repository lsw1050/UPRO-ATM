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

st.markdown("""
<style>
    /* 배경: 짙은 네이비 (가독성 유지) */
    .stApp { background: #0f172a; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #020617; border-right: 1px solid #334155; }
    
    /* 모든 글자를 선명한 흰색으로 고정 */
    h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown { 
        color: #FFFFFF !important; 
        font-family: 'Pretendard', sans-serif;
    }
    
    /* 주문 카드: 고대비 화이트 테두리 */
    .order-box {
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 20px;
        text-align: center;
        border: 3px solid #FFFFFF;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    
    /* 가격 숫자: 압도적 크기 (흰색) */
    .big-price {
        font-size: 72px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
        margin: 10px 0;
    }

    /* 메트릭 수치 가독성 */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 36px !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #CBD5E1 !important; }
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
    seed = st.number_input("💰 총 원금 (달러)", value=st.session_state.seed, step=100.0)
    qty = st.number_input("📦 보유 수량 (주)", value=st.session_state.qty, step=1)
    avg = st.number_input("🏷️ 나의 평단 ($)", value=st.session_state.avg, step=0.01)
    step = st.select_slider("🎯 매수 회차", options=[1, 2, 3], value=st.session_state.step)
    st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집 및 '확정 종가' 추출 로직
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    try:
        # 넉넉하게 60일치 데이터 수집
        raw = yf.download([TICKER, "USDKRW=X"], period="60d", progress=False)
        if raw.empty: return None
        
        # 'Close' 데이터만 추출
        df = raw['Close'] if isinstance(raw.columns, pd.MultiIndex) else raw[['Close']]
        df = df.dropna()
        
        # [핵심] 현재 시간이 장중(오전 9시 30분 ~ 오후 4시 EST)이거나, 
        # 마지막 데이터 날짜가 오늘 날짜라면 '미완성 봉'으로 간주하고 제외합니다.
        now_ny = datetime.now(pytz.timezone('America/New_York'))
        last_date = df.index[-1].date()
        
        # 오늘 날짜의 데이터가 포함되어 있다면 (장중 실시간 데이터)
        if last_date >= now_ny.date():
            # 장이 마감(오후 4시)되기 전이라면 마지막 줄을 버리고 '어제 종가'를 기준으로 삼습니다.
            if now_ny.hour < 16:
                df_final = df.iloc[:-1]
            else:
                df_final = df # 장 마감 후라면 오늘의 종가가 확정된 것이므로 그대로 사용
        else:
            df_final = df # 마지막 데이터가 과거라면 그대로 사용
            
        return df_final, df # (확정 데이터, 전체 데이터) 반환
    except: return None

market_result = get_market_data()

# ==========================================
# 3. 메인 화면 및 계산
# ==========================================
if market_result:
    final_data, full_data = market_result
    
    # [계산의 기준은 무조건 '확정된 마지막 종가']
    base_price = float(final_data[TICKER].iloc[-1]) # 이것이 시트의 '마지막 종가'가 됩니다.
    live_price = float(full_data[TICKER].iloc[-1]) # 메트릭에 표시할 현재가
    rate = float(full_data['USDKRW=X'].iloc[-1])
    
    # 시그마 계산 (확정 데이터의 마지막 2일 등락률 기반, ddof=0)
    returns = final_data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std(ddof=0)
    
    # LOC 가격 산출 (시트와 100% 동일 공식)
    buy_loc = base_price * (1 + BUY_MULT * sigma)
    sell_loc = base_price * (1 + SELL_MULT * sigma)
    
    # 기타 계좌 현황
    profit_loss_krw = (live_price - avg) * qty * rate
    return_rate = ((live_price - avg) / avg * 100) if avg > 0 else 0
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining_usd = seed - (qty * avg)
    buy_qty = int(min(target_usd, remaining_usd) / buy_loc) if buy_loc > 0 else 0

    # UI 출력
    st.markdown("<h1 style='text-align: center; color: #38bdf8; font-size: 48px;'>UPRO 매매</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #FFFFFF;'>산출 기준일: {final_data.index[-1].strftime('%Y-%m-%d')} (확정 종가: ${base_price:.2f})</p>", unsafe_allow_html=True)

    # 주문 카드 (고대비 흰색 글씨)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="order-box" style="background-color: rgba(220, 38, 38, 0.3); border-color: #ef4444;">
            <h2 style="color: #FFFFFF !important; margin: 0;">🔵 매수 LOC ({step}회차)</h2>
            <div class="big-price">${buy_loc:.2f}</div>
            <p style="font-size: 26px; font-weight: bold; color: white;">주문 수량: {buy_qty}주 구매</p>
        </div>""", unsafe_allow_html=True)
        st.button("📋 매수 복사", key="b_cp", use_container_width=True)

    with c2:
        st.markdown(f"""<div class="order-box" style="background-color: rgba(37, 99, 235, 0.3); border-color: #3b82f6;">
            <h2 style="color: #FFFFFF !important; margin: 0;">🔴 매도 LOC (전량)</h2>
            <div class="big-price">${sell_loc:.2f}</div>
            <p style="font-size: 26px; font-weight: bold; color: white;">주문 수량: {qty}주 판매</p>
        </div>""", unsafe_allow_html=True)
        st.button("📋 매도 복사", key="s_cp", use_container_width=True)

    # 하단 지표
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("💹 실시간 현재가", f"${live_price:,.2f}", f"{rate:,.1f}원")
    m2.metric("💰 원화 수익", f"{profit_loss_krw:+,.0f}원", f"{return_rate:+.2f}%")
    m3.metric("💵 가용 예수금", f"${remaining_usd:,.2f}", f"약 {remaining_usd*rate:,.0f}원", delta_color="off")

    # 차트 가이드
    st.subheader("📈 가격선 가이드")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=full_data.index[-20:], y=full_data[TICKER].tail(20), mode='lines+markers', line=dict(color='#22c55e', width=4)))
    for l in [{"y": sell_loc, "color": "#3b82f6", "text": "매도선"}, {"y": avg, "color": "#FFFFFF", "text": "평단선"}, {"y": buy_loc, "color": "#ef4444", "text": "매수선"}]:
        fig.add_hline(y=l['y'], line_dash="solid", line_color=l['color'], line_width=2)
        fig.add_annotation(x=1, y=l['y'], xref="paper", yref="y", text=f"<b>{l['text']} ${l['y']:.2f}</b>", showarrow=False, font=dict(color=l['color'], size=14), bgcolor="rgba(0,0,0,0.8)")
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # 잭팟 효과 (10만원 이상 수익 시)
    if profit_loss_krw >= 100000:
        components.html("""<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script><script>function rain(){var end=Date.now()+(3*1000);var ems=['💸','💵','💰','🏧'];(function frame(){confetti({particleCount:5,angle:60,spread:55,origin:{x:0,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});confetti({particleCount:5,angle:120,spread:55,origin:{x:1,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});if(Date.now()<end)requestAnimationFrame(frame);}());}setTimeout(rain, 500);</script>""", height=0)
else:
    st.error("데이터 연결 실패. 인터넷 상태를 확인하세요.")