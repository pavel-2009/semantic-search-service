"""Telegram bot routers."""

from .info_router import router as info_router
from .search_router import router as search_router

__all__ = ["info_router", "search_router"]
