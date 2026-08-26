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

TWISTED_REACTOR = (
    "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
)

PLAYWRIGHT_BROWSER_TYPE = "chromium"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}


# Скорость
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 3


# Таймауты
DOWNLOAD_TIMEOUT = 60
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000


# Retry только сетевых ошибок сервера.
RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [
    500,
    502,
    503,
    504,
]


# Логи
LOG_LEVEL = "INFO"