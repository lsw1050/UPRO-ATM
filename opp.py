import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정 및 사용자 입력 (사이드바)
# ==========================================
st.set_page_config(page_title="UPRO ATM Dashboard", page_icon="📈", layout="wide")

st.sidebar.header("⚙️ 투자 설정")
TOTAL_SEED_USD = st.sidebar.number_input("총 시드 ($)", value=37000.0)
HOLDING_QTY = st.sidebar.number_input("현재 보유 수량 (주)", value=77)
AVG_PRICE_USD = st.sidebar.number_input("나의 평단가 ($)", value=115.76)
CURRENT_STEP = st.sidebar.selectbox("현재 매수 회차", options=[1, 2, 3], index=1)

TICKER = "UPRO"
N_SIGMA = 2
BUY_MULT, SELL_MULT = 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집 및 계산 로직
# ==========================================
@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def get_data():
    tickers = [TICKER, "USDKRW=X"]
    data = yf.download(tickers, period="20d", progress=False)['Close']
    return data.dropna()

try:
    data = get_data()
    last_close_usd = float(data[TICKER].iloc[-1])
    exchange_rate = float(data['USDKRW=X'].iloc[-1])
    
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std()
    
    # 자산 계산
    used_cash_usd = HOLDING_QTY * AVG_PRICE_USD
    remaining_cash_usd = TOTAL_SEED_USD - used_cash_usd
    current_eval_usd = HOLDING_QTY * last_close_usd
    profit_loss_usd = current_eval_usd - used_cash_usd
    return_rate = (profit_loss_usd / used_cash_usd * 100) if used_cash_usd > 0 else 0

    # 주문 계산
    buy_loc_usd = last_close_usd * (1 + BUY_MULT * sigma)
    sell_loc_usd = last_close_usd * (1 + SELL_MULT * sigma)
    target_step_usd = TOTAL_SEED_USD * (WEIGHTS[CURRENT_STEP-1] / sum(WEIGHTS))
    buy_qty = int(min(target_step_usd, remaining_cash_usd) / buy_loc_usd) if buy_loc_usd > 0 else 0

    # ==========================================
    # 3. 웹 화면 구성 (모바일 최적화)
    # ==========================================
    st.title(f"🚀 {TICKER} 실전 대시보드")
    st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (환율: {exchange_rate:,.2f}원)")

    # 주요 지표 (KPI) - 모바일에서 가로로 배치됨
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"${last_close_usd:,.2f}", f"{exchange_rate * last_close_usd:,.0f}원")
    col2.metric("수익률", f"{return_rate:+.2f}%", f"${profit_loss_usd:+.2f}")
    col3.metric("남은 현금", f"${remaining_cash_usd:,.0f}", f"{remaining_cash_usd * exchange_rate:,.0f}원")

    st.divider()

    # 주문표 섹션
    st.subheader("🎯 내일의 LOC 주문")
    order_col1, order_col2 = st.columns(2)
    with order_col1:
        st.info(f"**🔵 매수 LOC**\n\n**Price:** ${buy_loc_usd:.2f}\n\n**Qty:** {buy_qty}주")
    with order_col2:
        st.error(f"**🔴 매도 LOC**\n\n**Price:** ${sell_loc_usd:.2f}\n\n**Qty:** {HOLDING_QTY}주")

    # 그래프 섹션 (Plotly 사용으로 모바일 터치 대응)
    st.subheader(f"📊 {TICKER} 최근 10일 추세")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index[-10:], y=data[TICKER].tail(10), mode='lines+markers', name='Price'))
    fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=20, b=20), height=300)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")