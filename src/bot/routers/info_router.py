"""Telegram handlers for movie details."""

import asyncio
import html

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

from src.backend.schemas import MovieResult
from src.services.search_service.search_service import SearchService
from src.core.dependencies import get_search_service
from src.core.logger import get_logger

logger = get_logger(__name__)
router = Router(name="info")


def get_service() -> SearchService:
    """Return the shared search service instance."""
    return get_search_service()


def movie_details(movie: MovieResult) -> str:
    """Build the detailed movie response."""
    lines = [f"🎬 <b>{html.escape(movie.title)}</b>"]
    if movie.year is not None:
        lines.append(f"📅 <b>Год:</b> {movie.year}")
    if movie.rating is not None:
        lines.append(f"⭐ <b>Рейтинг:</b> {movie.rating:.1f}")
    if movie.genres:
        lines.append(f"🎭 <b>Жанры:</b> {html.escape(', '.join(movie.genres))}")
    if movie.countries:
        lines.append(f"🌍 <b>Страны:</b> {html.escape(', '.join(movie.countries))}")
    if movie.description:
        lines.append(f"\n<b>Описание</b>\n{html.escape(movie.description)}")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("movie:"))
async def show_movie_details(callback: CallbackQuery) -> None:
    """Fetch and show full information for a selected movie."""
    if not callback.data or callback.message is None:
        return

    try:
        movie_id = int(callback.data.removeprefix("movie:"))
    except ValueError:
        await callback.answer(
            "Некорректный идентификатор фильма.",
            show_alert=True,
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        service = get_service()
        if hasattr(service, "get_by_id"):
            movie = await asyncio.to_thread(service.get_by_id, movie_id)
        else:
            points = await asyncio.to_thread(
                service.qdrant_repo.client.retrieve,
                collection_name=service.qdrant_repo.collection_name,
                ids=[movie_id],
                with_payload=True,
                with_vectors=False,
            )
            movie = None
            if points and points[0].payload:
                movie = MovieResult.model_validate(
                    {**points[0].payload, "score": 0.0}
                )
    except Exception:
        logger.exception("Movie lookup failed: movie_id=%d", movie_id)
        await callback.answer(
            "Не удалось получить информацию о фильме.",
            show_alert=True,
            parse_mode=ParseMode.HTML,
        )
        return

    if movie is None:
        await callback.answer(
            "Фильм не найден.",
            show_alert=True,
            parse_mode=ParseMode.HTML,
        )
        return

    await callback.answer()
    await callback.message.answer(
        movie_details(movie),
        parse_mode=ParseMode.HTML,
    )
