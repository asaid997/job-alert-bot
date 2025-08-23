# LinkedIn DevOps Job Alert Bot

This project automatically scrapes DevOps job postings from LinkedIn for multiple locations and sends them as formatted messages to a Telegram chat. It is designed to run on GitHub Actions every 10 minutes, using Playwright for browser automation.

## 📋 Quick Reference

| What You Can Do | How to Do It | File to Edit |
|----------------|--------------|--------------|
| Change job keywords (e.g., "Software Engineer") | Modify `keywords=` parameter | `temp.py` → `build_jobs_url()` |
| Add new countries/cities | Add geo ID to SEARCHES | `temp.py` → `SEARCHES` dict |
| Change frequency (every hour, daily, etc.) | Update cron schedule | `.github/workflows/job-alert.yml` |
| Modify time range (24h, week, etc.) | Change TIME_RANGE value | `temp.py` → `TIME_RANGE` |
| Customize message format | Edit Telegram formatting | `temp.py` → `format_job_for_telegram()` |
| Run locally for testing | Set env vars and run script | Command line |

**📚 Need detailed examples?** Check [EXAMPLES.md](EXAMPLES.md) for step-by-step configurations.
**🚀 New user?** Follow the [GETTING_STARTED.md](GETTING_STARTED.md) checklist for a 15-minute setup!

## What Can You Do With This Bot?

### 🎯 **Core Capabilities**
- **Automated Job Scraping**: Continuously monitors LinkedIn for DevOps engineer positions
- **Multi-Location Support**: Currently configured for Israel and Netherlands (easily customizable)
- **Telegram Integration**: Sends beautifully formatted job alerts with emojis directly to your Telegram
- **Smart Caching**: Maintains LinkedIn session between runs for reliability
- **Scheduled Execution**: Runs automatically every 10 minutes via GitHub Actions
- **Manual Triggers**: Can be triggered manually through GitHub Actions interface

### 🔧 **Customization Options**

> 💡 **See [EXAMPLES.md](EXAMPLES.md) for detailed configuration examples and more geo IDs**

#### **1. Change Job Search Keywords**
Edit the `build_jobs_url` function in `temp.py` to search for different roles:
```python
# Current: searches for "devops engineer"
f"https://www.linkedin.com/jobs/search/?keywords=devops%20engineer"

# Examples of what you can change it to:
# f"https://www.linkedin.com/jobs/search/?keywords=software%20engineer"
# f"https://www.linkedin.com/jobs/search/?keywords=data%20scientist"
# f"https://www.linkedin.com/jobs/search/?keywords=product%20manager"
```

#### **2. Add/Modify Search Locations**
Update the `SEARCHES` dictionary in `temp.py`:
```python
SEARCHES = {
    "NL": ["102890719", "3", "Netherlands"],    # Netherlands
    "IL": ["101620260", "2", "Israel"],         # Israel
    # Add more locations:
    # "US": ["103644278", "2", "United States"],
    # "UK": ["101165590", "2", "United Kingdom"],
    # "DE": ["101282230", "2", "Germany"],
}
```

#### **3. Adjust Time Range for Job Postings**
Modify `TIME_RANGE` in `temp.py`:
```python
TIME_RANGE = "r172800"   # Last 48 hours (current)
# TIME_RANGE = "r86400"  # Last 24 hours
# TIME_RANGE = "r604800" # Last week
```

#### **4. Change Execution Schedule**
Edit the cron expression in `.github/workflows/job-alert.yml`:
```yaml
schedule:
  - cron: '*/10 * * * *'  # Every 10 minutes (current)
  # - cron: '0 */2 * * *'  # Every 2 hours
  # - cron: '0 9 * * 1-5'  # 9 AM on weekdays only
```

### 🚀 **Deployment Options**

#### **Option 1: GitHub Actions (Recommended)**
- **Zero maintenance**: Runs automatically in the cloud
- **Free tier friendly**: Uses GitHub's free Actions minutes
- **Secure**: All credentials stored as GitHub secrets
- **Reliable**: Built-in retry mechanisms and error handling

#### **Option 2: Local Development/Testing**
- **Quick testing**: Run locally while customizing
- **Development**: Test changes before deploying
- **One-time runs**: Get immediate job alerts

