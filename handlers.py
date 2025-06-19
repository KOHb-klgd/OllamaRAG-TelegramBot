from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from typing import Dict, List
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


async def send_long_message(message: types.Message, text: str, max_length: int = 4096):
    """
    Отправляет длинное сообщение частями.
    """
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        await message.answer(chunk)


async def send_citation_chunks(message: types.Message, chunks_info: List[Dict]):
    """
    Отправляет цитируемые чанки, цитируя только первые три предложения каждого чанка.
    """
    if not chunks_info:
        await message.answer("Нет цитат для отображения.")
        return

    # Отправляем заголовок для цитат
    await message.answer("📚 **Релевантные цитаты:**", parse_mode=ParseMode.MARKDOWN)

    for chunk in chunks_info:
        source = chunk.get("source", "Неизвестный источник")
        section = chunk.get("section", "Неизвестный раздел")
        content = chunk.get("content", "Нет данных")

        # Ограничиваем текст чанка первыми тремя предложениями
        sentences = content.split('.')
        first_three_sentences = '.'.join(sentences[:3]) + '.'  # Берем первые три предложения и добавляем точку

        # Формируем текст цитаты
        citation_text = f"📄 **Источник:** {source}\n"
        citation_text += f"🔖 **Раздел:** {section}\n"
        citation_text += f"📝 **Текст:** {first_three_sentences}\n"

        # Проверяем длину текста
        if len(citation_text) > 4096:
            # Если текст слишком длинный, отправляем его частями
            await send_long_message(message, citation_text)
        else:
            # Если текст в пределах лимита, отправляем как есть
            await message.answer(citation_text, parse_mode=ParseMode.MARKDOWN)


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

            # Получаем ответ от LLM и цитируемые чанки
            response, chunks_info = await generate_response(message.text, use_context=True)

            # Отправляем ответ от LLM
            await message.answer(response, reply_markup=get_main_keyboard())

            # Отправляем цитируемые чанки
            if chunks_info:
                await send_citation_chunks(message, chunks_info[:3])

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
            response, _ = await generate_response(message.text, use_context=False)
            await message.answer(response, reply_markup=get_main_keyboard())
