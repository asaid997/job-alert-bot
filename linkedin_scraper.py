import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from playwright_stealth import Stealth

SEARCHES = {
    "NL": {
        "geo_id": "102890719",
        "region": "Netherlands",
        "titles": [
            "chemical engineering internship",
            "chemical engineer intern",
            "junior chemical engineer",
            "entry level chemical engineer",
            "graduate chemical engineer",
            "junior process engineer",
            "process engineer intern",
            "formulation engineer",
            "quality engineer chemical",
            "lab technician chemistry",
        ],
    }
}

# LinkedIn time range: r10800 = last 3 hours, r43200 = last 12 hours.
TIME_RANGE = os.environ.get("LINKEDIN_TIME_RANGE", "r10800").strip()

DOMAIN_TERMS = [
    "chemical",
    "chemistry",
    "chemist",
    "process",
    "formulation",
    "materials",
    "material science",
    "polymer",
    "pharma",
    "pharmaceutical",
    "biotech",
    "laboratory",
    "lab",
    "quality",
    "quality assurance",
    "quality control",
    "qa",
    "qc",
    "r&d",
    "research and development",
    "manufacturing",
    "production",
    "water treatment",
    "food technology",
    "environmental",
    "petrochemical",
]

LEVEL_TERMS = [
    "intern",
    "internship",
    "trainee",
    "traineeship",
    "graduate",
    "junior",
    "entry level",
    "associate",
    "student",
    "thesis",
    "starter",
    "stage",
    "afstudeer",
    "werkstudent",
]

REJECT_TITLE_TERMS = [
    "senior",
    "sr.",
    "lead",
    "principal",
    "staff",
    "manager",
    "director",
    "head of",
    "software",
    "frontend",
    "backend",
    "full stack",
    "data engineer",
    "data scientist",
    "devops",
    "site reliability",
    "platform engineer",
    "support engineer",
    "technical support",
    "customer support",
    "maintenance engineer",
    "sales",
    "account manager",
    "business analyst",
    "mechanical engineer",
    "electrical engineer",
    "civil engineer",
]

LINKEDIN_PAGE_RETRIES = 8
LINKEDIN_RETRY_DELAY_MS = 5000
JOBS_CACHE_FILE = Path("jobs-cache/last_jobs.json")
JOBS_CACHE_RUNS = 5
JOBS_TO_FILTER_FILE = Path("jobs_to_filter.json")
VIDEO_DIR = os.environ.get("LINKEDIN_VIDEO_DIR", "playwright-videos")


def build_jobs_url(job_title, geo_id, remotes):
    url = (
        "https://www.linkedin.com/jobs/search/"
        f"?distance=25"
        f"&f_TPR={TIME_RANGE}"
        f"&geoId={geo_id}"
        f"&keywords={quote_plus(job_title)}"
    )
    if remotes:
        url += f"&f_WT={remotes}"
    return url


def make_search_links():
    links = []

    for _key, search in SEARCHES.items():
        for title in search["titles"]:
            links.append(
                {
                    "region": search["region"],
                    "title": title,
                    "url": build_jobs_url(title, search["geo_id"], search.get("remotes")),
                }
            )

    return links


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


def extract_cached_job_id(url):
    match = re.search(r"/jobs/view/[^/-]*-?(\d+)", url or "")
    if match:
        return match.group(1)

    path = urlparse(url or "").path
    fallback = re.search(r"(\d{7,})", path)
    if fallback:
        return fallback.group(1)

    return url or ""


def flatten_job_ids(jobs_runs):
    seen = set()
    for run in jobs_runs:
        for job_id in run:
            seen.add(job_id)
    return seen


def cached_job_id(job):
    if job.get("job_id"):
        return str(job["job_id"])

    job_id = extract_cached_job_id(job.get("url"))
    if job_id:
        return job_id

    return job_identity(job)


