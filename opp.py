import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ==========================================
# 1. 페이지 설정 및 세션 초기화 (최상단 배치)
# ==========================================
st.set_page_config(page_title="UPRO 실전 매매 터미널", page_icon="🏦", layout="wide")

# [중요] 브라우저 세션에 데이터 고정
# 만약 아예 영구 저장을 원하시면 아래의 숫차들을 사용자님의 값으로 직접 수정해두세요.
if 'seed' not in st.session_state: st.session_state.seed = 37000.0
if 'qty' not in st.session_state: st.session_state.qty = 77
if 'avg' not in st.session_state: st.session_state.avg = 115.76
if 'step' not in st.session_state: st.session_state.step = 2

# 사이드바 입력창
st.sidebar.markdown("### 🏦 나의 계좌 정보 업데이트")
seed = st.sidebar.number_input("1. 총 투자 원금 ($)", value=st.session_state.seed, step=100.0)
qty = st.sidebar.number_input("2. 현재 보유 수량 (주)", value=st.session_state.qty, step=1)
avg = st.sidebar.number_input("3. 나의 현재 평단가 ($)", value=st.session_state.avg, step=0.01)
step = st.sidebar.select_slider("4. 다음 매수 회차 선택", options=[1, 2, 3], value=st.session_state.step)

# 입력 즉시 세션 상태 업데이트 (새로고침 시 유지)
st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 2. 데이터 수집 함수 (캐싱 적용)
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
# 3. 실시간 계산 로직 (UI 출력 전 계산 완료)
# ==========================================
if data is not None and not data.empty and len(data) >= 2:
    last_close = float(data[TICKER].iloc[-1])
    exchange_rate = float(data['USDKRW=X'].iloc[-1])
    
    # 자산 및 수익 계산
    used_cash_usd = qty * avg
    remaining_cash_usd = seed - used_cash_usd
    profit_loss_usd = (last_close - avg) * qty
    profit_loss_krw = profit_loss_usd * exchange_rate
    return_rate = (profit_loss_usd / used_cash_usd * 100) if used_cash_usd > 0 else 0
    
    # LOC 계산
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std() if len(returns) >= N_SIGMA else 0
    buy_loc = last_close * (1 + BUY_MULT * sigma)
    sell_loc = last_close * (1 + SELL_MULT * sigma)
    
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    buy_qty = int(min(target_usd, remaining_cash_usd) / buy_loc) if buy_loc > 0 else 0

    # ------------------------------------------
    # 🎈 [효과 발동] 수익 축하 로직 (수익금 10만원 이상)
    # ------------------------------------------
    if profit_loss_krw >= 100000:
        st.balloons() # 풍선 애니메이션
        # 황금 테두리 강제 주입
        st.markdown("""
            <style>
            [data-testid="stAppViewContainer"] {
                border: 10px solid #FFD700;
                box-sizing: border-box;
            }
            </style>
            """, unsafe_allow_html=True)
        st.success(f"🎊 축하합니다! 원화 수익 **{profit_loss_krw:,.0f}원** 달성! 황금 모드 가동! 🎊")

    # ==========================================
    # 4. 메인 화면 구성 (주문표 상단 배치)
    # ==========================================
    st.title("📟 UPRO 실전 매매 터미널")
    st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (환율: {exchange_rate:,.2f}원)")

    # [상단 주문 가이드 카드]
    st.divider()
    o1, o2 = st.columns(2)
    with o1:
        st.markdown(f"""
        <div style="background-color:rgba(255, 75, 75, 0.1); padding:20px; border-radius:10px; border-left: 8px solid #FF4B4B;">
            <h3 style="color:#FF4B4B; margin:0;">🔵 매수 LOC (Step {step})</h3>
            <h1 style="margin:10px 0;">${buy_loc:.2f}</h1>
            <h4 style="margin:0;">주문 수량: {buy_qty}주 <span style="font-size:14px; color:gray;">(약 {buy_loc*exchange_rate*buy_qty:,.0f}원)</span></h4>
        </div>
        """, unsafe_allow_html=True)
    with o2:
        st.markdown(f"""
        <div style="background-color:rgba(27, 107, 255, 0.1); padding:20px; border-radius:10px; border-left: 8px solid #1B6BFF;">
            <h3 style="color:#1B6BFF; margin:0;">🔴 매도 LOC (전량)</h3>
            <h1 style="margin:10px 0;">${sell_loc:.2f}</h1>
            <h4 style="margin:0;">주문 수량: {qty}주 <span style="font-size:14px; color:gray;">(약 {sell_loc*exchange_rate*qty:,.0f}원)</span></h4>
        </div>
        """, unsafe_allow_html=True)

    # [중단 자산 현황 섹션]
    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.metric("내 평단가", f"${avg:,.2f}", f"{avg*exchange_rate:,.0f}원", delta_color="off")
    p_color = "normal" if profit_loss_krw >= 0 else "inverse"
    c2.metric("원화 수익금", f"{profit_loss_krw:+,.0f}원", f"{return_rate:+.2f}%", delta_color=p_color)
    c3.metric("남은 현금", f"${remaining_cash_usd:,.2f}", f"{remaining_cash_usd*exchange_rate:,.0f}원", delta_color="off")

    # [하단 그래프 섹션] - 우측 라벨 보존
    st.divider()
    st.subheader("📈 실시간 가격 가이드라인")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index[-15:], y=data[TICKER].tail(15), mode='lines+markers', name='현재가', line=dict(color='#00FF00', width=2)))
    
    # 가이드라인 설정
    lines = [
        {"y": sell_loc, "color": "#1B6BFF", "text": "매도 LOC"},
        {"y": avg, "color": "white", "text": "내 평단가"},
        {"y": buy_loc, "color": "#FF4B4B", "text": "매수 LOC"}
    ]
    for line in lines:
        fig.add_hline(y=line["y"], line_dash="dot", line_color=line["color"], line_width=2)
        fig.add_annotation(
            x=1.02, y=line["y"], xref="paper", yref="y",
            text=f"<b>{line['text']}<br>${line['y']:.2f}</b>",
            showarrow=False, font=dict(size=13, color=line["color"]), align="left", xanchor="left"
        )

    fig.update_layout(template="plotly_dark", height=550, margin=dict(l=10, r=120, t=50, b=10),
                      xaxis=dict(showgrid=True, gridcolor='gray', tickformat='%m-%d'),
                      yaxis=dict(showgrid=True, gridcolor='gray', side="left"), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("데이터를 가져올 수 없습니다. 장외 시간이거나 환율 정보가 유효한지 확인하세요.")