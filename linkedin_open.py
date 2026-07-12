from linkedin_scraper import run_scrape
from messages import send_full_search_report_to_telegram


def main():
    result = run_scrape()

    print(
        "\nAll searches finished. "
        f"Sending {len(result['accepted'])} high-confidence and "
        f"{len(result['rejected'])} review jobs to Telegram."
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
