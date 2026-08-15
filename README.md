Semantic Content Search Engine

«Семантическая поисковая система на Python и C++ с векторной базой Qdrant, REST API и Telegram-интерфейсом.»

""Python" (https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)" (https://www.python.org/)
""C++" (https://img.shields.io/badge/C%2B%2B-20-00599C?logo=cplusplus&logoColor=white)" (https://isocpp.org/)
""FastAPI" (https://img.shields.io/badge/FastAPI-0.1+-009688?logo=fastapi&logoColor=white)" (https://fastapi.tiangolo.com/)
""Qdrant" (https://img.shields.io/badge/Qdrant-Vector%20DB-FF4F00)" (https://qdrant.tech/)
""Docker" (https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)" (https://www.docker.com/)
""Tests" (https://img.shields.io/badge/tests-pytest-0A9EDC)" (https://pytest.org/)

📌 О проекте

Semantic Content Search Engine — поисковая система, которая ищет контент по смыслу, а не только по совпадению ключевых слов.

Например, запрос:

пушистый домашний питомец

может найти материалы про кошек, даже если слово "кот" непосредственно в запросе отсутствует.

Система проходит полный pipeline:

Data Source
    ↓
Scraper
    ↓
C++ Text Cleaner
    ↓
Sentence Transformer
    ↓
Qdrant Vector Database
    ↓
FastAPI
    ↓
Telegram Bot / API Client

Проект демонстрирует практическую интеграцию Python, C++, ML-моделей, vector database, REST API и Docker.

---

✨ Возможности

- 🔎 Семантический поиск по текстовому контенту
- 🧠 Генерация embedding-векторов с помощью "sentence-transformers"
- 🗄️ Хранение и поиск векторов в Qdrant
- 🎯 Фильтрация результатов по metadata
- ⚡ Высокопроизводительная очистка текста на C++
- 🔗 Интеграция C++ и Python через "pybind11"
- 🌐 REST API на FastAPI
- 🤖 Telegram Bot на Aiogram 3
- 🕷️ Асинхронный сбор данных через "aiohttp"
- 🐳 Полностью контейнеризированное окружение
- 🧪 Unit и integration tests
- 🔄 CI через GitHub Actions

---

🏗️ Архитектура

┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                         │
├─────────────────┬─────────────────┬─────────────────────────┤
│                 │                 │                         │
│    Scraper      │     Qdrant      │        Backend          │
│    Python       │   Vector DB     │      FastAPI             │
│                 │                 │                         │
└────────┬────────┴────────┬────────┴──────────┬──────────────┘
         │                 │                   │
         ▼                 │                   ▼
┌─────────────────┐        │          ┌──────────────────────┐
│   C++ Cleaner   │        │          │    Telegram Bot      │
│     pybind11    │        │          │      Aiogram 3       │
└────────┬────────┘        │          └──────────────────────┘
         │                 │
         ▼                 ▼
┌─────────────────┐   ┌──────────────────┐
│ Sentence        │   │ Vector Search    │
│ Transformers    │   │ + Metadata       │
│ Embeddings      │   │ Filtering        │
└─────────────────┘   └──────────────────┘

Pipeline поиска

User Query
    │
    ▼
FastAPI
    │
    ▼
Text Cleaner
    │
    ▼
Embedding Model
    │
    ▼
Query Vector
    │
    ▼
Qdrant
    │
    ▼
Top-K Results
    │
    ▼
JSON Response / Telegram

---

🧩 Компоненты

Компонент| Технологии| Назначение
Scraper| Python, aiohttp, BeautifulSoup| Сбор исходных данных
C++ Cleaner| C++20, pybind11, CMake| Очистка и нормализация текста
Indexer| Python, Sentence Transformers| Создание embeddings
Qdrant| Qdrant| Хранение и поиск векторов
Backend| FastAPI, Pydantic| REST API
Telegram Bot| Aiogram 3| Пользовательский интерфейс
Infrastructure| Docker Compose| Запуск сервисов
Testing| pytest| Unit и integration tests
CI| GitHub Actions| Автоматические проверки

---

📂 Структура проекта

semantic-search/
│
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   └── app/
│       ├── main.py
│       ├── models.py
│       │
│       ├── api/
│       │   └── routes.py
│       │
│       ├── services/
│       │   ├── search_service.py
│       │   └── indexer.py
│       │
│       └── core/
│           ├── config.py
│           └── qdrant_client.py
│
├── scraper/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scraper.py
│   └── data/
│       └── raw_content.json
│
├── cpp_cleaner/
│   ├── CMakeLists.txt
│   ├── cleaner.cpp
│   ├── cleaner.h
│   ├── bindings.cpp
│   ├── setup.py
│   └── README.md
│
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── bot.py
│   └── handlers.py
│
└── tests/
    ├── conftest.py
    ├── test_search.py
    └── test_cleaner.py

---

🕷️ Data Collection

Проект может работать с различными типами контента:

- фильмы и сериалы;
- книги;
- статьи;
- товары;
- документы;
- записи базы знаний.

Для демонстрационной версии используется набор из 5000+ объектов.

Пример исходной записи:

{
  "id": "movie_001",
  "title": "Дюна: Часть вторая",
  "description": "Пол Атрейдес объединяется с фременами...",
  "genre": [
    "фантастика",
    "драма"
  ],
  "year": 2024,
  "actors": [
    "Тимоти Шаламе",
    "Зендея"
  ],
  "rating": 8.7
}

Scraper реализован асинхронно и поддерживает:

- пагинацию;
- обработку ошибок;
- повторные запросы;
- сохранение результата в JSON.

---

⚡ C++ Text Cleaner

Очистка текста вынесена в отдельный C++20-модуль.

Основная функция:

std::string clean_text(const std::string& input);

Модуль выполняет:

- удаление лишних символов;
- нормализацию пробелов;
- нормализацию кавычек;
- приведение текста к единому формату;
- удаление ненужного Unicode/emoji-мусора.

Python-интерфейс предоставляется через "pybind11":

from text_cleaner import clean_text

result = clean_text(text)

Зачем здесь C++?

Это отдельный эксперимент проекта с native extension и интеграцией C++/Python.

Производительность должна оцениваться отдельным benchmark-тестом:

Python implementation
        vs
C++ implementation

Такой подход позволяет не просто заявлять об ускорении, а показывать реальные результаты измерений.

---

🧠 Semantic Embeddings

После очистки текст преобразуется в embedding-вектор с помощью:

sentence-transformers

Используемая модель:

all-MiniLM-L6-v2

Размерность embedding:

384

Каждый объект превращается в точку в векторном пространстве.

Например:

{
  "id": "movie_001",
  "vector": [0.123, -0.456, "..."],
  "payload": {
    "title": "Дюна: Часть вторая",
    "genre": [
      "фантастика",
      "драма"
    ],
    "year": 2024,
    "rating": 8.7
  }
}

---

🗄️ Qdrant

Qdrant используется как vector database.

Он отвечает за:

- хранение embeddings;
- similarity search;
- фильтрацию по metadata;
- получение Top-K результатов.

Пример логического запроса:

Query:
"психоделический триллер про сон"

Filters:
genre = фантастика
year >= 2020

↓

Embedding

↓

Qdrant similarity search

↓

Top 5 results

---

🌐 REST API

Backend реализован на FastAPI.

"GET /health"

Проверка состояния сервиса.

Пример:

{
  "status": "healthy",
  "indexed_items": 5000
}

---

"GET /stats"

Возвращает статистику поискового индекса.

---

"POST /search"

Семантический поиск.

Request

{
  "query": "психоделический триллер про сон",
  "top_k": 5,
  "filter_genre": [
    "фантастика"
  ],
  "min_year": 2020
}

Response

{
  "success": true,
  "results": [
    {
      "id": "movie_001",
      "title": "Дюна: Часть вторая",
      "genre": [
        "фантастика",
        "драма"
      ],
      "year": 2024,
      "score": 0.89
    }
  ]
}

После запуска API также доступна автоматически генерируемая документация FastAPI:

/docs
/redoc

---

🤖 Telegram Bot

Telegram Bot предоставляет простой пользовательский интерфейс поверх REST API.

Поддерживаемые команды

Команда| Описание
"/start"| Информация о боте
"/search <query>"| Семантический поиск
"/trends"| Популярный контент
"/info <id>"| Информация об объекте

Пример:

/search грустное кино 90-х про любовь

Ответ:

🔍 Найдено 5 результатов

1. 🎬 Титаник (1997)
   Рейтинг: 8.0
   Релевантность: 92%

2. 🎬 Английский пациент (1996)
   Рейтинг: 7.8
   Релевантность: 87%

---

🐳 Docker

Все основные компоненты запускаются через Docker Compose.

Архитектура:

┌──────────────┐
│   scraper    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    indexer   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    qdrant    │
└──────┬───────┘
       ▲
       │
┌──────┴───────┐
│   backend    │
└──────┬───────┘
       ▲
       │
┌──────┴───────┐
│     bot      │
└──────────────┘

---

🚀 Быстрый запуск

1. Клонирование

git clone https://github.com/your-username/semantic-search.git

cd semantic-search

2. Настройка окружения

cp .env.example .env

Укажите необходимые переменные окружения, например:

BOT_TOKEN=your_telegram_bot_token
QDRANT_HOST=qdrant
QDRANT_PORT=6333

3. Запуск

docker compose up --build

После запуска:

FastAPI:
http://localhost:8000

Swagger:
http://localhost:8000/docs

Qdrant:
http://localhost:6333

4. Проверка

curl http://localhost:8000/health

Ожидаемый результат:

{
  "status": "healthy"
}

---

🧪 Тестирование

Для тестирования используется "pytest".

Запуск:

pytest

С coverage:

pytest --cov=app

Основные категории тестов:

- unit-тесты C++ cleaner;
- тесты FastAPI endpoints;
- тесты search service;
- integration-тесты с Qdrant;
- проверка корректности фильтрации;
- проверка формата API response.

Целевой уровень покрытия:

70%+

---

📊 Benchmark

Производительность C++ cleaner сравнивается с Python-реализацией на одинаковом наборе данных.

Пример:

Dataset: 5000 documents

Python:
████████████████████  X.XX sec

C++:
██                   X.XX sec

«Конкретные цифры должны быть получены реальным benchmark-тестом и не являются заранее заданным результатом.»

---

🔧 Конфигурация

Основные настройки передаются через environment variables.

Пример ".env":

BOT_TOKEN=your_token

QDRANT_HOST=qdrant
QDRANT_PORT=6333

DATA_PATH=/app/data/raw_content.json

EMBEDDING_MODEL=all-MiniLM-L6-v2

Секреты не должны храниться в Git.

Используйте:

.env

и добавьте его в:

.gitignore

В репозитории должен находиться только:

.env.example

---

🛠️ Технологический стек

Backend

- Python 3.11+
- FastAPI
- Pydantic
- Uvicorn

Data Collection

- aiohttp
- BeautifulSoup

Machine Learning

- Sentence Transformers
- PyTorch

Vector Search

- Qdrant

Native Extension

- C++20
- pybind11
- CMake

Telegram

- Aiogram 3

Infrastructure

- Docker
- Docker Compose
- GitHub Actions

Testing

- pytest
- pytest-asyncio
- pytest-cov

---

📈 Что демонстрирует проект

Проект объединяет несколько направлений разработки:

Навык| Реализация
Python Backend| FastAPI
Async Python| aiohttp / asyncio
Web Scraping| BeautifulSoup + aiohttp
Vector Search| Qdrant
Machine Learning| Sentence Transformers
C++| C++20 native module
Python/C++ Integration| pybind11
REST API| FastAPI
Telegram Development| Aiogram
Containers| Docker
Orchestration| Docker Compose
Testing| pytest
CI/CD| GitHub Actions

---

🗺️ Roadmap

Core

- [x] Scraper
- [x] C++ text cleaner
- [x] Python/C++ integration
- [x] Embedding generation
- [x] Qdrant indexing
- [x] Semantic search API
- [x] Telegram Bot
- [x] Docker Compose

Production improvements

- [ ] Redis cache
- [ ] PostgreSQL for structured metadata
- [ ] Celery background jobs
- [ ] Search result caching
- [ ] Structured logging
- [ ] Prometheus metrics
- [ ] Grafana dashboard
- [ ] CI pipeline
- [ ] Automated benchmark
- [ ] Load testing
- [ ] Authentication / API keys
- [ ] Rate limiting

---

💼 Возможные применения

Архитектура проекта может быть адаптирована под различные типы данных.

🛒 E-commerce

Семантический поиск по каталогу:

"лёгкая чёрная куртка для зимы"

📚 Knowledge Base

Поиск по внутренней документации:

"как восстановить доступ к аккаунту"

📄 Документы

Поиск информации по корпоративным документам.

🎬 Контент

Поиск фильмов, книг, статей и другого контента по описанию.

🤖 Recommendation Systems

Embedding-based retrieval может использоваться как один из компонентов рекомендательной системы.

---

🎯 Project Goals

Проект создан для практического изучения:

- semantic search;
- vector databases;
- embeddings;
- Python/C++ integration;
- asynchronous data processing;
- REST API development;
- containerization;
- testing and CI/CD.

Главная цель — построить не отдельный ML-эксперимент, а полноценный сервис от сбора данных до пользовательского интерфейса.

---

📄 License

This project is intended for educational and portfolio purposes.

Add your preferred license here, for example:

MIT License

---

👨‍💻 Author

Pavel

GitHub: "https://github.com/your-username"

---

⭐ Если проект оказался полезен

Если вам интересны:

- Semantic Search
- Vector Databases
- Python + C++
- FastAPI
- Qdrant
- ML Infrastructure

— можете посмотреть исходный код и предложить улучшения через Issues или Pull Requests.