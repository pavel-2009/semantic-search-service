"""Telegram handlers for movie details."""

import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from backend.schemas import MovieResult
from core.dependencies import get_search_service

logger = logging.getLogger(__name__)
router = Router(name="info")
search_service = get_search_service()


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
    if movie.director:
        lines.append(f"🎥 <b>Режиссёр:</b> {html.escape(movie.director)}")
    if movie.actors:
        lines.append(f"👥 <b>В ролях:</b> {html.escape(', '.join(movie.actors))}")
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
        await callback.answer("Некорректный идентификатор фильма.", show_alert=True)
        return

    try:
        movie = await asyncio.to_thread(search_service.get_by_id, movie_id)
    except Exception:
        logger.exception("Movie lookup failed: movie_id=%d", movie_id)
        await callback.answer("Не удалось получить информацию о фильме.", show_alert=True)
        return

    if movie is None:
        await callback.answer("Фильм не найден.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(movie_details(movie))
