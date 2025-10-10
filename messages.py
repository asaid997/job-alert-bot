"""
Messages module for handling AI-filtered job notifications.
Reads AI analysis results and prints/sends relevant jobs.
"""
import json
import os
import requests
import logging
from pathlib import Path
from datetime import datetime

# Telegram configuration
BOT_API = os.environ.get("TELEGRAM_BOT_API")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FILTERED_JOBS_FILE = Path("filtered_jobs.json")

def send_telegram_markdown_message(message: str) -> None:
    """Send a message to Telegram using Markdown formatting."""
    url = f"https://api.telegram.org/bot{BOT_API}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
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