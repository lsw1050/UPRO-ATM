import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(page_title="UPRO 실전 터미널", page_icon="💰", layout="wide")

# 사이드바 입력창
st.sidebar.header("⚙️ My Portfolio")
TOTAL_SEED_USD = st.sidebar.number_input("Total Seed ($)", value=37000.0, step=100.0)
HOLDING_QTY = st.sidebar.number_input("Holding Qty", value=77)
AVG_PRICE_USD = st.sidebar.number_input("Avg Price ($)", value=115.76, step=0.01)
CURRENT_STEP = st.sidebar.select_slider("Buy Step", options=[1, 2, 3], value=2)

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
# 3. 계산 및 UI 출력
# ==========================================
if data is not None and len(data) >= 2:
    # 기초 데이터 계산
    last_close_usd = float(data[TICKER].iloc[-1])
    exchange_rate = float(data['USDKRW=X'].iloc[-1])
    
    profit_loss_usd = (last_close_usd - AVG_PRICE_USD) * HOLDING_QTY
    profit_loss_krw = profit_loss_usd * exchange_rate
    return_rate = (profit_loss_usd / (HOLDING_QTY * AVG_PRICE_USD) * 100) if HOLDING_QTY > 0 else 0

    # ⭐ 목표 달성 알림 로직 (수익 10만원 이상)
    if profit_loss_krw >= 100000:
        st.balloons() # 화면에 풍선 애니메이션 효과
        st.success(f"🎊 축하합니다! 현재 원화 수익이 **{profit_loss_krw:,.0f}원**입니다! 목표 수익을 달성 중입니다! 🎊")
        # 황금색 테마 강조를 위한 문구
        st.markdown("""
            <style>
            .stApp {
                border: 5px solid #FFD700;
            }
            </style>
            """, unsafe_allow_html=True)
    elif profit_loss_krw > 0:
        st.info(f"✅ 현재 수익 중입니다! (+{profit_loss_krw:,.0f}원)")

    # (이후 계산 로직 동일)
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std()
    buy_loc_usd = last_close_usd * (1 + BUY_MULT * sigma)
    sell_loc_usd = last_close_usd * (1 + SELL_MULT * sigma)
    
    # --- 화면 표시 ---
    st.title("📟 실전 매매 터미널")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"${last_close_usd:,.2f}")
    
    # 수익률 컬러 적용
    p_color = "normal" if profit_loss_krw >= 0 else "inverse"
    col2.metric("원화 수익금", f"{profit_loss_krw:+,.0f}원", f"{return_rate:+.2f}%", delta_color=p_color)
    col3.metric("현재 환율", f"{exchange_rate:,.2f}원")

    st.divider()

    # 그래프 섹션 (우측 라벨 가독성 버전)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index[-15:], y=data[TICKER].tail(15), mode='lines+markers', name='Price', line=dict(color='#00FF00')))
    
    # 가이드라인 및 라벨 (우측 여백 배치)
    guide_lines = [
        {"y": sell_loc_usd, "color": "blue", "name": "매도 LOC"},
        {"y": AVG_PRICE_USD, "color": "white", "name": "내 평단가"},
        {"y": buy_loc_usd, "color": "red", "name": "매수 LOC"}
    ]
    
    for line in guide_lines:
        fig.add_hline(y=line["y"], line_dash="dot", line_color=line["color"])
        fig.add_annotation(
            x=1.02, y=line["y"], xref="paper", yref="y",
            text=f"<b>{line['name']}<br>${line['y']:.2f}</b>",
            showarrow=False, font=dict(color=line["color"], size=12), align="left", xanchor="left"
        )

    fig.update_layout(template="plotly_dark", height=500, margin=dict(r=120, l=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 주문표
    c_buy, c_sell = st.columns(2)
    with c_buy:
        st.info(f"### 🔵 매수 LOC (Step {CURRENT_STEP})\n**가격: `${buy_loc_usd:.2f}`**")
    with c_sell:
        st.error(f"### 🔴 매도 LOC (전량)\n**가격: `${sell_loc_usd:.2f}`**")

else:
    st.error("데이터를 가져올 수 없습니다.")