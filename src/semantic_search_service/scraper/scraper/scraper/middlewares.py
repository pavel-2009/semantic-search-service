from scrapy import signals


class ScraperSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        yield from result

    def process_spider_exception(self, response, exception, spider):
        return None

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s", spider.name)