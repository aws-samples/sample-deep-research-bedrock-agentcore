"""Financial market data and analysis tools

Provides comprehensive financial market data, analysis, and news tools using yfinance.
Based on financial-market MCP server functionality.
"""

import json
import asyncio
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field


# Helper functions for formatting output
def format_number(num):
    """Format a number with commas and 2 decimal places"""
    if num is None:
        return 'N/A'
    try:
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return 'N/A'


def format_percent(num):
    """Format a number as a percentage with 2 decimal places"""
    if num is None:
        return 'N/A'
    try:
        return f"{num*100:.2f}%"
    except (ValueError, TypeError):
        return 'N/A'


def format_stock_quote(quote):
    """Format stock quote data for display"""
    result = f"""
Symbol: {quote['symbol']}
Name: {quote['shortName'] or 'N/A'}
Price: ${format_number(quote['regularMarketPrice'])}
Change: ${format_number(quote['regularMarketChange'])} ({format_percent(quote['regularMarketChangePercent'])})
Previous Close: ${format_number(quote['regularMarketPreviousClose'])}
Open: ${format_number(quote['regularMarketOpen'])}
Day Range: ${format_number(quote['regularMarketDayLow'])} - ${format_number(quote['regularMarketDayHigh'])}
52 Week Range: ${format_number(quote['fiftyTwoWeekLow'])} - ${format_number(quote['fiftyTwoWeekHigh'])}
Volume: {format_number(quote['regularMarketVolume'])}
Avg. Volume: {format_number(quote['averageDailyVolume3Month'])}
Market Cap: ${format_number(quote['marketCap'])}
P/E Ratio: {format_number(quote['trailingPE'])}
EPS: ${format_number(quote['epsTrailingTwelveMonths'])}
Dividend Yield: {format_percent(quote['dividendYield'])}
""".strip()
    return result


def parse_news_item(item):
    """Parse news item from yfinance"""
    try:
        content = item.get('content', item)

        provider_name = "Unknown"
        if 'provider' in content and isinstance(content['provider'], dict):
            provider_name = content['provider'].get('displayName', provider_name)

        pub_date = datetime.now().isoformat()
        if 'pubDate' in content:
            pub_date = content['pubDate']
        elif 'providerPublishTime' in content and content['providerPublishTime']:
            pub_date = datetime.fromtimestamp(content['providerPublishTime']).isoformat()

        link = ""
        if 'clickThroughUrl' in content and isinstance(content['clickThroughUrl'], dict):
            link = content['clickThroughUrl'].get('url', "")
        elif 'link' in content:
            link = content['link']
        elif 'url' in content:
            link = content['url']

        summary = ""
        for field in ['summary', 'description', 'shortDescription', 'longDescription', 'snippetText']:
            if field in content and content[field]:
                summary = content[field]
                break

        return {
            "title": content.get("title", "No title available"),
            "publisher": provider_name,
            "link": link,
            "published_date": pub_date,
            "summary": summary
        }
    except Exception as e:
        return None


def format_analysis_results(data, indent=0):
    """Format complex JSON data into readable text"""
    if data is None:
        return "N/A"

    if isinstance(data, dict):
        result = ""
        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()

            if isinstance(value, dict) or isinstance(value, list):
                result += f"{' ' * indent}{formatted_key}:\n{format_analysis_results(value, indent + 2)}\n"
            else:
                if isinstance(value, float):
                    if abs(value) < 0.01:
                        formatted_value = f"{value:.2e}"
                    else:
                        formatted_value = f"{value:.2f}"

                    if "percent" in key.lower() or "growth" in key.lower() or "margin" in key.lower():
                        formatted_value += "%"
                elif isinstance(value, int) and value > 1000:
                    formatted_value = f"{value:,}"
                else:
                    formatted_value = str(value)

                result += f"{' ' * indent}{formatted_key}: {formatted_value}\n"
        return result

    elif isinstance(data, list):
        result = ""
        for i, item in enumerate(data):
            result += f"{' ' * indent}{i+1}. {format_analysis_results(item, indent + 2)}\n"
        return result

    else:
        return str(data)