def filter_uncached_jobs(accepted, rejected, notified_job_ids, this_run_job_ids):
    new_accepted = []
    new_rejected = []
    skipped_count = 0

    for source, target in ((accepted, new_accepted), (rejected, new_rejected)):
        for job in source:
            job_id = cached_job_id(job)
            if job_id not in notified_job_ids and job_id not in this_run_job_ids:
                target.append(job)
            else:
                skipped_count += 1
                print(
                    "Skipped already cached job: "
                    f"{job.get('title') or 'Unknown title'} ({job_id})"
                )

            this_run_job_ids.append(job_id)

    if skipped_count:
        print(f"Cache skipped {skipped_count} already-seen jobs for this search.")

    return new_accepted, new_rejected


def save_this_run_to_cache(jobs_runs, this_run_job_ids):
    print(f"[CACHE] jobs_runs before update: {jobs_runs}")
    print(f"[CACHE] this_run_job_ids before dedup: {this_run_job_ids}")

    seen = set()
    deduped_this_run_job_ids = []
    for job_id in this_run_job_ids:
        if job_id not in seen:
            deduped_this_run_job_ids.append(job_id)
            seen.add(job_id)

    if deduped_this_run_job_ids:
        jobs_runs.append(deduped_this_run_job_ids)
        if len(jobs_runs) > JOBS_CACHE_RUNS:
            jobs_runs = jobs_runs[-JOBS_CACHE_RUNS:]
        save_cached_jobs(jobs_runs)

    print(f"[CACHE] jobs_runs after update: {jobs_runs}")
    print(f"[CACHE] this_run_job_ids after dedup: {deduped_this_run_job_ids}")
    return jobs_runs


def write_jobs_to_filter_file(jobs):
    payload = []
    for job in jobs:
        payload.append(
            {
                "job": {
                    "title": job.get("title") or "",
                    "company": job.get("company") or "",
                    "location": job.get("location") or "",
                    "url": job.get("url") or "",
                },
                "location": job.get("search_region") or job.get("location") or "",
            }
        )

    with open(JOBS_TO_FILTER_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(payload)} new jobs to {JOBS_TO_FILTER_FILE}.")


def close_linkedin_sign_in_modal(page):
    page.wait_for_timeout(1000)

    dismiss_selectors = [
        'button[aria-label="Dismiss"]',
        'button[aria-label="Close"]',
        "#base-contextual-sign-in-modal button.modal__dismiss",
        ".contextual-sign-in-modal button.modal__dismiss",
        ".modal__dismiss",
    ]

    for selector in dismiss_selectors:
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=1000):
                button.click(timeout=1000)
                page.wait_for_timeout(500)
                return
        except Exception:
            pass

    page.evaluate(
        """
        () => {
            const selectors = [
                '#base-contextual-sign-in-modal',
                '.contextual-sign-in-modal',
                '.modal__overlay',
                '.modal-overlay',
                '[data-tracking-control-name="public_jobs_contextual-sign-in-modal_modal"]'
            ];

            for (const selector of selectors) {
                document.querySelectorAll(selector).forEach((node) => node.remove());
            }

            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }
        """
    )


