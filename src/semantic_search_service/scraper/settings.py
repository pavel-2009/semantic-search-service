from semantic_search_service.core.config import settings

BOT_NAME = "semantic_search_service"

SPIDER_MODULES = ["semantic_search_service.scraper.spiders"]
NEWSPIDER_MODULE = "semantic_search_service.scraper.spiders"

ROBOTSTXT_OBEY = False
COOKIES_ENABLED = False

ITEM_PIPELINES = {
    "semantic_search_service.scraper.pipelines.JsonPipeline": 300,
}

LOG_LEVEL = "INFO"

DEFAULT_REQUEST_HEADERS = {
    "X-API-KEY": settings.POISKKINO_API_KEY,
    "Accept": "application/json",
}

CONCURRENT_REQUESTS = 2
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [403, 429, 500, 502, 503, 504]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MIN_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
