"""Telegram handlers for movie search."""

import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.schemas import MovieResult, SearchRequest
from core.dependencies import get_search_service

logger = logging.getLogger(__name__)
router = Router(name="search")
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
    cards = [movie_card(movie, i) for i, movie in enumerate(results, 1)]
    return "🔎 <b>Результаты поиска</b>\n\n" + "\n\n".join(cards)


def search_results_keyboard(results: list[MovieResult]) -> InlineKeyboardMarkup:
    """Build detail buttons for search results."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Подробнее · {i}", callback_data=f"movie:{movie.id}")]
            for i, movie in enumerate(results, 1)
        ]
    )


async def _handle_search(message: Message, query: str) -> None:
    """Run a movie search and send formatted results."""
    query = query.strip()
    if len(query) < 2:
        await message.answer(
            "❌ Слишком короткий запрос. Напиши хотя бы 2 символа.",
            parse_mode=ParseMode.HTML,
        )
        return

    if len(query) > 500:
        await message.answer(
            "❌ Слишком длинный запрос. Максимум 500 символов.",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        results = await asyncio.to_thread(
            search_service.search,
            SearchRequest(query=query, top_k=10, filters=None),
        )
    except Exception:
        logger.exception("Telegram search failed: query=%r", query)
        await message.answer(
            "❌ <b>Не удалось выполнить поиск.</b>\nПопробуй ещё раз.",
            parse_mode=ParseMode.HTML,
        )
        return

    if not results:
        await message.answer(
            "🔎 <b>Ничего не найдено.</b>\nПопробуй изменить запрос.",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer(
        text=search_results_message(results),
        reply_markup=search_results_keyboard(results),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("search"))
async def search_movies(message: Message, command: CommandObject) -> None:
    """Search for the top 10 similar movies with /search."""
    await _handle_search(message, command.args or "")


@router.message(F.text & ~F.text.startswith("/"))
async def search_by_text(message: Message) -> None:
    """Search for the top 10 similar movies from a regular text message."""
    await _handle_search(message, message.text or "")
