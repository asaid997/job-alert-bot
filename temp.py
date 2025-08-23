from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import imaplib
import email
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import requests
import logging

BOT_API = os.environ.get('TELEGRAM_BOT_API')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

EMAIL = os.environ.get("LINKEDIN_EMAIL", "mahjongmasterph@gmail.com")
PASSWORD = os.environ.get("LINKEDIN_PASSWORD", "kokos123")
SESSION_FILE = Path(os.environ.get("LINKEDIN_SESSION_FILE", "linkedin_session.json"))
SEARCHES = {
	"NL": ["102890719", "3", "Netherlands"],
	"IL": ["101620260", "2", "Israel"]
}
TIME_RANGE = "r172800"  # Jobs posted in the last hour
HEADLESS = True
VIDEO_DIR = "playwright-videos"

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s: %(message)s',
    level=logging.INFO
)

def get_latest_verification_code():
    GMAIL_USER = "mahjongmasterph@gmail.com"
    GMAIL_PASS = "cbvnrlvobcbwignt"
    MAILBOX = "INBOX"
    search_phrase = "Here's your verification code"
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select(MAILBOX)
    result, data = mail.search(None, "ALL")
    ids = data[0].split()[::-1]  # newest first
    for eid in ids:
        result, msg_data = mail.fetch(eid, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        subject = msg['subject']
        if subject and search_phrase in subject:
            match = re.search(r'(\d{6})$', subject)
            mail.logout()
            if match:
                return match.group(1)
            else:
                return None
    mail.logout()
    return None

def build_jobs_url(location, geo_id, remote):
	"""Build the LinkedIn jobs search URL with the given parameters."""
	return (
		f"https://www.linkedin.com/jobs/search/?distance=25&f_TPR={TIME_RANGE}&f_WT={remote}&geoId={geo_id}&keywords=devops%20engineer"
	)

def extract_job_info(job):
	"""Extract title, company, location, url, logo, and applicants from a job card element."""
	title_a = job.query_selector('a.job-card-container__link, a.job-card-list__title')
	title = ''
	if title_a:
		title = title_a.get_attribute('aria-label')
		if not title:
			title = title_a.inner_text().split('\n')[0].strip()
	if not title:
		return None
	# Remove verification symbol or badge from title (if present)
	import re
	title = re.sub(r'\s*with verification.*$', '', title, flags=re.IGNORECASE)
	title = title.strip()
	url = title_a.get_attribute('href') if title_a else ''
	if url and not url.startswith('http'):
		url = 'https://www.linkedin.com' + url
	# Extract company name
	company_elem = job.query_selector('.artdeco-entity-lockup__subtitle span, .job-card-container__company-name, .job-card-container__primary-description')
	company = company_elem.inner_text().strip() if company_elem else 'N/A'
	location_span = job.query_selector('.job-card-container__metadata-wrapper li span, .job-search-card__location')
	location = location_span.inner_text().strip() if location_span else 'N/A'
	# Extract company logo (img)
	logo_elem = job.query_selector('img.ivm-view-attr__img--centered, img.artdeco-entity-image, img.job-card-container__image, img.job-card-list__logo')
	logo_url = logo_elem.get_attribute('src') if logo_elem else ''
	# Extract applicants count if available
	applicants_elem = job.query_selector('.job-card-container__footer-job-meta span, .job-card-container__applicant-count, .job-card-footer__meta span')
	applicants = applicants_elem.inner_text().strip() if applicants_elem else 'N/A'
	return {
		'title': title,
		'company': company,
		'location': location,
		'url': url,
		'logo': logo_url,
		'applicants': applicants
	}

def save_session(context):
	"""Save the browser context's storage state to a file for session reuse."""
	context.storage_state(path=SESSION_FILE)

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

def send_telegram_message(message: str) -> None:
    """Send a simple text message to the Telegram bot chat."""
    url = f"https://api.telegram.org/bot{BOT_API}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Message sent to Telegram!")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def send_telegram_html_message(message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_API}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Summary sent to Telegram!")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def format_jobs_page_for_telegram(jobs: list, location: str, page_num: int, timestamp: str) -> str:
    """Format a single page of jobs for Telegram, with timestamp."""
    lines = [f"*DevOps Jobs in {location}* (Page {page_num})\n_{timestamp}_\n"]
    if not jobs:
        lines.append("No jobs found.\n")
    else:
        for job in jobs:
            lines.append(f"[{job['title']}]({job['url']}) - {job['location']}")
    return '\n'.join(lines)

def send_telegram_markdown_message(message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_API}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        logging.info("Page/job sent to Telegram!")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

