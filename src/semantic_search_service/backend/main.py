"""Entry point for FastApi App"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Semantic Search API",
    description="Семантический поиск по фильмам с Qdrant и C++ Cleaner",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_headers=['*'],
    allow_methods=['*']
)
