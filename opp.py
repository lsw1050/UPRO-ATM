import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import streamlit.components.v1 as components
import json
import requests

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(page_title="LSW LOC Pro", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 스타일
# ==========================================
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', -apple-system, sans-serif !important; }
    .stApp { background: #1a1d23; }
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    .stButton > button {
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 14px 20px;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover { background: #1d4ed8; transform: translateY(-1px); }
    [data-testid="stNumberInput"] input {
        background: #252830 !important;
        border: 1px solid #3a3f4a !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-size: 16px !important;
    }
    .stSelectbox > div > div {
        background: #252830 !important;
        border: 1px solid #3a3f4a !important;
        border-radius: 8px !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: #252830;
        border-radius: 8px;
        padding: 10px 20px;
        color: #9ca3af;
    }
    .stTabs [aria-selected="true"] { background: #2563eb; color: white; }
    .stSuccess { background: rgba(34, 197, 94, 0.15) !important; border-radius: 8px !important; }
    .stInfo { background: rgba(59, 130, 246, 0.15) !important; border-radius: 8px !important; }
    [data-testid="column"] { min-width: 0 !important; }
    @media (max-width: 768px) {
        .block-container { padding: 1rem !important; max-width: 100% !important; }
        [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.5rem !important; }
        [data-testid="column"] { width: 50% !important; flex: 1 1 50% !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 전략 파라미터 (고정)
# ==========================================
TICKER = "UPRO"
N_SIGMA = 2
BUY_MULT = 0.85
SELL_MULT = 0.35
N_SPLIT = 3
WEIGHTS = [1, 1, 2]  # 1:1:2 비율

# ==========================================
# 데이터 저장/로드 함수 (JSON 파일 기반)
# ==========================================
DATA_FILE = "lsw_loc_data.json"

def load_data():
    """저장된 데이터 로드"""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "seed": 37000.0,
            "qty": 0,
            "avg": 0.0,
            "step": 1,
            "cash": 37000.0,
            "trades": [],
            "daily_records": []
        }

def save_data(data):
    """데이터 저장"""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

# ==========================================
# 시장 데이터 수집
# ==========================================
@st.cache_data(ttl=600)
def get_market_data(days=60):
    """시장 데이터 수집 (yfinance + fallback)"""
    try:
        import yfinance as yf
        # yfinance period 문자열 변환
        if days <= 30:
            period = "1mo"
        elif days <= 90:
            period = "3mo"
        elif days <= 180:
            period = "6mo"
        elif days <= 365:
            period = "1y"
        else:
            period = "2y"
        
        raw = yf.download([TICKER, "USDKRW=X"], period=period, progress=False, timeout=15)['Close']
        if raw is not None and not raw.empty and len(raw) >= 2:
            return raw.dropna()
    except:
        pass
    
    try:
        import time
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        end = int(time.time())
        start = end - (days * 24 * 60 * 60)
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

@st.cache_data(ttl=3600)
def get_backtest_data(days=365):
    """백테스팅용 장기 데이터 수집"""
    return get_market_data(days)

# ==========================================
# 백테스팅 함수
# ==========================================
def run_backtest(data, seed=37000, n_sigma=2, buy_mult=0.85, sell_mult=0.35, weights=[1,1,2]):
    """백테스팅 실행"""
    if data is None or len(data) < n_sigma + 2:
        return None
    
    prices = data[TICKER].values
    dates = data.index
    
    # 초기 상태
    cash = seed
    qty = 0
    avg_price = 0
    step = 0  # 0: 포지션 없음, 1~3: 매수 회차
    
    records = []
    
    for i in range(n_sigma, len(prices)):
        close = prices[i]
        prev_close = prices[i-1]
        
        # 변동성 계산 (n일 수익률 표준편차)
        returns = np.diff(prices[max(0,i-n_sigma):i+1]) / prices[max(0,i-n_sigma):i]
        sigma = np.std(returns, ddof=0) if len(returns) >= n_sigma else 0
        
        # LOC 가격 계산
        buy_loc = prev_close * (1 + buy_mult * sigma)
        sell_loc = prev_close * (1 + sell_mult * sigma)
        
        # 매수/매도 신호
        buy_signal = close <= buy_loc and step < len(weights)
        sell_signal = close >= sell_loc and qty > 0
        
        # 거래 실행
        trade_type = None
        trade_qty = 0
        trade_price = 0
        
        if sell_signal:
            # 매도 (전량)
            trade_type = "SELL"
            trade_qty = qty
            trade_price = close
            cash += qty * close
            qty = 0
            avg_price = 0
            step = 0
        
        if buy_signal and step < len(weights):
            # 매수
            target_pct = weights[step] / sum(weights)
            target_amount = seed * target_pct
            buy_qty = int(target_amount / close)
            
            if buy_qty > 0 and cash >= buy_qty * close:
                trade_type = "BUY"
                trade_qty = buy_qty
                trade_price = close
                
                # 평균단가 계산
                total_value = qty * avg_price + buy_qty * close
                qty += buy_qty
                avg_price = total_value / qty if qty > 0 else 0
                cash -= buy_qty * close
                step += 1
        
        # 자산 계산
        total_value = cash + qty * close
        pnl_pct = (total_value / seed - 1) * 100 if seed > 0 else 0
        
        records.append({
            "date": dates[i],
            "close": close,
            "buy_loc": buy_loc,
            "sell_loc": sell_loc,
            "sigma": sigma,
            "cash": cash,
            "qty": qty,
            "avg_price": avg_price,
            "total_value": total_value,
            "pnl_pct": pnl_pct,
            "trade_type": trade_type,
            "trade_qty": trade_qty,
            "trade_price": trade_price,
            "step": step
        })
    
    return pd.DataFrame(records)

# ==========================================
# 성과 지표 계산
# ==========================================
def calculate_metrics(bt_df, seed):
    """백테스트 성과 지표 계산 (확장)"""
    if bt_df is None or len(bt_df) == 0:
        return {}
    
    final_value = bt_df['total_value'].iloc[-1]
    total_return = (final_value / seed - 1) * 100
    
    # MDD 계산
    peak = bt_df['total_value'].expanding().max()
    drawdown = (bt_df['total_value'] - peak) / peak * 100
    mdd = drawdown.min()
    
    # 거래 횟수
    buy_count = len(bt_df[bt_df['trade_type'] == 'BUY'])
    sell_count = len(bt_df[bt_df['trade_type'] == 'SELL'])
    
    # Buy & Hold
    first_close = bt_df['close'].iloc[0]
    last_close = bt_df['close'].iloc[-1]
    bh_return = (last_close / first_close - 1) * 100
    bh_final = seed * (last_close / first_close)
    
    # Buy & Hold MDD
    bh_values = seed * (bt_df['close'] / first_close)
    bh_peak = bh_values.expanding().max()
    bh_drawdown = (bh_values - bh_peak) / bh_peak * 100
    bh_mdd = bh_drawdown.min()
    
    # 일 수 계산
    days = len(bt_df)
    years = days / 252  # 거래일 기준
    
    # CAGR 계산 (연환산 수익률)
    if years > 0:
        cagr = ((final_value / seed) ** (1 / years) - 1) * 100
        bh_cagr = ((bh_final / seed) ** (1 / years) - 1) * 100
    else:
        cagr = total_return
        bh_cagr = bh_return
    
    # 일간 수익률 계산
    daily_returns = bt_df['total_value'].pct_change().dropna()
    bh_daily_returns = bt_df['close'].pct_change().dropna()
    
    # 변동성 (연환산)
    volatility = daily_returns.std() * np.sqrt(252) * 100
    bh_volatility = bh_daily_returns.std() * np.sqrt(252) * 100
    
    # 샤프 비율 (무위험 이자율 4% 가정)
    risk_free = 0.04
    if volatility > 0:
        sharpe = (cagr / 100 - risk_free) / (volatility / 100)
    else:
        sharpe = 0
    
    if bh_volatility > 0:
        bh_sharpe = (bh_cagr / 100 - risk_free) / (bh_volatility / 100)
    else:
        bh_sharpe = 0
    
    # 승률 계산 (양수 수익 일 비율)
    win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100 if len(daily_returns) > 0 else 0
    bh_win_rate = (bh_daily_returns > 0).sum() / len(bh_daily_returns) * 100 if len(bh_daily_returns) > 0 else 0
    
    # 최고/최저 일간 수익률
    max_daily = daily_returns.max() * 100 if len(daily_returns) > 0 else 0
    min_daily = daily_returns.min() * 100 if len(daily_returns) > 0 else 0
    bh_max_daily = bh_daily_returns.max() * 100 if len(bh_daily_returns) > 0 else 0
    bh_min_daily = bh_daily_returns.min() * 100 if len(bh_daily_returns) > 0 else 0
    
    return {
        "initial": seed,
        "final": final_value,
        "total_return": total_return,
        "mdd": mdd,
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "max_daily": max_daily,
        "min_daily": min_daily,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "days": days,
        "bh_final": bh_final,
        "bh_return": bh_return,
        "bh_mdd": bh_mdd,
        "bh_cagr": bh_cagr,
        "bh_volatility": bh_volatility,
        "bh_sharpe": bh_sharpe,
        "bh_win_rate": bh_win_rate,
        "bh_max_daily": bh_max_daily,
        "bh_min_daily": bh_min_daily
    }

# ==========================================
# 메인 앱
# ==========================================

# 데이터 로드
saved_data = load_data()

# 세션 상태 초기화
if 'seed' not in st.session_state: st.session_state.seed = saved_data.get('seed', 37000.0)
if 'qty' not in st.session_state: st.session_state.qty = saved_data.get('qty', 0)
if 'avg' not in st.session_state: st.session_state.avg = saved_data.get('avg', 0.0)
if 'step' not in st.session_state: st.session_state.step = saved_data.get('step', 1)
if 'cash' not in st.session_state: st.session_state.cash = saved_data.get('cash', 37000.0)
if 'trades' not in st.session_state: st.session_state.trades = saved_data.get('trades', [])

# ==========================================
# 헤더
# ==========================================
st.markdown("""
<div style="display: flex; align-items: center; gap: 14px; padding: 16px 0; margin-bottom: 16px; border-bottom: 1px solid #2a2f38;">
    <div style="width: 48px; height: 48px; background: #2563eb; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 22px;">📈</span>
    </div>
    <div>
        <h1 style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0;">LSW LOC Pro</h1>
        <p style="color: #6b7280; font-size: 13px; margin: 2px 0 0 0;">시그마 자동매매 시스템 + 백테스팅</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 탭 구성
# ==========================================
tab1, tab2, tab3 = st.tabs(["📌 오늘의 주문", "📊 백테스팅", "📝 거래 기록"])

# 시장 데이터 가져오기
data = get_market_data(60)

# ==========================================
# TAB 1: 오늘의 주문 (기존 기능)
# ==========================================
with tab1:
    st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">⚙️ 계좌 설정</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        seed = st.number_input("💰 투자 원금 ($)", value=st.session_state.seed, step=100.0, key="input_seed")
        qty = st.number_input("📊 보유 수량 (주)", value=st.session_state.qty, step=1, key="input_qty")
    with c2:
        avg = st.number_input("💵 평균 단가 ($)", value=st.session_state.avg, step=0.01, key="input_avg")
        step = st.selectbox("🎯 매수 회차", options=[1, 2, 3], index=max(0, st.session_state.step - 1), key="input_step")
    
    # 세션 상태 업데이트
    st.session_state.seed = seed
    st.session_state.qty = qty
    st.session_state.avg = avg
    st.session_state.step = step
    
    if data is not None and len(data) >= 2:
        last_close = float(data[TICKER].iloc[-1])
        prev_close = float(data[TICKER].iloc[-2])
        rate = float(data['USDKRW=X'].iloc[-1])
        change_pct = (last_close - prev_close) / prev_close * 100
        
        used_cash = qty * avg
        pnl_usd = (last_close - avg) * qty if qty > 0 else 0
        pnl_krw = pnl_usd * rate
        pnl_pct = (pnl_usd / used_cash * 100) if used_cash > 0 else 0
        
        # 변동성 계산
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
            <script>!function(){var e=Date.now()+3e3;!function t(){confetti({particleCount:3,angle:60,spread:55,origin:{x:0,y:.6}}),confetti({particleCount:3,angle:120,spread:55,origin:{x:1,y:.6}}),Date.now()<e&&requestAnimationFrame(t)}()}();</script>
            """, height=1)

        # 가격 정보
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        h1, h2 = st.columns([2.5, 1])
        
        with h1:
            change_color = "#22c55e" if change_pct >= 0 else "#ef4444"
            change_arrow = "▲" if change_pct >= 0 else "▼"
            
            st.markdown(f"""
            <div style="background: #252830; border-radius: 12px; padding: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                    <span style="background: #2563eb; color: white; padding: 5px 12px; border-radius: 6px; font-size: 13px; font-weight: 700;">{TICKER}</span>
                    <span style="color: #9ca3af; font-size: 13px;">3배 레버리지 S&P500</span>
                </div>
                <div style="display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;">
                    <span style="font-size: 36px; font-weight: 800; color: #ffffff;">${last_close:,.2f}</span>
                    <span style="color: {change_color}; font-size: 15px; font-weight: 600;">{change_arrow} {abs(change_pct):.2f}%</span>
                </div>
                <p style="color: #6b7280; font-size: 12px; margin-top: 10px;">{data.index[-1].strftime("%Y년 %m월 %d일")} 기준 · σ = {sigma:.4f} · 환율 ₩{rate:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with h2:
            pnl_color = "#22c55e" if pnl_krw >= 0 else "#ef4444"
            pnl_bg = "#1a2e1a" if pnl_krw >= 0 else "#2e1a1a"
            
            st.markdown(f"""
            <div style="background: {pnl_bg}; border-radius: 12px; padding: 20px; text-align: center; height: 100%;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0 0 8px 0;">내 수익</p>
                <p style="color: {pnl_color}; font-size: 24px; font-weight: 800; margin: 0;">{pnl_krw:+,.0f}원</p>
                <p style="color: {pnl_color}; font-size: 13px; margin-top: 6px;">{pnl_pct:+.2f}%</p>
            </div>
            """, unsafe_allow_html=True)

        # LOC 주문 카드
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">📌 오늘의 주문</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div style="background: #252830; border-left: 4px solid #22c55e; border-radius: 8px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <span style="color: #22c55e; font-size: 14px; font-weight: 700;">▶ 매수 주문</span>
                    <span style="color: #6b7280; font-size: 12px;">{step}회차 / 3회차</span>
                </div>
                <p style="color: #6b7280; font-size: 11px; margin: 0 0 4px 0;">지정가</p>
                <p style="color: #ffffff; font-size: 28px; font-weight: 800; margin: 0 0 14px 0;">${buy_loc:.2f}</p>
                <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid #3a3f4a;">
                    <div>
                        <p style="color: #6b7280; font-size: 11px; margin: 0 0 3px 0;">주문 수량</p>
                        <p style="color: #ffffff; font-size: 15px; font-weight: 600; margin: 0;">{buy_qty}주</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="color: #6b7280; font-size: 11px; margin: 0 0 3px 0;">예상 금액</p>
                        <p style="color: #22c55e; font-size: 15px; font-weight: 600; margin: 0;">₩{buy_loc*rate*buy_qty:,.0f}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="background: #252830; border-left: 4px solid #ef4444; border-radius: 8px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <span style="color: #ef4444; font-size: 14px; font-weight: 700;">◀ 매도 주문</span>
                    <span style="color: #6b7280; font-size: 12px;">전량 매도</span>
                </div>
                <p style="color: #6b7280; font-size: 11px; margin: 0 0 4px 0;">지정가</p>
                <p style="color: #ffffff; font-size: 28px; font-weight: 800; margin: 0 0 14px 0;">${sell_loc:.2f}</p>
                <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid #3a3f4a;">
                    <div>
                        <p style="color: #6b7280; font-size: 11px; margin: 0 0 3px 0;">주문 수량</p>
                        <p style="color: #ffffff; font-size: 15px; font-weight: 600; margin: 0;">{qty}주</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="color: #6b7280; font-size: 11px; margin: 0 0 3px 0;">예상 금액</p>
                        <p style="color: #ef4444; font-size: 15px; font-weight: 600; margin: 0;">₩{sell_loc*rate*qty:,.0f}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 복사 버튼
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            buy_txt = f"UPRO 매수\n지정가: ${buy_loc:.2f}\n수량: {buy_qty}주"
            if st.button("📋 매수 주문 복사", use_container_width=True, key="cp_buy"):
                st.code(buy_txt)
                components.html(f"<script>navigator.clipboard.writeText(`{buy_txt}`);</script><p style='color:#22c55e;text-align:center;font-size:13px;'>✓ 복사 완료</p>", height=40)
        with b2:
            sell_txt = f"UPRO 매도\n지정가: ${sell_loc:.2f}\n수량: {qty}주"
            if st.button("📋 매도 주문 복사", use_container_width=True, key="cp_sell"):
                st.code(sell_txt)
                components.html(f"<script>navigator.clipboard.writeText(`{sell_txt}`);</script><p style='color:#22c55e;text-align:center;font-size:13px;'>✓ 복사 완료</p>", height=40)

        # 포트폴리오 현황
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">💼 포트폴리오 현황</div>', unsafe_allow_html=True)
        
        p1, p2, p3 = st.columns(3)
        with p1:
            st.markdown(f"""
            <div style="background: #252830; border-radius: 8px; padding: 16px;">
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 8px 0;">💰 보유 자산</p>
                <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">${used_cash:,.0f}</p>
                <p style="color: #6b7280; font-size: 11px; margin-top: 4px;">{qty}주 · 평단 ${avg:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
        with p2:
            st.markdown(f"""
            <div style="background: #252830; border-radius: 8px; padding: 16px;">
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 8px 0;">💵 잔여 현금</p>
                <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">${remaining:,.0f}</p>
                <p style="color: #6b7280; font-size: 11px; margin-top: 4px;">₩{remaining*rate:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        with p3:
            st.markdown(f"""
            <div style="background: #252830; border-radius: 8px; padding: 16px;">
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 8px 0;">📊 투자 진행률</p>
                <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">{progress:.1f}%</p>
                <div style="margin-top: 8px; height: 6px; background: #3a3f4a; border-radius: 3px; overflow: hidden;">
                    <div style="width: {min(progress, 100)}%; height: 100%; background: #2563eb; border-radius: 3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 거래 기록 버튼
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">💾 거래 기록</div>', unsafe_allow_html=True)
        
        r1, r2 = st.columns(2)
        with r1:
            if st.button("✅ 매수 체결 기록", use_container_width=True, key="rec_buy"):
                trade = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "BUY",
                    "price": round(buy_loc, 2),
                    "qty": buy_qty,
                    "step": step
                }
                st.session_state.trades.append(trade)
                
                # 포지션 업데이트
                new_qty = st.session_state.qty + buy_qty
                new_avg = ((st.session_state.qty * st.session_state.avg) + (buy_qty * buy_loc)) / new_qty if new_qty > 0 else 0
                st.session_state.qty = new_qty
                st.session_state.avg = round(new_avg, 2)
                st.session_state.step = min(step + 1, 3)
                
                # 저장
                save_data({
                    "seed": st.session_state.seed,
                    "qty": st.session_state.qty,
                    "avg": st.session_state.avg,
                    "step": st.session_state.step,
                    "trades": st.session_state.trades
                })
                st.success(f"✅ 매수 체결: {buy_qty}주 @ ${buy_loc:.2f}")
                st.rerun()
        
        with r2:
            if st.button("✅ 매도 체결 기록", use_container_width=True, key="rec_sell"):
                if qty > 0:
                    trade = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "type": "SELL",
                        "price": round(sell_loc, 2),
                        "qty": qty,
                        "step": 0
                    }
                    st.session_state.trades.append(trade)
                    
                    # 포지션 리셋
                    st.session_state.qty = 0
                    st.session_state.avg = 0.0
                    st.session_state.step = 1
                    
                    # 저장
                    save_data({
                        "seed": st.session_state.seed,
                        "qty": st.session_state.qty,
                        "avg": st.session_state.avg,
                        "step": st.session_state.step,
                        "trades": st.session_state.trades
                    })
                    st.success(f"✅ 매도 체결: {qty}주 @ ${sell_loc:.2f}")
                    st.rerun()
                else:
                    st.warning("⚠️ 매도할 수량이 없습니다")

    else:
        st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 40vh; text-align: center;">
            <div style="width: 40px; height: 40px; border: 3px solid #3a3f4a; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 20px;"></div>
            <p style="color: #6b7280; font-size: 14px;">데이터를 불러오는 중입니다...</p>
        </div>
        <style>@keyframes spin { to { transform: rotate(360deg); } }</style>
        """, unsafe_allow_html=True)

# ==========================================
# TAB 2: 백테스팅
# ==========================================
with tab2:
    st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">📊 백테스팅 설정</div>', unsafe_allow_html=True)
    
    # 기간 선택
    period_col1, period_col2 = st.columns([1, 3])
    with period_col1:
        bt_period = st.selectbox(
            "백테스트 기간",
            options=["6개월", "1년"],
            index=1,
            key="bt_period"
        )
    
    # 기간에 따른 일수 설정
    bt_days = 180 if bt_period == "6개월" else 365
    
    # 백테스트용 데이터 가져오기
    bt_data = get_backtest_data(bt_days)
    
    if bt_data is not None and len(bt_data) >= 10:
        # 백테스팅 실행
        bt_df = run_backtest(bt_data, seed=37000)
        
        if bt_df is not None and len(bt_df) > 0:
            metrics = calculate_metrics(bt_df, 37000)
            
            # 기간 정보 표시
            start_date = bt_df['date'].iloc[0].strftime('%Y.%m.%d')
            end_date = bt_df['date'].iloc[-1].strftime('%Y.%m.%d')
            
            st.markdown(f"""
            <div style="background: #252830; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
                <span style="color: #6b7280; font-size: 12px;">📅 테스트 기간: </span>
                <span style="color: #fff; font-size: 12px; font-weight: 600;">{start_date} ~ {end_date}</span>
                <span style="color: #6b7280; font-size: 12px;"> ({metrics['days']}일)</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 핵심 성과 요약 카드 (4개)
            st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">📈 핵심 성과</div>', unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            
            with m1:
                ret_color = "#22c55e" if metrics['total_return'] >= 0 else "#ef4444"
                diff = metrics['total_return'] - metrics['bh_return']
                diff_color = "#22c55e" if diff >= 0 else "#ef4444"
                st.markdown(f"""
                <div style="background: #252830; border-radius: 8px; padding: 16px; text-align: center;">
                    <p style="color: #6b7280; font-size: 11px; margin: 0 0 6px 0;">σ 전략 수익률</p>
                    <p style="color: {ret_color}; font-size: 24px; font-weight: 800; margin: 0;">{metrics['total_return']:+.2f}%</p>
                    <p style="color: {diff_color}; font-size: 11px; margin-top: 4px;">B&H 대비 {diff:+.2f}%p</p>
                </div>
                """, unsafe_allow_html=True)
            
            with m2:
                st.markdown(f"""
                <div style="background: #252830; border-radius: 8px; padding: 16px; text-align: center;">
                    <p style="color: #6b7280; font-size: 11px; margin: 0 0 6px 0;">σ 전략 MDD</p>
                    <p style="color: #ef4444; font-size: 24px; font-weight: 800; margin: 0;">{metrics['mdd']:.2f}%</p>
                    <p style="color: #6b7280; font-size: 11px; margin-top: 4px;">B&H: {metrics['bh_mdd']:.2f}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with m3:
                sharpe_color = "#22c55e" if metrics['sharpe'] > 0.5 else "#f59e0b" if metrics['sharpe'] > 0 else "#ef4444"
                st.markdown(f"""
                <div style="background: #252830; border-radius: 8px; padding: 16px; text-align: center;">
                    <p style="color: #6b7280; font-size: 11px; margin: 0 0 6px 0;">σ 전략 샤프</p>
                    <p style="color: {sharpe_color}; font-size: 24px; font-weight: 800; margin: 0;">{metrics['sharpe']:.2f}</p>
                    <p style="color: #6b7280; font-size: 11px; margin-top: 4px;">B&H: {metrics['bh_sharpe']:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with m4:
                st.markdown(f"""
                <div style="background: #252830; border-radius: 8px; padding: 16px; text-align: center;">
                    <p style="color: #6b7280; font-size: 11px; margin: 0 0 6px 0;">거래 횟수</p>
                    <p style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 0;">{metrics['buy_count'] + metrics['sell_count']}</p>
                    <p style="color: #6b7280; font-size: 11px; margin-top: 4px;">매수 {metrics['buy_count']} / 매도 {metrics['sell_count']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 자산 추이 차트
            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
            st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">📈 자산 추이 비교</div>', unsafe_allow_html=True)
            
            # 차트 데이터 준비
            sigma_values = bt_df['total_value'].values
            bh_values = 37000 * (bt_df['close'] / bt_df['close'].iloc[0]).values
            dates = bt_df['date'].values
            
            # Plotly 차트 생성
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            # σ 전략 라인 (파란색, 굵게)
            fig.add_trace(go.Scatter(
                x=dates,
                y=sigma_values,
                mode='lines',
                name='σ 전략',
                line=dict(color='#3b82f6', width=3),
                hovertemplate='<b>σ 전략</b><br>날짜: %{x|%Y-%m-%d}<br>자산: $%{y:,.0f}<extra></extra>'
            ))
            
            # Buy & Hold 라인 (주황색)
            fig.add_trace(go.Scatter(
                x=dates,
                y=bh_values,
                mode='lines',
                name='Buy & Hold',
                line=dict(color='#f97316', width=2, dash='dot'),
                hovertemplate='<b>Buy & Hold</b><br>날짜: %{x|%Y-%m-%d}<br>자산: $%{y:,.0f}<extra></extra>'
            ))
            
            # 초기 자본선 (점선)
            fig.add_hline(
                y=37000, 
                line_dash="dash", 
                line_color="#6b7280",
                line_width=1,
                annotation_text="초기자본 $37,000",
                annotation_position="bottom right",
                annotation_font_size=10,
                annotation_font_color="#6b7280"
            )
            
            # 레이아웃 설정
            fig.update_layout(
                plot_bgcolor='#1a1d23',
                paper_bgcolor='#1a1d23',
                height=400,
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(color='#9ca3af', size=12),
                    bgcolor='rgba(0,0,0,0)'
                ),
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='#2a2f38',
                    tickfont=dict(color='#6b7280', size=10),
                    linecolor='#2a2f38'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='#2a2f38',
                    tickfont=dict(color='#6b7280', size=10),
                    tickprefix='$',
                    tickformat=',.0f',
                    linecolor='#2a2f38'
                ),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # 최종 결과 비교 카드
            latest_sigma = metrics['final']
            latest_bh = metrics['bh_final']
            diff_value = latest_sigma - latest_bh
            diff_pct = metrics['total_return'] - metrics['bh_return']
            
            leg1, leg2, leg3 = st.columns(3)
            with leg1:
                sigma_color = "#22c55e" if metrics['total_return'] >= 0 else "#ef4444"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05)); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <div style="width: 16px; height: 4px; background: #3b82f6; border-radius: 2px;"></div>
                        <span style="color: #60a5fa; font-size: 12px; font-weight: 600;">σ 전략</span>
                    </div>
                    <p style="color: #fff; font-size: 22px; font-weight: 800; margin: 0;">${latest_sigma:,.0f}</p>
                    <p style="color: {sigma_color}; font-size: 13px; margin-top: 4px; font-weight: 600;">{metrics['total_return']:+.2f}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with leg2:
                bh_color = "#22c55e" if metrics['bh_return'] >= 0 else "#ef4444"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.15), rgba(249, 115, 22, 0.05)); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: 8px; padding: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <div style="width: 16px; height: 4px; background: #f97316; border-radius: 2px; border-style: dotted;"></div>
                        <span style="color: #fb923c; font-size: 12px; font-weight: 600;">Buy & Hold</span>
                    </div>
                    <p style="color: #fff; font-size: 22px; font-weight: 800; margin: 0;">${latest_bh:,.0f}</p>
                    <p style="color: {bh_color}; font-size: 13px; margin-top: 4px; font-weight: 600;">{metrics['bh_return']:+.2f}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with leg3:
                diff_color = "#22c55e" if diff_value >= 0 else "#ef4444"
                diff_icon = "▲" if diff_value >= 0 else "▼"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {'rgba(34, 197, 94, 0.15), rgba(34, 197, 94, 0.05)' if diff_value >= 0 else 'rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05)'}); border: 1px solid {'rgba(34, 197, 94, 0.3)' if diff_value >= 0 else 'rgba(239, 68, 68, 0.3)'}; border-radius: 8px; padding: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="color: {diff_color}; font-size: 14px;">{diff_icon}</span>
                        <span style="color: {diff_color}; font-size: 12px; font-weight: 600;">σ 전략 {'우위' if diff_value >= 0 else '열위'}</span>
                    </div>
                    <p style="color: {diff_color}; font-size: 22px; font-weight: 800; margin: 0;">${abs(diff_value):,.0f}</p>
                    <p style="color: {diff_color}; font-size: 13px; margin-top: 4px; font-weight: 600;">{diff_pct:+.2f}%p</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 상세 비교 테이블
            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
            st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">📋 상세 성과 비교</div>', unsafe_allow_html=True)
            
            # 비교 데이터프레임 생성
            comparison_data = {
                "지표": [
                    "초기 자본",
                    "최종 자산", 
                    "총 수익률",
                    "CAGR (연환산)",
                    "MDD (최대낙폭)",
                    "변동성 (연환산)",
                    "샤프 비율",
                    "승률 (양수일)",
                    "최고 일간 수익",
                    "최저 일간 수익"
                ],
                "σ 전략": [
                    f"${metrics['initial']:,.0f}",
                    f"${metrics['final']:,.0f}",
                    f"{metrics['total_return']:+.2f}%",
                    f"{metrics['cagr']:+.2f}%",
                    f"{metrics['mdd']:.2f}%",
                    f"{metrics['volatility']:.2f}%",
                    f"{metrics['sharpe']:.2f}",
                    f"{metrics['win_rate']:.1f}%",
                    f"{metrics['max_daily']:+.2f}%",
                    f"{metrics['min_daily']:+.2f}%"
                ],
                "Buy & Hold": [
                    f"${metrics['initial']:,.0f}",
                    f"${metrics['bh_final']:,.0f}",
                    f"{metrics['bh_return']:+.2f}%",
                    f"{metrics['bh_cagr']:+.2f}%",
                    f"{metrics['bh_mdd']:.2f}%",
                    f"{metrics['bh_volatility']:.2f}%",
                    f"{metrics['bh_sharpe']:.2f}",
                    f"{metrics['bh_win_rate']:.1f}%",
                    f"{metrics['bh_max_daily']:+.2f}%",
                    f"{metrics['bh_min_daily']:+.2f}%"
                ],
                "비교": [
                    "-",
                    f"${metrics['final'] - metrics['bh_final']:+,.0f}",
                    f"{metrics['total_return'] - metrics['bh_return']:+.2f}%p",
                    f"{metrics['cagr'] - metrics['bh_cagr']:+.2f}%p",
                    f"{metrics['mdd'] - metrics['bh_mdd']:+.2f}%p",
                    f"{metrics['volatility'] - metrics['bh_volatility']:+.2f}%p",
                    f"{metrics['sharpe'] - metrics['bh_sharpe']:+.2f}",
                    f"{metrics['win_rate'] - metrics['bh_win_rate']:+.1f}%p",
                    f"{metrics['max_daily'] - metrics['bh_max_daily']:+.2f}%p",
                    f"{metrics['min_daily'] - metrics['bh_min_daily']:+.2f}%p"
                ]
            }
            
            comparison_df = pd.DataFrame(comparison_data)
            
            # 스타일링된 데이터프레임 표시
            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "지표": st.column_config.TextColumn("지표", width="medium"),
                    "σ 전략": st.column_config.TextColumn("σ 전략", width="small"),
                    "Buy & Hold": st.column_config.TextColumn("Buy & Hold", width="small"),
                    "비교": st.column_config.TextColumn("차이 (σ-B&H)", width="small")
                }
            )
            
            # 전략 우위 분석
            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
            st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">🏆 전략 비교 요약</div>', unsafe_allow_html=True)
            
            # 어떤 전략이 우위인지 계산
            sigma_wins = 0
            bh_wins = 0
            
            comparisons = [
                ("수익률", metrics['total_return'], metrics['bh_return'], True),
                ("MDD", metrics['mdd'], metrics['bh_mdd'], False),  # 낮을수록 좋음
                ("샤프비율", metrics['sharpe'], metrics['bh_sharpe'], True),
                ("변동성", metrics['volatility'], metrics['bh_volatility'], False),  # 낮을수록 좋음
            ]
            
            for name, sigma_val, bh_val, higher_better in comparisons:
                if higher_better:
                    if sigma_val > bh_val:
                        sigma_wins += 1
                    elif bh_val > sigma_val:
                        bh_wins += 1
                else:
                    if sigma_val < bh_val:
                        sigma_wins += 1
                    elif bh_val < sigma_val:
                        bh_wins += 1
            
            winner = "σ 전략" if sigma_wins > bh_wins else "Buy & Hold" if bh_wins > sigma_wins else "무승부"
            winner_color = "#2563eb" if sigma_wins > bh_wins else "#f97316" if bh_wins > sigma_wins else "#6b7280"
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {winner_color}15, {winner_color}05); border: 1px solid {winner_color}40; border-radius: 12px; padding: 20px; text-align: center;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0 0 8px 0;">테스트 기간 우위 전략</p>
                <p style="color: {winner_color}; font-size: 28px; font-weight: 800; margin: 0;">{winner}</p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 8px;">σ 전략 {sigma_wins}승 vs Buy & Hold {bh_wins}승</p>
                <div style="display: flex; justify-content: center; gap: 20px; margin-top: 12px;">
                    <span style="color: #9ca3af; font-size: 11px;">수익률 / MDD / 샤프비율 / 변동성 기준</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.warning("📊 백테스팅을 위한 충분한 데이터가 없습니다. 잠시 후 다시 시도해주세요.")

# ==========================================
# TAB 3: 거래 기록
# ==========================================
with tab3:
    st.markdown('<div style="color: #9ca3af; font-size: 13px; font-weight: 600; margin-bottom: 12px;">📝 실전 거래 기록</div>', unsafe_allow_html=True)
    
    if st.session_state.trades:
        trades_df = pd.DataFrame(st.session_state.trades)
        trades_df.columns = ['날짜', '유형', '체결가', '수량', '회차']
        
        # 색상 스타일링
        def style_type(val):
            if val == 'BUY':
                return 'color: #22c55e'
            elif val == 'SELL':
                return 'color: #ef4444'
            return ''
        
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        
        # 실전 성과 요약
        buy_trades = [t for t in st.session_state.trades if t['type'] == 'BUY']
        sell_trades = [t for t in st.session_state.trades if t['type'] == 'SELL']
        
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div style="background: #252830; border-radius: 8px; padding: 16px; text-align: center;">
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 6px 0;">총 거래</p>
                <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">{len(st.session_state.trades)}회</p>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div style="background: #252830; border-radius: 8px; padding: 16px; text-align: center;">
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 6px 0;">매수</p>
                <p style="color: #22c55e; font-size: 20px; font-weight: 700; margin: 0;">{len(buy_trades)}회</p>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div style="background: #252830; border-radius: 8px; padding: 16px; text-align: center;">
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 6px 0;">매도</p>
                <p style="color: #ef4444; font-size: 20px; font-weight: 700; margin: 0;">{len(sell_trades)}회</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 기록 초기화 버튼
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("🗑️ 거래 기록 초기화", use_container_width=True, key="clear_trades"):
            st.session_state.trades = []
            save_data({
                "seed": st.session_state.seed,
                "qty": 0,
                "avg": 0.0,
                "step": 1,
                "trades": []
            })
            st.success("✅ 거래 기록이 초기화되었습니다")
            st.rerun()
    else:
        st.info("📝 아직 기록된 거래가 없습니다. '오늘의 주문' 탭에서 체결을 기록하세요.")

# ==========================================
# 푸터
# ==========================================
st.markdown("""
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #2a2f38; text-align: center;">
    <p style="color: #4b5563; font-size: 11px;">LSW LOC Pro v2.0 · 시그마 기반 LOC 자동매매 시스템</p>
    <p style="color: #374151; font-size: 10px; margin-top: 4px;">⚠️ 투자의 책임은 본인에게 있습니다</p>
</div>
""", unsafe_allow_html=True)
