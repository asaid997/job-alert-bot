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
import sys
from urllib.parse import urlparse
from gemini import batch_job_analysis, test_gemini_simple

BOT_API = os.environ.get("TELEGRAM_BOT_API")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SEARCHES = {
    "NL": {
        "geo_id": "102890719",
        "region": "Netherlands",
        "remotes": "2,3",  # 3: remote, 2: on-site/hybrid
        "titles": ["devops engineer", "site reliability engineer"],
    },
    "IL": {
        "geo_id": "101620260",
        "region": "Israel",
        "remotes": "2",
        "titles": ["devops engineer", "site reliability engineer"],
    },
}
TIME_RANGE = "r10800"  # Jobs posted in the last 3 hours
HEADLESS = True
VIDEO_DIR = "playwright-videos"
JOBS_CACHE_FILE = Path("jobs-cache/last_jobs.json")
JOBS_CACHE_RUNS = 5
JOBS_TO_FILTER = []
JOBS_TO_FILTER_FILE = Path("jobs_to_filter.json")


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

    match = re.search(r"/jobs/view/[^/-]*-?(\d+)", url)
    if match:
        return match.group(1)
    # Fallback: try to find a long number in the path
    path = urlparse(url).path
    fallback = re.search(r"(\d{7,})", path)
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
    format="[%(asctime)s] %(levelname)s: %(message)s", level=logging.INFO
)


def build_jobs_url(job_title, geo_id, remotes):
    """Build the LinkedIn jobs search URL with the given parameters."""
    return f"https://www.linkedin.com/jobs/search/?distance=25&f_TPR={TIME_RANGE}&f_WT={remotes}&geoId={geo_id}&keywords={quote_plus(job_title)}"


def is_login_redirect(page):
    """Check if LinkedIn redirected to login page."""
    try:
        # Wait a moment for any JS redirects to complete
        time.sleep(2)

        current_url = page.url
        logging.info(f"🔍 Current URL: {current_url}")

        # Check for login/auth URLs (more comprehensive patterns)
        login_patterns = [
            "/login",
            "/authwall",
            "/checkpoint",
            "/uas/login",
            "linkedin.com/login",
            "linkedin.com/authwall",
            "challenge",
            "signup",
            "guest",
        ]

        if any(pattern in current_url.lower() for pattern in login_patterns):
            logging.warning(f"🚨 Login redirect detected via URL: {current_url}")
            return True

        # Check for login page elements
        login_selectors = [
            'input[name="session_key"]',  # Email field
            'input[name="session_password"]',  # Password field
            'input[id="username"]',  # Alternative email field
            'button[data-tracking-control-name*="sign-in"]',  # Sign in button
            ".authwall",  # Auth wall class
            '[data-test-id="sign-in-form"]',  # Sign in form
        ]

        for selector in login_selectors:
            if page.query_selector(selector):
                logging.warning(f"🚨 Login redirect detected via element: {selector}")
                return True

        # Check if we can find expected job search elements
        job_indicators = [
            "ul.jobs-search__results-list",
            ".jobs-search-results-list",
            '[data-test-id="job-search-results"]',
        ]

        has_job_elements = any(
            page.query_selector(selector) for selector in job_indicators
        )
        if not has_job_elements:
            logging.warning("🚨 No job search elements found - might be login page")
            return True

        return False

    except Exception as e:
        logging.error(f"Error checking login redirect: {e}")
        return False


def handle_login_redirect(page):
    """Clear session and retry - Option 2 approach."""
    logging.warning("🚨 Login redirect detected! Clearing session...")
    try:
        # Clear all cookies and storage
        page.context.clear_cookies()
        time.sleep(5)  # Wait before retry
        logging.info("✅ Session cleared, ready to retry")
        return True
    except Exception as e:
        logging.error(f"Failed to clear session: {e}")
        return False


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
        lines.append(f"\U0001f4bc <b>DevOps Jobs in {location}</b>\n")
        if not jobs:
            lines.append("No jobs found.\n")
            continue
        for job in jobs:
            lines.append(
                f"<b>{job['title']}</b>\n"
                f"<b>Company:</b> {job['company']}\n"
                f"<b>Location:</b> {job['location']}\n"
                f"<a href='{job['url']}'>View on LinkedIn</a>\n"
            )
            lines.append("---\n")
        total_jobs += len(jobs)
    lines.append(f"\n<b>Total jobs found:</b> {total_jobs}")
    return "\n".join(lines)


