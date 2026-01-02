import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import pytz
import numpy as np
import streamlit.components.v1 as components
import json

# ==========================================
# 1. 페이지 설정 및 전역 스타일
# ==========================================
st.set_page_config(page_title="S-ATM 🏧", page_icon="🏧", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%); border-right: 1px solid rgba(255,255,255,0.1); }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; border-radius: 12px; padding: 12px 24px;
        font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

if 'seed' not in st.session_state: st.session_state.seed = 37000.0
if 'qty' not in st.session_state: st.session_state.qty = 77
if 'avg' not in st.session_state: st.session_state.avg = 115.76
if 'step' not in st.session_state: st.session_state.step = 2

with st.sidebar:
    st.markdown("<div style='text-align: center; padding: 20px 0;'><h1 style='font-size: 48px; margin: 0;'>🏧</h1><h3 style='color: #00d4ff; margin: 10px 0;'>나의 계좌 정보</h3></div>", unsafe_allow_html=True)
    seed = st.number_input("💰 총 투자 원금 (달러)", value=st.session_state.seed, step=100.0)
    qty = st.number_input("📊 현재 보유 수량 (주)", value=st.session_state.qty, step=1)
    avg = st.number_input("💵 나의 현재 평단가 ($)", value=st.session_state.avg, step=0.01)
    step = st.select_slider("🎯 다음 매수 회차", options=[1, 2, 3], value=st.session_state.step)
    st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집 및 '확정 종가' 분리 로직
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    try:
        # 넉넉하게 60일치 데이터 수집
        raw = yf.download([TICKER, "USDKRW=X"], period="60d", progress=False)
        if raw.empty: return None
        df = raw['Close'] if isinstance(raw.columns, pd.MultiIndex) else raw[['Close']]
        df = df.dropna()
        
        # [핵심] 현재 시간이 미국 장중이라면 마지막 줄(실시간 봉)을 제외하고 계산용 데이터 생성
        now_ny = datetime.now(pytz.timezone('America/New_York'))
        last_date = df.index[-1].date()
        
        # 오늘 날짜 데이터가 들어왔는데 아직 장이 마감(오전 4시 EST) 전이라면
        if last_date >= now_ny.date() and now_ny.hour < 16:
            df_confirmed = df.iloc[:-1] # 어제까지의 확정 데이터
        else:
            df_confirmed = df # 이미 장이 끝났다면 오늘 데이터가 확정 종가
            
        return df_confirmed, df # (확정 데이터, 실시간 포함 전체 데이터)
    except: return None

market_result = get_market_data()