def get_left_jobs_panel_state(page):
    return page.evaluate(
        """
        () => {
            const jobSelectors = [
                'main#main-content.two-pane-serp-page__results',
                'main.two-pane-serp-page__results',
                '.two-pane-serp-page__results-list',
                '.jobs-search-results-list',
                '.jobs-search-results__list',
                '.jobs-search-results-list__list',
                'ul.jobs-search__results-list',
                '.scaffold-layout__list',
                '[data-results-list-top-scroll-sentinel]'
            ];

            let list = null;
            for (const selector of jobSelectors) {
                list = document.querySelector(selector);
                if (list) {
                    break;
                }
            }

            if (!list) {
                const cards = [...document.querySelectorAll('li, .base-card, .job-card-container')];
                list = cards.find((card) => {
                    const rect = card.getBoundingClientRect();
                    return rect.width > 100 && rect.left < window.innerWidth * 0.55;
                });
            }

            if (!list) {
                return { found: false, scrollHeight: 0, jobCount: 0 };
            }

            let panel = document.querySelector('main#main-content.two-pane-serp-page__results')
                || document.querySelector('main.two-pane-serp-page__results')
                || document.querySelector('.two-pane-serp-page__results-list')
                || list;
            while (panel && panel !== document.body && panel !== document.documentElement) {
                const style = window.getComputedStyle(panel);
                const canScroll = panel.scrollHeight > panel.clientHeight + 10;
                const overflowAllowsScroll = ['auto', 'scroll', 'overlay', 'visible'].includes(style.overflowY);

                if (canScroll && overflowAllowsScroll && panel.getBoundingClientRect().left < window.innerWidth * 0.65) {
                    break;
                }

                panel = panel.parentElement;
            }

            if (!panel || panel === document.body || panel === document.documentElement) {
                panel = list.scrollHeight > list.clientHeight + 10
                    ? list
                    : list.closest('main, section, div') || list;
            }

            const jobCount = document.querySelectorAll(
                'li .base-card, li .job-card-container, li.jobs-search-results__list-item, ul.jobs-search__results-list > li'
            ).length;
            const panelRect = panel.getBoundingClientRect();
            const listRect = list.getBoundingClientRect();
            const mouseRect = listRect.width > 0 && listRect.height > 0 ? listRect : panelRect;
            const scrollingElement = document.scrollingElement || document.documentElement;

            return {
                found: true,
                scrollTop: panel.scrollTop,
                scrollHeight: panel.scrollHeight,
                clientHeight: panel.clientHeight,
                windowY: window.scrollY,
                documentHeight: scrollingElement.scrollHeight,
                atBottom: panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 5,
                windowAtBottom: window.scrollY + window.innerHeight >= scrollingElement.scrollHeight - 5,
                jobCount,
                mouseX: Math.min(Math.max(mouseRect.left + mouseRect.width / 2, 5), window.innerWidth - 5),
                mouseY: Math.min(Math.max(mouseRect.top + Math.min(mouseRect.height / 2, window.innerHeight * 0.65), 5), window.innerHeight - 5),
                targetClass: panel.className || panel.tagName
            };
        }
        """
    )


def force_scroll_left_jobs_panel(page):
    return page.evaluate(
        """
        () => {
            const jobSelectors = [
                'main#main-content.two-pane-serp-page__results',
                'main.two-pane-serp-page__results',
                '.two-pane-serp-page__results-list',
                '.jobs-search-results-list',
                '.jobs-search-results__list',
                '.jobs-search-results-list__list',
                'ul.jobs-search__results-list',
                '.scaffold-layout__list',
                '.scaffold-layout__list-container',
                '[data-results-list-top-scroll-sentinel]'
            ];

            let list = null;
            for (const selector of jobSelectors) {
                list = document.querySelector(selector);
                if (list) {
                    break;
                }
            }

            if (!list) {
                const cards = [...document.querySelectorAll('li, .base-card, .job-card-container')];
                list = cards.find((card) => {
                    const rect = card.getBoundingClientRect();
                    return rect.width > 100 && rect.left < window.innerWidth * 0.55;
                });
            }

            const scrollingElement = document.scrollingElement || document.documentElement;
            let panel = document.querySelector('main#main-content.two-pane-serp-page__results')
                || document.querySelector('main.two-pane-serp-page__results')
                || document.querySelector('.two-pane-serp-page__results-list')
                || scrollingElement;

            if (list && (!panel || panel === scrollingElement)) {
                let node = list;
                while (node && node !== document.body && node !== document.documentElement) {
                    const rect = node.getBoundingClientRect();
                    const leftSide = rect.left < window.innerWidth * 0.65 && rect.width > 100;
                    const canScroll = node.scrollHeight > node.clientHeight + 10;

                    if (leftSide && canScroll) {
                        panel = node;
                        break;
                    }

                    node = node.parentElement;
                }
            }

            const beforeTop = panel === scrollingElement ? window.scrollY : panel.scrollTop;
            const scrollAmount = Math.max(window.innerHeight * 0.85, 900);

            if (panel === scrollingElement) {
                window.scrollBy(0, scrollAmount);
            } else {
                panel.scrollBy(0, scrollAmount);
                panel.dispatchEvent(new Event('scroll', { bubbles: true }));
            }

            const afterTop = panel === scrollingElement ? window.scrollY : panel.scrollTop;
            if (afterTop === beforeTop) {
                const cards = [...document.querySelectorAll(
                    'main#main-content li, main.two-pane-serp-page__results li, .two-pane-serp-page__results-list li'
                )];
                const lastCard = cards[cards.length - 1];
                if (lastCard) {
                    lastCard.scrollIntoView({ block: 'end', inline: 'nearest' });
                    return true;
                }
            }

            return afterTop !== beforeTop;
        }
        """
    )


