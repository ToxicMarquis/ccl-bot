import os
import asyncio
import logging
import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile, InputMediaPhoto
from aiogram.filters import Command
from functools import wraps

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

CHANNEL_ID = os.getenv("CHANNEL_ID", "@chesstourname")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/chesstourname")
TEAM_URL = "https://lichess.org/team/ilAYFF9R"
MAIN_URL = "https://i.imgur.com/h6WQbRi.png"
ADMINS = {1834341648, 657785765}
BROADCAST_DELAY = 0.05
DB_PATH = "/data/ccl_bot.db"
TOURNAMENTS = {
    "stage_1": {
        "name": "1-й этап",
        "date": "28.06.2025 12:00 по Мск (завершился)",
        "description": "Режим: <a href='https://lichess.org/variant/kingOfTheHill'>King of the Hill</a>\nДлительность: 90 минут\nКонтроль: 5+0",
        "stage_url": "https://lichess.org/tournament/JTR3p99u",
        "img_url": "https://i.imgur.com/1pzxEG1.png"
    },
    "stage_2": {
        "name": "2-й этап", 
        "date": "05.07.2025 12:00 по Мск (завершился)",
        "description": "Режим: <a href='https://lichess.org/variant/Horde'>Horde</a>\nДлительность: 90 минут\nКонтроль: 5+0",
        "stage_url": "https://lichess.org/tournament/j46dTG8F",
        "img_url": "https://ibb.co/XrwwVmQs"
    },
    "stage_3": {
        "name": "3-й этап",
        "date": "12.07.2025 12:00 по Мск", 
        "description": "Режим: <a href='https://lichess.org/variant/ThreeCheck'>Three Check</a>\nДлительность: 90 минут\nКонтроль: 5+0",
        "stage_url": "https://lichess.org/tournament/Y7HE5KFl",
        "img_url": "https://i.imgur.com/zH4aoF3.png"
    }
}

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS)
        await db.commit()
        yield db

async def add_user(uid: int):
    async with get_db() as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
        await db.commit()

async def get_all_user_ids() -> list[int]:
    async with get_db() as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
    return [r[0] for r in rows]

async def users_count() -> int:
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
    return row[0] if row else 0

def admin_only(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        # Находим объект message или callback из args/kwargs
        message = None
        for arg in args:
            if isinstance(arg, types.Message):
                message = arg
                break
        if not message:
            message = kwargs.get("message")
        if not message:
            callback = next((a for a in args if isinstance(a, types.CallbackQuery)), None)
            if callback:
                message = callback.message

        user_id = None
        if message:
            user_id = message.from_user.id
        elif "event_from_user" in kwargs:
            user_id = kwargs["event_from_user"].id

        if user_id in ADMINS:
            return await handler(*args, **kwargs)
        if message:
            await message.answer("⛔ Доступ запрещён")
        return
    return wrapper

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки для пользователя {user_id}: {e}")
        return False

def create_stages_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 1 этап", callback_data="stage_1"),
            InlineKeyboardButton(text="🏆 2 этап", callback_data="stage_2"),
            InlineKeyboardButton(text="🏆 3 этап", callback_data="stage_3")
        ]
    ])
    return keyboard

def create_subscription_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])
    return keyboard

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await add_user(message.from_user.id)
    
    welcome_text = (
        "🏆 <b>Добро пожаловать в бот турниров CCL!</b>\n"
        "Используйте команду /tourname для участия в турнире.\n"
        "Для участия необходимо быть подписанным на наш канал."
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("tourname"))
async def tourname_command(message: types.Message):
    await add_user(message.from_user.id)
    
    user_id = message.from_user.id
    username = message.from_user.username or "Неизвестно"

    logger.info(f"Пользователь {username} ({user_id}) вызвал команду /tourname")

    if await check_subscription(user_id):
        await message.answer_photo(
            photo=MAIN_URL,
            caption=(
                "🏆 <b>Выберите этап турнира CCL:</b>\n"
                "Все этапы проходят онлайн на платформе Lichess."
            ),
            reply_markup=create_stages_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Пожалуйста, подпишитесь на канал:</b>\n"
            "Для участия в турнире необходимо быть подписанным на наш официальный канал.",
            reply_markup=create_subscription_keyboard(),
            parse_mode="HTML"
        )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await add_user(message.from_user.id)
    
    help_text = (
        "🤖 <b>Команды бота CCL Tournament:</b>\n"
        "/start - Начать работу с ботом\n"
        "/tourname - Участие в турнире\n"
        "/help - Показать эту справку\n\n"
        "📋 <b>Как участвовать:</b>\n"
        "1. Подпишитесь на наш канал\n"
        "2. Используйте команду /tourname\n"
        "3. Выберите этап турнира\n"
        "4. Вступите в команду на Lichess\n\n"
        "❓ При возникновении проблем обратитесь к администраторам канала."
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("stats"))
@admin_only
async def stats_command(message: types.Message):
    count = await users_count()
    await message.answer(f"👥 Всего пользователей: <b>{count}</b>", parse_mode="HTML")