### 📱 **What You'll Receive**
Each job alert includes:
- 📋 **Job Title** (clickable link to LinkedIn)
- 🏢 **Company Name**
- 📍 **Location** with country indicator
- 🕐 **Timestamp** of when the job was found
- Beautiful emoji formatting for easy reading

### 🛠 **Advanced Customizations**

#### **Message Formatting**
Customize the `format_job_for_telegram` function to change how jobs appear:
- Add salary information (if available)
- Include job description snippets
- Change emoji styles
- Modify message layout

#### **Filtering Options**
Add custom filters in the `scrape_jobs` function:
- Filter by company size
- Exclude specific companies
- Filter by experience level
- Include only remote/hybrid positions

#### **Multiple Telegram Destinations**
- Send to multiple chat groups
- Create different alerts for different roles
- Separate alerts by location

## Features
- Scrapes DevOps jobs from LinkedIn for Israel and Netherlands
- Sends each job as a neat, emoji-rich Telegram message
- Caches LinkedIn session for faster, more reliable scraping
- Runs on a schedule (every 10 minutes) via GitHub Actions
- All secrets and credentials are managed via GitHub Actions secrets

## Quick Start Guide

### 1. Fork or Clone Repository
```bash
git clone https://github.com/asaid997/job-alert-bot.git
cd job-alert-bot
```

