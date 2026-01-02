import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import streamlit.components.v1 as components
import json


# ==========================================
# 1. 페이지 설정 및 전역 스타일
# ==========================================
st.set_page_config(page_title="LSW-ATM 🏧", page_icon="🏧", layout="wide")

# [전역 CSS] 세련된 다크 테마
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
</style>
""", unsafe_allow_html=True)

# [세션 상태 관리]
if 'seed' not in st.session_state: st.session_state.seed = 37000.0
if 'qty' not in st.session_state: st.session_state.qty = 77
if 'avg' not in st.session_state: st.session_state.avg = 115.76
if 'step' not in st.session_state: st.session_state.step = 2

# 사이드바
st.sidebar.markdown("""
<div style="text-align: center; padding: 20px 0;">
    <h1 style="font-size: 48px; margin: 0;">🏧</h1>
    <h3 style="color: #00d4ff; margin: 10px 0;">나의 계좌 정보</h3>
</div>
""", unsafe_allow_html=True)

seed = st.sidebar.number_input("💰 총 투자 원금 (달러)", value=st.session_state.seed, step=100.0)
qty = st.sidebar.number_input("📊 현재 보유 수량 (주)", value=st.session_state.qty, step=1)
avg = st.sidebar.number_input("💵 나의 현재 평단가 ($)", value=st.session_state.avg, step=0.01)
step = st.sidebar.select_slider("🎯 다음 매수 회차", options=[1, 2, 3], value=st.session_state.step)

st.session_state.seed, st.session_state.qty, st.session_state.avg, st.session_state.step = seed, qty, avg, step

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
# 3. 실시간 계산 및 효과 로직
# ==========================================
if data is not None and not data.empty and len(data) >= 2:
    last_close = float(data[TICKER].iloc[-1])
    rate = float(data['USDKRW=X'].iloc[-1])
    
    used_cash_usd = qty * avg
    profit_loss_usd = (last_close - avg) * qty
    profit_loss_krw = profit_loss_usd * rate
    return_rate = (profit_loss_usd / used_cash_usd * 100) if used_cash_usd > 0 else 0
    
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std(ddof=0) if len(returns) >= N_SIGMA else 0
    
    buy_loc = last_close * (1 + BUY_MULT * sigma)
    sell_loc = last_close * (1 + SELL_MULT * sigma)
    
    target_usd = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining_usd = seed - used_cash_usd
    buy_qty = int(min(target_usd, remaining_usd) / buy_loc) if buy_loc > 0 else 0

    # 잭팟 효과
    if profit_loss_krw >= 100000:
        components.html(
            """
            <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
            <script>
                function rainMoney() {
                    var end = Date.now() + (3 * 1000);
                    var emojis = ['💸', '💵', '💰', '🏧', '🤑'];
                    (function frame() {
                        confetti({
                            particleCount: 5, angle: 60, spread: 55, origin: { x: 0, y: 0.5 },
                            shapes: ['text'], shapeOptions: { text: { value: emojis[Math.floor(Math.random() * emojis.length)] } }, scalar: 3
                        });
                        confetti({
                            particleCount: 5, angle: 120, spread: 55, origin: { x: 1, y: 0.5 },
                            shapes: ['text'], shapeOptions: { text: { value: emojis[Math.floor(Math.random() * emojis.length)] } }, scalar: 3
                        });
                        if (Date.now() < end) requestAnimationFrame(frame);
                    }());
                }
                setTimeout(rainMoney, 500);
            </script>
            """,
            height=300,
        )

        st.markdown("""
            <style>
            @keyframes gold-glow {
                0% { border-color: #FFD700; box-shadow: 0 0 10px #FFD700, inset 0 0 10px #FFD700; }
                50% { border-color: #FFA500; box-shadow: 0 0 30px #FFA500, inset 0 0 30px #FFA500; }
                100% { border-color: #FFD700; box-shadow: 0 0 10px #FFD700, inset 0 0 10px #FFD700; }
            }
            [data-testid="stAppViewContainer"] {
                border: 10px solid #FFD700;
                animation: gold-glow 2s infinite alternate;
                box-sizing: border-box;
            }
            </style>
            """, unsafe_allow_html=True)
        
        st.success(f"🏆 **수익금 {profit_loss_krw:,.0f}원 돌파!** 🏧 돈 비가 내립니다! 💸")

    # ==========================================
    # 4. 화면 구성
    # ==========================================
    
    # 헤더
    st.markdown("""
    <div style="text-align: center; padding: 20px 0 30px 0;">
        <h1 style="
            font-size: 42px;
            font-weight: 800;
            background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 50%, #f472b6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        ">SIGMA SIGNAL</h1>
        <p style="color: #6b7280; margin-top: 10px; font-size: 14px;">
            시그마 기반 LOC 주문 시스템
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # LOC 주문 카드
    o1, o2 = st.columns(2)
    with o1:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(239,68,68,0.2) 0%, rgba(239,68,68,0.05) 100%);
            border: 1px solid rgba(239,68,68,0.3);
            border-radius: 20px;
            padding: 28px;
        ">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <span style="font-size: 28px;">🔴</span>
                <span style="color: #ef4444; font-weight: 600; font-size: 16px;">매수 LOC (Step {step})</span>
            </div>
            <div style="font-size: 42px; font-weight: 800; color: #ffffff; margin: 10px 0;">
                ${buy_loc:.2f}
            </div>
            <div style="color: #9ca3af; font-size: 15px; margin-top: 15px;">
                📦 주문 수량: <span style="color: #ffffff; font-weight: 600;">{buy_qty}주</span>
            </div>
            <div style="color: #6b7280; font-size: 13px; margin-top: 5px;">
                ₩ {buy_loc*rate*buy_qty:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with o2:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(59,130,246,0.2) 0%, rgba(59,130,246,0.05) 100%);
            border: 1px solid rgba(59,130,246,0.3);
            border-radius: 20px;
            padding: 28px;
        ">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <span style="font-size: 28px;">🔵</span>
                <span style="color: #3b82f6; font-weight: 600; font-size: 16px;">매도 LOC (전량)</span>
            </div>
            <div style="font-size: 42px; font-weight: 800; color: #ffffff; margin: 10px 0;">
                ${sell_loc:.2f}
            </div>
            <div style="color: #9ca3af; font-size: 15px; margin-top: 15px;">
                📦 주문 수량: <span style="color: #ffffff; font-weight: 600;">{qty}주</span>
            </div>
            <div style="color: #6b7280; font-size: 13px; margin-top: 5px;">
                ₩ {sell_loc*rate*qty:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 복사 버튼
    st.write("")
    copy1, copy2 = st.columns(2)
    
    with copy1:
        buy_text = f"UPRO 매수 LOC\n지정가: ${buy_loc:.2f}\n수량: {buy_qty}주"
        if st.button("📋 매수 주문 복사", use_container_width=True, key="copy_buy"):
            st.code(buy_text, language=None)
            components.html(f"""
                <script>navigator.clipboard.writeText(`{buy_text}`);</script>
                <p style="color: #10b981; font-weight: bold; text-align: center;">✅ 클립보드에 복사됨!</p>
            """, height=50)
    
    with copy2:
        sell_text = f"UPRO 매도 LOC\n지정가: ${sell_loc:.2f}\n수량: {qty}주 (전량)"
        if st.button("📋 매도 주문 복사", use_container_width=True, key="copy_sell"):
            st.code(sell_text, language=None)
            components.html(f"""
                <script>navigator.clipboard.writeText(`{sell_text}`);</script>
                <p style="color: #10b981; font-weight: bold; text-align: center;">✅ 클립보드에 복사됨!</p>
            """, height=50)

    # ==========================================
    # [수정] 주요 지표 - st.columns + st.markdown 조합
    # ==========================================
    st.write("")
    
    # 수익 상태에 따른 색상
    profit_color = "#10b981" if profit_loss_krw >= 0 else "#ef4444"
    profit_icon = "📈" if profit_loss_krw >= 0 else "📉"
    
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
        ">
            <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">💹 현재가</div>
            <div style="color: #ffffff; font-size: 32px; font-weight: 700;">${last_close:,.2f}</div>
            <div style="color: #6b7280; font-size: 13px; margin-top: 8px;">₩{rate:,.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with m2:
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.03);
            border: 1px solid {profit_color}40;
            border-radius: 16px;
            padding: 24px;
            text-align: center;
        ">
            <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">{profit_icon} 원화 수익금</div>
            <div style="color: {profit_color}; font-size: 32px; font-weight: 700;">{profit_loss_krw:+,.0f}원</div>
            <div style="color: {profit_color}; font-size: 13px; margin-top: 8px;">{return_rate:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with m3:
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
        ">
            <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">💵 남은 현금</div>
            <div style="color: #ffffff; font-size: 32px; font-weight: 700;">${remaining_usd:,.2f}</div>
            <div style="color: #6b7280; font-size: 13px; margin-top: 8px;">₩{remaining_usd*rate:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    # 차트 섹션
    st.markdown("""
    <div style="margin: 30px 0 15px 0;">
        <h3 style="color: #ffffff; font-size: 20px; font-weight: 600;">
            📈 실시간 가격 가이드라인
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index[-15:], 
        y=data[TICKER].tail(15), 
        mode='lines+markers', 
        name='현재가', 
        line=dict(color='#10b981', width=3),
        marker=dict(size=8, color='#10b981', line=dict(width=2, color='#ffffff'))
    ))
    
    guides = [
        {"y": sell_loc, "color": "#3b82f6", "text": "매도 LOC"},
        {"y": avg, "color": "#fbbf24", "text": "내 평단가"},
        {"y": buy_loc, "color": "#ef4444", "text": "매수 LOC"}
    ]
    for line in guides:
        fig.add_hline(y=line["y"], line_dash="dot", line_color=line["color"], line_width=2)
        fig.add_annotation(
            x=1.02, y=line["y"], xref="paper", yref="y", 
            text=f"<b>{line['text']}<br>${line['y']:.2f}</b>",
            showarrow=False, 
            font=dict(size=12, color=line["color"]), 
            align="left", 
            xanchor="left"
        )

    fig.update_layout(
        template="plotly_dark",
        height=500,
        margin=dict(l=10, r=120, t=30, b=10),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.02)',
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
    )
    st.plotly_chart(fig, use_container_width=True)

    # 거래 기록 섹션
    st.markdown("""
    <div style="margin: 40px 0 20px 0;">
        <h3 style="color: #ffffff; font-size: 20px; font-weight: 600;">
            💾 거래 기록
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 매수 기록 저장", use_container_width=True, key="save_buy"):
            record = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type": "BUY",
                "price": round(buy_loc, 2),
                "qty": buy_qty,
                "step": step
            }
            try:
                with open("trade_log.json", "r") as f:
                    logs = json.load(f)
            except:
                logs = []
            logs.append(record)
            with open("trade_log.json", "w") as f:
                json.dump(logs, f, indent=2)
            st.success("✅ 매수 기록 저장 완료!")
    
    with col2:
        if st.button("📤 매도 기록 저장", use_container_width=True, key="save_sell"):
            record = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type": "SELL",
                "price": round(sell_loc, 2),
                "qty": qty,
                "step": 0
            }
            try:
                with open("trade_log.json", "r") as f:
                    logs = json.load(f)
            except:
                logs = []
            logs.append(record)
            with open("trade_log.json", "w") as f:
                json.dump(logs, f, indent=2)
            st.success("✅ 매도 기록 저장 완료!")
    
    if st.checkbox("📜 거래 내역 보기"):
        try:
            with open("trade_log.json", "r") as f:
                logs = json.load(f)
            if logs:
                df_logs = pd.DataFrame(logs)
                st.dataframe(df_logs, use_container_width=True)
            else:
                st.info("거래 내역이 없습니다.")
        except FileNotFoundError:
            st.info("거래 내역이 없습니다.")

    # 푸터
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 30px 0;
        margin-top: 40px;
        border-top: 1px solid rgba(255,255,255,0.1);
        color: #6b7280;
        font-size: 12px;
    ">
        <p>σ = {sigma:.6f} | N = {N_SIGMA} | Buy×{BUY_MULT} | Sell×{SELL_MULT}</p>
        <p style="margin-top: 5px;">Last Updated: {data.index[-1].strftime("%Y-%m-%d")}</p>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align: center; padding: 100px 20px;">
        <div style="font-size: 64px; margin-bottom: 20px;">⏳</div>
        <h2 style="color: #ffffff; margin-bottom: 10px;">데이터 로딩 중...</h2>
        <p style="color: #6b7280;">잠시만 기다려주세요.</p>
    </div>
    """, unsafe_allow_html=True)