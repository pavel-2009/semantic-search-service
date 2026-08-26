import random
import logging
from scrapy import signals

logger = logging.getLogger(__name__)


class RandomHeadersMiddleware:
    """Добавляет случайные заголовки для имитации реального пользователя"""
    
    # Список популярных User-Agent
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    ]
    
    REFERERS = [
        "https://www.ivi.ru/",
        "https://www.ivi.ru/movies",
        "https://www.google.com/",
        "https://yandex.ru/",
        "https://www.ivi.ru/movies/new",
        "https://www.ivi.ru/movies/best",
    ]
    
    ACCEPT_LANGS = [
        "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "ru-RU;q=0.9,en;q=0.8",
    ]
    
    def process_request(self, request, spider):
        # Случайный User-Agent
        request.headers['User-Agent'] = random.choice(self.USER_AGENTS)
        
        # Случайный Referer
        request.headers['Referer'] = random.choice(self.REFERERS)
        
        # Случайный Accept-Language
        request.headers['Accept-Language'] = random.choice(self.ACCEPT_LANGS)
        
        # Основные заголовки браузера
        request.headers['Accept'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        request.headers['Accept-Encoding'] = "gzip, deflate, br"
        request.headers['Connection'] = "keep-alive"
        request.headers['Upgrade-Insecure-Requests'] = "1"
        request.headers['Sec-Fetch-Dest'] = "document"
        request.headers['Sec-Fetch-Mode'] = "navigate"
        request.headers['Sec-Fetch-Site'] = "none"
        request.headers['Sec-Fetch-User'] = "?1"
        request.headers['Cache-Control'] = "max-age=0"
        
        return None