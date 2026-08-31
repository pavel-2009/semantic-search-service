from core.config import settings


BOT_NAME = "semantic_search_service"

SPIDER_MODULES = [
    "scraper.spiders",
]

NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = False

COOKIES_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
    "X-API-KEY": settings.POISKKINO_API_KEY,
    "Accept": "application/json",
}

ITEM_PIPELINES = {
    "scraper.pipelines.JsonPipeline": 300,
}

LOG_LEVEL = "INFO"

CONCURRENT_REQUESTS = 1

DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

RETRY_ENABLED = True
RETRY_TIMES = 2

RETRY_HTTP_CODES = [
    429,
    500,
    502,
    503,
    504,
]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MIN_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
