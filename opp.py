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
st.set_page_config(page_title="LSW SIGNAL", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

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
    
    /* 모바일 최적화 */
    @media (max-width: 768px) {
        .block-container { padding: 1rem !important; }
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
        <h1 style="color: #ffffff; font-size: 24px; font-weight: 700; margin: 0;">LSW SIGNAL</h1>
        <p style="color: #6b7280; font-size: 12px; margin: 2px 0 0 0;">변동성 자동매매 시스템</p>
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
    # 📖 사용 가이드
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p style="color: #6b7280; font-size: 13px; font-weight: 600; margin-bottom: 15px;">📖 S-ATM 사용 가이드</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="padding: 10px 0;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
            <span style="font-size: 24px;">💡</span>
            <div>
                <p style="color: #a5b4fc; font-size: 16px; font-weight: 700; margin: 0;">시그마(σ) 기반 LOC 분할매수 전략</p>
                <p style="color: #6b7280; font-size: 12px; margin: 4px 0 0 0;">변동성을 활용한 자동 지정가 매매 시스템</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("""
        <div style="background: rgba(255,255,255,0.02); border-radius: 14px; padding: 18px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <div style="width: 28px; height: 28px; background: linear-gradient(135deg, #22c55e, #16a34a); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-weight: 800; font-size: 13px;">1</span>
                </div>
                <p style="color: #ffffff; font-size: 14px; font-weight: 600; margin: 0;">투자금 설정</p>
            </div>
            <p style="color: #9ca3af; font-size: 12px; line-height: 1.6; margin: 0;">
                상단 <span style="color: #a5b4fc;">⚙️ 계좌 설정</span>에서 투자 원금(달러)을 입력하세요.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with g2:
        st.markdown("""
        <div style="background: rgba(255,255,255,0.02); border-radius: 14px; padding: 18px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <div style="width: 28px; height: 28px; background: linear-gradient(135deg, #3b82f6, #1d4ed8); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-weight: 800; font-size: 13px;">2</span>
                </div>
                <p style="color: #ffffff; font-size: 14px; font-weight: 600; margin: 0;">LOC 주문 확인</p>
            </div>
            <p style="color: #9ca3af; font-size: 12px; line-height: 1.6; margin: 0;">
                <span style="color: #4ade80;">매수가</span>와 <span style="color: #f87171;">매도가</span>는 매일 자동 업데이트됩니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    g3, g4 = st.columns(2)
    with g3:
        st.markdown("""
        <div style="background: rgba(255,255,255,0.02); border-radius: 14px; padding: 18px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <div style="width: 28px; height: 28px; background: linear-gradient(135deg, #f59e0b, #d97706); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-weight: 800; font-size: 13px;">3</span>
                </div>
                <p style="color: #ffffff; font-size: 14px; font-weight: 600; margin: 0;">3회 분할 매수</p>
            </div>
            <p style="color: #9ca3af; font-size: 12px; line-height: 1.6; margin: 0;">
                투자금을 <span style="color: #a5b4fc;">1:1:2</span> 비율로 3회 나눠 투자합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with g4:
        st.markdown("""
        <div style="background: rgba(255,255,255,0.02); border-radius: 14px; padding: 18px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <div style="width: 28px; height: 28px; background: linear-gradient(135deg, #ec4899, #be185d); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-weight: 800; font-size: 13px;">4</span>
                </div>
                <p style="color: #ffffff; font-size: 14px; font-weight: 600; margin: 0;">증권사 주문</p>
            </div>
            <p style="color: #9ca3af; font-size: 12px; line-height: 1.6; margin: 0;">
                복사 버튼 → 증권사 앱 <span style="color: #fbbf24;">LOC 주문</span>에 붙여넣기
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="padding: 16px; background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.15); border-radius: 12px; margin-top: 8px;">
        <p style="color: #fbbf24; font-size: 13px; font-weight: 600; margin: 0 0 6px 0;">⚡ 처음 시작하는 경우</p>
        <p style="color: #9ca3af; font-size: 12px; line-height: 1.5; margin: 0;">
            보유 수량/평단가를 <span style="color: #fff;">0</span>으로, 매수 회차를 <span style="color: #fff;">1회차</span>로 설정 후 시작하세요.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="padding: 16px; background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.15); border-radius: 12px; margin-top: 12px;">
        <p style="color: #a5b4fc; font-size: 13px; font-weight: 600; margin: 0 0 6px 0;">📌 LOC 주문이란?</p>
        <p style="color: #9ca3af; font-size: 12px; line-height: 1.5; margin: 0;">
            장 마감 시점에 지정가로 체결되는 주문. 한국시간 오전 5~6시에 실행됩니다.
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