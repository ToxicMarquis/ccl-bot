
import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

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

TOURNAMENTS = {
    "stage_1": {
        "name": "1-й этап",
        "date": "28.06.2025 12:00 по Мск",
        "description": "Режим: [King of the Hill](https://lichess.org/variant/kingOfTheHill)\nДлительность: 90 минут\nКонтроль: 5+0",
        "stage_url": "https://lichess.org/tournament/JTR3p99u",
        "img_url": "https://imgur.com/MGfpe8j.png"
    },
    "stage_2": {
        "name": "2-й этап", 
        "date": "05.07.2025 12:00 по Мск",
        "description": "Режим: [Horde](https://lichess.org/variant/Horde)\nДлительность: 90 минут\nКонтроль: 5+0",
        "stage_url": "https://lichess.org/tournament/j46dTG8F",
        "img_url": "https://imgur.com/amplxVA.png"
    },
    "stage_3": {
        "name": "3-й этап",
        "date": "12.07.2025 12:00 по Мск", 
        "description": "Режим: [Three Check](https://lichess.org/variant/ThreeCheck)\nДлительность: 90 минут\nКонтроль: 5+0",
        "stage_url": "https://lichess.org/tournament/Y7HE5KFl",
        "img_url": "https://imgur.com/H9MOTx7.png"
    }
}

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
    welcome_text = (
        "🏆 Добро пожаловать в бот турниров CCL!\n"
        "Используйте команду /tourname для участия в турнире.\n"
        "Для участия необходимо быть подписанным на наш канал."
    )
    await message.answer(welcome_text)

@dp.message(Command("tourname"))
async def tourname_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Неизвестно"

    logger.info(f"Пользователь {username} ({user_id}) вызвал команду /tourname")

    if await check_subscription(user_id):
        await message.answer(
            "🏆 Выберите этап турнира CCL:\n"
            "Все этапы проходят онлайн на платформе Lichess.",
            reply_markup=create_stages_keyboard()
        )
    else:
        await message.answer(
            "❌ Пожалуйста, подпишитесь на канал:\n"
            "Для участия в турнире необходимо быть подписанным на наш официальный канал.",
            reply_markup=create_subscription_keyboard()
        )

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: types.CallbackQuery):
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

@dp.callback_query(F.data.startswith("stage_"))
async def stage_handler(callback: types.CallbackQuery):
    stage_id = callback.data

    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ Пожалуйста, подпишитесь на канал:",
            reply_markup=create_subscription_keyboard()
        )
        await callback.answer("❌ Необходима подписка на канал!", show_alert=True)
        return

    tournament = TOURNAMENTS.get(stage_id)
    if not tournament:
        await callback.answer("❌ Этап не найден!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Участвовать в этапе", url=tournament["stage_url"])],
        [InlineKeyboardButton(text="⬅️ Назад к этапам", callback_data="back_to_stages")]
    ])

    message_text = types.InputMediaPhoto(
        text=f"🏆 <b>{tournament['name']} онлайн-турнира CCL</b>\n📅 Дата: {tournament['date']}\n📝 {tournament['description']}\nЧтобы принять участие необходимо быть участником нашей [команды на Lichess]({TEAM_URL}).",
        image=tournament["img_url"],
        parse_mode="HTML"
    )

    await callback.message.edit_text(
        message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_stages")
async def back_to_stages_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🏆 Выберите этап турнира CCL:\n"
        "Все этапы проходят онлайн на платформе Lichess.",
        reply_markup=create_stages_keyboard()
    )
    await callback.answer()

@dp.message(Command("help"))
async def help_command(message: types.Message):
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

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🤖 Бот запущен успешно!")
        logger.info(f"📢 ID канала: {CHANNEL_ID}")
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
