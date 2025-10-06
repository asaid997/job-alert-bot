"""
Messages module for handling AI-filtered job notifications.
Reads AI analysis results and prints/sends relevant jobs.
"""
import json
import os
import requests
import logging
from pathlib import Path

# Telegram configuration
BOT_API = os.environ.get("TELEGRAM_BOT_API")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
JOBS_TO_FILTER_FILE = Path("jobs_to_filter.json")

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
    if not JOBS_TO_FILTER_FILE.exists():
        logging.warning(f"AI results file not found: {JOBS_TO_FILTER_FILE}")
        return None
    
    try:
        with open(JOBS_TO_FILTER_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        # Parse JSON from the AI response
        return json.loads(content)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse AI results JSON: {e}")
        return None
    except Exception as e:
        logging.error(f"Error loading AI results: {e}")
        return None

def process_and_print_relevant_jobs():
    """Load AI results and print jobs that are relevant for DevOps/your profile."""
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
        
        relevant_jobs = []
        for result in job_analyses:
            if result.get('relevant', False):
                relevant_jobs.append(result)
        
        if not relevant_jobs:
            print("😞 No jobs found that match your DevOps profile")
            return
        
        print(f"🎯 Found {len(relevant_jobs)} jobs you can apply to:\n")
        
        for i, job_result in enumerate(relevant_jobs, 1):
            job_id = job_result.get('job_id', 'Unknown')
            score = job_result.get('score', 'N/A')
            category = job_result.get('category', 'Unknown')
            reason = job_result.get('reason', 'No reason provided')
            
            print(f"🚀 Job #{i} (ID: {job_id})")
            print(f"   📊 AI Score: {score}/10")
            print(f"   📂 Category: {category}")
            print(f"   💡 Why it's relevant: {reason}")
            print(f"   ✅ Status: RECOMMENDED")
            print("-" * 50)
    
    else:
        print("⚠️  Unexpected AI results format")
        print("Raw results:")
        print(ai_results)

def main():
    """Main function to process and display relevant jobs."""
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s',
        level=logging.INFO
    )
    
    print("🤖 AI Job Filter & Telegram Messenger")
    print("=" * 40)
    
    # Print relevant jobs (not send to Telegram yet)
    process_and_print_relevant_jobs()

if __name__ == "__main__":
    main()