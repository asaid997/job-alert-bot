# UK Obstetrics & Gynaecology Job Alerts

Searches LinkedIn across the **whole United Kingdom** for O&G doctor vacancies,
including Trust Doctor, SHO, Junior/Clinical Fellow, Locally Employed Doctor and
registrar roles accepting **ST1, ST2 or ST3**, with advertised minimum experience
within **0–5 years**. Both `gynaecology` and `gynecology` searches are included.

## Matching rules

- Accept SHO and ST1–ST3 entry levels, including ST3+ and ranges starting at ST3.
  Senior House Officer and Senior Clinical Fellow at ST3 are not rejected for
  containing “senior”. Explicit ST4+ entry levels, consultants, Specialist Grade
  and non-doctor roles are excluded.
- ICU/intensive-care, orthodontics/dental and psychiatry posts are excluded
  when identified in the title, even when the hospital description mentions O&G.
  General Safety Officer and Safety Evaluation Physician roles are also excluded.
- Every reported job needs O&G evidence in its title or role description.
  Generic titles such as "Speciality Doctor" are checked by fetching the advert;
  if the specialty cannot be confirmed, they are excluded. An employer name,
  search keyword or general hospital list of services does not establish O&G.
- Senior clinical fellow/registrar posts need a confirmed SHO/ST1–ST3 grade
  before appearing in alerts. Their details are checked first; an unavailable
  description or unclear grade does not qualify a senior post for an alert.
  Mandatory higher-grade criteria, such as a satisfactory ST5 ARCP, override
  a lower grade in the title. Colleagues' grades and desirable criteria do not.
- Read the advert description before checking experience. Explicit required
  minima above five years are excluded; months and written numbers are recognised.
  Ranges use their lower bound, so a role accepting 3–7 years remains eligible.
- Other O&G roles with missing/ambiguous grades or unspecified/only desirable
  experience stay in the job list for manual checking. An unavailable description
  can only pass this check if the title itself identifies O&G. Specialty Doctor
  posts in O&G without a stated equivalent grade also need checking.
  Rejected jobs are not listed in Telegram alerts.
- Experience requirements are checked individually, not added together. A minimum
  of four postgraduate years including two in O&G is not treated as six years.
- These are search matches, not confirmation of eligibility. Read the full person
  specification, including GMC registration, exams, clinical competencies,
  previous NHS experience and sponsorship. ANIOS does not map automatically to a
  UK training grade. The parser is conservative and cannot interpret every advert.

## Running

```sh
python3 -m venv .venv
.venv/bin/pip install playwright==1.44.0 playwright_stealth==2.0.3
.venv/bin/python -m playwright install chromium
.venv/bin/python linkedin_open.py
```

Set `TELEGRAM_BOT_API` and `TELEGRAM_CHAT_ID` to enable delivery. Multiple chat IDs
can be comma-separated. With these unset, scraping runs without sending messages.
No LinkedIn login credentials are used by the current public-page scraper.

Alerts start with a minimal **Hephaestus Job Forge** headline, the report run
date/time in UTC and the number of jobs found. One numbered list
shows clickable job titles, hospitals and locations with emojis, followed by one
random Hephaestus quote. There are no sections or match explanations. Long lists
continue in another message only when needed for Telegram's size limit, with the
quote at the very end; empty runs stay silent.

The GitHub Actions workflow runs every three hours from 06:00 through midnight:
**06:00, 09:00, 12:00, 15:00, 18:00, 21:00 and 00:00 UTC** year-round. There is no
03:00 run or summer/winter adjustment. It can also be dispatched manually. Each run searches the **last six
hours only**. Job IDs are retained for 48 non-empty runs in a separate UK O&G
cache so the previous chemistry searches do not suppress medical vacancies.

To scan existing postings locally without a posting-date cutoff:

```sh
LINKEDIN_TIME_RANGE='' .venv/bin/python linkedin_scraper.py
```

`linkedin_scraper.py` prints and caches results; `linkedin_open.py` additionally
sends alerts. Use the latter for the normal scheduled workflow. A scraper-only run
marks results seen, so use a separate cache if you want those results sent later.

## Configuration and checks

- Searches/location: `SEARCHES` in `linkedin_scraper.py`. UK geo ID `101165590`
  covers England, Scotland, Wales and Northern Ireland; no city-radius filter.
- Grade/experience rules: `job_filters.py`.
- Posting window: `LINKEDIN_TIME_RANGE` (`r21600` = 6 hours; empty = all dates).
- Alert wording: `messages.py`.
- Schedule/environment: `.github/workflows/job-alert.yml`.

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests use synthetic adverts and mocked detail pages, without sending messages.
LinkedIn may restrict public-page access; roles with missing detail pages are
only kept for review when their titles establish O&G and the senior-grade rules
allow it. NHS Jobs/Trac integrations are not implemented.

Never commit credentials or local secret files.

## License

MIT