def send_telegram_markdown_message(message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_API}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        logging.info("Page/job sent to Telegram!")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")


def format_job_for_telegram(job: dict, location: str) -> str:
    """Format a single job for Telegram with emojis and a friendly template."""
    return (
        f"\U0001f4cb *Job:* [{job['title']}]({job['url']})\n"
        f"\U0001f3e2 *Company:* {job['company']}\n"
        f"\U0001f4cd *Location:* {job['location']} ({location})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )


def send_location_header(location: str) -> None:
    # Use green squares, check marks, and a long separator for a bold, professional look
    green_square = "\U0001f7e9"
    check = "\u2705"
    rocket = "\U0001f680"
    chart = "\U0001f4c8"
    briefcase = "\U0001f4bc"
    bulb = "\U0001f4a1"
    sparkle = "\u2728"
    separator = green_square * 10
    msg = (
        f"{separator}\n"
        f"{sparkle}{check}{rocket}{chart}{briefcase} *{bulb} DEVOPS JOBS IN {location.upper()} {bulb}* {briefcase}{chart}{rocket}{check}{sparkle}\n"
        f"{separator}"
    )
    send_telegram_markdown_message(msg)


def main() -> None:
    try:
        logging.info("Job alert script started.")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                record_video_dir=VIDEO_DIR,
                record_video_size={"width": 1280, "height": 900},
            )
            page = context.new_page()

            athens_tz = pytz.timezone("Europe/Athens")
            now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
            now_athens = now_utc.astimezone(athens_tz)
            print(f"Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(
                f"Current time (Athens): {now_athens.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )

            # Load previous jobs cache (list of lists of job IDs)
            jobs_runs = load_cached_jobs()
            notified_job_ids = flatten_job_ids(jobs_runs)
            this_run_job_ids = []

            for key in SEARCHES:
                region_info = SEARCHES[key]
                geo_id = region_info["geo_id"]
                location = region_info["region"]
                remotes = region_info["remotes"]
                region_found_jobs = False
                for job_title in region_info["titles"]:
                    jobs_url = build_jobs_url(job_title, geo_id, remotes)
                    logging.info(f"Navigating to jobs URL: {jobs_url}")
                    page.goto(jobs_url)

                    # 🚨 Check for login redirect immediately
                    if is_login_redirect(page):
                        if handle_login_redirect(page):
                            # Retry navigation with cleared session
                            logging.info("Retrying navigation with fresh session...")
                            page.goto(jobs_url)
                            if is_login_redirect(page):
                                logging.info(
                                    "Retrying navigation with fresh session..."
                                )
                                page.goto(jobs_url)
                        else:
                            logging.error(
                                f"Failed to handle login redirect. Skipping {job_title}"
                            )
                            continue

                    # Try to dismiss the cookie/banner if present
                    try:
                        page.get_by_role("button", name="Dismiss").click(timeout=3000)
                        logging.info(f"0.5")
                        logging.info("Dismissed banner.")
                    except Exception:
                        logging.info("No dismiss button found.")

                    logging.info(f"1")
                    # Check for 'We couldn’t find a match for' message
                    if page.get_by_text(
                        "We couldn’t find a match for", exact=False
                    ).is_visible():
                        logging.info(
                            f"No jobs found for {location} [{job_title}] (LinkedIn search page says no match). Skipping to next."
                        )
                        continue
                    logging.info(f"2")

                    # Wait for the jobs list to appear (increased timeout)
                    page.wait_for_selector(
                        "ul.jobs-search__results-list", timeout=20000
                    )
                    jobs_list = page.query_selector("ul.jobs-search__results-list")
                    logging.info(f"3")
                    if not jobs_list:
                        logging.warning(
                            f"Jobs list selector not found for {location} [{job_title}]. Skipping to next."
                        )
                        continue

                    logging.info(f"4")
                    # Click the first job card to focus the list (improves scroll reliability)
                    # But don't click if it might cause navigation
                    try:
                        first_job_card = jobs_list.query_selector("li div.base-card")
                        if first_job_card:
                            # Just focus without clicking to avoid navigation
                            first_job_card.scroll_into_view_if_needed()
                            time.sleep(0.5)
                        logging.info(f"5 - Focused first job card")
                    except Exception as e:
                        logging.warning(f"Could not focus first job card: {e}")
                    logging.info(f"5----------------")

                    # Scroll to the bottom and handle 'See more jobs' and end message
                    _prev_height = -1
                    _max_scrolls = 100
                    _scroll_count = 0
                    while _scroll_count < _max_scrolls:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1500)
                        try:
                            if page.get_by_text(
                                "You've viewed all jobs for"
                            ).is_visible():
                                logging.info(
                                    "Reached end: 'You've viewed all jobs for' message found."
                                )
                                break
                        except Exception:
                            pass
                        try:
                            see_more_btn = page.get_by_role(
                                "button", name="See more jobs"
                            )
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

                    logging.info(f"6----------------")
                    # Re-query the jobs list to ensure it's still valid after scrolling
                    try:
                        jobs_list = page.query_selector("ul.jobs-search__results-list")
                        if not jobs_list:
                            logging.warning(
                                f"Jobs list disappeared after scrolling for {location} [{job_title}]. Skipping."
                            )
                            continue

                        # Scrape all job items robustly, matching LinkedIn's structure
                        job_items = jobs_list.query_selector_all("li")
                        logging.info(
                            f"Found {len(job_items)} jobs for {location} [{job_title}]."
                        )
                    except Exception as e:
                        logging.error(f"Error querying job items: {e}")
                        continue

                    jobs_sent_for_region = 0
                    logging.info(f"7----------------")
                    for job in job_items:
                        card = job.query_selector("div.base-card")
                        if not card:
                            continue
                        job_dict = extract_job_info(card)
                        job_id = extract_job_id(job_dict["url"])
                        logging.info(f"Found job: {job_dict['title']} ({job_id})")
                        if (
                            job_id not in notified_job_ids
                            and job_id not in this_run_job_ids
                        ):
                            if not region_found_jobs:
                                # send_location_header(
                                #     location,
                                #     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                # )
                                region_found_jobs = True
                            # Only notify new jobs (not seen in previous runs or this run)
                            msg = format_job_for_telegram(
                                job_dict,
                                location
                            )
                            # send_telegram_markdown_message(msg)
                            logging.info(
                                f"Sent notification for job: {job_dict['title']} ({job_id})"
                            )
                            JOBS_TO_FILTER.append({
                                "job": job_dict,
                                "location": location
                            })
                            jobs_sent_for_region += 1
                        else:
                            logging.info(
                                f"Skipped already notified job: {job_dict['title']} ({job_id})"
                            )
                        this_run_job_ids.append(job_id)

                    logging.info(f"8----------------")
            # Log cache state before update
            logging.info(f"[CACHE] jobs_runs before update: {jobs_runs}")
            logging.info(f"[CACHE] this_run_job_ids before dedup: {this_run_job_ids}")
            logging.info(f"[CACHE] notified_job_ids: {notified_job_ids}")

            # Remove duplicates from this_run_job_ids (preserve order)
            seen = set()
            deduped_this_run_job_ids = []
            for job_id in this_run_job_ids:
                if job_id not in seen:
                    deduped_this_run_job_ids.append(job_id)
                    seen.add(job_id)

            # Only append if there are jobs in this run
            if deduped_this_run_job_ids:
                jobs_runs.append(deduped_this_run_job_ids)
                if len(jobs_runs) > JOBS_CACHE_RUNS:
                    jobs_runs = jobs_runs[-JOBS_CACHE_RUNS:]
                save_cached_jobs(jobs_runs)

            # Log cache state after update
            logging.info(f"[CACHE] jobs_runs after update: {jobs_runs}")
            logging.info(
                f"[CACHE] this_run_job_ids after dedup: {deduped_this_run_job_ids}"
            )

            # if test_gemini_simple():
            #     jobs = batch_job_analysis(JOBS_TO_FILTER)

            # Write jobs to file
            with open(JOBS_TO_FILTER_FILE, "w", encoding="utf-8") as f:
                f.write(str(JOBS_TO_FILTER))

    except Exception as e:
        error_msg = f"Job failed: {str(e)}\n" + traceback.format_exc()
        print(error_msg)
        logging.error(error_msg)
        sys.exit(1)  # Exit with error code 1 to signal failure


main()