### 2. Set Up Telegram Bot
1. **Create a Bot**: Message [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot`
   - Choose a name and username for your bot
   - Save the API token you receive

2. **Get Your Chat ID**:
   - Start a chat with your new bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":` in the response
   - Or message [@userinfobot](https://t.me/userinfobot) to get your chat ID

### 3. Configure GitHub Secrets
Go to your repository **Settings > Secrets and variables > Actions** and add:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `TELEGRAM_BOT_API` | Bot token from BotFather | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | `123456789` |
| `LINKEDIN_EMAIL` | Your LinkedIn login email | `your.email@gmail.com` |
| `LINKEDIN_PASSWORD` | Your LinkedIn password | `your_secure_password` |

### 4. Enable the Workflow
1. Go to **Actions** tab in your repository
2. Click "I understand my workflows and want to enable them"
3. Find "LinkedIn DevOps Job Alert" workflow
4. Click "Enable workflow"
5. Uncomment the schedule in `.github/workflows/job-alert.yml`:
   ```yaml
   schedule:
     - cron: '*/10 * * * *'  # Runs every 10 minutes
   ```

### 5. Test Your Setup
- Go to **Actions** tab
- Click "LinkedIn DevOps Job Alert"
- Click "Run workflow" button
- Monitor the run and check your Telegram for messages

## Local Development & Testing

### Requirements
- Python 3.11+
- LinkedIn account
- Telegram bot token

### Setup Steps
1. **Install Dependencies**:
   ```bash
   pip install playwright requests
   playwright install chromium
   ```

2. **Set Environment Variables**:
   ```bash
   export TELEGRAM_BOT_API="your_bot_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   export LINKEDIN_EMAIL="your_email"
   export LINKEDIN_PASSWORD="your_password"
   ```

3. **Run the Script**:
   ```bash
   python temp.py
   ```

### Development Tips
- Set `HEADLESS = False` in `temp.py` to see the browser in action
- Check `playwright-videos/` folder for recorded sessions
- Monitor logs for debugging information
- Use `linkedin_session.json` to avoid repeated logins

## Troubleshooting

### Common Issues

#### ❌ "No jobs found" or Empty Results
**Possible Causes:**
- LinkedIn changed their page structure
- Network connectivity issues
- Rate limiting by LinkedIn

**Solutions:**
1. Check if you can manually access LinkedIn job search
2. Verify the search URLs are working
3. Wait a few hours and try again (rate limiting)
4. Check GitHub Actions logs for detailed error messages

#### ❌ LinkedIn Login Failures
**Possible Causes:**
- Incorrect credentials
- Two-factor authentication enabled
- LinkedIn security restrictions

**Solutions:**
1. Verify credentials in GitHub secrets
2. Temporarily disable 2FA for the account
3. Check for "Login attempt" emails from LinkedIn
4. Use an app-specific password if available

#### ❌ Telegram Messages Not Sent
**Possible Causes:**
- Incorrect bot token or chat ID
- Bot not started by the user
- Network issues

**Solutions:**
1. Test bot manually by sending `/start` to your bot
2. Verify bot token and chat ID are correct
3. Check if the bot is blocked or deleted

#### ❌ GitHub Actions Failures
**Common Error Messages:**
- `Error: Process completed with exit code 1`: Check logs for specific Python errors
- `Login failed or took too long`: LinkedIn login issues
- `Failed to send Telegram message`: Telegram configuration problems

**Solutions:**
1. Check the Actions logs for detailed error messages
2. Look for debug artifacts (screenshots, HTML dumps)
3. Verify all secrets are properly set
4. Try running the workflow manually first

### Getting Help
1. **Check Logs**: Always examine GitHub Actions logs first
2. **Debug Artifacts**: Download screenshots and HTML dumps when login fails
3. **Test Locally**: Run the script locally to isolate issues
4. **Monitor Rate Limits**: LinkedIn may temporarily block frequent requests

## FAQ

### Q: How often does the bot check for jobs?
A: By default, every 10 minutes. You can adjust this in the workflow YAML file.

### Q: Can I add more countries/locations?
A: Yes! Find the LinkedIn geo ID for your desired location and add it to the `SEARCHES` dictionary.

### Q: Will this work with other job titles?
A: Absolutely! Modify the `keywords` parameter in the `build_jobs_url` function.

### Q: Is my LinkedIn account safe?
A: The bot uses legitimate browser automation. However, excessive usage might trigger LinkedIn's anti-bot measures.

### Q: Can I send alerts to multiple Telegram chats?
A: Yes, but you'll need to modify the code to support multiple chat IDs.

### Q: How do I find geo IDs for new locations?
A: Visit LinkedIn jobs, search for your location, and extract the `geoId` parameter from the URL.

### Q: What if LinkedIn blocks my account?
A: Use the account sparingly, respect rate limits, and avoid running the bot too frequently.

## Security Best Practices
## Security Best Practices

### 🔐 **Credential Management**
- **Never commit secrets**: Always use GitHub Actions secrets for sensitive data
- **Use environment variables**: The script reads all credentials from environment variables
- **Rotate credentials**: Regularly update your LinkedIn password and bot tokens
- **Dedicated account**: Consider using a separate LinkedIn account for automation

### 🛡️ **Account Safety**
- **Respect rate limits**: Don't run the bot too frequently to avoid LinkedIn restrictions
- **Monitor usage**: Keep an eye on GitHub Actions usage to stay within free tier limits
- **Regular maintenance**: Update dependencies and monitor for LinkedIn changes

### 🔒 **Privacy Considerations**
- **Public repositories**: Be extra careful with secrets in public repos
- **Telegram security**: Ensure your bot token is kept secure
- **Data handling**: The bot doesn't store job data permanently (privacy-friendly)

## Contributing

### Ways to Improve This Bot
- **Add new job sites**: Extend beyond LinkedIn (Indeed, Glassdoor, etc.)
- **Better filtering**: Add company size, salary range, experience level filters
- **Enhanced formatting**: Improve Telegram message appearance
- **Database integration**: Store and track job applications
- **Email alerts**: Add email notification option
- **Web interface**: Build a simple web dashboard

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Test changes locally
4. Submit a pull request
5. Ensure all tests pass

## Technical Architecture

### Components
- **Playwright**: Browser automation for LinkedIn scraping
- **Telegram Bot API**: Message delivery system
- **GitHub Actions**: Serverless execution environment
- **Session Caching**: Maintains login state between runs

### Data Flow
1. GitHub Actions triggers the workflow
2. Script loads cached LinkedIn session (if available)
3. Navigates to LinkedIn job search pages
4. Extracts job information using CSS selectors
5. Formats jobs into Telegram messages
6. Sends alerts via Telegram Bot API
7. Caches session for next run

## License

MIT License - Feel free to use, modify, and distribute this project.

---

## 🚀 Ready to Get Started?

1. **Fork this repository**
2. **Set up your Telegram bot** (5 minutes)
3. **Configure GitHub secrets** (5 minutes)
4. **Run your first job alert** (instantly!)

**Need help?** Check the troubleshooting section or create an issue in this repository.