def click_see_more_jobs(page):
    try:
        see_more_jobs = page.get_by_role("button", name="See more jobs", exact=True).first
        if see_more_jobs.is_visible(timeout=1000):
            see_more_jobs.scroll_into_view_if_needed(timeout=1000)
            see_more_jobs.click(timeout=1500)
            page.wait_for_timeout(3000)
            print("Clicked See more jobs.")
            return True
    except Exception:
        pass

    return False


def reached_all_jobs_message(page):
    try:
        message = page.locator(
            'p.inline-notification__text',
            has_text="You've viewed all jobs for this search",
        ).first
        if message.is_visible(timeout=1000):
            return True
    except Exception:
        pass

    try:
        return page.get_by_text(
            "You've viewed all jobs for this search",
            exact=True,
        ).is_visible(timeout=1000)
    except Exception:
        return False


def reached_no_results_message(page):
    try:
        body_text = page.locator("body").inner_text(timeout=1000)
    except Exception:
        return False

    normalized = re.sub(r"\s+", " ", body_text).strip().lower()
    return (
        "we couldn’t find a match" in normalized
        or "we couldn't find a match" in normalized
        or "please make sure your keywords are spelled correctly" in normalized
    )


def reached_auth_wall(page):
    current_url = page.url.lower()
    if "/authwall" in current_url:
        return True

    try:
        title = page.title().lower()
    except Exception:
        title = ""

    try:
        body_text = page.locator("body").inner_text(timeout=1000)
    except Exception:
        body_text = ""

    normalized = re.sub(r"\s+", " ", body_text).strip().lower()
    return (
        "sign up | linkedin" in title
        or (
            "join linkedin" in normalized
            and ("agree & join" in normalized or "already on linkedin" in normalized)
        )
    )


def search_results_ready(page):
    if reached_auth_wall(page):
        return False

    if reached_no_results_message(page) or reached_all_jobs_message(page):
        return True

    try:
        state = get_left_jobs_panel_state(page)
    except Exception:
        return False

    return bool(state.get("found") and state.get("jobCount", 0) > 0)


def open_search_with_retries(page, url):
    for attempt in range(1, LINKEDIN_PAGE_RETRIES + 1):
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        close_linkedin_sign_in_modal(page)

        if search_results_ready(page):
            return True

        reason = "auth wall" if reached_auth_wall(page) else "results not ready"
        print(
            f"LinkedIn returned {reason}; retrying original search URL "
            f"({attempt}/{LINKEDIN_PAGE_RETRIES})."
        )

        if attempt < LINKEDIN_PAGE_RETRIES:
            page.wait_for_timeout(LINKEDIN_RETRY_DELAY_MS)

    print("Could not load a real LinkedIn search result page after retries.")
    return False


def reached_terminal_search_state(page):
    if reached_all_jobs_message(page):
        print("Reached LinkedIn's end-of-results message.")
        return True

    if reached_no_results_message(page):
        print("LinkedIn says no matching jobs were found for this search.")
        return True

    return False


