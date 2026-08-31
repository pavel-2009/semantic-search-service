"""Telegram bot for semantic movie search."""

import asyncio
import html
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.schemas import MovieResult, SearchRequest
from core.config import settings
from core.dependencies import get_search_service

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
search_service = get_search_service()


def movie_card(movie: MovieResult, position: int) -> str:
    """Build one formatted movie result."""
    lines = [f"<b>{position}. {html.escape(movie.title)}</b>"]

    metadata: list[str] = []
    if movie.year is not None:
        metadata.append(f"📅 {movie.year}")
    if movie.rating is not None:
        metadata.append(f"⭐ {movie.rating:.1f}")
    if movie.score is not None:
        metadata.append(f"🎯 {movie.score:.2f}")

    if metadata:
        lines.append("  ·  ".join(metadata))
    if movie.genres:
        lines.append(f"🎬 {html.escape(', '.join(movie.genres))}")

    return "\n".join(lines)


def search_results_message(results: list[MovieResult]) -> str:
    """Build the complete search results message."""
    cards = [movie_card(movie, index) for index, movie in enumerate(results, start=1)]
    return "🔎 <b>Результаты поиска</b>\n\n" + "\n\n".join(cards)


def search_results_keyboard(results: list[MovieResult]) -> InlineKeyboardMarkup:
    """Build one inline button for each movie."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Подробнее · {index}",
                    callback_data=f"movie:{movie.id}",
                )
            ]
            for index, movie in enumerate(results, start=1)
        ]
    )


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


@dp.message(CommandStart())
async def start(message: Message) -> None:
    """Handle /start."""
    await message.answer(
        "🎬 <b>Семантический поиск фильмов</b>\n\n"
        "Опиши фильм или настроение — я найду подходящие варианты."
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
            SearchRequest(query=query, top_k=10, filters=None),
        )
    except Exception:
        logger.exception("Telegram search failed: query=%r", query)
        await message.answer("❌ <b>Не удалось выполнить поиск.</b>\nПопробуй ещё раз.")
        return

    if not results:
        await message.answer("🔎 <b>Ничего не найдено.</b>\nПопробуй изменить запрос.")
        return

    # Send all results as one Telegram message. This avoids the per-chat
    # message rate limit and makes the result look like a single search page.
    await message.answer(
        search_results_message(results),
        reply_markup=search_results_keyboard(results),
    )


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
