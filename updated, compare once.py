import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import math

# --- SETTINGS & THEME ---
st.set_page_config(page_title="WealthMax India v70.0 - Enhanced", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: white; color: #1e1e1e; }
    .section-header { 
        background-color: #f8f9fa; padding: 12px; border-left: 6px solid #1e3c72; 
        font-weight: bold; margin-top: 25px; border-bottom: 1px solid #eee;
    }
    .report-title { color: #1e3c72; font-weight: 800; border-bottom: 2px solid #1e3c72; padding-bottom: 10px; }
    .math-box { background-color: #f1f8e9; padding: 20px; border-radius: 8px; border: 1px solid #c5e1a5; margin: 10px 0; font-family: monospace; }
    .tax-row { color: #d32f2f; font-weight: bold; }
    .recovery-tip { background-color: #fff3cd; padding: 15px; border-left: 5px solid #ffc107; margin-top: 10px; color: #856404; }
    .success-box { background-color: #d4edda; padding: 15px; border-left: 5px solid #28a745; margin-top: 10px; color: #155724; }
    .stress-box { background-color: #f8d7da; padding: 15px; border-radius: 8px; border: 1px solid #f5c6cb; margin: 10px 0; }
    .liquidity-high { color: #28a745; font-weight: bold; }
    .liquidity-medium { color: #ffc107; font-weight: bold; }
    .liquidity-low { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- LIVE MARKET DATA FUNCTION ---
@st.cache_data(ttl=3600)
def fetch_live_market_data():
    try:
        usd_inr_data = yf.download('INR=X', period='5d', progress=False)['Close']
        usd_inr = float(usd_inr_data.iloc[-1])
        nifty_data = yf.download('^NSEI', period='1y', progress=False)['Close']
        nifty_current = float(nifty_data.iloc[-1])
        nifty_sma200 = float(nifty_data.rolling(window=200).mean().iloc[-1])
        is_bullish = nifty_current > nifty_sma200
        gold_data = yf.download('GC=F', period='5d', progress=False)['Close']
        gold_usd_oz = float(gold_data.iloc[-1])
        gold_inr_gram = (gold_usd_oz / 31.1035) * usd_inr
        silver_data = yf.download('SI=F', period='5d', progress=False)['Close']
        silver_usd_oz = float(silver_data.iloc[-1])
        silver_inr_gram = (silver_usd_oz / 31.1035) * usd_inr
        return {'usd_inr': usd_inr, 'nifty': nifty_current, 'is_bullish': is_bullish, 'gold_gram': gold_inr_gram, 'silver_gram': silver_inr_gram}
    except Exception:
        return {'usd_inr': 90.66, 'nifty': 23000, 'is_bullish': True, 'gold_gram': 7200, 'silver_gram': 95}

# --- CALCULATION FUNCTIONS (STEP-UP READY) ---
def calculate_fv_step_up(rate, years, sip, lumpsum, step_up_pct):
    r = rate / 12
    total_fv_sip = 0
    current_sip = sip
    fv_lump = lumpsum * ((1 + r) ** (years * 12))
    for year in range(1, int(years) + 1):
        months_remaining = (years - year) * 12
        year_fv = 0
        for month in range(12):
            year_fv += current_sip * ((1 + r) ** (months_remaining + (12 - month - 1)))
        total_fv_sip += year_fv
        current_sip *= (1 + step_up_pct)
    # Handle fractional months if any
    fractional_months = (years - int(years)) * 12
    if fractional_months > 0:
        for m in range(int(fractional_months)):
            total_fv_sip += current_sip * ((1 + r) ** (int(fractional_months) - m - 1))
    return fv_lump + total_fv_sip

def calculate_required_sip_step_up(target, rate, years, lumpsum, step_up_pct):
    low = 0
    high = max(target / 12, 1000000)
    for _ in range(50):
        mid = (low + high) / 2
        fv = calculate_fv_step_up(rate, years, mid, lumpsum, step_up_pct)
        if fv < target: low = mid
        else: high = mid
    return high

def get_allocation_tactical(risk_type, is_bullish):
    # Strategic base weights
    allocs = {
        'Conservative': {'Equity Index': 15, 'Debt Funds': 45, 'Govt Bonds': 30, 'Gold': 10},
        'Balanced': {'Equity Flexi': 50, 'Debt Funds': 25, 'Corp Bonds': 15, 'Gold': 10},
        'Aggressive': {'Equity Mid/Small': 75, 'Intl Equity': 10, 'Debt/Cash': 10, 'Gold': 5}
    }
    base = allocs.get(risk_type, allocs['Balanced']).copy()
    if not is_bullish:
        equity_key = [k for k in base.keys() if 'Equity' in k][0]
        base[equity_key] -= 10
        base['Gold'] += 3
        debt_target = 'Debt Funds' if 'Debt Funds' in base else 'Govt Bonds'
        base[debt_target] += 7
    return base

# --- MAIN APP ---
market_data = fetch_live_market_data()
st.title("🏦 WealthMax India v70.0 - Enhanced Edition")
st.caption(f"AI-Powered Goal-Based Wealth Management | Step-Up SIP & Tactical Allocation Enabled")

# 1. LIVE MARKET DATA
st.markdown(f"### 📊 LIVE MARKET DATA ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
c1, c2, c3, c4 = st.columns(4)
c1.metric("USD/INR", f"₹{market_data['usd_inr']:.2f}")
c2.metric("Nifty 50", f"{market_data['nifty']:,.0f}", delta="BULLISH" if market_data['is_bullish'] else "BEARISH")
c3.metric("Gold (Intl)", f"₹{market_data['gold_gram']:,.0f}/g")
c4.metric("Silver (Intl)", f"₹{market_data['silver_gram']:,.0f}/g")
st.divider()

# 2. CLIENT INPUTS
st.header("📋 Step 1: Client Information")
col_a, col_b = st.columns(2)
with col_a:
    client_name = st.text_input("Client Name", placeholder="Enter name...")
    lumpsum = st.number_input("Initial Lumpsum (₹)", min_value=0, value=0)
    sip = st.number_input("Starting Monthly SIP (₹)", min_value=0, value=0)
    step_up_pct = st.slider("Annual SIP Step-Up (%)", 0, 25, 10) / 100
with col_b:
    risk_choices = {
        "Conservative (7.5% CAGR)": {'cagr': 0.075, 'type': 'Conservative'},
        "Balanced (9-10.5% CAGR)": {'cagr': 0.105 if market_data['is_bullish'] else 0.09, 'type': 'Balanced'},
        "Aggressive (11.5-14.5% CAGR)": {'cagr': 0.145 if market_data['is_bullish'] else 0.115, 'type': 'Aggressive'}
    }
    risk_choice = st.selectbox("Risk Profile", ["Select Profile..."] + list(risk_choices.keys()))

st.divider()

# 3. LIFE EVENTS
st.header("🎯 Step 2: Life Events Planning")
life_events_db = {
    "Child's Education": {'age': True, 'emg': False}, "Child's Marriage": {'age': True, 'emg': False},
    "Home Purchase": {'age': False, 'emg': False}, "Retirement Planning": {'age': False, 'emg': False},
    "Medical Emergency Fund": {'age': False, 'emg': True}
}
selected_events = st.multiselect("Select Goals", list(life_events_db.keys()))
goal_configs = []
for event in selected_events:
    with st.expander(f"⚙️ {event.upper()} CONFIG"):
        col1, col2, col3 = st.columns(3)
        with col1: amt = st.number_input("Target (₹)", key=f"a_{event}", min_value=0)
        if life_events_db[event]['emg']: yrs = 0
        elif life_events_db[event]['age']:
            with col2: c_age = st.number_input("Child Age", key=f"c_{event}", value=0)
            with col3: t_age = st.number_input("Target Age", key=f"t_{event}", value=18)
            yrs = max(1, t_age - c_age) if c_age > 0 else 0
        else:
            with col2: yrs = st.number_input("Years to Goal", key=f"y_{event}", value=0)
        if amt > 0: goal_configs.append({'name': event, 'amount': amt, 'years': yrs})

if st.button("🚀 GENERATE WEALTH PLAN", type="primary"):
    if not client_name or risk_choice == "Select Profile..." or not goal_configs:
        st.error("Missing Inputs!")
    else:
        goal_configs = sorted(goal_configs, key=lambda x: x['years'])
        config = risk_choices[risk_choice]; cagr = config['cagr']; risk_type = config['type']
        
        st.markdown(f"<h1 class='report-title'>📊 WEALTH REPORT: {client_name.upper()}</h1>", unsafe_allow_html=True)
        
        # SECTION 1: MARKET
        st.markdown('<div class="section-header">[SECTION 1: AI MARKET VALIDATION]</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Sentiment", "BULLISH" if market_data['is_bullish'] else "BEARISH")
        col2.metric("Tactical Shift", "OFFENSIVE" if market_data['is_bullish'] else "DEFENSIVE")
        col3.metric("Projected CAGR", f"{cagr*100:.1f}%")
        
        # SECTION 2: SEQUENTIAL GOALS
        st.markdown('<div class="section-header">[SECTION 2: STEP-UP GOAL ANALYSIS]</div>', unsafe_allow_html=True)
        curr_corpus = lumpsum; total_inv = lumpsum; run_sip = sip; last_yr = 0
        
        for goal in goal_configs:
            gap = goal['years'] - last_yr
            pre_tax = calculate_fv_step_up(cagr, gap, run_sip, curr_corpus, step_up_pct)
            
            # Tracking investment for tax
            inv_period = 0; temp_sip = run_sip
            for _ in range(int(gap)):
                inv_period += (temp_sip * 12)
                temp_sip *= (1 + step_up_pct)
            total_inv += inv_period
            
            tax = max(0, (pre_tax - total_inv) - 125000) * 0.125
            post_tax = pre_tax - tax
            target_inf = goal['amount'] * (1.06 ** goal['years'])
            
            st.markdown(f"### 🎯 {goal['name']} (Year {goal['years']})")
            st.markdown(f'<div class="math-box"><b>Wealth:</b> ₹{post_tax:,.0f}<br><b>Goal:</b> ₹{target_inf:,.0f}</div>', unsafe_allow_html=True)
            
            if post_tax < target_inf:
                req = calculate_required_sip_step_up(target_inf, cagr, goal['years'], lumpsum, step_up_pct)
                st.error(f"❌ Shortfall: ₹{target_inf - post_tax:,.0f}")
                st.info(f"💡 Starting SIP required: ₹{req:,.0f} (at {step_up_pct*100}% step-up)")
                curr_corpus = 0
            else:
                st.success(f"✅ Achieved! Surplus: ₹{post_tax - target_inf:,.0f}")
                curr_corpus = post_tax - target_inf
                total_inv = curr_corpus
            
            run_sip *= ((1 + step_up_pct) ** gap)
            last_yr = goal['years']
            st.divider()

        # SECTION 3: ALLOCATION
        st.markdown('<div class="section-header">[SECTION 3: TACTICAL ASSET ALLOCATION]</div>', unsafe_allow_html=True)
        alloc = get_allocation_tactical(risk_type, market_data['is_bullish'])
        df_alloc = pd.DataFrame([{'Asset': k, 'Weight %': v} for k, v in alloc.items()])
        st.dataframe(df_alloc, use_container_width=True, hide_index=True)
        fig = px.pie(df_alloc, values='Weight %', names='Asset', title=f"Tactical {risk_type} Split")
        st.plotly_chart(fig, use_container_width=True)