def load_all_jobs(page):
    stuck_scrolls = 0
    max_scrolls = 80

    for scroll_number in range(1, max_scrolls + 1):
        close_linkedin_sign_in_modal(page)
        if reached_terminal_search_state(page):
            return

        before = get_left_jobs_panel_state(page)
        if before.get("found"):
            page.mouse.move(before["mouseX"], before["mouseY"])
            page.mouse.wheel(0, 3000)
        page.wait_for_timeout(3000)
        close_linkedin_sign_in_modal(page)
        after = get_left_jobs_panel_state(page)

        if reached_terminal_search_state(page):
            return

        if click_see_more_jobs(page):
            close_linkedin_sign_in_modal(page)
            if reached_terminal_search_state(page):
                return
            stuck_scrolls = 0
            continue

        before_state = (
            before.get("scrollTop"),
            before.get("windowY"),
            before.get("scrollHeight"),
            before.get("documentHeight"),
            before.get("jobCount"),
        )
        after_state = (
            after.get("scrollTop"),
            after.get("windowY"),
            after.get("scrollHeight"),
            after.get("documentHeight"),
            after.get("jobCount"),
        )
        moved_or_loaded = after_state != before_state

        if not moved_or_loaded:
            force_scroll_left_jobs_panel(page)
            page.wait_for_timeout(3000)
            close_linkedin_sign_in_modal(page)
            after = get_left_jobs_panel_state(page)
            after_state = (
                after.get("scrollTop"),
                after.get("windowY"),
                after.get("scrollHeight"),
                after.get("documentHeight"),
                after.get("jobCount"),
            )
            moved_or_loaded = after_state != before_state

        print(
            f"Scroll {scroll_number}: panel top {after.get('scrollTop')}, "
            f"window y {after.get('windowY')}, jobs {after.get('jobCount')}, "
            f"target {after.get('targetClass')}"
        )

        if moved_or_loaded:
            stuck_scrolls = 0
        else:
            stuck_scrolls += 1
            if stuck_scrolls >= 4:
                print("No scroll movement, no new jobs, and no See more jobs button appeared.")
                return

    print("Stopped scrolling after max scroll limit.")


def scrape_loaded_jobs(page):
    return page.evaluate(
        """
        () => {
            const cleanText = (value) => (value || '').replace(/\\s+/g, ' ').trim();
            const jobIdFromValue = (value) => {
                const text = String(value || '');
                const patterns = [
                    /\\/jobs\\/view\\/(\\d+)/,
                    /currentJobId=(\\d+)/,
                    /jobPosting:(\\d+)/,
                    /\\/jobPosting\\/(\\d+)/,
                    /jobId=(\\d+)/,
                    /data-job-id=["']?(\\d+)/,
                    /data-occludable-job-id=["']?(\\d+)/
                ];

                for (const pattern of patterns) {
                    const match = text.match(pattern);
                    if (match) {
                        return match[1];
                    }
                }
                return '';
            };
            const firstText = (root, selectors) => {
                for (const selector of selectors) {
                    const node = root.querySelector(selector);
                    const text = cleanText(node ? node.textContent : '');
                    if (text) {
                        return text;
                    }
                }
                return '';
            };
            const firstHref = (root, selectors) => {
                for (const selector of selectors) {
                    const node = root.querySelector(selector);
                    const href = node ? node.getAttribute('href') : '';
                    if (href) {
                        return new URL(href, window.location.href).href;
                    }
                }
                return '';
            };
            const firstJobId = (root, url) => {
                const fromUrl = jobIdFromValue(url);
                if (fromUrl) {
                    return fromUrl;
                }

                const selectors = [
                    '[data-entity-urn]',
                    '[data-job-id]',
                    '[data-id]',
                    '[data-occludable-job-id]',
                    'a[href*="/jobs/view/"]'
                ];
                const nodes = [root, ...root.querySelectorAll(selectors.join(','))];
                const attrNames = [
                    'data-entity-urn',
                    'data-job-id',
                    'data-id',
                    'data-occludable-job-id',
                    'href'
                ];

                for (const node of nodes) {
                    for (const attrName of attrNames) {
                        const jobId = jobIdFromValue(node.getAttribute(attrName));
                        if (jobId) {
                            return jobId;
                        }
                    }

                    for (const attr of [...(node.attributes || [])]) {
                        const jobId = jobIdFromValue(attr.value);
                        if (jobId) {
                            return jobId;
                        }
                    }
                }

                return '';
            };

            const resultsRoot = document.querySelector('main#main-content.two-pane-serp-page__results')
                || document.querySelector('main.two-pane-serp-page__results')
                || document;

            const cards = [...resultsRoot.querySelectorAll(
                'div.job-search-card, div.base-search-card, li.jobs-search-results__list-item, div.job-card-container'
            )];

            const jobs = [];
            const seen = new Set();

            for (const card of cards) {
                const title = firstText(card, [
                    'h3.base-search-card__title',
                    '.base-search-card__title',
                    'a.base-card__full-link span.sr-only',
                    '.job-card-list__title',
                    '.job-card-container__link',
                    'a[href*="/jobs/view/"]'
                ]);
                const company = firstText(card, [
                    'h4.base-search-card__subtitle',
                    '.base-search-card__subtitle',
                    '.job-card-container__primary-description',
                    '.artdeco-entity-lockup__subtitle'
                ]);
                const location = firstText(card, [
                    'span.job-search-card__location',
                    '.job-search-card__location',
                    '.job-card-container__metadata-item',
                    '.artdeco-entity-lockup__caption'
                ]);
                const url = firstHref(card, [
                    'a.base-card__full-link',
                    'a[href*="/jobs/view/"]',
                    '.job-card-container__link'
                ]);
                const job_id = firstJobId(card, url);

                if (!title && !company && !location) {
                    continue;
                }

                const key = job_id ? `job:${job_id}` : (url || `${title}|${company}|${location}`);
                if (seen.has(key)) {
                    continue;
                }

                seen.add(key);
                jobs.push({ title, company, location, url, job_id });
            }

            return jobs;
        }
        """
    )


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip().lower()


