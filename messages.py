"""
Messages module for handling AI-filtered job notifications.
Reads AI analysis results and prints/sends relevant jobs.
"""
import json
import os
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Telegram configuration
BOT_API = os.environ.get(
    "TELEGRAM_BOT_API",
    "",
).strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
FILTERED_JOBS_FILE = Path("filtered_jobs.json")
TELEGRAM_MESSAGE_LIMIT = 4096


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
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
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


def format_report_job_entry(job: dict, index: int, emoji: str) -> str:
    search_bits = []
    if job.get("search_region"):
        search_bits.append(job["search_region"])
    if job.get("search_title"):
        search_bits.append(job["search_title"])

    search_line = ""
    if search_bits:
        search_line = f"\n🔎 <b>Found via:</b> {html_escape(' / '.join(search_bits))}"

    return (
        f"{emoji} <b>{index}.</b> {format_job_title(job)}\n"
        f"🏢 <b>Company:</b> {html_escape(job.get('company') or 'Unknown company')}\n"
        f"📍 <b>Location:</b> {html_escape(job.get('location') or 'Unknown location')}"
        f"{search_line}\n"
        f"💡 <b>Reason:</b> {html_escape(job.get('filter_reason') or 'n/a')}"
    )


def build_report_section(title: str, description: str, jobs: list, emoji: str) -> str:
    if not jobs:
        return f"{title}\n{description}\n\n😕 No jobs in this section."

    entries = [
        format_report_job_entry(job, index, emoji)
        for index, job in enumerate(jobs, start=1)
    ]
    return f"{title}\n{description}\n━━━━━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(entries)


