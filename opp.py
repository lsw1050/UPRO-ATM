import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정 및 테마
# ==========================================
st.set_page_config(page_title="UPRO ATM Trading Bot", page_icon="💰", layout="wide")

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
@st.cache_data(ttl=600) # 10분마다 자동 갱신
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
    # 기초 데이터 추출
    last_close_usd = float(data[TICKER].iloc[-1])
    prev_close_usd = float(data[TICKER].iloc[-2])
    exchange_rate = float(data['USDKRW=X'].iloc[-1])
    
    # 변동성 및 자산 계산
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std() if len(returns) >= N_SIGMA else 0
    
    used_cash_usd = HOLDING_QTY * AVG_PRICE_USD
    remaining_cash_usd = TOTAL_SEED_USD - used_cash_usd
    current_eval_usd = HOLDING_QTY * last_close_usd
    profit_loss_usd = current_eval_usd - used_cash_usd
    return_rate = (profit_loss_usd / used_cash_usd * 100) if used_cash_usd > 0 else 0
    
    # 주문값 계산
    buy_loc_usd = last_close_usd * (1 + BUY_MULT * sigma)
    sell_loc_usd = last_close_usd * (1 + SELL_MULT * sigma)
    target_step_usd = TOTAL_SEED_USD * (WEIGHTS[CURRENT_STEP-1] / sum(WEIGHTS))
    buy_qty = int(min(target_step_usd, remaining_cash_usd) / buy_loc_usd) if buy_loc_usd > 0 else 0

    # --- UI 상단: 타이틀 및 환율 ---
    st.title(f"🚀 {TICKER} ATM 실전 전략")
    st.markdown(f"**현재 환율:** 1$ = `{exchange_rate:,.2f}원` | **데이터 기준:** `{datetime.now().strftime('%H:%M:%S')}`")

    # --- UI 중단: 주요 지표 (KPI Cards) ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    
    price_delta = f"{((last_close_usd - prev_close_usd)/prev_close_usd*100):+.2f}%"
    m1.metric("Current Price", f"${last_close_usd:,.2f}", price_delta)
    
    m2.metric("Profit / Loss", f"{return_rate:+.2f}%", f"${profit_loss_usd:+,.2f}", delta_color="normal")
    
    m3.metric("Available Cash", f"${remaining_cash_usd:,.0f}", f"{remaining_cash_usd*exchange_rate:,.0f}원", delta_color="off")
    
    total_asset_usd = current_eval_usd + remaining_cash_usd
    m4.metric("Total Equity", f"${total_asset_usd:,.0f}", f"{total_asset_usd*exchange_rate:,.0f}원", delta_color="off")

    # --- UI 하단: 차트와 주문표 (좌우 배치) ---
    st.divider()
    col_chart, col_order = st.columns([2, 1])

    with col_chart:
        st.subheader("📊 Price Trend & Guide Lines")
        # Plotly 차트 고도화
        fig = go.Figure()
        
        # 주가 선
        fig.add_trace(go.Scatter(x=data.index[-15:], y=data[TICKER].tail(15), 
                                 mode='lines+markers', name='Price', line=dict(color='#1f77b4', width=3)))
        
        # 내 평단가 라인 (황금색 점선)
        fig.add_hline(y=AVG_PRICE_USD, line_dash="dash", line_color="#FFD700", 
                      annotation_text=f"My Avg (${AVG_PRICE_USD})", annotation_position="top left")
        
        # 매수/매도 LOC 라인
        fig.add_hline(y=buy_loc_usd, line_dash="dot", line_color="#007bff", 
                      annotation_text="Buy LOC", annotation_position="bottom right")
        fig.add_hline(y=sell_loc_usd, line_dash="dot", line_color="#dc3545", 
                      annotation_text="Sell LOC", annotation_position="top right")

        fig.update_layout(template="plotly_white", height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_order:
        st.subheader("🎯 Order Sheet")
        with st.container(border=True):
            st.write(f"**Step {CURRENT_STEP} 매수 계획**")
            st.info(f"🔵 **매수 LOC**\n\n**Price:** `${buy_loc_usd:.2f}`\n\n**Qty:** `{buy_qty}주` (약 {buy_loc_usd*exchange_rate:,.0f}원)")
            
        with st.container(border=True):
            st.write("**전량 매도 계획**")
            st.error(f"🔴 **매도 LOC**\n\n**Price:** `${sell_loc_usd:.2f}`\n\n**Qty:** `{HOLDING_QTY}주` (약 {sell_loc_usd*exchange_rate:,.0f}원)")
            
        st.caption("※ LOC 주문은 종가가 설정가보다 유리할 때 체결됩니다.")

else:
    st.warning("데이터를 불러올 수 없습니다. 장 개시 상태를 확인해 주세요.")