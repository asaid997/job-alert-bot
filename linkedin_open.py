from linkedin_scraper import run_scrape
from messages import send_full_search_report_to_telegram


def main():
    result = run_scrape()

    print(
        "\nAll searches finished. "
        f"Found {len(result['accepted'])} matches and "
        f"{sum(job.get('match_status') == 'review' for job in result['rejected'])} jobs needing review."
    )
    send_full_search_report_to_telegram(
        result["accepted"],
        result["rejected"],
        result["links"],
        result["started_at"],
        result["total_scraped"],
        result["time_range_label"],
    )


if __name__ == "__main__":
    main()
