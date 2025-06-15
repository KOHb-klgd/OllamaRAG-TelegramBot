from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from typing import Dict
from config import Config, logger
from utils import generate_response


class UserStates(StatesGroup):
    WAITING_FOR_QUERY = State()
    IN_CHAT_MODE = State()


# Словарь для хранения режима работы для каждого пользователя
user_modes: Dict[int, str] = {}


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает главную клавиатуру."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Поиск по базе знаний")],
            [KeyboardButton(text="💬 Поговорить по душам")],
        ],
        resize_keyboard=True,
    )


def register_handlers(dp: Dispatcher) -> None:
    """Регистрирует все обработчики."""

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        """Обработчик команды /start."""
        await state.clear()
        user_id = message.from_user.id
        user_modes[user_id] = None  # Сбрасываем режим для пользователя
        logger.info(f"Пользователь {user_id} начал работу с ботом.")
        await message.answer(
            "🤖 Привет! Я умный бот с двумя режимами:\n"
            "1. <b>🔍 Поиск по базе знаний</b> — ищу ответы в документах\n"
            "2. <b>💬 Поговорить по душам</b> — свободный диалог с ИИ",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    @dp.message(lambda message: message.text == "🔍 Поиск по базе знаний")
    async def enable_rag_mode(message: types.Message, state: FSMContext):
        """Активирует режим поиска по базе знаний."""
        user_id = message.from_user.id
        user_modes[user_id] = "RAG"
        logger.info(f"Пользователь {user_id} включил режим поиска по базе знаний.")
        await state.set_state(UserStates.WAITING_FOR_QUERY)
        await message.answer(
            "🔍 Режим поиска по базе знаний активирован.\nОтправьте ваш запрос:",
            reply_markup=get_main_keyboard(),
        )

    @dp.message(lambda message: message.text == "💬 Поговорить по душам")
    async def enable_chat_mode(message: types.Message, state: FSMContext):
        """Активирует режим свободного общения."""
        user_id = message.from_user.id
        user_modes[user_id] = "CHAT"
        logger.info(f"Пользователь {user_id} включил режим свободного общения.")
        await state.set_state(UserStates.IN_CHAT_MODE)
        await message.answer(
            "💬 Режим свободного общения активирован.\nОтправьте сообщение:",
            reply_markup=get_main_keyboard(),
        )

    @dp.message(UserStates.WAITING_FOR_QUERY)
    async def process_rag_query(message: types.Message, bot: Bot):
        """Обрабатывает запрос в режиме поиска по базе знаний."""
        user_id = message.from_user.id
        if user_modes.get(user_id) != "RAG":
            logger.warning(f"Пользователь {user_id} попытался использовать поиск без активации режима.")
            await message.answer("Пожалуйста, активируйте режим поиска по базе знаний.")
            return

        async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
            logger.info(f"Обработка запроса пользователя {user_id}: {message.text}")
            response = await generate_response(message.text, use_context=True)
            await message.answer(response, reply_markup=get_main_keyboard())

    @dp.message(UserStates.IN_CHAT_MODE)
    async def process_chat_message(message: types.Message, bot: Bot):
        """Обрабатывает сообщение в режиме свободного общения."""
        user_id = message.from_user.id
        if user_modes.get(user_id) != "CHAT":
            logger.warning(f"Пользователь {user_id} попытался использовать чат без активации режима.")
            await message.answer("Пожалуйста, активируйте режим свободного общения.")
            return

        async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
            logger.info(f"Обработка сообщения пользователя {user_id}: {message.text}")
            response = await generate_response(message.text, use_context=False)
            await message.answer(response, reply_markup=get_main_keyboard())
