"""Telegram job notification formatting and delivery."""
import json
import os
import logging
import random
import re
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

# Telegram configuration
BOT_API = os.environ.get(
    "TELEGRAM_BOT_API",
    "",
).strip()
CHAT_IDS = [
    chat_id.strip()
    for chat_id in os.environ.get("TELEGRAM_CHAT_ID", "").split(",")
    if chat_id.strip()
]
FILTERED_JOBS_FILE = Path("filtered_jobs.json")
TELEGRAM_MESSAGE_LIMIT = 4096

# Keep the original Hephaestus quote pool, choosing one closing line per report.
FORGE_QUOTES = [
    "Right smart of you!",
    "Got a discerning eye.",
    "Good selection, that.",
    "What a bargain.",
    "Let's get to work!",
    "Cheers!",
    "That I can do.",
    "Done and done.",
    "No problem!",
    "Simple.",
    "Can do.",
    "Here you go!",
    "Suit yourself, witchie!",
    "Made to order!",
    "Just what you wanted, right?",
    "Soon as I'm through, you go knock some sense into some wretches for me, would you?",
    "You got a dangerous line of work, witchie. Though I can get you some protection here.",
    "Don't sweat it, you'll be as good as new here in a bit.",
    (
        "Can't guarantee a weapon worthy of the gods is going to be enough for you to "
        "see this through. But I can guarantee you're getting the very best."
    ),
]


def random_hephaestus_quote() -> str:
    quote = html_escape(random.choice(FORGE_QUOTES))
    return f'\n\n🔥 <i>Hephaestus: “{quote}”</i>'


def normalize_bot_token(value: str) -> str:
    if "/bot" not in value:
        return value

    match = re.search(r"/bot([^/]+)/", value)
    return match.group(1) if match else value


