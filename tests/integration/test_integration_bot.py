"""Integration tests for Telegram bot."""

import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup

from bot.routers.search_router import _handle_search, search_results_message
from bot.routers.info_router import movie_details
from backend.schemas import MovieResult


class TestBot:
    """Test Telegram bot functionality."""

    @pytest.mark.asyncio
    async def test_handle_search_success(self):
        """Успешный поиск."""
        message = AsyncMock(spec=Message)
        message.text = "inception"
        message.answer = AsyncMock()
        
        with patch('bot.routers.search_router.search_service') as mock_service:
            mock_service.search.return_value = [
                MovieResult(id=1, title="Inception", year=2010, rating=8.8, score=0.95)
            ]
            
            await _handle_search(message, "inception")
            
            message.answer.assert_called_once()
            call_kwargs = message.answer.call_args[1]
            assert "Результаты поиска" in call_kwargs.get("text", "")
            assert "Inception" in call_kwargs.get("text", "")
            assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_handle_search_empty(self):
        """Пустой результат."""
        message = AsyncMock(spec=Message)
        message.text = "xyz123"
        message.answer = AsyncMock()
        
        with patch('bot.routers.search_router.search_service') as mock_service:
            mock_service.search.return_value = []
            
            await _handle_search(message, "xyz123")
            
            message.answer.assert_called_once_with(
                "🔎 <b>Ничего не найдено.</b>\nПопробуй изменить запрос.",
                parse_mode="HTML"
            )

    @pytest.mark.asyncio
    async def test_handle_search_short_query(self):
        """Слишком короткий запрос."""
        message = AsyncMock(spec=Message)
        message.answer = AsyncMock()
        
        await _handle_search(message, "a")
        
        message.answer.assert_called_once_with(
            "❌ Слишком короткий запрос. Напиши хотя бы 2 символа.",
            parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_handle_search_long_query(self):
        """Слишком длинный запрос."""
        message = AsyncMock(spec=Message)
        message.answer = AsyncMock()
        
        await _handle_search(message, "a" * 501)
        
        message.answer.assert_called_once_with(
            "❌ Слишком длинный запрос. Максимум 500 символов.",
            parse_mode="HTML"
        )

    def test_movie_details_formatting(self):
        """Форматирование деталей фильма."""
        movie = MovieResult(
            id=1,
            title="Inception",
            year=2010,
            rating=8.8,
            genres=["sci-fi", "thriller"],
            countries=["USA"],
            director="Christopher Nolan",
            actors=["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
            description="A thief who steals corporate secrets",
            score=0.95
        )
        
        details = movie_details(movie)
        
        assert "Inception" in details
        assert "2010" in details
        assert "8.8" in details
        assert "sci-fi" in details
        assert "Christopher Nolan" in details
        assert "Leonardo DiCaprio" in details
        assert "A thief who steals corporate secrets" in details

    def test_search_results_message(self):
        """Форматирование результатов поиска."""
        movies = [
            MovieResult(id=1, title="Inception", year=2010, score=0.95),
            MovieResult(id=2, title="The Dark Knight", year=2008, score=0.89)
        ]
        
        message = search_results_message(movies)
        
        assert "Результаты поиска" in message
        assert "1. Inception" in message
        assert "2. The Dark Knight" in message
        assert "2010" in message
        assert "2008" in message