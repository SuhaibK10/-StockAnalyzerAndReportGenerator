import streamlit as st
import yfinance as yf
import os
import requests
from dotenv import load_dotenv
import plotly.graph_objects as go
from yahooquery import search
import google.generativeai as genai



load_dotenv()
genai.configure(api_key=os.getenv("AIzaSyDDMxs-wB0h441GK94sKLUg7Hq0pIWzrDg"))
model = genai.GenerativeModel("gemini-1.5-pro")


#Stock Ticker on top
def render_stock_ticker():
    tickers = {
        "TECHM": (1484.10, "+0.59%"),
        "BHARTIARTL": (1924.10, "+0.47%"),
        "TATASTEEL": (158.55, "-0.66%"),
        "TATACONSUM": (1062.10, "-0.92%"),
        "SBIN": (800.15, "+0.57%"),
        "NESTLEIND": (2255.00, "-0.98%")
    }

    html = '<marquee style="font-size:16px; color:white; background-color:#000000; padding:10px;">'
    for symbol, (price, change) in tickers.items():
        color = 'green' if '-' not in change else 'red'
        arrow = '▲' if '-' not in change else '▼'
        html += f'<span style="margin-right: 20px;">{symbol} {price} <span style="color:{color};">{arrow} {change}</span></span>'
    html += '</marquee>'
    st.markdown(html, unsafe_allow_html=True)

# Fetch Stock Data
def fetch_stock_data(ticker, period="6mo", interval="1d"):
    stock = yf.Ticker(ticker)
    data = stock.history(period=period, interval=interval)
    data.reset_index(inplace=True)
    return data

def get_latest_price(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")['Close'].iloc[-1]
    return round(price, 2)

# Generate report and insight using Gemini
def generate_insight(ticker, data):
    prompt = f"""You are a financial analyst. Analyze the stock data below for {ticker}:

{data.tail(7).to_string()}

Give a plain-English summary of trends, volatility, support/resistance levels, and suggest a short insight."""
    response = model.generate_content(prompt)
    return response.text

# Search Company for ticker
def search_tickers(query):
    results = search(query)['quotes']
    suggestions = []
    for item in results:
        if 'symbol' in item and 'shortname' in item:
            ticker = item['symbol']
            name = item['shortname']
            if ticker.endswith(".NS") or ticker.isupper():
                suggestions.append(f"{ticker} – {name}")
    return suggestions

# Gainers and Losers
def get_yahoo_gainers_losers():
    headers = {"User-Agent": "Mozilla/5.0"}
    gainers_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_gainers&count=5"
    losers_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_losers&count=5"

    gainers_response = requests.get(gainers_url, headers=headers).json()
    losers_response = requests.get(losers_url, headers=headers).json()

    gainers_data = gainers_response['finance']['result'][0]['quotes']
    losers_data = losers_response['finance']['result'][0]['quotes']

    gainers = [{
        "symbol": g['symbol'],
        "shortName": g.get('shortName', 'N/A'),
        "price": g['regularMarketPrice'],
        "changePercent": g['regularMarketChangePercent']
    } for g in gainers_data]

    losers = [{
        "symbol": l['symbol'],
        "shortName": l.get('shortName', 'N/A'),
        "price": l['regularMarketPrice'],
        "changePercent": l['regularMarketChangePercent']
    } for l in losers_data]

    return gainers, losers

#Display Gainers and Losers
def show_top_movers():
    try:
        gainers, losers = get_yahoo_gainers_losers()
        st.subheader("📈 Top Gainers")
        cols = st.columns(len(gainers))
        for i, stock in enumerate(gainers):
            with cols[i]:
                st.metric(
                    label=f"**{stock['symbol']}**\n{stock['shortName']}",
                    value=f"${stock['price']}",
                    delta=f"+{round(stock['changePercent'], 2)}%",
                    delta_color="normal"
                )

        st.subheader("📉 Top Losers")
        cols = st.columns(len(losers))
        for i, stock in enumerate(losers):
            with cols[i]:
                st.metric(
                    label=f"**{stock['symbol']}**\n{stock['shortName']}",
                    value=f"${stock['price']}",
                    delta=f"{round(stock['changePercent'], 2)}%",
                    delta_color="inverse"
                )

    except Exception as e:
        st.warning("⚠️ Could not fetch live gainers/losers from Yahoo Finance.")
        print("Yahoo Screener Error:", e)

#Streamlit UI

st.set_page_config(page_title="📈 Stock Analyzer AI", layout="wide")
render_stock_ticker()

col1, col2 = st.columns([6, 1])
with col1:
    st.title("📊 Stock Analyzer AI")
with col2:
    st.markdown(
        "<div style='text-align:right; font-size:16px; margin-top:8px;'>"
        "By <b>Suhaib Khan</b>"
        "</div>",
        unsafe_allow_html=True
    )

show_top_movers()
st.markdown("---")

# Search Company
st.markdown("### 🔍 Search a Company")
company_query = st.text_input("Type company name (e.g., Reliance, Apple, Infosys)", "")
selected = None
if company_query:
    matches = search_tickers(company_query)
    if matches:
        selected = st.selectbox("Select a match", matches)
    else:
        st.warning("No matches found.")

# Analyze Button
if selected:
    ticker = selected.split("–")[0].strip()
    st.success(f"Selected Ticker: {ticker}")

    if st.button("Analyze"):
        with st.spinner("📦 Fetching data..."):
            data = fetch_stock_data(ticker)
            current_price = get_latest_price(ticker)
            currency_symbol = "₹" if ticker.endswith(".NS") else "$"
            st.subheader(f"📍 Current Price: {currency_symbol}{current_price}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], name='Close Price'))
            fig.update_layout(title="Price Trend", xaxis_title="Date", yaxis_title="Price")
            st.plotly_chart(fig, use_container_width=True)

        with st.spinner("🧠 Generating AI Report..."):
            report = generate_insight(ticker, data)
            st.markdown("### 🧠 AI-Generated Report")
            st.info(report)
