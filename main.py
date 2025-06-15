import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config, logger
from handlers import register_handlers


async def main():
    """Запуск бота."""
    bot = Bot(token=Config.BOT_TOKEN, proxy=Config.PROXY_URL)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем обработчики
    register_handlers(dp)

    logger.info("Бот запущен и готов к работе!")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