# Helper functions for analysis interpretation
def interpret_rsi(rsi: float) -> str:
    if rsi >= 70:
        return "Overbought"
    elif rsi <= 30:
        return "Oversold"
    else:
        return "Neutral"


def interpret_macd(macd: float, signal: float) -> str:
    if macd > signal:
        return "Bullish"
    elif macd < signal:
        return "Bearish"
    else:
        return "Neutral"


def interpret_ma_trend(ma_distances: dict) -> str:
    if ma_distances["from_200sma"] > 0 and ma_distances["from_50sma"] > 0:
        return "Uptrend"
    elif ma_distances["from_200sma"] < 0 and ma_distances["from_50sma"] < 0:
        return "Downtrend"
    else:
        return "Mixed"


def interpret_relative_strength(stock_change: float, sp500_change: float) -> str:
    if stock_change > sp500_change:
        return "Outperforming market"
    elif stock_change < sp500_change:
        return "Underperforming market"
    else:
        return "Market performer"


async def fetch_fundamental_analysis(equity):
    """Fetch comprehensive fundamental analysis data"""
    try:
        ticker = yf.Ticker(equity)
        info = ticker.info
        if not info:
            raise ValueError(f"No fundamental data available for {equity}")

        return {
            "company_info": {
                "longName": info.get("longName"),
                "shortName": info.get("shortName"),
                "industry": info.get("industry"),
                "sector": info.get("sector"),
                "country": info.get("country"),
                "website": info.get("website"),
                "fullTimeEmployees": info.get("fullTimeEmployees"),
                "longBusinessSummary": info.get("longBusinessSummary")
            },
            "valuation_metrics": {
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "priceToBook": info.get("priceToBook"),
                "priceToSalesTrailing12Months": info.get("priceToSalesTrailing12Months"),
                "enterpriseValue": info.get("enterpriseValue"),
                "enterpriseToEbitda": info.get("enterpriseToEbitda"),
                "enterpriseToRevenue": info.get("enterpriseToRevenue"),
                "bookValue": info.get("bookValue")
            },
            "earnings_and_revenue": {
                "totalRevenue": info.get("totalRevenue"),
                "revenueGrowth": info.get("revenueGrowth"),
                "revenuePerShare": info.get("revenuePerShare"),
                "ebitda": info.get("ebitda"),
                "ebitdaMargins": info.get("ebitdaMargins"),
                "netIncomeToCommon": info.get("netIncomeToCommon"),
                "earningsGrowth": info.get("earningsGrowth"),
                "earningsQuarterlyGrowth": info.get("earningsQuarterlyGrowth"),
                "forwardEps": info.get("forwardEps"),
                "trailingEps": info.get("trailingEps")
            },
            "margins_and_returns": {
                "profitMargins": info.get("profitMargins"),
                "operatingMargins": info.get("operatingMargins"),
                "grossMargins": info.get("grossMargins"),
                "returnOnEquity": info.get("returnOnEquity"),
                "returnOnAssets": info.get("returnOnAssets")
            },
            "dividends": {
                "dividendYield": info.get("dividendYield"),
                "dividendRate": info.get("dividendRate"),
                "payoutRatio": info.get("payoutRatio"),
                "fiveYearAvgDividendYield": info.get("fiveYearAvgDividendYield")
            },
            "balance_sheet": {
                "totalCash": info.get("totalCash"),
                "totalDebt": info.get("totalDebt"),
                "debtToEquity": info.get("debtToEquity"),
                "currentRatio": info.get("currentRatio"),
                "quickRatio": info.get("quickRatio")
            },
            "ownership": {
                "heldPercentInstitutions": info.get("heldPercentInstitutions"),
                "heldPercentInsiders": info.get("heldPercentInsiders"),
                "floatShares": info.get("floatShares"),
                "sharesOutstanding": info.get("sharesOutstanding"),
                "shortRatio": info.get("shortRatio")
            },
            "analyst_opinions": {
                "recommendationKey": info.get("recommendationKey"),
                "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
                "targetMeanPrice": info.get("targetMeanPrice"),
                "targetHighPrice": info.get("targetHighPrice"),
                "targetLowPrice": info.get("targetLowPrice")
            },
            "risk_metrics": {
                "beta": info.get("beta"),
                "52WeekChange": info.get("52WeekChange"),
                "SandP52WeekChange": info.get("SandP52WeekChange")
            }
        }
    except Exception as e:
        raise Exception(f"Fundamental analysis failed: {str(e)}")


