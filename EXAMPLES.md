# Configuration Examples

This file contains practical examples of how to customize the LinkedIn job alert bot for different scenarios.

## Example 1: Software Engineering Jobs in Multiple US Cities

```python
# Update SEARCHES in temp.py
SEARCHES = {
    "SF": ["90000084", "2", "San Francisco Bay Area"],
    "NYC": ["90000070", "2", "New York City"],
    "SEA": ["90000110", "2", "Seattle"],
    "LA": ["90000071", "2", "Los Angeles"]
}

# Update build_jobs_url function
def build_jobs_url(location, geo_id, remote):
    return (
        f"https://www.linkedin.com/jobs/search/?distance=25&f_TPR={TIME_RANGE}&f_WT={remote}&geoId={geo_id}&keywords=software%20engineer"
    )
```

## Example 2: Data Science Jobs with Broader Time Range

```python
# Update TIME_RANGE for weekly job posts
TIME_RANGE = "r604800"  # Last week

# Update search keyword
def build_jobs_url(location, geo_id, remote):
    return (
        f"https://www.linkedin.com/jobs/search/?distance=25&f_TPR={TIME_RANGE}&f_WT={remote}&geoId={geo_id}&keywords=data%20scientist"
    )
```

## Example 3: Remote-Only Product Manager Jobs

```python
# Focus on remote positions
SEARCHES = {
    "REMOTE_US": ["103644278", "2", "United States (Remote)"],
    "REMOTE_EU": ["100506914", "2", "Europe (Remote)"]
}

# Update for product manager roles
def build_jobs_url(location, geo_id, remote):
    return (
        f"https://www.linkedin.com/jobs/search/?distance=25&f_TPR={TIME_RANGE}&f_WT=2&geoId={geo_id}&keywords=product%20manager"
    )
```

## Example 4: Multiple Job Types in Same Location

```python
# Create different searches for different roles
SEARCHES = {
    "IL_DEV": ["101620260", "2", "Israel - DevOps"],
    "IL_DATA": ["101620260", "2", "Israel - Data Science"], 
    "IL_PM": ["101620260", "2", "Israel - Product Manager"]
}

# Then modify the main function to handle different keywords per search
def main():
    logging.info("Job alert script started.")
    browser, page = open_linkedin()
    
    # Define keywords for each search
    search_keywords = {
        "IL_DEV": "devops engineer",
        "IL_DATA": "data scientist", 
        "IL_PM": "product manager"
    }
    
    for key in SEARCHES.keys():
        location, geoid, remote = SEARCHES[key][2], SEARCHES[key][0], SEARCHES[key][1]
        keyword = search_keywords.get(key, "devops engineer")
        scrape_jobs(page, browser, location, geoid, remote, keyword)
```

## Example 5: Custom Telegram Message Format

```python
def format_job_for_telegram(job: dict, location: str, timestamp: str) -> str:
    """Enhanced format with more details"""
    return (
        f"🚀 **{job['title']}**\n"
        f"🏢 {job['company']}\n"
        f"📍 {job['location']} ({location})\n"
        f"💼 [Apply Here]({job['url']})\n"
        f"🕒 Found: {timestamp}\n"
        f"─────────────────────"
    )
```

## Example 6: Hourly Schedule (More Frequent Checks)

```yaml
# In .github/workflows/job-alert.yml
schedule:
  - cron: '0 * * * *'  # Every hour at minute 0
```

## Example 7: Business Hours Only Schedule

```yaml
# In .github/workflows/job-alert.yml
schedule:
  - cron: '0 9-17 * * 1-5'  # Every hour from 9 AM to 5 PM, Monday to Friday
```

## Common LinkedIn Geo IDs

Here are some popular location geo IDs you can use:

### United States
- `103644278` - United States (National)
- `90000084` - San Francisco Bay Area
- `90000070` - New York City Area
- `90000110` - Greater Seattle Area
- `90000071` - Greater Los Angeles Area
- `90000074` - Greater Boston Area
- `90000002` - Greater Chicago Area

### Europe  
- `101165590` - United Kingdom
- `101282230` - Germany
- `105015875` - France
- `103350119` - Spain
- `103544275` - Italy
- `102890719` - Netherlands
- `105117694` - Sweden

### Other Regions
- `101174742` - Canada
- `101452733` - Australia
- `102257491` - Japan
- `102748797` - Singapore
- `101620260` - Israel

### Finding New Geo IDs
1. Go to LinkedIn Jobs
2. Search for jobs in your desired location
3. Look at the URL for `geoId=` parameter
4. Use that number in your configuration

## Remote Work Type Codes
- `1` - On-site
- `2` - Remote  
- `3` - Hybrid

Use these in your SEARCHES configuration as the second parameter.