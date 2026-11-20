"""Run the movie scraper."""

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from src.scraper.spiders.movie_spider import MovieSpider


def main() -> None:
    """Run the configured movie spider and JSON pipeline."""
    settings = get_project_settings()
    settings.setmodule("src.scraper.settings")

    process = CrawlerProcess(settings)
    crawler = process.create_crawler(MovieSpider)
    process.crawl(crawler)
    process.start()
    if not crawler.stats.get_value("scraper/export_committed", False):
        raise SystemExit("Scraper did not complete successfully; previous data was preserved.")


if __name__ == "__main__":
    main()