def format_job_for_telegram(job: dict, location: str, timestamp: str) -> str:
    """Format a single job for Telegram with emojis and a friendly template."""
    return (
        f"\U0001F4CB *Job:* [{job['title']}]({job['url']})\n"
        f"\U0001F3E2 *Company:* {job['company']}\n"
        f"\U0001F4CD *Location:* {job['location']} ({location})\n"
        f"\U0001F552 _Posted: {timestamp}_\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

def send_location_header(location: str, timestamp: str) -> None:
    msg = (
        f"\U0001F4C8\U0001F4BC *\U0001F4A1 DEVOPS JOBS IN {location.upper()} \U0001F4A1*\n"
        f"_Run at: {timestamp}_\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_telegram_markdown_message(msg)

def scrape_jobs(page: Page, browser: Browser, location: str, geoid: str, remote: str) -> list:
    logging.info(f"Starting scrape for location: {location} (geoId={geoid}, remote={remote})")
    jobs_url = build_jobs_url(location, geoid, remote)
    logging.info(f"Navigating to jobs URL: {jobs_url}")
    page.goto(jobs_url)
    page.wait_for_timeout(2000)  # Wait 2 seconds for the page to reload
    header_title = f"devops engineer in {location}"
    try:
        page.wait_for_selector(f'[title="{header_title}"]', timeout=10000)
        logging.info(f"Found header: {header_title}")
    except Exception:
        logging.warning(f"Header with title '{header_title}' not found.")
        return []
    page_num = 1
    all_jobs = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Send location header before jobs
    send_location_header(location, timestamp)
    while True:
        logging.info(f"Scraping page {page_num} for {location}...")
        sentinel_div = page.query_selector('div[data-results-list-top-scroll-sentinel]')
        if not sentinel_div:
            logging.warning("Sentinel div with data-results-list-top-scroll-sentinel not found.")
            break
        jobs_list = sentinel_div.evaluate_handle('el => el.nextElementSibling && el.nextElementSibling.tagName == "UL" ? el.nextElementSibling : null')
        if not jobs_list:
            logging.warning("No <ul> found immediately after the sentinel div.")
            break
        page.evaluate('el => el.scrollIntoView({behavior: "smooth", block: "end"})', jobs_list)
        page.wait_for_timeout(2000)
        jobs = jobs_list.query_selector_all('li')
        valid_jobs = [info for job in jobs if (info := extract_job_info(job))]
        all_jobs.extend(valid_jobs)
        logging.info(f"Found {len(valid_jobs)} jobs on page {page_num} for {location}")
        # Send each job as a separate Telegram message
        for job in valid_jobs:
            msg = format_job_for_telegram(job, location, timestamp)
            logging.info(f"Sending job to Telegram: {job['title']} at {job['company']}")
            send_telegram_markdown_message(msg)
        pagination = page.query_selector('ul.jobs-search-pagination__pages')
        if not pagination:
            logging.info("No pagination bar found. Ending scrape for this location.")
            break
        next_btn = pagination.query_selector('button[aria-label="Page next"]:not([disabled])')
        if next_btn:
            try:
                next_btn.click()
                page.wait_for_timeout(2000)
                page_num += 1
                continue
            except Exception as e:
                logging.error(f"Failed to click next page button: {e}")
                break
        else:
            logging.info("No next page button. Finished scraping this location.")
            break
    return all_jobs

def open_linkedin() -> Tuple[Browser, Page]:
    logging.info("Starting Playwright and browser...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=HEADLESS)
    context = None
    viewport = {"width": 1920, "height": 1080}
    video_opts = {"dir": VIDEO_DIR, "size": viewport}
    if SESSION_FILE.exists():
        logging.info(f"Loading session from file: {SESSION_FILE}")
        context = browser.new_context(storage_state=str(SESSION_FILE), viewport=viewport, record_video_dir=VIDEO_DIR, record_video_size=viewport)
    else:
        logging.info("No session file found. Logging in...")
        context = browser.new_context(viewport=viewport, record_video_dir=VIDEO_DIR, record_video_size=viewport)
    page = context.new_page()
    page.goto("https://www.linkedin.com/login")
    # Handle account selection screen if present
    try:
        account_selector = 'button[aria-label*="bar rafa"], div[role="button"]:has-text("bar rafa")'
        if page.is_visible(account_selector, timeout=2000):
            logging.info("Account selection screen detected. Clicking on account...")
            page.click(account_selector)
            page.wait_for_timeout(5000)  # Wait 5 seconds for verification screen
            # Check for verification code input
            if page.is_visible('input[name="pin"]', timeout=2000):
                logging.info("Verification code screen detected. Fetching code from email...")
                code = get_latest_verification_code()
                if code:
                    page.fill('input[name="pin"]', code)
                    page.click('button[type="submit"]')
                    logging.info("Verification code submitted.")
                else:
                    logging.error("No verification code found in email.")
    except Exception:
        pass
    if not SESSION_FILE.exists():
        logging.info("Filling login form...")
        page.fill('input[name="session_key"]', EMAIL)
        page.fill('input[name="session_password"]', PASSWORD)
        page.click('button[type="submit"]')
        try:
            page.wait_for_selector('input[role="combobox"]', timeout=10000)
            logging.info("Login successful. Saving session.")
            save_session(context)
            logging.info(f"Session saved to {SESSION_FILE}")
        except Exception:
            logging.error("Login failed or took too long.")
            # Save screenshot and HTML for debugging
            screenshot_path = "linkedin_login_failure.png"
            html_path = "linkedin_login_failure.html"
            try:
                page.screenshot(path=screenshot_path)
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page.content())
                logging.error(f"Saved screenshot to {screenshot_path} and HTML to {html_path}")
            except Exception as e:
                logging.error(f"Failed to save screenshot or HTML: {e}")
            browser.close()
            playwright.stop()
            exit(1)
    else:
        logging.info("Session loaded, should be logged in.")
    return browser, page

def main() -> None:
    logging.info("Job alert script started.")
    browser, page = open_linkedin()
    for key in ("IL", "NL"):
        location, geoid, remote = SEARCHES[key][2], SEARCHES[key][0], SEARCHES[key][1]
        scrape_jobs(page, browser, location, geoid, remote)
    # logging.info("All locations processed. Waiting for user to close browser...")
    # input("Press Enter to close the browser...")
    # browser.close()
    logging.info("Browser closed. Script finished.")

if __name__ == "__main__":
	main()
