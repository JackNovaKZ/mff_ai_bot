import os
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import OpenAI
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

# НАСТРОЙКА ЛОГИРОВАНИЯ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("🚀 STARTING MFF BOT WEB SERVER")
logger.info("=" * 60)

# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://mff-ai-bot-5.onrender.com")
PORT = int(os.getenv("PORT", 10000))

if not TOKEN or not OPENAI_API_KEY:
    logger.error("❌ Missing environment variables!")
    sys.exit(1)

logger.info(f"✅ Telegram Token: {TOKEN[:10]}...")
logger.info(f"✅ OpenAI Key: {OPENAI_API_KEY[:10]}...")

# ИНИЦИАЛИЗАЦИЯ
client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ПРОМПТЫ
CHARACTERS = {
    "Emily": """You are Emily, 13 years old from California. Speak friendly English to help students learn. Keep responses simple.""",
    "John": """You are John, 12 years old from UK. Speak simple English to help students practice. Be patient and friendly."""
}

user_sessions = {}

# КЛАВИАТУРА
def get_characters_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Emily 🇺🇸", callback_data="char_Emily"),
        InlineKeyboardButton(text="John 🇬🇧", callback_data="char_John")
    )
    return builder.as_markup()

# КОМАНДА /START
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"User {message.from_user.id}: /start")
    await message.answer(
        "👋 Welcome to MFF!\nChoose your friend:",
        reply_markup=get_characters_keyboard()
    )

# ВЫБОР ПЕРСОНАЖА
@dp.callback_query(lambda c: c.data and c.data.startswith("char_"))
async def select_character(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    character = callback.data.split("_")[1]
    user_sessions[user_id] = character
    
    greeting = f"Hi! I'm {character}. Let's chat in English! 😊"
    await callback.answer(f"You chose {character}!")
    await callback.message.answer(greeting)
    logger.info(f"User {user_id} selected {character}")

# ОБРАБОТКА СООБЩЕНИЙ
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if not message.text or message.text.startswith('/'):
        return
    
    if user_id not in user_sessions:
        await message.answer("Please choose a character with /start")
        return
    
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except:
        pass
    
    character = user_sessions[user_id]
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": CHARACTERS[character]},
                {"role": "user", "content": message.text}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        reply = response.choices[0].message.content
        await message.answer(reply)
        logger.info(f"Reply to {user_id}: {reply[:30]}...")
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await message.answer("Sorry, technical issues. Try again!")

# ВЕБ-СЕРВЕР И ВЕБХУКИ
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

logger.info(f"🌐 Webhook URL: {WEBHOOK_URL}")
logger.info(f"🔌 Port: {PORT}")

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    logger.info("✅ Webhook removed")

# HEALTH CHECK
async def health_check(request):
    return web.Response(text="✅ MFF Bot is running!\nSend /start in Telegram")

# СОЗДАНИЕ И ЗАПУСК СЕРВЕРА
def main():
    logger.info("🌍 Creating web application...")
    
    app = web.Application()
    
    # Регистрируем вебхук
    handler = SimpleRequestHandler(dp, bot)
    handler.register(app, path=WEBHOOK_PATH)
    
    # Добавляем health check
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    # Startup/shutdown
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    logger.info(f"🚀 Starting server on port {PORT}...")
    logger.info("🤖 Bot is ready! Send /start in Telegram")
    
    # Запускаем сервер
    web.run_app(
        app,
        host='0.0.0.0',
        port=PORT,
        access_log=logger,
        print=None  # Отключаем стандартный вывод aiohttp
    )

if __name__ == "__main__":
    main()
