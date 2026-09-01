"""Telegram bot entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.routers import info_router, search_router
from core.config import settings

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
dp.include_routers(search_router, info_router)


@dp.message(CommandStart())
async def start(message: Message) -> None:
    """Handle /start."""
    await message.answer(
        "🎬 <b>Семантический поиск фильмов</b>\n\n"
        "Опиши фильм или настроение — я найду подходящие варианты.",
        parse_mode=ParseMode.HTML,
    )


async def main() -> None:
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped by user")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
