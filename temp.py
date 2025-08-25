from playwright.sync_api import sync_playwright
from urllib.parse import quote_plus
import traceback
import os
import re
from datetime import datetime, timedelta
import time
from pathlib import Path
import requests
import logging
import pytz
import json
from urllib.parse import urlparse

BOT_API = os.environ.get('TELEGRAM_BOT_API')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SEARCHES = {
    "NL": {
        "geo_id": "102890719",
        "region": "Netherlands",
        "remotes": "2,3",  # 3: remote, 2: on-site/hybrid
        "titles": ["devops engineer", "site reliability engineer", "SRE"]
    },
    "IL": {
        "geo_id": "101620260",
        "region": "Israel",
        "remotes": "2",
        "titles": ["devops engineer", "site reliability engineer", "SRE"]
    }
}
TIME_RANGE = "r1000800"  # Jobs posted in the last 3 hours
HEADLESS = True
VIDEO_DIR = "playwright-videos"
JOBS_CACHE_FILE = Path("jobs_cache/last_jobs.json")
JOBS_CACHE_RUNS = 3

# Cache is a list of lists, each sublist is a list of job URLs for a run
def load_cached_jobs():
    if JOBS_CACHE_FILE.exists():
        with open(JOBS_CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_cached_jobs(runs):
    JOBS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"[DEBUG] Saving jobs cache to: {JOBS_CACHE_FILE.resolve()}")
    with open(JOBS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(runs, f)
    print(f"[DEBUG] Jobs cache file exists: {JOBS_CACHE_FILE.exists()}")


def extract_job_id(url):
    # Works for any subdomain and ignores query params
    # Example: https://il.linkedin.com/jobs/view/senior-devops-engineer-at-akamai-technologies-4264658112?position=2&pageNum=0
    import re
    match = re.search(r'/jobs/view/[^/-]*-?(\d+)', url)
    if match:
        return match.group(1)
    # Fallback: try to find a long number in the path
    path = urlparse(url).path
    fallback = re.search(r'(\d{7,})', path)
    if fallback:
        return fallback.group(1)
    return url  # fallback to full URL if no ID found

# Flatten all job URLs from all runs into a set
def flatten_job_urls(jobs_runs):
    seen = set()
    for run in jobs_runs:
        for url in run:
            seen.add(url)
    return seen


def flatten_job_ids(jobs_runs):
    seen = set()
    for run in jobs_runs:
        for job_id in run:
            seen.add(job_id)
    return seen

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s: %(message)s',
    level=logging.INFO
)


def build_jobs_url(job_title, geo_id, remotes):
    """Build the LinkedIn jobs search URL with the given parameters."""
    return (
        f"https://www.linkedin.com/jobs/search/?distance=25&f_TPR={TIME_RANGE}&f_WT={remotes}&geoId={geo_id}&keywords={quote_plus(job_title)}"
    )

def extract_job_info(card):
    # Title and URL
    title_a = card.query_selector("a.base-card__full-link")
    title = ""
    url = ""
    if title_a:
        sr_only = title_a.query_selector("span.sr-only")
        title = sr_only.inner_text().strip() if sr_only else ""
        url = title_a.get_attribute("href")
    # Company
    company = ""
    company_a = card.query_selector("h4.base-search-card__subtitle a")
    if company_a:
        company = company_a.inner_text().strip()
    # Location
    location_span = card.query_selector("span.job-search-card__location")
    location = location_span.inner_text().strip() if location_span else ""
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
    }

def format_jobs_for_telegram(jobs_by_location: dict) -> str:
    """Format the job results as a neat Telegram message."""
    lines = []
    total_jobs = 0
    for location, jobs in jobs_by_location.items():
        lines.append(f"\U0001F4BC <b>DevOps Jobs in {location}</b>\n")
        if not jobs:
            lines.append("No jobs found.\n")
            continue
        for job in jobs:
            lines.append(f"<b>{job['title']}</b>\n"
                         f"<b>Company:</b> {job['company']}\n"
                         f"<b>Location:</b> {job['location']}\n"
                         f"<a href='{job['url']}'>View on LinkedIn</a>\n")
            lines.append("---\n")
        total_jobs += len(jobs)
    lines.append(f"\n<b>Total jobs found:</b> {total_jobs}")
    return '\n'.join(lines)

def send_telegram_markdown_message(message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_API}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        # response = requests.post(url, data=payload)
        # response.raise_for_status()
        logging.info("Page/job sent to Telegram!")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

