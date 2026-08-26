BOT_NAME = "scraper"

SPIDER_MODULES = [
    "scraper.spiders",
]

NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = False

# ---------- PLAYWRIGHT ----------
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 30000,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-web-security",
        "--lang=ru-RU",
        "--window-size=1920,1080",
    ]
}

PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000

# ---------- СКОРОСТЬ И ЗАДЕРЖКИ ----------
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

DOWNLOAD_DELAY = 3.0
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5.0
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# ---------- ПОВТОРНЫЕ ПОПЫТКИ ----------
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 403, 429, 408]

# ---------- MIDDLEWARES (упрощённые) ----------
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,  # включаем редиректы
    'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': 580,
}

# Включаем RefererMiddleware для правильной обработки рефереров
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.referer.RefererMiddleware': 700,
}

# ---------- ТАЙМАУТЫ ----------
DOWNLOAD_TIMEOUT = 120

# ---------- ПРОЧЕЕ ----------
COOKIES_ENABLED = False
HTTPCACHE_ENABLED = False
LOG_LEVEL = "INFO"

# Простой список User-Agent вместо библиотеки
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"