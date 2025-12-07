import os
import sys
import logging
import threading
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from http.server import HTTPServer, BaseHTTPRequestHandler
import google.generativeai as genai  # <-- НОВЫЙ ИМПОРТ

# ========== HTTP СЕРВЕР ДЛЯ RENDER ==========
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <html>
        <head><title>MFF Bot</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ MFF Bot is Running!</h1>
            <p>Telegram: @MFF_ai_bot</p>
            <p>Send /start to start chatting</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        # Пишем логи в stderr
        sys.stderr.write("%s - %s\n" % (self.address_string(), format%args))

def start_http_server():
    """Запуск HTTP сервера для Render"""
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    sys.stderr.write(f"🌐 HTTP Server started on port {port}\n")
    server.serve_forever()

# ========== TELEGRAM БОТ ==========
# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Получаем переменные
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # <-- ИЗМЕНЕНО

logger.info("=" * 60)
logger.info("🤖 STARTING MFF TELEGRAM BOT")
logger.info("=" * 60)

if not TOKEN:
    logger.error("❌ Missing TELEGRAM_TOKEN!")
    sys.exit(1)

logger.info(f"✅ Telegram Token: {TOKEN[:10]}...")

# Настройка Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info(f"✅ Gemini API Key: {GEMINI_API_KEY[:10]}...")
else:
    logger.warning("⚠️ No Gemini API Key, will use fallback responses")

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Промпты для персонажей
CHARACTERS = {
    "Emily": """You are Emily Carter, 13 years old from San Diego, California, USA.
You are friendly, positive and a bit talkative.
You like: drawing, music, beach, beginner surfing, Roblox, pop-punk music, sushi rolls, ice cream, milkshakes.
You dislike: math homework, fish, extreme heat.
You are chatting with a 6th-grade student learning English. Speak ONLY in English.
Keep your responses simple, friendly and helpful for language practice.
If user says "Bottle of water", reply: "Okay, I'm back. What's interesting with you?" """,
    
    "John": """You are John Williams, 12 years old from Cambridge, UK.
You are friendly, calm and patient with language learners.
You like: football, cricket, volunteering, playing with younger brother, chess, cherry pie, fresh pastries, milk tea, bubble tea.
You dislike: fish, broccoli, horror movies, math (but you manage), skateboarding after falling.
You speak English and basic French. Chat ONLY in English.
Keep sentences simple for a 6th-grade ESL student.
If user says "Bottle of water", reply: "Okay. Funny. I'll stay for 30 minutes more. Do you have something important?" """
}

# Хранение выбора пользователей
user_sessions = {}

# Клавиатура выбора персонажа
def get_characters_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Emily 🇺🇸", callback_data="char_Emily"),
        InlineKeyboardButton(text="John 🇬🇧", callback_data="char_John")
    )
    return builder.as_markup()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"👤 User {message.from_user.id} sent /start")
    await message.answer(
        "👋 Welcome to **MFF - My Foreign Friend!**\n\n"
        "Practice English by chatting with virtual friends:\n\n"
        "• **Emily** - 13 years, California, loves drawing & surfing\n"
        "• **John** - 12 years, UK, loves football & chess\n\n"
        "Choose your conversation partner:",
        reply_markup=get_characters_keyboard(),
        parse_mode="Markdown"
    )

# Выбор персонажа
@dp.callback_query(lambda c: c.data and c.data.startswith("char_"))
async def select_character(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    character = callback.data.split("_")[1]
    user_sessions[user_id] = character
    
    if character == "Emily":
        greeting = "Hi there! 😊 I'm Emily from sunny California! Do you like drawing or maybe surfing? I'm still learning but it's so fun!"
    else:
        greeting = "Hello! ⚽ I'm John from Cambridge. Nice to meet you! Do you play football or chess? I love both!"
    
    await callback.answer(f"You chose {character}!")
    await callback.message.answer(greeting)
    logger.info(f"User {user_id} selected {character}")

# Функция для получения ответа от Gemini
async def get_gemini_response(character: str, user_message: str) -> str:
    """Получаем ответ от Gemini API"""
    try:
        if not GEMINI_API_KEY:
            raise Exception("No Gemini API key")
        
        # Подготовка промпта
        system_prompt = CHARACTERS[character]
        full_prompt = f"{system_prompt}\n\nUser: {user_message}\n\nYour response:"
        
        # Создаем модель
        model = genai.GenerativeModel('gemini-pro')
        
        # Генерируем ответ
        response = model.generate_content(
            full_prompt,
            generation_config={
                'max_output_tokens': 150,
                'temperature': 0.7,
            }
        )
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        raise

# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Пропускаем команды
    if not message.text or message.text.startswith('/'):
        return
    
    logger.info(f"User {user_id}: {message.text[:50]}...")
    
    # Проверяем, выбран ли персонаж
    if user_id not in user_sessions:
        await message.answer("Please choose a character first with /start")
        return
    
    # Показываем "печатает..."
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except:
        pass
    
    character = user_sessions[user_id]
    
    try:
        # Запрос к Gemini
        reply = await get_gemini_response(character, message.text)
        
        # Если Gemini вернул пустой ответ
        if not reply:
            raise Exception("Empty response from Gemini")
            
        await message.answer(reply)
        logger.info(f"Bot ({character}): {reply[:50]}...")
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        # Fallback ответы
        fallback_responses = {
            "Emily": [
                "Hi there! 😊 What would you like to talk about?",
                "Hey! How's your day going?",
                "Nice to chat with you! What are your hobbies?"
            ],
            "John": [
                "Hello! ⚽ Ready for a conversation?",
                "Hey there! What's on your mind?",
                "Good to see you! Want to chat about sports or games?"
            ]
        }
        import random
        reply = random.choice(fallback_responses[character])
        await message.answer(reply)

# Запуск Telegram бота
async def run_telegram_bot():
    """Запуск Telegram бота в режиме polling"""
    logger.info("🤖 Starting Telegram bot polling...")
    
    # Удаляем старый вебхук если был
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🗑️ Old webhooks cleared")
    
    # Запускаем polling
    await dp.start_polling(bot)

def start_bot():
    """Запуск бота в отдельном потоке"""
    asyncio.run(run_telegram_bot())

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def main():
    logger.info("🚀 Starting MFF Bot System...")
    
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    logger.info("🌐 HTTP server thread started")
    
    # Запускаем Telegram бота в основном потоке
    logger.info("🤖 Starting Telegram bot...")
    logger.info("📱 Send /start to your bot in Telegram!")
    
    try:
        # Запускаем бота
        asyncio.run(run_telegram_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()
