import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(page_title="UPRO 실전 매매 터미널", page_icon="🏦", layout="wide")

# 사이드바: 실전 입력 터미널 (여기서 입력하면 코드를 고칠 필요가 없습니다!)
st.sidebar.markdown("### 🏦 나의 계좌 정보 업데이트")
st.sidebar.write("매일 매매 후 아래 정보를 수정하세요.")

# 웹에서 직접 입력받는 칸들
TOTAL_SEED_USD = st.sidebar.number_input("1. 총 투자 원금 ($)", value=37000.0, step=100.0, help="전체 투자 가능한 총 예산을 입력하세요.")
HOLDING_QTY = st.sidebar.number_input("2. 현재 보유 수량 (주)", value=77, step=1, help="현재 계좌에 있는 주식 수를 입력하세요.")
AVG_PRICE_USD = st.sidebar.number_input("3. 나의 현재 평단가 ($)", value=115.76, step=0.01, help="증권사 앱에 표시된 평단가를 입력하세요.")
CURRENT_STEP = st.sidebar.select_slider("4. 다음 매수 회차 선택", options=[1, 2, 3], value=2, help="오늘이 몇 번째 분할 매수인지 선택하세요.")

st.sidebar.divider()
st.sidebar.caption("💡 여기서 입력한 정보는 웹 페이지에 즉시 반영됩니다.")

# 전략 고정 변수
TICKER = "UPRO"
N_SIGMA = 2
BUY_MULT, SELL_MULT = 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집
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
# 3. 실시간 계산 및 화면 출력
# ==========================================
if data is not None and not data.empty and len(data) >= 2:
    last_close_usd = float(data[TICKER].iloc[-1])
    exchange_rate = float(data['USDKRW=X'].iloc[-1])
    
    # 계산 (사용자가 웹에서 입력한 변수들을 그대로 사용)
    used_cash_usd = HOLDING_QTY * AVG_PRICE_USD
    remaining_cash_usd = TOTAL_SEED_USD - used_cash_usd
    current_eval_usd = HOLDING_QTY * last_close_usd
    profit_loss_usd = current_eval_usd - used_cash_usd
    return_rate_usd = (profit_loss_usd / used_cash_usd * 100) if used_cash_usd > 0 else 0
    
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std() if len(returns) >= N_SIGMA else 0
    buy_loc_usd = last_close_usd * (1 + BUY_MULT * sigma)
    sell_loc_usd = last_close_usd * (1 + SELL_MULT * sigma)
    
    target_step_usd = TOTAL_SEED_USD * (WEIGHTS[CURRENT_STEP-1] / sum(WEIGHTS))
    buy_qty = int(min(target_step_usd, remaining_cash_usd) / buy_loc_usd) if buy_loc_usd > 0 else 0

    # --- 메인 화면 구성 ---
    st.title("📟 실전 매매 터미널")
    
    # 상단 요약 카드 (USD & KRW)
    st.subheader("💰 실시간 자산 현황")
    c1, c2, c3 = st.columns(3)
    c1.metric("내 평단가", f"${AVG_PRICE_USD:,.2f}", f"{AVG_PRICE_USD*exchange_rate:,.0f}원", delta_color="off")
    c2.metric("현재 수익률 (USD)", f"{return_rate_usd:+.2f}%", f"${profit_loss_usd:+,.2f}")
    c3.metric("원화 수익금", f"{profit_loss_usd * exchange_rate:+,.0f}원", f"환율: {exchange_rate:,.1f}")

    st.divider()

    # 주문표 (가장 중요한 정보)
    st.subheader("🎯 오늘의 LOC 주문 가이드")
    st.write(f"오늘 주식 수량이 변했다면 왼쪽 메뉴에서 정보를 업데이트하세요.")
    
    o1, o2 = st.columns(2)
    with o1:
        st.success(f"### 🔵 매수 LOC (Step {CURRENT_STEP})\n\n**가격: `${buy_loc_usd:.2f}`**\n\n**수량: `{buy_qty}주`**")
    with o2:
        st.warning(f"### 🔴 매도 LOC (전량)\n\n**가격: `${sell_loc_usd:.2f}`**\n\n**수량: `{HOLDING_QTY}주`**")

  # --- 그래프 섹션 (가로 가독성 강화 버전) ---
    st.divider()
    st.subheader("📈 실시간 가격 가이드라인 (우측 정렬)")

    fig = go.Figure()

    # 1. 주가 선
    fig.add_trace(go.Scatter(
        x=data.index[-15:], 
        y=data[TICKER].tail(15), 
        mode='lines+markers', 
        name='현재가',
        line=dict(color='#00FF00', width=2)
    ))

    # 가이드라인 설정 (글씨를 밖으로 빼기 위해 별도의 annotation 사용)
    lines = [
        {"y": sell_loc_usd, "color": "blue", "text": "매도 LOC", "pos": "top"},
        {"y": AVG_PRICE_USD, "color": "white", "text": "내 평단가", "pos": "middle"},
        {"y": buy_loc_usd, "color": "red", "text": "매수 LOC", "pos": "bottom"}
    ]

    for line in lines:
        # 가로 점선 추가
        fig.add_hline(
            y=line["y"], 
            line_dash="dot", 
            line_color=line["color"], 
            line_width=2
        )
        
        # 우측 여백에 글씨 추가 (xref="paper"를 사용하여 차트 바깥쪽 정렬)
        fig.add_annotation(
            x=1.02, # 차트 오른쪽 끝에서 살짝 밖으로 (0~1 범위 밖)
            y=line["y"],
            xref="paper",
            yref="y",
            text=f"<b>{line['text']}<br>${line['y']:.2f}</b>",
            showarrow=False,
            font=dict(size=13, color=line["color"]),
            align="left",
            xanchor="left"
        )

    # 차트 레이아웃 설정
    fig.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=120, t=50, b=10), # 오른쪽 여백(r)을 120으로 대폭 확대
        xaxis=dict(showgrid=True, gridcolor='gray', tickformat='%m-%d'),
        yaxis=dict(showgrid=True, gridcolor='gray', side="left"), # 기본 축은 왼쪽
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("시장이 닫혀있거나 데이터를 가져올 수 없습니다.")