import os
import sys
import logging
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from anthropic import Anthropic

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

sys.path.append("/Users/diegocordoba/diegocordoba/dashboard")
try:
    from dashboard_eureka import load_market_data
except ImportError:
    logging.error("Could not import load_market_data from dashboard_eureka.py")
    load_market_data = None

TELEGRAM_BOT_TOKEN = os.environ.get("EUREKA_TELEGRAM_BOT_TOKEN")
if TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN.strip()

TELEGRAM_CHAT_ID = os.environ.get("PRIME_TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if ANTHROPIC_API_KEY:
    ANTHROPIC_API_KEY = ANTHROPIC_API_KEY.strip()

if not TELEGRAM_BOT_TOKEN:
    logging.warning("Missing EUREKA_TELEGRAM_BOT_TOKEN environment variable.")
if not ANTHROPIC_API_KEY:
    logging.warning("Missing ANTHROPIC_API_KEY environment variable.")

if ANTHROPIC_API_KEY:
    ai_client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    ai_client = None

def generate_system_prompt():
    prompt = """You are Eureka, an autonomous sovereign wealth management AI for Diego Cordoba.
You must adopt a highly confident, analytical, and concise tone similar to 'Dr. Prime'.
You use live data provided to you to answer questions about the portfolio.
Never hallucinate stats. Use only the context provided.
Do not use emojis excessively. Keep it professional, cold, and calculated."""
    return [{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}]

def get_live_context():
    if not load_market_data:
        return "System error: dashboard script not found."
    try:
        data = load_market_data()
        tickers = data["ticker_signals"]
        vix = data["vix_label"]
        
        context_str = f"Live Market Context (VIX: {vix}):\n"
        avg_conv = 0
        for tk, sig in tickers.items():
            if tk in data['prices']:
                price = float(data['prices'][tk].dropna().iloc[-1])
            else:
                price = 0.0
            context_str += f"- {tk}: Price=${price:.2f}, "
            context_str += f"Signal={sig['signal']}, Conviction={sig['conviction']}/100, Distance: {sig['dist_to_trigger']}\n"
            avg_conv += sig['conviction']
        
        if len(tickers) > 0:
            avg_conv //= len(tickers)
            
        context_str += f"Overall Eureka Conviction: {avg_conv}/100\n"
        return context_str
    except Exception as e:
        return f"Error loading market data: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Eureka Sovereign Node initialized. How can I assist you today?")

chat_history = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text
    live_data = get_live_context()
    
    if not ai_client:
        await context.bot.send_message(chat_id=chat_id, text="Error: ANTHROPIC_API_KEY is not configured.")
        return

    if chat_id not in chat_history:
        chat_history[chat_id] = []
    messages = chat_history[chat_id]

    # Strip old cache_control
    for msg in messages:
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict) and "cache_control" in block:
                    del block["cache_control"]

    prompt = f"User says: {user_message}\n\nHere is the latest data:\n{live_data}"
    new_user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ]
    }
    messages.append(new_user_message)
    
    if len(messages) > 20:
        messages = messages[-20:]
        chat_history[chat_id] = messages
    
    try:
        response = ai_client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            system=generate_system_prompt(),
            messages=messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        reply = response.content[0].text
        messages.append({"role": "assistant", "content": reply})
        await context.bot.send_message(chat_id=chat_id, text=reply)
    except Exception as e:
        logging.error(f"Anthropic exception: {e}")
        if len(messages) > 0 and messages[-1]["role"] == "user":
            messages.pop()
        await context.bot.send_message(chat_id=chat_id, text=f"Error generating AI response: {e}")

async def morning_briefing(context: ContextTypes.DEFAULT_TYPE):
    if not TELEGRAM_CHAT_ID:
        logging.warning("No chat_id set for morning briefing.")
        return
        
    try:
        data = load_market_data()
        vix = data["vix_label"]
        tickers = data["ticker_signals"]
        
        # Determine if it's "quiet"
        any_signals = any(sig["signal"] != "HOLD" for sig in tickers.values())
        
        if not any_signals:
            # Format explicit quiet message
            dist_texts = []
            for tk, sig in tickers.items():
                if "SNDK" in tk or "SNXX" in tk:
                    dist_texts.append(f"{tk} {sig['dist_to_trigger'].lower()}")
            
            dist_str = ", ".join(dist_texts)
            
            text = f"🛡️ **Eureka Morning Briefing**\n\nNo signal today because: VIX={vix}, MOM_TP already fired, {dist_str}."
        else:
            text = f"🚨 **Eureka Morning Briefing**\n\nSignals are active! VIX is {vix}.\n"
            for tk, sig in tickers.items():
                if sig["signal"] != "HOLD":
                    text += f"- {tk}: {sig['signal']} (Conviction: {sig['conviction']}/100)\n"

        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown")
        logging.info("Sent morning briefing.")
    except Exception as e:
        logging.error(f"Failed to send morning briefing: {e}")

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("Set EUREKA_TELEGRAM_BOT_TOKEN to run the bot.")
        sys.exit(1)

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connection_pool_size=8, pool_timeout=60.0)
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(request).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    import datetime
    # Run at 9:00 AM every day
    target_time = datetime.time(hour=9, minute=0, second=0)
    application.job_queue.run_daily(morning_briefing, time=target_time, days=(1, 2, 3, 4, 5))
    
    logging.info("Starting Eureka Telegram Bot polling...")
    application.run_polling()