# ==========================================
# 3. 실시간 계산 및 화면 구성
# ==========================================
if market_result:
    final_data, full_data = market_result
    
    # [계산의 기준: 무조건 확정된 종가]
    base_price = float(final_data[TICKER].iloc[-1]) # 기준 종가
    live_price = float(full_data[TICKER].iloc[-1]) # 현재 실시간 가격
    rate = float(full_data['USDKRW=X'].iloc[-1])
    
    # 시그마 계산 (확정 데이터 기준, ddof=0)
    returns = final_data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std(ddof=0) if len(returns) >= N_SIGMA else 0
    
    # LOC 주문가 산출 (base_price가 전일 종가이므로 하루 종일 고정됨)
    buy_loc = base_price * (1 + BUY_MULT * sigma)
    sell_loc = base_price * (1 + SELL_MULT * sigma)
    
    # 수익 및 수량 계산
    profit_loss_krw = (live_price - avg) * qty * rate
    return_rate = ((live_price - avg) / (qty * avg) * 100) if (qty * avg) > 0 else 0
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining_usd = seed - (qty * avg)
    buy_qty = int(min(target_usd, remaining_usd) / buy_loc) if buy_loc > 0 else 0

    # 헤더
    st.markdown(f"""<div style="text-align: center; padding: 20px 0 30px 0;">
        <h1 style="font-size: 42px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 50%, #f472b6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;">📟 UPRO S-ATM</h1>
        <p style="color: #6b7280; margin-top: 10px; font-size: 14px;">산출 기준일: {final_data.index[-1].strftime('%Y-%m-%d')} (종가: ${base_price:.2f})</p>
    </div>""", unsafe_allow_html=True)

    # LOC 주문 카드
    o1, o2 = st.columns(2)
    with o1:
        st.markdown(f"""<div style="background: linear-gradient(135deg, rgba(239,68,68,0.2) 0%, rgba(239,68,68,0.05) 100%); border: 2px solid #ef4444; border-radius: 20px; padding: 28px; text-align: center;">
            <div style="color: #ef4444; font-weight: 600; font-size: 18px; margin-bottom: 10px;">🔴 매수 LOC 주문 ({step}회차)</div>
            <div style="font-size: 56px; font-weight: 900; color: #ffffff;">${buy_loc:.2f}</div>
            <div style="color: #ffffff; font-size: 20px; margin-top: 15px;">주문 수량: <b>{buy_qty}주</b></div>
            <div style="color: #6b7280; font-size: 14px;">(약 {buy_loc*rate*buy_qty:,.0f}원)</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📋 매수 주문 복사", use_container_width=True):
            st.code(f"UPRO {buy_qty}주 ${buy_loc:.2f} LOC 매수")

    with o2:
        st.markdown(f"""<div style="background: linear-gradient(135deg, rgba(59,130,246,0.2) 0%, rgba(59,130,246,0.05) 100%); border: 2px solid #3b82f6; border-radius: 20px; padding: 28px; text-align: center;">
            <div style="color: #3b82f6; font-weight: 600; font-size: 18px; margin-bottom: 10px;">🔵 매도 LOC 주문 (전량)</div>
            <div style="font-size: 56px; font-weight: 900; color: #ffffff;">${sell_loc:.2f}</div>
            <div style="color: #ffffff; font-size: 20px; margin-top: 15px;">주문 수량: <b>{qty}주</b></div>
            <div style="color: #6b7280; font-size: 14px;">(약 {sell_loc*rate*qty:,.0f}원)</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📋 매도 주문 복사", use_container_width=True):
            st.code(f"UPRO {qty}주 ${sell_loc:.2f} LOC 매도")

    # 주요 지표
    st.write("")
    m1, m2, m3 = st.columns(3)
    p_color = "#10b981" if profit_loss_krw >= 0 else "#ef4444"
    
    with m1:
        st.markdown(f"<div style='background:rgba(255,255,255,0.03); border-radius:16px; padding:20px; text-align:center;'><div style='color:#6b7280;font-size:14px;'>💹 현재가</div><div style='color:#ffffff;font-size:28px;font-weight:700;'>${live_price:,.2f}</div><div style='color:#6b7280;font-size:13px;'>₩{rate:,.1f}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div style='background:rgba(255,255,255,0.03); border-radius:16px; padding:20px; text-align:center; border: 1px solid {p_color}40;'><div style='color:#6b7280;font-size:14px;'>💰 원화 수익금</div><div style='color:{p_color};font-size:28px;font-weight:700;'>{profit_loss_krw:+,.0f}원</div><div style='color:{p_color};font-size:13px;'>{return_rate:+.2f}%</div></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div style='background:rgba(255,255,255,0.03); border-radius:16px; padding:20px; text-align:center;'><div style='color:#6b7280;font-size:14px;'>💵 가용 예수금</div><div style='color:#ffffff;font-size:28px;font-weight:700;'>${remaining_usd:,.2f}</div><div style='color:#6b7280;font-size:13px;'>약 {remaining_usd*rate:,.0f}원</div></div>", unsafe_allow_html=True)

    # 차트
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=full_data.index[-15:], y=full_data[TICKER].tail(15), mode='lines+markers', line=dict(color='#10b981', width=3)))
    for l in [{"y": sell_loc, "color": "#3b82f6", "text": "매도선"}, {"y": avg, "color": "#fbbf24", "text": "평단선"}, {"y": buy_loc, "color": "#ef4444", "text": "매수선"}]:
        fig.add_hline(y=l['y'], line_dash="dot", line_color=l['color'], line_width=2)
        fig.add_annotation(x=1.02, y=l['y'], xref="paper", yref="y", text=f"<b>{l['text']} ${l['y']:.2f}</b>", showarrow=False, font=dict(size=12, color=l['color']), align="left", xanchor="left")
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=120, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,0.02)')
    st.plotly_chart(fig, use_container_width=True)

    # 잭팟 효과
    if profit_loss_krw >= 100000:
        components.html("""<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script><script>function rain(){var end=Date.now()+(3*1000);var ems=['💸','💵','💰','🏧','🤑'];(function frame(){confetti({particleCount:5,angle:60,spread:55,origin:{x:0,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});confetti({particleCount:5,angle:120,spread:55,origin:{x:1,y:0.5},shapes:['text'],shapeOptions:{text:{value:ems[Math.floor(Math.random()*ems.length)]}},scalar:3});if(Date.now()<end)requestAnimationFrame(frame);}());}setTimeout(rain, 500);</script>""", height=0)
        st.markdown("<style>[data-testid='stAppViewContainer']{border:10px solid #FFD700; box-sizing:border-box;}</style>", unsafe_allow_html=True)
else:
    st.error("데이터 로딩 중...")