import os
import urllib.request
import urllib.parse
import json
import getpass

def test_telegram():
    print("🧠 DR. PRIME — Telegram Notification Tester")
    print("==========================================")
    
    # Try to get from environment first
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        bot_token = getpass.getpass("Enter your Telegram Bot Token (from @BotFather): ")
    else:
        print("✅ Found TELEGRAM_BOT_TOKEN in environment.")
        
    if not chat_id:
        chat_id = input("Enter your Telegram Chat ID: ")
    else:
        print("✅ Found TELEGRAM_CHAT_ID in environment.")
        
    message = "🧠 *DR. PRIME · SYSTEM TEST*\n\nIf you are reading this, your Telegram notification integration is working perfectly. The neural link is stable."
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    print("\nSending test notification...")
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("ok"):
                print("✅ SUCCESS! Check your Telegram app.")
            else:
                print(f"❌ API returned an error: {result}")
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")

if __name__ == "__main__":
    test_telegram()
