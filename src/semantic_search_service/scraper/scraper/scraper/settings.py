BOT_NAME = "scraper"

SPIDER_MODULES = [
    "scraper.spiders",
]

NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = False

# Playwright
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}

# Скорость
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Таймауты
DOWNLOAD_TIMEOUT = 60
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000

# Retry только сетевых ошибок сервера
RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504]

# Логи
LOG_LEVEL = "INFO"

COOKIES_ENABLED = False

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 4.0   
AUTOTHROTTLE_MAX_DELAY = 60.0   
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0 

DOWNLOAD_DELAY = 3.5
RANDOMIZE_DOWNLOAD_DELAY = True

HTTPCACHE_ENABLED = False

PLAYWRIGHT_CONTEXT_ARGS = {
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "viewport": {"width": 1920, "height": 1080},
    "locale": "ru-RU",
    "timezone_id": "Europe/Moscow",
}