def format_job_for_telegram(job: dict, location: str, timestamp: str) -> str:
    """Format a single job for Telegram with emojis and a friendly template."""
    return (
        f"\U0001F4CB *Job:* [{job['title']}]({job['url']})\n"
        f"\U0001F3E2 *Company:* {job['company']}\n"
        f"\U0001F4CD *Location:* {job['location']} ({location})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

def send_location_header(location: str, timestamp: str) -> None:
    # Use green squares, check marks, and a long separator for a bold, professional look
    green_square = '\U0001F7E9'
    check = '\u2705'
    rocket = '\U0001F680'
    chart = '\U0001F4C8'
    briefcase = '\U0001F4BC'
    bulb = '\U0001F4A1'
    sparkle = '\u2728'
    separator = green_square * 24
    msg = (
        f"{separator}\n"
        f"{sparkle}{check}{rocket}{chart}{briefcase} *{bulb} DEVOPS JOBS IN {location.upper()} {bulb}* {briefcase}{chart}{rocket}{check}{sparkle}\n"
        f"_Run at: {timestamp}_\n"
        f"{separator}"
    )
    send_telegram_markdown_message(msg)

def main() -> None:
    try:
        logging.info("Job alert script started.")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            athens_tz = pytz.timezone('Europe/Athens')
            now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
            now_athens = now_utc.astimezone(athens_tz)
            print(f"Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"Current time (Athens): {now_athens.strftime('%Y-%m-%d %H:%M:%S %Z')}")

            # Load previous jobs cache (list of lists of job IDs)
            jobs_runs = load_cached_jobs()
            notified_job_ids = flatten_job_ids(jobs_runs)
            this_run_job_ids = []

            for key in SEARCHES:
                region_info = SEARCHES[key]
                geo_id = region_info["geo_id"]
                location = region_info["region"]
                remotes = region_info["remotes"]
                for job_title in region_info["titles"]:
                    jobs_url = build_jobs_url(job_title, geo_id, remotes)
                    logging.info(f"Navigating to jobs URL: {jobs_url}")
                    page.goto(jobs_url)

                    # Try to dismiss the cookie/banner if present
                    try:
                        page.get_by_role("button", name="Dismiss").click(timeout=3000)
                        logging.info("Dismissed banner.")
                    except Exception:
                        logging.info("No dismiss button found.")

                    # Check for 'We couldn’t find a match for' message
                    if page.get_by_text("We couldn’t find a match for", exact=False).is_visible():
                        logging.info(f"No jobs found for {location} [{job_title}] (LinkedIn search page says no match). Skipping to next.")
                        continue

                    # Wait for the jobs list to appear
                    page.wait_for_selector("ul.jobs-search__results-list", timeout=10000)
                    jobs_list = page.query_selector("ul.jobs-search__results-list")
                    if not jobs_list:
                        logging.warning(f"Jobs list selector not found for {location} [{job_title}]. Skipping to next.")
                        continue

                    # Click the first job card to focus the list (improves scroll reliability)
                    first_job_card = jobs_list.query_selector("li div.base-card")
                    if first_job_card:
                        first_job_card.click()
                        time.sleep(0.5)

                    # Scroll to the bottom and handle 'See more jobs' and end message
                    _prev_height = -1
                    _max_scrolls = 100
                    _scroll_count = 0
                    while _scroll_count < _max_scrolls:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1500)
                        try:
                            if page.get_by_text("You've viewed all jobs for").is_visible():
                                logging.info("Reached end: 'You've viewed all jobs for' message found.")
                                break
                        except Exception:
                            pass
                        try:
                            see_more_btn = page.get_by_role("button", name="See more jobs")
                            if see_more_btn.is_visible():
                                see_more_btn.click()
                                logging.info("Clicked 'See more jobs' button.")
                                page.wait_for_timeout(1500)
                        except Exception:
                            pass
                        new_height = page.evaluate("document.body.scrollHeight")
                        if new_height == _prev_height:
                            break
                        _prev_height = new_height
                        _scroll_count += 1

                    # Scrape all job items robustly, matching LinkedIn's structure
                    job_items = jobs_list.query_selector_all("li")
                    logging.info(f"Found {len(job_items)} jobs for {location} [{job_title}].")
                    for job in job_items:
                        card = job.query_selector("div.base-card")
                        if not card:
                            continue
                        job_dict = extract_job_info(card)
                        job_id = extract_job_id(job_dict["url"])
                        logging.info(f"Found job: {job_dict['title']} ({job_id})")
                        if job_id not in notified_job_ids:
                            # Only notify new jobs
                            msg = format_job_for_telegram(job_dict, location, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            send_telegram_markdown_message(msg)
                            logging.info(f"Sent notification for job: {job_dict['title']} ({job_id})")
                        else:
                            logging.info(f"Skipped already notified job: {job_dict['title']} ({job_id})")
                        this_run_job_ids.append(job_id)
    except Exception as e:
        error_msg = f"Job failed: {str(e)}\n" + traceback.format_exc()
        print(error_msg)
        logging.error(error_msg)

main()