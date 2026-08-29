"""Basic Telegram bot for semantic movie search."""

import asyncio
import html
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from semantic_search_service.backend.schemas import MovieResult, SearchRequest
from semantic_search_service.core.config import settings
from semantic_search_service.core.dependencies import get_search_service

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
search_service = get_search_service()


def movie_card(movie: MovieResult) -> str:
    """Build a compact movie search result."""
    parts = [f"<b>{html.escape(movie.title)}</b>"]
    if movie.year is not None:
        parts.append(f"📅 {movie.year}")
    if movie.rating is not None:
        parts.append(f"⭐ {movie.rating:.1f}")
    if movie.genres:
        parts.append(f"🎬 {html.escape(', '.join(movie.genres))}")
    return "\n".join(parts)


def movie_details(movie: MovieResult) -> str:
    """Build the detailed movie response."""
    lines = [f"<b>{html.escape(movie.title)}</b>"]
    if movie.year is not None:
        lines.append(f"📅 Год: {movie.year}")
    if movie.rating is not None:
        lines.append(f"⭐ Рейтинг: {movie.rating:.1f}")
    if movie.genres:
        lines.append(f"🎬 Жанры: {html.escape(', '.join(movie.genres))}")
    if movie.countries:
        lines.append(f"🌍 Страны: {html.escape(', '.join(movie.countries))}")
    if movie.director:
        lines.append(f"🎥 Режиссёр: {html.escape(movie.director)}")
    if movie.actors:
        lines.append(f"👥 Актёры: {html.escape(', '.join(movie.actors))}")
    if movie.description:
        lines.append(f"\n{html.escape(movie.description)}")
    return "\n".join(lines)


@dp.message(CommandStart())
async def start(message: Message) -> None:
    """Handle /start."""
    await message.answer(
        "🎬 <b>Семантический поиск фильмов</b>\n\n"
        "Напиши, какой фильм ты хочешь посмотреть — я найду похожие."
    )


@dp.message(F.text)
async def search_movies(message: Message) -> None:
    """Search for the top 10 similar movies."""
    query = message.text.strip()
    if not query:
        return
    try:
        results = await asyncio.to_thread(
            search_service.search,
            SearchRequest(query=query, top_k=10),
        )
    except Exception:
        logger.exception("Telegram search failed: query=%r", query)
        await message.answer("❌ Не удалось выполнить поиск. Попробуй ещё раз.")
        return

    if not results:
        await message.answer("🔎 По твоему запросу ничего не найдено.")
        return

    for movie in results:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подробнее", callback_data=f"movie:{movie.id}")]
            ]
        )
        await message.answer(movie_card(movie), reply_markup=keyboard)


@dp.callback_query(F.data.startswith("movie:"))
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


async def main() -> None:
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
