import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정 및 테마
# ==========================================
st.set_page_config(page_title="UPRO ATM Bot (USD/KRW)", page_icon="💰", layout="wide")

# 사이드바 설정
st.sidebar.header("⚙️ My Portfolio")
TOTAL_SEED_USD = st.sidebar.number_input("Total Seed ($)", value=37000.0, step=100.0)
HOLDING_QTY = st.sidebar.number_input("Holding Qty (Shares)", value=77)
AVG_PRICE_USD = st.sidebar.number_input("Avg Purchase Price ($)", value=115.76, step=0.01)
CURRENT_STEP = st.sidebar.select_slider("Current Buy Step", options=[1, 2, 3], value=2)

TICKER = "UPRO"
N_SIGMA = 2
BUY_MULT, SELL_MULT = 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집 함수
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    tickers = [TICKER, "USDKRW=X"]
    try:
        raw_data = yf.download(tickers, period="30d", progress=False)['Close']
        if raw_data.empty: return None
        return raw_data.dropna()
    except: return None

data = get_market_data()

# ==========================================
# 3. 로직 계산 및 UI 구성
# ==========================================
if data is not None and not data.empty and len(data) >= 2:
    # 기초 데이터
    last_close_usd = float(data[TICKER].iloc[-1])
    prev_close_usd = float(data[TICKER].iloc[-2])
    exchange_rate = float(data['USDKRW=X'].iloc[-1])
    
    # [USD 계산]
    used_cash_usd = HOLDING_QTY * AVG_PRICE_USD
    remaining_cash_usd = TOTAL_SEED_USD - used_cash_usd
    current_eval_usd = HOLDING_QTY * last_close_usd
    profit_loss_usd = current_eval_usd - used_cash_usd
    return_rate_usd = (profit_loss_usd / used_cash_usd * 100) if used_cash_usd > 0 else 0
    
    # [KRW 계산] - 실시간 환율 적용
    profit_loss_krw = profit_loss_usd * exchange_rate
    current_eval_krw = current_eval_usd * exchange_rate
    used_cash_krw = used_cash_usd * exchange_rate
    
    # 변동성 및 주문값
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std() if len(returns) >= N_SIGMA else 0
    buy_loc_usd = last_close_usd * (1 + BUY_MULT * sigma)
    sell_loc_usd = last_close_usd * (1 + SELL_MULT * sigma)
    
    target_step_usd = TOTAL_SEED_USD * (WEIGHTS[CURRENT_STEP-1] / sum(WEIGHTS))
    buy_qty = int(min(target_step_usd, remaining_cash_usd) / buy_loc_usd) if buy_loc_usd > 0 else 0

    # --- UI 상단 ---
    st.title(f"🚀 {TICKER} ATM 실전 전략")
    st.markdown(f"**실시간 환율:** `1$ = {exchange_rate:,.2f}원` | **업데이트:** `{datetime.now().strftime('%H:%M:%S')}`")

    # --- UI 중단: 주요 지표 (USD & KRW 분리) ---
    st.divider()
    
    # 첫 번째 줄: 달러 기준 성과
    st.subheader("💵 USD Performance (달러 기준)")
    u1, u2, u3, u4 = st.columns(4)
    price_delta = f"{((last_close_usd - prev_close_usd)/prev_close_usd*100):+.2f}%"
    u1.metric("Current Price", f"${last_close_usd:,.2f}", price_delta)
    u2.metric("USD Profit/Loss", f"{return_rate_usd:+.2f}%", f"${profit_loss_usd:+,.2f}")
    u3.metric("Available Cash", f"${remaining_cash_usd:,.2f}")
    u4.metric("Total Equity", f"${(current_eval_usd + remaining_cash_usd):,.2f}")

    # 두 번째 줄: 원화 기준 성과
    st.subheader("🇰🇷 KRW Performance (원화 환산)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("현재가 (원)", f"{last_close_usd * exchange_rate:,.0f}원")
    # 원화 수익금 강조
    k2.metric("원화 수익금", f"{profit_loss_krw:+,.0f}원", f"{return_rate_usd:+.2f}%")
    k3.metric("남은 현금 (원)", f"{remaining_cash_usd * exchange_rate:,.0f}원")
    k4.metric("총 자산 (원)", f"{(current_eval_usd + remaining_cash_usd) * exchange_rate:,.0f}원")

    # --- UI 하단: 차트와 주문표 ---
    st.divider()
    col_chart, col_order = st.columns([2, 1])

    with col_chart:
        st.subheader("📊 Price Trend")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index[-15:], y=data[TICKER].tail(15), 
                                 mode='lines+markers', name='Price', line=dict(color='#1f77b4', width=3)))
        
        # 가이드 라인
        fig.add_hline(y=AVG_PRICE_USD, line_dash="dash", line_color="#FFD700", annotation_text="My Avg")
        fig.add_hline(y=buy_loc_usd, line_dash="dot", line_color="#007bff", annotation_text="Buy LOC")
        fig.add_hline(y=sell_loc_usd, line_dash="dot", line_color="#dc3545", annotation_text="Sell LOC")

        fig.update_layout(template="plotly_white", height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_order:
        st.subheader("🎯 Order Sheet")
        st.info(f"🔵 **매수 LOC (Step {CURRENT_STEP})**\n\n**Price:** `${buy_loc_usd:.2f}`\n\n**Qty:** `{buy_qty}주` (약 {buy_loc_usd*exchange_rate:,.0f}원)")
        st.error(f"🔴 **매도 LOC (전량)**\n\n**Price:** `${sell_loc_usd:.2f}`\n\n**Qty:** `{HOLDING_QTY}주` (약 {sell_loc_usd*exchange_rate:,.0f}원)")
        st.caption("※ 주문 전 증권사 현재가를 반드시 확인하세요.")

else:
    st.warning("데이터를 불러올 수 없습니다.")