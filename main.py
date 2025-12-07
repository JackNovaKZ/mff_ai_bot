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
import google.generativeai as genai

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
        sys.stderr.write("%s - %s\n" % (self.address_string(), format%args))

def start_http_server():
    """Запуск HTTP сервера для Render"""
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    sys.stderr.write(f"🌐 HTTP Server started on port {port}\n")
    server.serve_forever()

# ========== TELEGRAM БОТ ==========
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Получаем переменные
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

# ========== ФИНАЛЬНЫЕ ИСПРАВЛЕННЫЕ ПРОМПТЫ ==========
CHARACTERS = {
    "Emily": """Ты Emily Carter, 13 лет из Сан-Диего, Калифорния, США.
Личность: дружелюбная, позитивная, творческая, любишь искусство.
Интересы: рисование, поп-музыка, сёрфинг для начинающих, Roblox, суши, мороженое, собаки.
Не любишь: математику, рыбу, сильную жару.

Ты общаешься с учеником 6 класса, который учит английский.

ВАЖНЕЙШЕЕ ПРАВИЛО: Когда ученик задаёт тебе вопрос - ТЫ ДОЛЖЕН ОТВЕТИТЬ НА НЕГО!

Как отвечать:
1. Сначала ДАЙ ПРЯМОЙ ОТВЕТ на вопрос
2. Ответ должен быть КОРОТКИМ (1-2 предложения)
3. Говори ТОЛЬКО на английском
4. Будь дружелюбной
5. Можно добавить встречный вопрос

Примеры:
- Вопрос: "How old are you?" → Ответ: "I'm 13 years old!"
- Вопрос: "Where are you from?" → Ответ: "I'm from San Diego, California!"
- Вопрос: "What do you like?" → Ответ: "I love drawing and surfing!"
- Вопрос: "Do you have pets?" → Ответ: "Yes! I have a dog named Sparky!"

Если не понимаешь вопрос: "Could you ask that differently?"

ПОМНИ: Твоя главная задача - ОТВЕЧАТЬ НА ВОПРОСЫ ученика!""",

    "John": """Ты John Williams, 12 лет из Кембриджа, Великобритания.
Личность: спокойный, терпеливый, дружелюбный, любишь спорт.
Интересы: футбол (болеешь за Chelsea), крикет, шахматы, видеоигры, выпечка, чай.
Не любишь: рыбу, брокколи, фильмы ужасов, скучные уроки.

Ты общаешься с учеником 6 класса, который учит английский.

ВАЖНЕЙШЕЕ ПРАВИЛО: Когда ученик задаёт тебе вопрос - ТЫ ДОЛЖЕН ОТВЕТИТЬ НА НЕГО!

Как отвечать:
1. Сначала ДАЙ ЧЁТКИЙ ОТВЕТ на вопрос
2. Ответ должен быть ЯСНЫМ и коротким
3. Говори ТОЛЬКО на английском
4. Будь терпеливым
5. Можно задать свой вопрос

Примеры:
- Вопрос: "How old are you?" → Ответ: "I'm 12 years old!"
- Вопрос: "Where do you live?" → Ответ: "I live in Cambridge, UK!"
- Вопрос: "What sports do you play?" → Ответ: "I play football every weekend!"
- Вопрос: "Do you like video games?" → Ответ: "Yes! I love Minecraft and FIFA!"

Если вопрос непонятен: "Could you rephrase that, please?"

ПОМНИ: Твоя главная задача - ПОМОГАТЬ с практикой английского, отвечая на вопросы!"""
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
        greeting = "Hi! I'm Emily from California! 😊 Ask me anything!"
    else:
        greeting = "Hello! I'm John from the UK! ⚽ What would you like to know?"
    
    await callback.answer(f"You chose {character}!")
    await callback.message.answer(greeting)
    logger.info(f"User {user_id} selected {character}")

# Функция для получения ответа от Gemini
async def get_gemini_response(character: str, user_message: str) -> str:
    """Получаем ответ от Gemini API"""
    try:
        if not GEMINI_API_KEY:
            raise Exception("No Gemini API key")
        
        system_prompt = CHARACTERS[character]
        
        # Жёсткий промпт с фокусом на ответе
        full_prompt = f"""{system_prompt}

СТУДЕНТ СПРАШИВАЕТ: "{user_message}"

ЭТО ВОПРОС! Ты должен ответить на него.

ТВОЙ ОТВЕТ ДОЛЖЕН:
1. Сначала ответить на вопрос студента
2. Быть коротким и ясным
3. Быть на английском
4. Быть дружелюбным
5. Не игнорировать вопрос!

НАПИШИ СВОЙ ОТВЕТ (на английском):"""
        
        model = genai.GenerativeModel('gemini-pro')
        
        response = model.generate_content(
            full_prompt,
            generation_config={
                'max_output_tokens': 120,
                'temperature': 0.3,  # Меньше креативности, больше точности
                'top_p': 0.8,
                'top_k': 40
            }
        )
        
        reply = response.text.strip()
        
        # Очистка ответа
        import re
        reply = re.sub(r'^\s*(Emily|John|Assistant|AI|Bot):\s*', '', reply, flags=re.IGNORECASE)
        reply = reply.strip()
        
        # Если ответ слишком общий - пробуем ещё раз
        if len(reply) < 10 or reply.lower().startswith(('hello', 'hi', 'hey')):
            raise Exception("Response too generic")
        
        return reply
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        raise

# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if not message.text or message.text.startswith('/'):
        return
    
    logger.info(f"User {user_id}: {message.text[:50]}...")
    
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
        
        if not reply or len(reply.strip()) < 5:
            raise Exception("Empty or too short response")
            
        await message.answer(reply)
        logger.info(f"Bot ({character}): {reply[:50]}...")
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        # Умные fallback ответы в зависимости от вопроса
        if '?' in message.text:
            # Если был вопрос - даём ответ
            if "old" in message.text.lower():
                reply = "I'm 13 years old!" if character == "Emily" else "I'm 12 years old!"
            elif "where" in message.text.lower():
                reply = "I'm from California!" if character == "Emily" else "I'm from England!"
            elif "name" in message.text.lower():
                reply = "I'm Emily!" if character == "Emily" else "I'm John!"
            else:
                reply = {
                    "Emily": "That's a good question! I think...",
                    "John": "Hmm, let me think about that..."
                }[character]
        else:
            # Если не вопрос - обычный ответ
            fallback_responses = {
                "Emily": [
                    "Hi! What would you like to know about me?",
                    "Nice to chat! Ask me anything!",
                    "Hello! I'm here to help with English practice!"
                ],
                "John": [
                    "Hey! Ready to practice English?",
                    "Hi there! What's on your mind?",
                    "Hello! Want to chat about hobbies or school?"
                ]
            }
            import random
            reply = random.choice(fallback_responses[character])
        
        await message.answer(reply)

# Запуск Telegram бота
async def run_telegram_bot():
    """Запуск Telegram бота в режиме polling"""
    logger.info("🤖 Starting Telegram bot polling...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🗑️ Old webhooks cleared")
    
    try:
        await bot.session.close()
        logger.info("🔒 Old bot session closed")
    except:
        pass
    
    await asyncio.sleep(3)
    logger.info("⏱️ Waited 3 seconds for cleanup")
    
    logger.info("🚀 Starting fresh polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

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
        asyncio.run(run_telegram_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()
