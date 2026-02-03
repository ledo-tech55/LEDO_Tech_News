import feedparser
import requests
import time
import os
import re 
from datetime import datetime, timedelta
# NEW: Import dotenv to manage secrets safely
from dotenv import load_dotenv 

# ==========================================
# CONFIGURATION
# ==========================================
# 1. Load secrets from local .env file (if running on laptop)
load_dotenv()

# 2. Get the keys securely. 
# If running on GitHub, it gets them from "Secrets".
# If running locally, it gets them from the .env file.
BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHAT_ID = os.getenv("CHAT_ID")

# Safety Check: Stop immediately if keys are missing
if not BOT_TOKEN or not CHAT_ID:
    print("⚠️ ERROR: Security credentials not found!")
    print("-> If running locally: Create a .env file with BOT_TOKEN and CHAT_ID.")
    print("-> If running on GitHub: Check your Settings -> Secrets.")
    exit(1)

# ==========================================
# VERIFIED & OFFICIAL NEWS SOURCES
# ==========================================
FEEDS = {
    "🔐 Security (BleepingComputer)": "https://www.bleepingcomputer.com/feed/",
    "🏢 Google Official": "https://blog.google/rss/",
    "🪟 Microsoft Official": "https://blogs.microsoft.com/feed/",
    "⚡ The Verge (Top Tech)": "https://www.theverge.com/rss/index.xml",
    "📱 Mobile (GSMArena)": "https://www.gsmarena.com/rss-news-reviews.php3",
    "🧠 AI News": "https://www.artificialintelligence-news.com/feed/",
    "📈 TechCrunch (Business)": "https://techcrunch.com/feed/",
    "🔌 Wired (Culture & Tech)": "https://www.wired.com/feed/rss",
    "👨‍💻 Coding (Google Devs)": "https://developers.googleblog.com/feeds/posts/default",
}

KEYWORDS = [
    "hack", "breach", "leak", "password", "malware", "alert",
    "gmail", "meta", "facebook", "instagram", "tiktok", "whatsapp",
    "apple", "ios", "iphone", "samsung", "galaxy", "android",
    "ai agent", "gpt", "gemini", "openai", "automation", "robot",
    "gta", "playstation", "ps5", "xbox", "nintendo",
    "c#", ".net", "visual studio", "python", "api", "update" ,"vulnerability", "zero-day", "exploit", "ransomware", "ddos", "cyberattack", "data breach", "phishing", "cybersecurity", "infosec",
]

def clean_summary(html_text):
    """
    Cleans the RSS summary:
    1. Removes HTML tags (like <div>, <br>, <a>).
    2. Truncates it to 400 characters.
    """
    if not html_text:
        return "No summary available."
    
    # Remove HTML tags using Regex
    clean_text = re.sub('<[^<]+?>', '', html_text)
    
    # Fix weird whitespace
    clean_text = " ".join(clean_text.split())
    
    # Shorten it
    if len(clean_text) > 400:
        return clean_text[:400] + "..."
    return clean_text

def get_last_message_id():
    """Gets the ID of the last message sent to the bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url).json()
        if "result" in response and len(response["result"]) > 0:
            return response["result"][-1]["update_id"]
    except:
        pass
    return None

def check_for_commands(last_update_id):
    """Checks if you sent /start to the bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 5}
    try:
        response = requests.get(url, params=params).json()
        if "result" in response:
            for update in response["result"]:
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"]
                    if text.strip().lower() == "/start":
                        return True, update["update_id"]
                return False, update["update_id"]
    except Exception as e:
        print(f"Connection Error: {e}")
    return False, last_update_id

def send_telegram_alert(category, title, link, summary):
    message = (
        f"🚨 <b>LEDO TECH NEWS ALERT</b> 🚨\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📂 <b>Source:</b> {category}\n"
        f"📰 <b>Topic:</b> {title}\n\n"
        f"📝 <b>Summary:</b>\n<i>{summary}</i>\n\n"
        f"🔗 <a href='{link}'>Click to Read Full Report</a>"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error: {e}")

def check_news(time_window_minutes):
    """Checks RSS feeds for news in the last X minutes"""
    print(f"🔎 Scanning news from last {time_window_minutes} minutes...")
    check_limit = datetime.now() - timedelta(minutes=time_window_minutes)
    found_any = False
    
    for category, rss_url in FEEDS.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    article_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    
                    # ONLY send if the article is newer than our check limit
                    # This prevents sending the same old content
                    if article_time > check_limit:
                        
                        # Check keywords
                        if any(word in entry.title.lower() for word in KEYWORDS):
                            
                            # Get Description/Summary
                            raw_summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
                            clean_desc = clean_summary(raw_summary)
                            
                            send_telegram_alert(category, entry.title, entry.link, clean_desc)
                            print(f" -> SENT: {entry.title}")
                            found_any = True
                            time.sleep(1)
        except Exception as e:
            print(f"Error {category}: {e}")
    
    if not found_any:
        print("✅ Scan complete. No matches found.")
    else:
        print("✅ Scan complete. Alerts sent.")

def run_hybrid_bot():
    # 1. GITHUB MODE (Runs once, fast)
    # The 'GITHUB_ACTIONS' variable is automatically set by GitHub.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print("--- RUNNING IN GITHUB CLOUD MODE ---")
        check_news(time_window_minutes=45)
        return

    # 2. LOCAL LAPTOP MODE (Runs forever, listens for /start)
    print("--- RUNNING IN LOCAL HYBRID MODE ---")
    print("1. Checking last 24 hours of news immediately...")
    check_news(time_window_minutes=1440) 
    
    print("2. Listening for /start command & Auto-checking every 30 mins...")
    last_update_id = get_last_message_id() or 0
    last_auto_check = time.time()
    
    while True:
        # A. Check for /start command
        triggered, new_id = check_for_commands(last_update_id)
        if new_id:
            last_update_id = new_id
        
        if triggered:
            print("🚀 Command /start received! Checking news manually...")
            send_telegram_alert("SYSTEM", "Manual Check Started...", "https://ledo.tech", "Checking trusted sources now...")
            check_news(time_window_minutes=1440) # Check last 24h
        
        # B. Automatic Timer (Every 30 mins)
        if time.time() - last_auto_check > 1800: # 1800 seconds = 30 mins
            print("⏰ Auto-timer triggered.")
            check_news(time_window_minutes=30)
            last_auto_check = time.time()
            
        time.sleep(2) 

if __name__ == "__main__":
    run_hybrid_bot()