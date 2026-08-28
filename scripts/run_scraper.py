"""Run the movie scraper."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from semantic_search_service.scraper.spiders.movie_spider import MovieSpider


def main() -> None:
    """Run the configured movie spider and JSON pipeline."""
    settings = get_project_settings()
    settings.setmodule("semantic_search_service.scraper.settings")

    process = CrawlerProcess(settings)
    process.crawl(MovieSpider)
    process.start()


if __name__ == "__main__":
    main()