def telegram_request(bot_token: str, method: str, payload: dict = None) -> dict:
    bot_token = normalize_bot_token(bot_token)
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    data = None
    headers = {}

    if payload is not None:
        data = urlencode(payload).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = Request(url, data=data, headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def send_telegram_markdown_message(message: str) -> None:
    """Send a message to Telegram using Markdown formatting."""
    for chat_id in CHAT_IDS:
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            telegram_request(BOT_API, "sendMessage", payload)
            logging.info("Message sent to Telegram!")
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {e}")

def format_job_for_telegram(job: dict, location: str, ai_data: dict = None) -> str:
    """Format a single job for Telegram with AI insights."""
    base_msg = (
        f"\U0001f4cb *Job:* [{job['title']}]({job['url']})\n"
        f"\U0001f3e2 *Company:* {job['company']}\n"
        f"\U0001f4cd *Location:* {job['location']} ({location})\n"
    )
    
    if ai_data:
        score = ai_data.get('score', 'N/A')
        category = ai_data.get('category', 'Unknown')
        reason = ai_data.get('reason', 'No reason provided')
        
        base_msg += (
            f"\U0001f916 *AI Score:* {score}/10\n"
            f"\U0001f4bc *Category:* {category}\n"
            f"\U0001f4a1 *AI Insight:* {reason}\n"
        )
    
    base_msg += "━━━━━━━━━━━━━━━━━━━━━━"
    return base_msg

def load_ai_results():
    """Load AI-filtered job results from file."""
    if not FILTERED_JOBS_FILE.exists():
        logging.warning(f"AI results file not found: {FILTERED_JOBS_FILE}")
        return None
    
    try:
        with open(FILTERED_JOBS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        # The file contains a JSON-encoded string, so parse it as a string first
        try:
            # First parse: removes the outer quotes and unescapes the JSON string
            json_string = json.loads(content)
            # Second parse: converts the JSON string to actual objects
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            # Fallback: try parsing as regular JSON (in case format changes)
            return json.loads(content)
            
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse AI results JSON: {e}")
        logging.error(f"Content preview: {content[:200]}...")
        return None
    except Exception as e:
        logging.error(f"Error loading AI results: {e}")
        return None

def process_and_send_relevant_jobs():
    """Load AI results and send Telegram notifications for relevant DevOps jobs."""
    print("🔍 Loading AI-filtered job results...")
    
    ai_results = load_ai_results()
    if not ai_results:
        print("❌ No AI results found or failed to load")
        return
    
    print(f"📊 AI Results loaded successfully")
    
    # Parse the AI response structure
    if isinstance(ai_results, dict) and 'results' in ai_results:
        job_analyses = ai_results['results']
        summary = ai_results.get('summary', {})
        
        total_jobs = summary.get('total_jobs', len(job_analyses))
        relevant_count = summary.get('relevant_count', 0)
        
        print(f"📈 Summary: {relevant_count}/{total_jobs} jobs deemed relevant by AI")
        print("=" * 60)
        
        # Filter for relevant jobs only
        relevant_jobs = [job for job in job_analyses if job.get('relevant', False)]
        
        if not relevant_jobs:
            print("😞 No jobs found that match your DevOps profile")
            # Send summary message to Telegram
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            summary_msg = f"🤖 *Job Alert Summary*\n\n📅 Run at: {timestamp}\n📊 Analyzed: {total_jobs} jobs\n❌ No relevant DevOps positions found this time."
            # send_telegram_markdown_message(summary_msg)
            return
        
        print(f"🎯 Found {len(relevant_jobs)} relevant DevOps jobs!")
        
        # Send summary message first
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary_msg = (
            f"🤖 *Job Alert Summary*\n\n"
            f"📅 Run at: {timestamp}\n"
            f"📊 Analyzed: {total_jobs} jobs\n"
            f"✅ Relevant: {len(relevant_jobs)} DevOps positions\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_telegram_markdown_message(summary_msg)
        
        # Send individual job notifications
        for i, job_result in enumerate(relevant_jobs, 1):
            job_title = job_result.get('job_title', 'Unknown Title')
            company = job_result.get('company', 'Unknown Company')
            location = job_result.get('location', 'Unknown Location')
            link = job_result.get('link', '#')
            score = job_result.get('score', 'N/A')
            category = job_result.get('category', 'Unknown')
            reason = job_result.get('reason', 'No reason provided')
            
            # Create job message
            job_msg = (
                f"🚀 *DevOps Job #{i}/{len(relevant_jobs)}*\n\n"
                f"📋 *Position:* [{job_title}]({link})\n"
                f"🏢 *Company:* {company}\n"
                f"📍 *Location:* {location}\n"
                f"🤖 *AI Score:* {score}/10\n"
                f"🎯 *Category:* {category}\n"
                f"💡 *Why Relevant:* {reason}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            
            send_telegram_markdown_message(job_msg)
            print(f"✅ Sent notification for: {job_title} at {company}")
        
        print(f"\n🎉 Successfully sent {len(relevant_jobs)} job notifications to Telegram!")
    
    else:
        print("⚠️  Unexpected AI results format")
        print("Raw results:")
        print(ai_results)

def process_and_print_relevant_jobs():
    """Alias for backward compatibility - prints jobs without sending notifications."""
    print("🔍 Loading AI-filtered job results...")
    
    ai_results = load_ai_results()
    if not ai_results:
        print("❌ No AI results found or failed to load")
        return
    
    print(f"📊 AI Results loaded successfully")
    
    # Parse the AI response structure
    if isinstance(ai_results, dict) and 'results' in ai_results:
        job_analyses = ai_results['results']
        summary = ai_results.get('summary', {})
        
        total_jobs = summary.get('total_jobs', len(job_analyses))
        relevant_count = summary.get('relevant_count', 0)
        
        print(f"📈 Summary: {relevant_count}/{total_jobs} jobs deemed relevant by AI")
        print("=" * 60)
        
        relevant_jobs = [job for job in job_analyses if job.get('relevant', False)]
        
        if not relevant_jobs:
            print("😞 No jobs found that match your DevOps profile")
            return
        
        print(f"🎯 Found {len(relevant_jobs)} jobs you can apply to:\n")
        
        for i, job_result in enumerate(relevant_jobs, 1):
            job_title = job_result.get('job_title', 'Unknown')
            company = job_result.get('company', 'Unknown')
            score = job_result.get('score', 'N/A')
            category = job_result.get('category', 'Unknown')
            reason = job_result.get('reason', 'No reason provided')
            
            print(f"🚀 Job #{i}: {job_title} at {company}")
            print(f"   📊 AI Score: {score}/10")
            print(f"   📂 Category: {category}")
            print(f"   💡 Why it's relevant: {reason}")
            print("-" * 50)
    
    else:
        print("⚠️  Unexpected AI results format")
        print("Raw results:")
        print(ai_results)


def send_telegram_html_message(bot_token: str, chat_id: str, text: str) -> bool:
    try:
        telegram_request(
            bot_token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": "true",
                "parse_mode": "HTML",
            },
        )
        time.sleep(0.15)
        return True
    except Exception as exc:
        print(f"Failed to send Telegram message: {exc}")
        return False


def html_escape(value) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_job_title(job: dict) -> str:
    title = html_escape(job.get("title") or "Unknown title")
    url = job.get("url")
    if not url:
        return title

    return f'<a href="{html_escape(url)}">{title}</a>'


def format_report_job_entry(job: dict, index: int) -> str:
    details = " · ".join(
        f"{emoji} {html_escape(job[key])}"
        for key, emoji in (("company", "🏥"), ("location", "📍")) if job.get(key)
    )
    title = f"🔨 {index}. {format_job_title(job)}"
    return f"{title}\n{details}" if details else title


def build_full_search_report_messages(
    accepted: list,
    rejected: list,
    links: list,
    started_at: datetime,
    total_scraped: int,
    time_range_label: str,
) -> list:
    """One continuous job list, chunked only between jobs for Telegram's size limit."""
    jobs = accepted + [job for job in rejected if job.get("match_status") == "review"]
    if not jobs:
        return []
    report_time = started_at.astimezone(ZoneInfo("Europe/Amsterdam"))
    timestamp = report_time.strftime("%d %b %Y, %H:%M")
    footer = random_hephaestus_quote()
    # Reserve space before chunking so even the longest quote fits the last message.
    message_limit = TELEGRAM_MESSAGE_LIMIT - len(footer)
    result = []
    current = (
        "🔥⚒️ <b>Hephaestus Job Forge</b>\n"
        f"🕒 Report run at {timestamp} (Netherlands time)\n"
        f"🩺 {len(jobs)} job{'s' if len(jobs) != 1 else ''} found"
    )
    for index, job in enumerate(jobs, start=1):
        entry = format_report_job_entry(job, index)
        addition = f"\n\n{entry}" if current else entry
        if current and len(current) + len(addition) > message_limit:
            result.append(current)
            current = entry
        else:
            current += addition
    if current:
        result.append(current + footer)
    return result


def send_full_search_report_to_telegram(
    accepted: list,
    rejected: list,
    links: list,
    started_at: datetime,
    total_scraped: int,
    time_range_label: str,
) -> None:
    bot_token = normalize_bot_token(BOT_API)
    if not bot_token:
        print("Telegram disabled: TELEGRAM_BOT_API is not set.")
        return

    if not CHAT_IDS:
        print("Telegram disabled: TELEGRAM_CHAT_ID is not set.")
        return

    # Missing descriptions/grades must not silently hide potentially suitable jobs.
    if not accepted and not any(job.get("match_status") == "review" for job in rejected):
        print("Telegram skipped: no matching jobs or jobs needing review this run.")
        return

    messages = build_full_search_report_messages(
        accepted,
        rejected,
        links,
        started_at,
        total_scraped,
        time_range_label,
    )
    if len(messages) > 1:
        print(
            "Telegram report is too long for one message. "
            f"Sending {len(messages)} Telegram messages instead."
        )

    for chat_id in CHAT_IDS:
        for message in messages:
            send_telegram_html_message(bot_token, chat_id, message)


def main():
    """Main function to process and send relevant job notifications."""
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s',
        level=logging.INFO
    )
    
    print("🤖 AI Job Filter & Telegram Messenger")
    print("=" * 40)
    
    # Check if we have Telegram credentials
    if not BOT_API or not CHAT_IDS:
        print("⚠️  Telegram credentials not found, only printing results...")
        process_and_print_relevant_jobs()
    else:
        print("📱 Telegram credentials found, sending notifications...")
        process_and_send_relevant_jobs()

if __name__ == "__main__":
    main()
