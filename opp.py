import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정 및 사용자 입력
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
# 2. 데이터 수집 로직 (보완됨)
# ==========================================
@st.cache_data(ttl=3600)
def get_data():
    # 데이터 수집 기간을 30일로 늘려 안전성 확보
    tickers = [TICKER, "USDKRW=X"]
    try:
        raw_data = yf.download(tickers, period="30d", progress=False)['Close']
        # 데이터가 비어있는지 확인
        if raw_data.empty:
            return None
        return raw_data.dropna()
    except:
        return None

# 데이터 가져오기 실행
data = get_data()

# ==========================================
# 3. 계산 및 화면 구성
# ==========================================
st.title(f"🚀 {TICKER} 실전 대시보드")

if data is not None and not data.empty and len(data) >= 2:
    try:
        last_close_usd = float(data[TICKER].iloc[-1])
        exchange_rate = float(data['USDKRW=X'].iloc[-1])
        
        # 변동성 계산
        returns = data[TICKER].pct_change().dropna()
        sigma = returns.tail(N_SIGMA).std() if len(returns) >= N_SIGMA else 0
        
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

        # --- 화면 출력 ---
        st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (환율: {exchange_rate:,.2f}원)")

        col1, col2, col3 = st.columns(3)
        col1.metric("현재가", f"${last_close_usd:,.2f}", f"{exchange_rate * last_close_usd:,.0f}원")
        col2.metric("수익률", f"{return_rate:+.2f}%", f"${profit_loss_usd:+.2f}")
        col3.metric("남은 현금", f"${remaining_cash_usd:,.0f}", f"{remaining_cash_usd * exchange_rate:,.0f}원")

        st.divider()

        st.subheader("🎯 내일의 LOC 주문")
        order_col1, order_col2 = st.columns(2)
        with order_col1:
            st.info(f"**🔵 매수 LOC**\n\n**Price:** ${buy_loc_usd:.2f} (약 {buy_loc_usd*exchange_rate:,.0f}원)\n\n**Qty:** {buy_qty}주")
        with order_col2:
            st.error(f"**🔴 매도 LOC**\n\n**Price:** ${sell_loc_usd:.2f} (약 {sell_loc_usd*exchange_rate:,.0f}원)\n\n**Qty:** {HOLDING_QTY}주")

        st.subheader(f"📊 {TICKER} 최근 10일 추세")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index[-10:], y=data[TICKER].tail(10), mode='lines+markers', name='Price'))
        fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=20, b=20), height=300)
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"계산 중 오류가 발생했습니다: {e}")
else:
    st.warning("⚠️ 실시간 데이터를 불러올 수 없습니다. 잠시 후 다시 시도하거나 인터넷 연결을 확인해 주세요.")
    st.info("현재 시장이 닫혀 있거나 주말인 경우 데이터 업데이트가 지연될 수 있습니다.")