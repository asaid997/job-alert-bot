# LinkedIn DevOps Job Alert Bot

This project automatically scrapes DevOps job postings from LinkedIn for multiple locations and sends them as formatted messages to a Telegram chat. It is designed to run on GitHub Actions every 10 minutes, using Playwright for browser automation.

## Features
- Scrapes DevOps jobs from LinkedIn for Israel and Netherlands
- Sends each job as a neat, emoji-rich Telegram message
- Caches LinkedIn session for faster, more reliable scraping
- Runs on a schedule (every 10 minutes) via GitHub Actions
- All secrets and credentials are managed via GitHub Actions secrets

## Setup

### 1. Fork or clone this repository

### 2. Set up GitHub Actions Secrets
Go to your repository Settings > Secrets and add the following:
- `TELEGRAM_BOT_API`: Your Telegram bot API token (from BotFather)
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (where messages will be sent)
- `LINKEDIN_EMAIL`: LinkedIn login email
- `LINKEDIN_PASSWORD`: LinkedIn login password

### 3. Workflow
The workflow is defined in `.github/workflows/job-alert.yml` and will:
- Run every 10 minutes (or on manual dispatch)
- Use a prebuilt Playwright Python Docker image for fast, reliable scraping
- Cache the LinkedIn session file and job results between runs

### 4. Customization
- To change locations, edit the `SEARCHES` dictionary in `temp.py`.
- To change the search keyword, edit the `build_jobs_url` function in `temp.py`.
- To adjust the schedule, edit the `cron` value in the workflow YAML.

## Local Development
1. Install Python 3.11+
2. Install dependencies:
   ```sh
   pip install playwright requests
   playwright install chromium
   ```
3. Set environment variables (see above)
4. Run the script:
   ```sh
   python temp.py
   ```

## Security
- Never commit your secrets to the repository. Always use GitHub Actions secrets.
- The script uses environment variables for all sensitive data.

## License
MIT
