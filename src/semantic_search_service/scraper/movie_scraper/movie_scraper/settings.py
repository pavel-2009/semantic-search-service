BOT_NAME = "movie_scraper"

ROBOTSTXT_OBEY = False

# Обычный скачиватель (без Playwright)
CONCURRENT_REQUESTS = 5  # можно больше, API быстро отвечает
DOWNLOAD_DELAY = 0.5

# Retry на случай ошибок API
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 429]

COOKIES_ENABLED = False
LOG_LEVEL = "INFO"

# Отключаем всё, что связано с Playwright
DOWNLOAD_HANDLERS = {}
TWISTED_REACTOR = None

ITEM_PIPELINES = {
    "scraper.pipelines.JsonPipeline": 300,
}