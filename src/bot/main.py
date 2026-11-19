"""Telegram bot entry point."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.bot.api_client import api_client
from src.bot.routers import info_router, search_router
from src.core.config import settings
from src.core.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

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
    token = settings.BOT_TOKEN.strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Add your Telegram bot token to the .env file "
            "or the process environment."
        )

    bot = Bot(token=token)
    logger.info("Starting Telegram bot")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped by user")
    finally:
        await bot.session.close()
        await api_client.close()


if __name__ == "__main__":
    asyncio.run(main())