def build_report_header(
    accepted: list,
    rejected: list,
    links: list,
    started_at: datetime,
    total_scraped: int,
    time_range_label: str,
) -> str:
    timestamp = started_at.strftime("%Y-%m-%d %H:%M:%S")
    reviewed_total = len(accepted) + len(rejected)
    return (
        "✅✅✅✅✅✅✅ <b>New Job Search</b> ✅✅✅✅✅✅✅\n\n"
        "🤖 <b>Job Summary Report</b>\n"
        f"🕒 <b>Time of searching:</b> {html_escape(timestamp)}\n"
        f"⏱️ <b>Looking back:</b> {html_escape(time_range_label)}\n"
        f"🔎 <b>Search filters:</b> {len(links)}\n"
        f"📊 <b>Loaded cards:</b> {total_scraped}\n"
        f"🧾 <b>Unique new jobs reviewed:</b> {reviewed_total}\n"
        f"✅ <b>High confidence:</b> {len(accepted)}\n"
        f"🧐 <b>Required reviewing:</b> {len(rejected)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )


def build_full_search_report(
    accepted: list,
    rejected: list,
    links: list,
    started_at: datetime,
    total_scraped: int,
    time_range_label: str,
) -> str:
    header = build_report_header(
        accepted,
        rejected,
        links,
        started_at,
        total_scraped,
        time_range_label,
    )
    high_confidence = build_report_section(
        "✅ <b>Section 1: High confidence jobs</b>",
        "These look like the strongest chemical junior/internship matches.",
        accepted,
        "🧪",
    )
    required_review = build_report_section(
        "🧐 <b>Section 2: Required reviewing</b>",
        (
            "These appeared in the searches, but the rule filter thinks they may not fit.\n"
            "Review them manually before ignoring them."
        ),
        rejected,
        "🔍",
    )

    return f"{header}\n\n{high_confidence}\n\n{required_review}"


def split_text_message(text: str, continuation_title: str) -> list:
    safe_limit = TELEGRAM_MESSAGE_LIMIT - 200
    if len(text) <= safe_limit:
        return [text]

    messages = []
    current = ""
    for line in text.splitlines():
        addition = line if not current else f"\n{line}"
        if current and len(current) + len(addition) > safe_limit:
            messages.append(current)
            current = f"{continuation_title} continued\n━━━━━━━━━━━━━━━━━━━━━━\n{line}"
        else:
            current += addition

    if current:
        messages.append(current)

    return messages


def build_report_section_messages(
    title: str,
    description: str,
    jobs: list,
    emoji: str,
) -> list:
    safe_limit = TELEGRAM_MESSAGE_LIMIT - 200
    section_header = f"{title}\n{description}\n━━━━━━━━━━━━━━━━━━━━━━"
    if not jobs:
        return [f"{section_header}\n\n😕 No jobs in this section."]

    messages = []
    current = section_header
    for index, job in enumerate(jobs, start=1):
        entry = "\n\n" + format_report_job_entry(job, index, emoji)
        if len(current) + len(entry) > safe_limit:
            messages.append(current)
            current = f"{title} continued\n━━━━━━━━━━━━━━━━━━━━━━" + entry
        else:
            current += entry

    messages.append(current)
    return messages


def build_no_new_jobs_message(
    links: list,
    started_at: datetime,
    total_scraped: int,
    time_range_label: str,
) -> str:
    timestamp = started_at.strftime("%Y-%m-%d %H:%M:%S")
    header = (
        "🟡 <b>New Job Search</b>\n\n"
        "🤖 <b>Job Summary Report</b>\n"
        f"🕒 <b>Time of searching:</b> {html_escape(timestamp)}\n"
        f"⏱️ <b>Looking back:</b> {html_escape(time_range_label)}\n"
        f"🔎 <b>Search filters:</b> {len(links)}\n"
        f"📊 <b>Loaded cards:</b> {total_scraped}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    if total_scraped > 0:
        body = (
            f"🔁 Found {total_scraped} job card{'s' if total_scraped != 1 else ''}, "
            "but all of them were already seen in a previous run. No new unique jobs this time."
        )
    else:
        body = "😴 No jobs found in this search window."

    return f"{header}\n\n{body}"


def build_full_search_report_messages(
    accepted: list,
    rejected: list,
    links: list,
    started_at: datetime,
    total_scraped: int,
    time_range_label: str,
) -> list:
    if not accepted and not rejected:
        return [
            build_no_new_jobs_message(links, started_at, total_scraped, time_range_label)
        ]

    report = build_full_search_report(
        accepted,
        rejected,
        links,
        started_at,
        total_scraped,
        time_range_label,
    )
    if len(report) <= TELEGRAM_MESSAGE_LIMIT - 200:
        return [report]

    messages = split_text_message(
        build_report_header(
            accepted,
            rejected,
            links,
            started_at,
            total_scraped,
            time_range_label,
        ),
        "🤖 <b>Job Summary Report</b>",
    )
    messages.extend(
        build_report_section_messages(
            "✅ <b>Section 1: High confidence jobs</b>",
            "These look like the strongest chemical junior/internship matches.",
            accepted,
            "🧪",
        )
    )
    messages.extend(
        build_report_section_messages(
            "🧐 <b>Section 2: Required reviewing</b>",
            (
                "These appeared in the searches, but the rule filter thinks they may not fit.\n"
                "Review them manually before ignoring them."
            ),
            rejected,
            "🔍",
        )
    )
    return messages


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

    if not CHAT_ID:
        print("Telegram disabled: TELEGRAM_CHAT_ID is not set.")
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

    for message in messages:
        send_telegram_html_message(bot_token, CHAT_ID, message)


def main():
    """Main function to process and send relevant job notifications."""
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s',
        level=logging.INFO
    )
    
    print("🤖 AI Job Filter & Telegram Messenger")
    print("=" * 40)
    
    # Check if we have Telegram credentials
    if not BOT_API or not CHAT_ID:
        print("⚠️  Telegram credentials not found, only printing results...")
        process_and_print_relevant_jobs()
    else:
        print("📱 Telegram credentials found, sending notifications...")
        process_and_send_relevant_jobs()

if __name__ == "__main__":
    main()
