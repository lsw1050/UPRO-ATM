import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
import streamlit.components.v1 as components
import json
import requests

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(page_title="LSW LOC", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 스타일
# ==========================================
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    * { font-family: 'Pretendard', -apple-system, sans-serif !important; }
    
    .stApp {
        background: linear-gradient(180deg, #0f0f13 0%, #1a1a23 100%);
    }
    
    /* 사이드바 완전히 숨기기 */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    
    .stButton > button {
        background: linear-gradient(135deg, #5046e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 14px;
        padding: 16px 24px;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 4px 20px rgba(80, 70, 229, 0.25);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 12px 35px rgba(80, 70, 229, 0.35);
    }
    
    [data-testid="stNumberInput"] input {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
    }
    
    .stSuccess { background: rgba(34, 197, 94, 0.1) !important; border-radius: 12px !important; }
    .stInfo { background: rgba(59, 130, 246, 0.1) !important; border-radius: 12px !important; }
    
    /* 모바일에서도 PC처럼 보이게 - 2열 레이아웃 유지 */
    [data-testid="column"] {
        min-width: 0 !important;
    }
    
    /* 모바일 뷰포트 강제 확대 방지 */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem !important;
            max-width: 100% !important;
        }
        
        /* 컬럼이 세로로 쌓이지 않도록 */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 0.5rem !important;
        }
        
        [data-testid="column"] {
            width: 50% !important;
            flex: 1 1 50% !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 세션 상태
# ==========================================
if 'seed' not in st.session_state: st.session_state.seed = 37000.0
if 'qty' not in st.session_state: st.session_state.qty = 77
if 'avg' not in st.session_state: st.session_state.avg = 115.76
if 'step' not in st.session_state: st.session_state.step = 2

# ==========================================
# 상단 헤더
# ==========================================
st.markdown("""
<div style="display: flex; align-items: center; gap: 16px; padding: 10px 0 20px 0;">
    <div style="
        width: 50px; height: 50px;
        background: linear-gradient(145deg, #5046e5, #7c3aed);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 30px rgba(80, 70, 229, 0.3);
    ">
        <span style="font-size: 24px;">💎</span>
    </div>
    <div>
        <h1 style="color: #ffffff; font-size: 24px; font-weight: 700; margin: 0;">LSW LOC</h1>
        <p style="color: #6b7280; font-size: 12px; margin: 2px 0 0 0;">시그마 자동매매 시스템</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 계좌 설정
# ==========================================
st.markdown('<p style="color: #6b7280; font-size: 13px; font-weight: 600; margin-bottom: 15px;">⚙️ 계좌 설정</p>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    seed = st.number_input("💰 투자 원금 ($)", value=st.session_state.seed, step=100.0, key="input_seed")
    qty = st.number_input("📊 보유 수량 (주)", value=st.session_state.qty, step=1, key="input_qty")
with c2:
    avg = st.number_input("💵 평균 단가 ($)", value=st.session_state.avg, step=0.01, key="input_avg")
    step = st.selectbox("🎯 매수 회차", options=[1, 2, 3], index=st.session_state.step - 1, key="input_step")

st.session_state.seed = seed
st.session_state.qty = qty
st.session_state.avg = avg
st.session_state.step = step

TICKER = "UPRO"
N_SIGMA, BUY_MULT, SELL_MULT = 2, 0.85, 0.35
WEIGHTS = [1, 1, 2]

# ==========================================
# 데이터 수집
# ==========================================
@st.cache_data(ttl=600)
def get_market_data():
    try:
        import yfinance as yf
        raw = yf.download([TICKER, "USDKRW=X"], period="30d", progress=False, timeout=10)['Close']
        if raw is not None and not raw.empty and len(raw) >= 2:
            return raw.dropna()
    except:
        pass
    
    try:
        import time
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        end = int(time.time())
        start = end - (30 * 24 * 60 * 60)
        data_dict = {}
        
        for ticker in [TICKER, "USDKRW=X"]:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={start}&period2={end}&interval=1d"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                result = resp.json()['chart']['result'][0]
                dates = pd.to_datetime(result['timestamp'], unit='s')
                data_dict[ticker] = pd.Series(result['indicators']['quote'][0]['close'], index=dates)
        
        if len(data_dict) == 2:
            return pd.DataFrame(data_dict).dropna()
    except:
        pass
    
    return None

data = get_market_data()

# ==========================================
# 메인
# ==========================================
if data is not None and not data.empty and len(data) >= 2:
    last_close = float(data[TICKER].iloc[-1])
    prev_close = float(data[TICKER].iloc[-2])
    rate = float(data['USDKRW=X'].iloc[-1])
    change_pct = (last_close - prev_close) / prev_close * 100
    
    used_cash = qty * avg
    pnl_usd = (last_close - avg) * qty
    pnl_krw = pnl_usd * rate
    pnl_pct = (pnl_usd / used_cash * 100) if used_cash > 0 else 0
    
    returns = data[TICKER].pct_change().dropna()
    sigma = returns.tail(N_SIGMA).std(ddof=0) if len(returns) >= N_SIGMA else 0
    
    buy_loc = last_close * (1 + BUY_MULT * sigma)
    sell_loc = last_close * (1 + SELL_MULT * sigma)
    
    target = seed * (WEIGHTS[step-1] / sum(WEIGHTS))
    remaining = seed - used_cash
    buy_qty = int(min(target, remaining) / buy_loc) if buy_loc > 0 else 0
    progress = (used_cash / seed * 100) if seed > 0 else 0

    # 수익 효과
    if pnl_krw >= 100000:
        components.html("""
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
        <script>!function(){var e=Date.now()+3e3;!function t(){confetti({particleCount:3,angle:60,spread:55,origin:{x:0,y:.6},shapes:["text"],shapeOptions:{text:{value:["💎","💰","✨"]}},scalar:2}),confetti({particleCount:3,angle:120,spread:55,origin:{x:1,y:.6},shapes:["text"],shapeOptions:{text:{value:["💎","💰","✨"]}},scalar:2}),Date.now()<e&&requestAnimationFrame(t)}()}();</script>
        """, height=1)

    # ==========================================
    # 가격 정보 헤더
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    h1, h2 = st.columns([2.5, 1])
    
    with h1:
        change_color = "#22c55e" if change_pct >= 0 else "#ef4444"
        change_bg = "rgba(34,197,94,0.12)" if change_pct >= 0 else "rgba(239,68,68,0.12)"
        change_arrow = "▲" if change_pct >= 0 else "▼"
        
        st.markdown(f"""
        <div style="padding: 10px 0 25px 0;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 6px 14px; border-radius: 10px; font-size: 14px; font-weight: 700; color: white;">{TICKER}</div>
                <span style="color: #6b7280; font-size: 13px;">3배 레버리지 S&P500</span>
            </div>
            <div style="display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap;">
                <span style="font-size: 42px; font-weight: 800; color: #ffffff;">${last_close:,.2f}</span>
                <div style="padding: 6px 14px; border-radius: 10px; background: {change_bg};">
                    <span style="color: {change_color}; font-size: 16px; font-weight: 700;">{change_arrow} {abs(change_pct):.2f}%</span>
                </div>
            </div>
            <p style="color: #4b5563; font-size: 13px; margin-top: 12px;">{data.index[-1].strftime("%Y년 %m월 %d일")} 기준 · 환율 ₩{rate:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with h2:
        pnl_color = "#22c55e" if pnl_krw >= 0 else "#ef4444"
        pnl_bg = "rgba(34,197,94,0.08)" if pnl_krw >= 0 else "rgba(239,68,68,0.08)"
        pnl_border = "rgba(34,197,94,0.15)" if pnl_krw >= 0 else "rgba(239,68,68,0.15)"
        
        st.markdown(f"""
        <div style="background: {pnl_bg}; border: 1px solid {pnl_border}; border-radius: 20px; padding: 24px; text-align: center;">
            <p style="color: #9ca3af; font-size: 13px; margin: 0 0 8px 0;">내 수익</p>
            <p style="color: {pnl_color}; font-size: 28px; font-weight: 800; margin: 0;">{pnl_krw:+,.0f}원</p>
            <p style="color: {pnl_color}; font-size: 14px; margin-top: 8px;">{pnl_pct:+.2f}%</p>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # LOC 주문 카드
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p style="color: #6b7280; font-size: 13px; font-weight: 600; margin-bottom: 15px;">📌 오늘의 주문</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(165deg, rgba(34,197,94,0.06) 0%, rgba(17,17,24,0.9) 100%); border: 1px solid rgba(34,197,94,0.12); border-radius: 24px; padding: 24px; border-top: 4px solid #22c55e;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                <span style="background: rgba(34,197,94,0.1); color: #4ade80; padding: 8px 14px; border-radius: 10px; font-size: 13px; font-weight: 700;">매수 주문</span>
                <span style="color: #6b7280; font-size: 12px;">{step}회차 / 3회차</span>
            </div>
            <p style="color: #71717a; font-size: 12px; margin: 0 0 6px 0;">지정가</p>
            <p style="color: #ffffff; font-size: 34px; font-weight: 800; margin: 0 0 18px 0;">${buy_loc:.2f}</p>
            <div style="display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.04);">
                <div>
                    <p style="color: #52525b; font-size: 11px; margin: 0 0 4px 0;">주문 수량</p>
                    <p style="color: #ffffff; font-size: 16px; font-weight: 700; margin: 0;">{buy_qty}주</p>
                </div>
                <div style="text-align: right;">
                    <p style="color: #52525b; font-size: 11px; margin: 0 0 4px 0;">예상 금액</p>
                    <p style="color: #ffffff; font-size: 16px; font-weight: 700; margin: 0;">₩{buy_loc*rate*buy_qty:,.0f}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: linear-gradient(165deg, rgba(239,68,68,0.06) 0%, rgba(17,17,24,0.9) 100%); border: 1px solid rgba(239,68,68,0.12); border-radius: 24px; padding: 24px; border-top: 4px solid #ef4444;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                <span style="background: rgba(239,68,68,0.1); color: #f87171; padding: 8px 14px; border-radius: 10px; font-size: 13px; font-weight: 700;">매도 주문</span>
                <span style="color: #6b7280; font-size: 12px;">전량 매도</span>
            </div>
            <p style="color: #71717a; font-size: 12px; margin: 0 0 6px 0;">지정가</p>
            <p style="color: #ffffff; font-size: 34px; font-weight: 800; margin: 0 0 18px 0;">${sell_loc:.2f}</p>
            <div style="display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.04);">
                <div>
                    <p style="color: #52525b; font-size: 11px; margin: 0 0 4px 0;">주문 수량</p>
                    <p style="color: #ffffff; font-size: 16px; font-weight: 700; margin: 0;">{qty}주</p>
                </div>
                <div style="text-align: right;">
                    <p style="color: #52525b; font-size: 11px; margin: 0 0 4px 0;">예상 금액</p>
                    <p style="color: #ffffff; font-size: 16px; font-weight: 700; margin: 0;">₩{sell_loc*rate*qty:,.0f}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 복사 버튼
    st.write("")
    b1, b2 = st.columns(2)
    with b1:
        buy_txt = f"UPRO 매수\n지정가: ${buy_loc:.2f}\n수량: {buy_qty}주"
        if st.button("📋  매수 주문 복사", use_container_width=True, key="cp_buy"):
            st.code(buy_txt)
            components.html(f"<script>navigator.clipboard.writeText(`{buy_txt}`);</script><p style='color:#4ade80;text-align:center;font-size:13px;'>✓ 복사 완료</p>", height=40)
    with b2:
        sell_txt = f"UPRO 매도\n지정가: ${sell_loc:.2f}\n수량: {qty}주"
        if st.button("📋  매도 주문 복사", use_container_width=True, key="cp_sell"):
            st.code(sell_txt)
            components.html(f"<script>navigator.clipboard.writeText(`{sell_txt}`);</script><p style='color:#4ade80;text-align:center;font-size:13px;'>✓ 복사 완료</p>", height=40)

    # ==========================================
    # 포트폴리오 현황
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p style="color: #6b7280; font-size: 13px; font-weight: 600; margin-bottom: 15px;">💼 포트폴리오 현황</p>', unsafe_allow_html=True)
    
    p1, p2, p3 = st.columns(3)
    
    with p1:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 18px; padding: 20px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 18px;">💰</span>
                <span style="color: #71717a; font-size: 12px;">보유 자산</span>
            </div>
            <p style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0;">${used_cash:,.0f}</p>
            <p style="color: #52525b; font-size: 11px; margin-top: 6px;">{qty}주 · 평단 ${avg:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with p2:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 18px; padding: 20px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 18px;">💵</span>
                <span style="color: #71717a; font-size: 12px;">잔여 현금</span>
            </div>
            <p style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0;">${remaining:,.0f}</p>
            <p style="color: #52525b; font-size: 11px; margin-top: 6px;">₩{remaining*rate:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with p3:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 18px; padding: 20px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 18px;">📊</span>
                <span style="color: #71717a; font-size: 12px;">투자 진행률</span>
            </div>
            <p style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0;">{progress:.1f}%</p>
            <div style="margin-top: 10px; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden;">
                <div style="width: {min(progress, 100)}%; height: 100%; background: linear-gradient(90deg, #5046e5, #7c3aed); border-radius: 3px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # 📖 사용 가이드 (상세 버전)
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p style="color: #6b7280; font-size: 13px; font-weight: 600; margin-bottom: 15px;">📖사용 가이드</p>', unsafe_allow_html=True)
    
    # 전략 소개
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(99,102,241,0.02) 100%); border: 1px solid rgba(99,102,241,0.2); border-radius: 20px; padding: 24px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <span style="font-size: 28px;">💡</span>
            <div>
                <p style="color: #a5b4fc; font-size: 18px; font-weight: 700; margin: 0;">변동성 기반 LOC 매매 전략</p>
                <p style="color: #6b7280; font-size: 13px; margin: 4px 0 0 0;">변동성을 활용한 자동 지정가 매매 시스템</p>
            </div>
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.8; margin: 0;">
            이 전략은 <span style="color: #ffffff;">시장 변동성(σ, 시그마)</span>을 기반으로 매수/매도 가격을 자동 계산합니다.
            변동성이 클수록 매수가와 매도가의 폭이 넓어지고, 변동성이 작으면 폭이 좁아집니다.
            이를 통해 시장 상황에 맞는 <span style="color: #a5b4fc;">적응형 지정가 매매</span>가 가능합니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 1
    st.markdown("""
    <div style="background: rgba(34,197,94,0.06); border: 1px solid rgba(34,197,94,0.15); border-left: 4px solid #22c55e; border-radius: 12px; padding: 20px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #22c55e, #16a34a); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: 800; font-size: 14px;">1</span>
            </div>
            <p style="color: #4ade80; font-size: 16px; font-weight: 700; margin: 0;">투자 원금 설정</p>
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.7; margin: 0 0 12px 0;">
            상단 <span style="color: #ffffff;">⚙️ 계좌 설정</span> 영역에서 본인의 <span style="color: #4ade80;">총 투자 원금(달러)</span>을 입력하세요.
        </p>
        <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
            <p style="color: #6b7280; font-size: 12px; margin: 0;">
                💡 <span style="color: #9ca3af;">예시: $30,000을 투자할 계획이라면 "투자 원금"에 30000 입력</span>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 2
    st.markdown("""
    <div style="background: rgba(59,130,246,0.06); border: 1px solid rgba(59,130,246,0.15); border-left: 4px solid #3b82f6; border-radius: 12px; padding: 20px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #3b82f6, #1d4ed8); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: 800; font-size: 14px;">2</span>
            </div>
            <p style="color: #60a5fa; font-size: 16px; font-weight: 700; margin: 0;">보유 현황 입력</p>
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.7; margin: 0 0 12px 0;">
            현재 보유 중인 <span style="color: #60a5fa;">주식 수량</span>과 <span style="color: #60a5fa;">평균 매수 단가</span>를 입력하세요.
        </p>
        <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
            <p style="color: #6b7280; font-size: 12px; margin: 0 0 6px 0;">
                💡 <span style="color: #9ca3af;">처음 시작하는 경우: 보유 수량 = 0, 평균 단가 = 0 으로 설정</span>
            </p>
            <p style="color: #6b7280; font-size: 12px; margin: 0;">
                💡 <span style="color: #9ca3af;">이미 보유 중인 경우: 증권사 앱에서 확인한 수량과 평단가 입력</span>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 3
    st.markdown("""
    <div style="background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.15); border-left: 4px solid #f59e0b; border-radius: 12px; padding: 20px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #f59e0b, #d97706); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: 800; font-size: 14px;">3</span>
            </div>
            <p style="color: #fbbf24; font-size: 16px; font-weight: 700; margin: 0;">매수 회차 선택</p>
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.7; margin: 0 0 12px 0;">
            투자금은 <span style="color: #fbbf24;">1 : 1 : 2</span> 비율로 총 3회에 나눠 투자합니다. 현재 몇 회차 매수인지 선택하세요.
        </p>
        <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0 0 4px 0;">
                • <span style="color: #ffffff;">1회차</span>: 총 투자금의 25% 매수 (첫 진입)
            </p>
            <p style="color: #9ca3af; font-size: 12px; margin: 0 0 4px 0;">
                • <span style="color: #ffffff;">2회차</span>: 총 투자금의 25% 추가 매수 (하락 시 물타기)
            </p>
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                • <span style="color: #ffffff;">3회차</span>: 총 투자금의 50% 추가 매수 (최종 물타기)
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 4
    st.markdown("""
    <div style="background: rgba(236,72,153,0.06); border: 1px solid rgba(236,72,153,0.15); border-left: 4px solid #ec4899; border-radius: 12px; padding: 20px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #ec4899, #be185d); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: 800; font-size: 14px;">4</span>
            </div>
            <p style="color: #f472b6; font-size: 16px; font-weight: 700; margin: 0;">LOC 주문 복사 → 증권사 앱에서 주문</p>
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.7; margin: 0 0 12px 0;">
            화면에 표시된 <span style="color: #4ade80;">매수 지정가</span>와 <span style="color: #f87171;">매도 지정가</span>를 확인하고,
            <span style="color: #f472b6;">"주문 복사"</span> 버튼을 눌러 증권사 앱에 붙여넣기 하세요.
        </p>
        <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0 0 6px 0;">
                📱 <span style="color: #ffffff;">증권사 앱 주문 방법</span>
            </p>
            <p style="color: #6b7280; font-size: 12px; margin: 0 0 4px 0;">
                1. 증권사 앱 실행 → 해외주식 → UPRO 검색
            </p>
            <p style="color: #6b7280; font-size: 12px; margin: 0 0 4px 0;">
                2. 주문 유형에서 <span style="color: #fbbf24;">"LOC (장마감지정가)"</span> 선택
            </p>
            <p style="color: #6b7280; font-size: 12px; margin: 0;">
                3. 복사한 지정가와 수량 입력 후 주문
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 5
    st.markdown("""
    <div style="background: rgba(139,92,246,0.06); border: 1px solid rgba(139,92,246,0.15); border-left: 4px solid #8b5cf6; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #8b5cf6, #6d28d9); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: 800; font-size: 14px;">5</span>
            </div>
            <p style="color: #a78bfa; font-size: 16px; font-weight: 700; margin: 0;">체결 후 정보 업데이트</p>
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.7; margin: 0 0 12px 0;">
            주문이 체결되면 <span style="color: #a78bfa;">보유 수량</span>과 <span style="color: #a78bfa;">평균 단가</span>를 업데이트하고,
            다음 매수 회차로 변경하세요.
        </p>
        <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
            <p style="color: #6b7280; font-size: 12px; margin: 0 0 4px 0;">
                ✅ 매수 체결 시: 보유 수량 ↑, 평단가 업데이트, 매수 회차 +1
            </p>
            <p style="color: #6b7280; font-size: 12px; margin: 0;">
                ✅ 매도 체결 시: 보유 수량 = 0, 평단가 = 0, 매수 회차 = 1회차로 리셋
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # LOC 설명 + 주의사항
    lc1, lc2 = st.columns(2)
    
    with lc1:
        st.markdown("""
        <div style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.15); border-radius: 16px; padding: 20px; height: 100%;">
            <p style="color: #a5b4fc; font-size: 14px; font-weight: 700; margin: 0 0 12px 0;">📌 LOC 주문이란?</p>
            <p style="color: #9ca3af; font-size: 12px; line-height: 1.7; margin: 0 0 12px 0;">
                <span style="color: #ffffff;">Limit On Close</span> (장마감지정가)
            </p>
            <p style="color: #6b7280; font-size: 12px; line-height: 1.6; margin: 0;">
                • 미국 장 마감 직전에 체결되는 지정가 주문<br>
                • 한국시간 기준 오전 5~6시에 실행<br>
                • 지정가 이하(매수) / 이상(매도)일 때만 체결<br>
                • 체결 안 되면 자동 취소됨
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with lc2:
        st.markdown("""
        <div style="background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.15); border-radius: 16px; padding: 20px; height: 100%;">
            <p style="color: #f87171; font-size: 14px; font-weight: 700; margin: 0 0 12px 0;">⚠️ 주의사항</p>
            <p style="color: #6b7280; font-size: 12px; line-height: 1.6; margin: 0;">
                • 3배 레버리지 ETF는 <span style="color: #f87171;">변동성이 큰</span> 상품입니다<br>
                • 감정 개입 최소화<br>
                • 반드시 <span style="color: #ffffff;">멈추지 말고</span>투자해야함<br>
                • 매일 주문을 갱신해야 합니다 (가격 변동)<br>
                • 손실/수익에 일희일비 금지
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # 거래 기록
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p style="color: #6b7280; font-size: 13px; font-weight: 600; margin-bottom: 15px;">📝 거래 기록</p>', unsafe_allow_html=True)
    
    r1, r2 = st.columns(2)
    with r1:
        if st.button("💾  매수 기록 저장", use_container_width=True, key="sv_b"):
            rec = {"날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "유형": "매수", "가격": round(buy_loc, 2), "수량": buy_qty, "회차": step}
            try:
                with open("trade_log.json", "r") as f: logs = json.load(f)
            except: logs = []
            logs.append(rec)
            with open("trade_log.json", "w") as f: json.dump(logs, f, indent=2, ensure_ascii=False)
            st.success("✅ 매수 기록이 저장되었습니다")

    with r2:
        if st.button("💾  매도 기록 저장", use_container_width=True, key="sv_s"):
            rec = {"날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "유형": "매도", "가격": round(sell_loc, 2), "수량": qty, "회차": 0}
            try:
                with open("trade_log.json", "r") as f: logs = json.load(f)
            except: logs = []
            logs.append(rec)
            with open("trade_log.json", "w") as f: json.dump(logs, f, indent=2, ensure_ascii=False)
            st.success("✅ 매도 기록이 저장되었습니다")

    st.write("")
    if st.checkbox("📜 거래 내역 보기"):
        try:
            with open("trade_log.json", "r") as f: logs = json.load(f)
            if logs: 
                st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
            else: 
                st.info("저장된 거래 내역이 없습니다")
        except: 
            st.info("저장된 거래 내역이 없습니다")

else:
    st.markdown("""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; text-align: center;">
        <div style="width: 50px; height: 50px; border: 3px solid rgba(124, 58, 237, 0.2); border-top-color: #7c3aed; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 24px;"></div>
        <p style="color: #71717a; font-size: 15px;">데이터를 불러오는 중입니다...</p>
    </div>
    <style>@keyframes spin { to { transform: rotate(360deg); } }</style>
    """, unsafe_allow_html=True)
    
    import time
    time.sleep(5)
    st.rerun()