async def fetch_technical_analysis(equity):
    """Fetch technical analysis data"""
    try:
        ticker = yf.Ticker(equity)
        hist = ticker.history(period="1y")
        if hist.empty:
            raise ValueError(f"No historical data available for {equity}")

        current_price = hist["Close"].iloc[-1]
        avg_volume = hist["Volume"].mean()

        sma_20 = hist["Close"].rolling(window=20).mean().iloc[-1]
        sma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
        sma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]

        delta = hist["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        high_low = hist["High"] - hist["Low"]
        high_close = (hist["High"] - hist["Close"].shift()).abs()
        low_close = (hist["Low"] - hist["Close"].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=14).mean().iloc[-1]

        ema12 = hist["Close"].ewm(span=12, adjust=False).mean()
        ema26 = hist["Close"].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = macd - signal_line

        price_changes = {
            "1d": hist["Close"].pct_change(periods=1).iloc[-1] * 100,
            "5d": hist["Close"].pct_change(periods=5).iloc[-1] * 100,
            "20d": hist["Close"].pct_change(periods=20).iloc[-1] * 100
        }

        ma_distances = {
            "from_20sma": ((current_price / sma_20) - 1) * 100,
            "from_50sma": ((current_price / sma_50) - 1) * 100,
            "from_200sma": ((current_price / sma_200) - 1) * 100
        }

        return {
            "price": current_price,
            "avg_volume": avg_volume,
            "moving_averages": {
                "sma_20": sma_20,
                "sma_50": sma_50,
                "sma_200": sma_200
            },
            "indicators": {
                "rsi": rsi,
                "atr": atr,
                "atr_percent": (atr / current_price) * 100,
                "macd": macd.iloc[-1],
                "macd_signal": signal_line.iloc[-1],
                "macd_histogram": macd_histogram.iloc[-1]
            },
            "trend_analysis": price_changes,
            "ma_distances": ma_distances
        }
    except Exception as e:
        raise Exception(f"Technical analysis failed: {str(e)}")


async def fetch_comprehensive_analysis(equity):
    """Fetch comprehensive investment analysis"""
    try:
        fundamental_data = await fetch_fundamental_analysis(equity)
        technical_data = await fetch_technical_analysis(equity)

        current_price = technical_data["price"]
        target_price = fundamental_data["analyst_opinions"]["targetMeanPrice"]

        upside_potential = ((target_price / current_price) - 1) * 100 if target_price else None

        return {
            "core_valuation": {
                "current_price": current_price,
                "pe_ratio": {
                    "trailing": fundamental_data["valuation_metrics"]["trailingPE"],
                    "forward": fundamental_data["valuation_metrics"]["forwardPE"],
                },
                "price_to_book": fundamental_data["valuation_metrics"]["priceToBook"],
                "enterprise_to_ebitda": fundamental_data["valuation_metrics"]["enterpriseToEbitda"]
            },
            "growth_metrics": {
                "revenue_growth": fundamental_data["earnings_and_revenue"]["revenueGrowth"],
                "earnings_growth": fundamental_data["earnings_and_revenue"]["earningsGrowth"],
                "profit_margin": fundamental_data["margins_and_returns"]["profitMargins"],
                "return_on_equity": fundamental_data["margins_and_returns"]["returnOnEquity"]
            },
            "financial_health": {
                "debt_to_equity": fundamental_data["balance_sheet"]["debtToEquity"],
                "current_ratio": fundamental_data["balance_sheet"]["currentRatio"],
                "quick_ratio": fundamental_data["balance_sheet"]["quickRatio"],
                "beta": fundamental_data["risk_metrics"]["beta"]
            },
            "market_sentiment": {
                "analyst_recommendation": fundamental_data["analyst_opinions"]["recommendationKey"],
                "target_price": {
                    "mean": target_price,
                    "current": current_price,
                    "upside_potential": upside_potential
                },
                "institutional_holdings": fundamental_data["ownership"]["heldPercentInstitutions"],
                "insider_holdings": fundamental_data["ownership"]["heldPercentInsiders"]
            },
            "technical_signals": {
                "rsi": {
                    "value": technical_data["indicators"]["rsi"],
                    "signal": interpret_rsi(technical_data["indicators"]["rsi"])
                },
                "macd": {
                    "value": technical_data["indicators"]["macd"],
                    "signal": technical_data["indicators"]["macd_signal"],
                    "histogram": technical_data["indicators"]["macd_histogram"],
                    "trend": interpret_macd(
                        technical_data["indicators"]["macd"],
                        technical_data["indicators"]["macd_signal"]
                    )
                },
                "moving_averages": {
                    "sma_50": technical_data["moving_averages"]["sma_50"],
                    "sma_200": technical_data["moving_averages"]["sma_200"],
                    "price_vs_sma200": technical_data["ma_distances"]["from_200sma"],
                    "trend": interpret_ma_trend(technical_data["ma_distances"])
                }
            },
            "momentum": {
                "short_term": technical_data["trend_analysis"]["20d"],
                "year_to_date": fundamental_data["risk_metrics"]["52WeekChange"],
                "relative_strength": {
                    "vs_sp500": fundamental_data["risk_metrics"]["SandP52WeekChange"],
                    "interpretation": interpret_relative_strength(
                        fundamental_data["risk_metrics"]["52WeekChange"] or 0,
                        fundamental_data["risk_metrics"]["SandP52WeekChange"] or 0
                    )
                }
            }
        }
    except Exception as e:
        raise Exception(f"Comprehensive analysis failed: {str(e)}")


# Tool definitions using @tool decorator
@tool
def stock_quote(symbol: str) -> str:
    """Get real-time stock quote information for a given ticker symbol.

    Provides current price, daily change, volume, market cap, P/E ratio, dividend yield, and 52-week range.
    Useful for quick snapshot of a stock's current market status and valuation metrics.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)

    Returns:
        Formatted stock quote with current price, change, volume, and key financial metrics
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info:
            return f"No data found for symbol: {symbol}"

        quote_data = {
            "symbol": symbol,
            "shortName": info.get("shortName") or info.get("longName") or symbol,
            "regularMarketPrice": info.get("regularMarketPrice"),
            "regularMarketChange": info.get("regularMarketChange"),
            "regularMarketChangePercent": info.get("regularMarketChangePercent"),
            "regularMarketPreviousClose": info.get("regularMarketPreviousClose"),
            "regularMarketOpen": info.get("regularMarketOpen"),
            "regularMarketDayLow": info.get("regularMarketDayLow"),
            "regularMarketDayHigh": info.get("regularMarketDayHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "regularMarketVolume": info.get("regularMarketVolume"),
            "averageDailyVolume3Month": info.get("averageDailyVolume3Month"),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "epsTrailingTwelveMonths": info.get("epsTrailingTwelveMonths"),
            "dividendYield": info.get("dividendYield")
        }

        return format_stock_quote(quote_data)
    except Exception as e:
        return f"Error retrieving stock quote: {str(e)}"


@tool
def stock_history(symbol: str, period: str = "1mo", interval: str = "1d") -> str:
    """Get historical stock price and volume data over a specified time period.

    Provides OHLCV (Open, High, Low, Close, Volume) data formatted as a table for trend analysis.
    Essential for analyzing price patterns, volatility, and trading volume trends over time.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)
        period: Time period - 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max (default: 1mo)
        interval: Data interval - 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo (default: 1d)

    Returns:
        Historical price data with date, open, high, low, close, and volume
    """
    try:
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']

        if period not in valid_periods:
            return f"Invalid period: {period}. Valid periods are: {', '.join(valid_periods)}"

        if interval not in valid_intervals:
            return f"Invalid interval: {interval}. Valid intervals are: {', '.join(valid_intervals)}"

        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval)

        if history.empty:
            return f"No historical data found for symbol: {symbol}"

        result = f"Historical data for {symbol} ({period}, {interval} intervals)\n"
        result += f"Currency: {ticker.info.get('currency', 'USD')}\n\n"

        result += "Date       | Open     | High     | Low      | Close    | Volume\n"
        result += "-----------|----------|----------|----------|----------|-----------\n"

        max_points = 10
        step = max(1, len(history) // max_points)

        for i in range(0, len(history), step):
            date = history.index[i].strftime('%Y-%m-%d')

            open_price = history['Open'].iloc[i] if 'Open' in history.columns else None
            high = history['High'].iloc[i] if 'High' in history.columns else None
            low = history['Low'].iloc[i] if 'Low' in history.columns else None
            close = history['Close'].iloc[i] if 'Close' in history.columns else None
            volume = history['Volume'].iloc[i] if 'Volume' in history.columns else None

            open_str = f"${open_price:.2f}" if open_price is not None else 'N/A'
            high_str = f"${high:.2f}" if high is not None else 'N/A'
            low_str = f"${low:.2f}" if low is not None else 'N/A'
            close_str = f"${close:.2f}" if close is not None else 'N/A'
            volume_str = f"{volume:,}" if volume is not None else 'N/A'

            result += f"{date.ljust(11)} | {open_str.ljust(8)} | {high_str.ljust(8)} | {low_str.ljust(8)} | {close_str.ljust(8)} | {volume_str}\n"

        if not history.empty and 'Close' in history.columns:
            first_close = history['Close'].iloc[0]
            last_close = history['Close'].iloc[-1]

            change = last_close - first_close
            percent_change = (change / first_close) * 100 if first_close else 0

            result += f"\nPrice Change: ${change:.2f} ({percent_change:.2f}%)"

        return result
    except Exception as e:
        return f"Error retrieving stock history: {str(e)}"


@tool
def financial_news(symbol: str, count: int = 5) -> str:
    """Get the latest financial news articles specifically related to a stock symbol.

    Retrieves recent news from financial publishers covering company announcements, earnings, analyst reports, and market-moving events.
    Excellent for understanding recent developments and market sentiment around a specific stock.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)
        count: Number of news articles to return, 1-20 (default: 5)

    Returns:
        Latest news articles with title, publisher, publication date, summary, and link
    """
    try:
        if not symbol or len(symbol.strip()) == 0:
            return "Please provide a valid stock ticker symbol."

        symbol = symbol.strip().upper()
        count = min(max(count, 1), 20)

        ticker = yf.Ticker(symbol)
        news_data = ticker.news

        if not news_data:
            return f"No recent news found for {symbol}."

        formatted_news = []
        news_count = min(count, len(news_data))

        for item in news_data[:news_count]:
            parsed_item = parse_news_item(item)
            if parsed_item:
                formatted_news.append(parsed_item)

        if not formatted_news:
            return f"No news articles could be processed for {symbol}."

        result = f"Latest news for {symbol} ({len(formatted_news)} articles):\n\n"
        for i, item in enumerate(formatted_news, 1):
            result += f"{i}. {item['title']}\n"
            result += f"   Publisher: {item['publisher']}\n"
            result += f"   Date: {item['published_date']}\n"
            if item['summary']:
                result += f"   Summary: {item['summary']}\n"
            if item['link']:
                result += f"   Link: {item['link']}\n"
            result += "\n"

        return result

    except Exception as e:
        return f"Error retrieving financial news: {str(e)}"


@tool
def comprehensive_stock_analysis(symbol: str) -> str:
    """Get a complete multi-faceted investment analysis combining fundamental and technical factors.

    Performs deep analysis covering: valuation metrics (P/E, P/B, EPS growth), financial health (profit margins, ROE, debt ratios),
    technical indicators (RSI, MACD, moving averages), market sentiment, and relative market performance.
    Provides interpreted signals (bullish/bearish/neutral) and actionable investment indicators. Use this for thorough due diligence.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)

    Returns:
        Comprehensive analysis with company info, valuation metrics, financial health, technical signals, and interpreted investment indicators
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = loop.run_until_complete(fetch_comprehensive_analysis(symbol))
            return format_analysis_results(data)
        finally:
            loop.close()
    except Exception as e:
        return f"Error retrieving comprehensive analysis: {str(e)}"


# Create tool instances for export
finance_stock_quote = stock_quote
finance_stock_history = stock_history
finance_news = financial_news
finance_comprehensive_analysis = comprehensive_stock_analysis
