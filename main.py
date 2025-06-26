
import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настройки канала (замените на ваши значения)
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")  # ID канала
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/your_channel")  # URL канала
TEAM_URL = "https://lichess.org/team/ilAYFF9R"  # URL команды Lichess

# Информация о турнирах
TOURNAMENTS = {
    "stage_1": {
        "name": "1-й этап",
        "date": "28.06.2025",
        "description": "28.06.2025 пройдёт 1-й этап онлайн-турнир CCL."
    },
    "stage_2": {
        "name": "2-й этап", 
        "date": "05.07.2025",
        "description": "05.07.2025 пройдёт 2-й этап онлайн-турнир CCL."
    },
    "stage_3": {
        "name": "3-й этап",
        "date": "12.07.2025", 
        "description": "12.07.2025 пройдёт 3-й этап онлайн-турнир CCL."
    }
}

# Функция для проверки подписки
async def check_subscription(user_id: int) -> bool:
    """Проверяет подписку пользователя на канал"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки для пользователя {user_id}: {e}")
        return False

# Функция создания клавиатуры с этапами
def create_stages_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками этапов турнира"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 1 этап", callback_data="stage_1"),
            InlineKeyboardButton(text="🏆 2 этап", callback_data="stage_2")
        ],
        [
            InlineKeyboardButton(text="🏆 3 этап", callback_data="stage_3")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_stages")
        ]
    ])
    return keyboard

# Функция создания клавиатуры подписки
def create_subscription_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой подписки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])
    return keyboard

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = (
        "🏆 Добро пожаловать в бот турниров CCL!\n\n"
        "Используйте команду /tourname для участия в турнире.\n"
        "Для участия необходимо быть подписанным на наш канал."
    )
    await message.answer(welcome_text)

# Обработчик команды /tourname
@dp.message(Command("tourname"))
async def tourname_command(message: types.Message):
    """Основной обработчик команды турнира"""
    user_id = message.from_user.id
    username = message.from_user.username or "Неизвестно"

    logger.info(f"Пользователь {username} ({user_id}) вызвал команду /tourname")

    # Проверяем подписку
    if await check_subscription(user_id):
        await message.answer(
            "🏆 Выберите этап турнира CCL:\n\n"
            "Все этапы проходят онлайн на платформе Lichess.",
            reply_markup=create_stages_keyboard()
        )
    else:
        await message.answer(
            "❌ Пожалуйста, подпишитесь на канал:\n\n"
            "Для участия в турнире необходимо быть подписанным на наш официальный канал.",
            reply_markup=create_subscription_keyboard()
        )

# Обработчик проверки подписки
@dp.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: types.CallbackQuery):
    """Обработчик повторной проверки подписки"""
    user_id = callback.from_user.id

    if await check_subscription(user_id):
        await callback.message.edit_text(
            "🏆 Выберите этап турнира CCL:\n\n"
            "Все этапы проходят онлайн на платформе Lichess.",
            reply_markup=create_stages_keyboard()
        )
    else:
        await callback.answer(
            "❌ Вы ещё не подписались на канал. Пожалуйста, подпишитесь и попробуйте снова.",
            show_alert=True
        )

    await callback.answer()

# Обработчик обновления этапов
@dp.callback_query(F.data == "refresh_stages")
async def refresh_stages_handler(callback: types.CallbackQuery):
    """Обработчик обновления списка этапов"""
    user_id = callback.from_user.id

    if await check_subscription(user_id):
        await callback.message.edit_reply_markup(reply_markup=create_stages_keyboard())
        await callback.answer("✅ Список этапов обновлён!")
    else:
        await callback.message.edit_text(
            "❌ Пожалуйста, подпишитесь на канал:",
            reply_markup=create_subscription_keyboard()
        )
        await callback.answer("❌ Подписка не найдена!", show_alert=True)

# Универсальный обработчик этапов
@dp.callback_query(F.data.startswith("stage_"))
async def stage_handler(callback: types.CallbackQuery):
    """Универсальный обработчик кнопок этапов"""
    stage_id = callback.data

    # Проверяем подписку
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ Пожалуйста, подпишитесь на канал:",
            reply_markup=create_subscription_keyboard()
        )
        await callback.answer("❌ Необходима подписка на канал!", show_alert=True)
        return

    # Получаем информацию о турнире
    tournament = TOURNAMENTS.get(stage_id)
    if not tournament:
        await callback.answer("❌ Этап не найден!", show_alert=True)
        return

    # Создаем клавиатуру для этапа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Участвовать в этапе", url=TEAM_URL)],
        [InlineKeyboardButton(text="⬅️ Назад к этапам", callback_data="back_to_stages")]
    ])

    # Формируем текст сообщения
    message_text = (
        f"🏆 {tournament['name']} онлайн-турнир CCL\n\n"
        f"📅 Дата: {tournament['date']}\n\n"
        f"📝 {tournament['description']}\n\n"
        f"Чтобы принять участие необходимо быть участником нашей "
        f"[команды на Lichess]({TEAM_URL})."
    )

    await callback.message.edit_text(
        message_text,
        reply_markup=keyboard,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await callback.answer()

# Обработчик возврата к этапам
@dp.callback_query(F.data == "back_to_stages")
async def back_to_stages_handler(callback: types.CallbackQuery):
    """Обработчик возврата к списку этапов"""
    await callback.message.edit_text(
        "🏆 Выберите этап турнира CCL:\n\n"
        "Все этапы проходят онлайн на платформе Lichess.",
        reply_markup=create_stages_keyboard()
    )
    await callback.answer()

# Обработчик команды /help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Обработчик команды помощи"""
    help_text = (
        "🤖 **Команды бота CCL Tournament:**\n\n"
        "/start - Начать работу с ботом\n"
        "/tourname - Участие в турнире\n"
        "/help - Показать эту справку\n\n"
        "📋 **Как участвовать:**\n"
        "1. Подпишитесь на наш канал\n"
        "2. Используйте команду /tourname\n"
        "3. Выберите этап турнира\n"
        "4. Вступите в команду на Lichess\n\n"
        "❓ При возникновении проблем обратитесь к администраторам канала."
    )
    await message.answer(help_text, parse_mode="Markdown")

# Основная функция запуска бота
async def main():
    """Основная функция запуска бота"""
    try:
        # Удаляем вебхуки и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🤖 Бот запущен успешно!")
        logger.info(f"📢 ID канала: {CHANNEL_ID}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска бота: {e}")
        raise

# Обработчик завершения работы
async def shutdown():
    """Корректное завершение работы бота"""
    logger.info("🔄 Завершение работы бота...")
    await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка: {e}")
    finally:
        asyncio.run(shutdown())