def term_pattern(term):
    escaped = re.escape(term.lower())
    starts_word = term[0].isalnum()
    ends_word = term[-1].isalnum()
    prefix = r"(?<![a-z0-9])" if starts_word else ""
    suffix = r"(?![a-z0-9])" if ends_word else ""
    return prefix + escaped + suffix


def matching_terms(text, terms):
    return [term for term in terms if re.search(term_pattern(term), text)]


def classify_job(job):
    title = normalize_text(job.get("title"))
    company = normalize_text(job.get("company"))
    text = f"{title} {company}"

    reject_matches = matching_terms(title, REJECT_TITLE_TERMS)
    if reject_matches:
        return False, f"title reject terms: {', '.join(reject_matches)}"

    domain_matches = matching_terms(text, DOMAIN_TERMS)
    if not domain_matches:
        return False, "no chemical/process/lab/domain signal"

    level_matches = matching_terms(title, LEVEL_TERMS)
    if not level_matches:
        return False, "no internship/junior/entry-level signal"

    return True, (
        f"domain: {', '.join(domain_matches[:3])}; "
        f"level: {', '.join(level_matches[:3])}"
    )


def filter_jobs(jobs):
    accepted = []
    rejected = []

    for job in jobs:
        is_accepted, reason = classify_job(job)
        enriched = {**job, "filter_reason": reason}
        if is_accepted:
            accepted.append(enriched)
        else:
            rejected.append(enriched)

    return accepted, rejected


def print_job_list(jobs, heading):
    print(f"\n{heading} ({len(jobs)}):")
    if not jobs:
        print("  none")
        return

    for index, job in enumerate(jobs, start=1):
        print(f"{index}. {job.get('title') or 'Unknown title'}")
        print(f"   Company: {job.get('company') or 'Unknown company'}")
        print(f"   Location: {job.get('location') or 'Unknown location'}")
        if job.get("url"):
            print(f"   Link: {job.get('url')}")
        print(f"   Reason: {job.get('filter_reason')}")