@dp.message(Command("broadcast"))
@admin_only
async def broadcast_command(message: types.Message):
    # Извлекаем текст после команды
    text = message.text.replace("/broadcast", "").strip()
    
    if not text:
        await message.answer("⚠️ Использование: /broadcast текст сообщения")
        return

    users = await get_all_user_ids()
    sent, failed = 0, 0
    
    status_msg = await message.answer(f"📤 Начинаю рассылку {len(users)} пользователям...")

    for uid in users:
        try:
            await bot.send_message(uid, text, parse_mode="HTML", disable_web_page_preview=True)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Не удалось отправить пользователю {uid}: {e}")
        
        await asyncio.sleep(BROADCAST_DELAY)

    await status_msg.edit_text(
        f"✅ Рассылка завершена.\n"
        f"Успешно: <b>{sent}</b>\n"
        f"Ошибки: <b>{failed}</b>",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await check_subscription(user_id):
        await callback.message.delete()
        
        await callback.message.answer_photo(
            photo=MAIN_URL,
            caption=(
                "🏆 <b>Выберите этап турнира CCL:</b>\n"
                "Все этапы проходят онлайн на платформе Lichess."
            ),
            reply_markup=create_stages_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer(
            "❌ Вы ещё не подписались на канал. Пожалуйста, подпишитесь и попробуйте снова.",
            show_alert=True
        )

    await callback.answer()

@dp.callback_query(F.data.startswith("stage_"))
async def stage_handler(callback: types.CallbackQuery):
    stage_id = callback.data
    user_id = callback.from_user.id

    if not await check_subscription(user_id):
        await callback.message.delete()
        
        await callback.message.answer(
            "❌ <b>Пожалуйста, подпишитесь на канал:</b>",
            reply_markup=create_subscription_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("❌ Необходима подписка на канал!", show_alert=True)
        return

    tournament = TOURNAMENTS.get(stage_id)
    if not tournament:
        await callback.answer("❌ Этап не найден!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Перейти к этапу", url=tournament["stage_url"])],
        [InlineKeyboardButton(text="⬅️ Назад к этапам", callback_data="back_to_stages")]
    ])

    message_text = (
        f"🏆 <b>{tournament['name']} онлайн-турнира CCL</b>\n"
        f"📅 <b>Дата:</b> {tournament['date']}\n"
        f"📝 <b>Детали:</b>\n{tournament['description']}\n\n"
        f"Чтобы принять участие необходимо быть участником нашей "
        f"<a href='{TEAM_URL}'>команды на Lichess</a>."
    )

    await callback.message.delete()
    
    await callback.message.answer_photo(
        photo=tournament["img_url"],
        caption=message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_stages")
async def back_to_stages_handler(callback: types.CallbackQuery):
    await callback.message.delete()
    
    await callback.message.answer_photo(
        photo=MAIN_URL,
        caption=(
            "🏆 <b>Выберите этап турнира CCL:</b>\n"
            "Все этапы проходят онлайн на платформе Lichess."
        ),
        reply_markup=create_stages_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🤖 Бот запущен успешно!")
        logger.info(f"📢 ID канала: {CHANNEL_ID}")
        logger.info(f"📊 Администраторы: {ADMINS}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска бота: {e}")
        raise

async def shutdown():
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
