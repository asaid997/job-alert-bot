# Getting Started Checklist

Follow this checklist to get your LinkedIn job alert bot up and running in under 15 minutes!

## ✅ Step-by-Step Setup

### Phase 1: Repository Setup (2 minutes)
- [ ] Fork this repository to your GitHub account
- [ ] Clone the repository to your local machine (optional, for testing)

### Phase 2: Telegram Bot Setup (5 minutes)
- [ ] Open Telegram and search for [@BotFather](https://t.me/botfather)
- [ ] Send `/newbot` to BotFather
- [ ] Choose a name for your bot (e.g., "My Job Alert Bot")
- [ ] Choose a username (e.g., "my_job_alert_bot")
- [ ] Copy and save the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
- [ ] Start a chat with your new bot (click the link BotFather provides)
- [ ] Send `/start` to your bot
- [ ] Get your chat ID by visiting: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
- [ ] Look for `"chat":{"id":` in the response and copy the number

### Phase 3: GitHub Secrets Configuration (3 minutes)
- [ ] Go to your forked repository on GitHub
- [ ] Click **Settings** → **Secrets and variables** → **Actions**
- [ ] Click **New repository secret** and add each of these:

| Secret Name | Value |
|-------------|--------|
| `TELEGRAM_BOT_API` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID number |
| `LINKEDIN_EMAIL` | Your LinkedIn email |
| `LINKEDIN_PASSWORD` | Your LinkedIn password |

### Phase 4: Enable Automation (2 minutes)
- [ ] Go to the **Actions** tab in your repository
- [ ] Click "I understand my workflows and want to enable them"
- [ ] Edit `.github/workflows/job-alert.yml`
- [ ] Uncomment the schedule lines (remove the `#`):
  ```yaml
  schedule:
    - cron: '*/10 * * * *'  # Runs every 10 minutes
  ```
- [ ] Commit the changes

### Phase 5: Test Your Setup (3 minutes)
- [ ] Go to **Actions** tab
- [ ] Click on "LinkedIn DevOps Job Alert" workflow
- [ ] Click **Run workflow** button (green button on the right)
- [ ] Wait for the workflow to complete (should take 1-2 minutes)
- [ ] Check your Telegram for job alert messages! 🎉

## 🎯 Success Indicators

After completing the setup, you should see:
- ✅ Green checkmark on your workflow run
- ✅ Messages in your Telegram chat with job listings
- ✅ Emoji-formatted job alerts with company names and links

## 🚨 Troubleshooting Quick Fixes

### No Telegram Messages?
1. Check if your bot token and chat ID are correct
2. Make sure you sent `/start` to your bot
3. Verify the secrets are spelled exactly right (case-sensitive)

### Workflow Failing?
1. Click on the failed workflow to see error details
2. Common issue: LinkedIn login problems (check credentials)
3. Try running the workflow again (sometimes it's temporary)

### No Jobs Found?
1. This is normal if there are no new jobs in the time range
2. The bot only shows jobs posted in the last 48 hours by default
3. Try changing locations or keywords (see [EXAMPLES.md](EXAMPLES.md))

## 🔄 What Happens Next?

Once set up successfully:
- Your bot will automatically run every 10 minutes
- You'll get Telegram notifications for new DevOps jobs in Israel and Netherlands
- The bot maintains a LinkedIn session to avoid repeated logins
- You can manually trigger runs anytime from the Actions tab

## 🎨 Ready to Customize?

Now that it's working, you might want to:
- **Change job types**: Edit keywords in `temp.py` (see [README.md](README.md))
- **Add locations**: Include more countries/cities  
- **Adjust frequency**: Change the cron schedule
- **Customize messages**: Modify the Telegram format

Check [EXAMPLES.md](EXAMPLES.md) for detailed customization examples!

---

**🎉 Congratulations!** You now have your own personal job alert system running automatically in the cloud!