def print_filtered_jobs(jobs, search_label):
    accepted, rejected = filter_jobs(jobs)
    print(f"\nScraped {len(jobs)} jobs for {search_label}.")
    print_job_list(accepted, "Accepted chemical junior/internship matches")
    print_job_list(rejected, "Rejected jobs for review")
    return accepted, rejected


def time_range_label():
    if not TIME_RANGE.startswith("r"):
        return TIME_RANGE

    try:
        seconds = int(TIME_RANGE[1:])
    except ValueError:
        return TIME_RANGE

    hours = seconds // 3600
    if hours >= 24 and hours % 24 == 0:
        days = hours // 24
        return f"last {days} day{'s' if days != 1 else ''}"
    if hours:
        return f"last {hours} hour{'s' if hours != 1 else ''}"

    minutes = seconds // 60
    return f"last {minutes} minute{'s' if minutes != 1 else ''}"


def linkedin_job_id_from_url(value):
    patterns = [
        r"/jobs/view/(\d+)",
        r"currentJobId=(\d+)",
        r"jobPosting:(\d+)",
        r"/jobPosting/(\d+)",
        r"jobId=(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, value or "")
        if match:
            return match.group(1)

    return ""


def job_identity(job):
    job_id = (job.get("job_id") or "").strip()
    if not job_id:
        job_id = linkedin_job_id_from_url(job.get("url"))
    if job_id:
        return f"job:{job_id}"

    url = (job.get("url") or "").strip()
    if url:
        return f"url:{url}"

    return "|".join(
        [
            (job.get("title") or "").strip().lower(),
            (job.get("company") or "").strip().lower(),
            (job.get("location") or "").strip().lower(),
        ]
    )


def add_search_context(job, link):
    return {
        **job,
        "search_region": link["region"],
        "search_title": link["title"],
        "search_url": link["url"],
    }


def add_unique_jobs(target, jobs, link, seen_jobs):
    for job in jobs:
        key = job_identity(job)
        if key in seen_jobs:
            continue

        seen_jobs.add(key)
        target.append(add_search_context(job, link))


def run_scrape():
    from playwright.sync_api import sync_playwright

    links = make_search_links()
    search_started_at = datetime.now()
    all_accepted = []
    all_rejected = []
    seen_jobs = set()
    total_scraped = 0
    jobs_runs = load_cached_jobs()
    notified_job_ids = flatten_job_ids(jobs_runs)
    this_run_job_ids = []

    print(f"[CACHE] Loaded {len(notified_job_ids)} cached job IDs.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Europe/Amsterdam",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1280, "height": 800},
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        Stealth().apply_stealth_sync(context)
        page = context.new_page()

        for index, link in enumerate(links, start=1):
            print(f"\n[{index}/{len(links)}] {link['region']} - {link['title']}")
            print(link["url"])
            if not open_search_with_retries(page, link["url"]):
                print("Skipped this search. Moving to next link.")
                continue

            load_all_jobs(page)
            jobs = scrape_loaded_jobs(page)
            total_scraped += len(jobs)
            accepted, rejected = print_filtered_jobs(jobs, f"{link['region']} - {link['title']}")
            new_accepted, new_rejected = filter_uncached_jobs(
                accepted,
                rejected,
                notified_job_ids,
                this_run_job_ids,
            )
            add_unique_jobs(all_accepted, new_accepted, link, seen_jobs)
            add_unique_jobs(all_rejected, new_rejected, link, seen_jobs)

            print("Loaded. Moving to next link.")

        context.close()
        browser.close()

    save_this_run_to_cache(jobs_runs, this_run_job_ids)
    write_jobs_to_filter_file(all_accepted + all_rejected)

    return {
        "accepted": all_accepted,
        "rejected": all_rejected,
        "links": links,
        "started_at": search_started_at,
        "total_scraped": total_scraped,
        "time_range_label": time_range_label(),
    }


def main():
    result = run_scrape()
    print(
        "\nAll searches finished. "
        f"Found {len(result['accepted'])} high-confidence and "
        f"{len(result['rejected'])} review jobs after cache filtering."
    )


if __name__ == "__main__":
    main()
