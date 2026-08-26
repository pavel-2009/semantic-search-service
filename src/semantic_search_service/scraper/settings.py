BOT_NAME = "semantic_search_service"

SPIDER_MODULES = ["semantic_search_service.scraper.spiders"]
NEWSPIDER_MODULE = "semantic_search_service.scraper.spiders"

ROBOTSTXT_OBEY = False
COOKIES_ENABLED = False

CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 0.2

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

ITEM_PIPELINES = {
    "semantic_search_service.scraper.pipelines.JsonPipeline": 300,
}

LOG_LEVEL = "INFO"
