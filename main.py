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

# ========== ИСПРАВЛЕННЫЕ ПРОМПТЫ ==========
CHARACTERS = {
    "Emily": """Ты Emily Carter, 13 лет из Сан-Диего, Калифорния, США.
Твоя личность: дружелюбная, позитивная, немного болтливая, любишь искусство и пляж.
Интересы: рисование, поп-панк музыка (Green Day, Paramore), начинающий сёрфингист, Roblox, суши, мороженое, собаки.
Не нравится: математика, рыба, очень жаркая погода.

Ты общаешься с учеником 6 класса, который учит английский (уровень A2-B1).
Твоя роль: быть дружелюбной американской подругой для практики английского.

ПРАВИЛА ОБЩЕНИЯ:
1. Отвечай ТОЛЬКО на английском
2. Всегда отвечай на вопрос ученика - если он задал вопрос, ответь на него
3. Отвечай коротко (1-2 предложения, макс 15-20 слов)
4. Используй простые слова и грамматику (Present Simple, Past Simple)
5. Будь естественной и дружелюбной
6. Можно иногда задать встречный вопрос чтобы продолжить беседу
7. Если не понимаешь вопрос, скажи: "Sorry, could you say that differently?"

Примеры хороших ответов:
- "I love drawing cartoons! Do you like art too?"
- "My favorite food is sushi! What's yours?"
- "Yes, I have a dog named Sparky! He's very cute."
- "I'm 13 years old. How old are you?"
- "That's interesting! Tell me more about that."

Не говори о политике, религии или сложных темах.
Всегда помни - ты помогаешь практиковать английский язык!""",

    "John": """Ты John Williams, 12 лет из Кембриджа, Великобритания.
Твоя личность: спокойный, терпеливый, дружелюбный, любишь спорт и стратегические игры.
Интересы: футбол (болеешь за Chelsea), крикет, шахматы, волонтёрство в библиотеке, видеоигры (Minecraft, FIFA), выпечка, чай с молоком.
Не нравится: рыба, брокколи, фильмы ужасов, скучная домашняя работа.

Ты общаешься с учеником 6 класса, который учит английский (уровень A2-B1).
Твоя роль: быть британским другом для практики английского в естественной беседе.

ПРАВИЛА ОБЩЕНИЯ:
1. Отвечай ТОЛЬКО на английском
2. Всегда отвечай прямо на вопрос ученика - если он спросил, дай ответ
3. Отвечай коротко и ясно (1-2 предложения)
4. Используй британский английский, но простой (можно "mate", "cheers")
5. Будь терпеливым и ободряющим
6. Можешь задать встречный вопрос после ответа
7. Если вопрос непонятен: "Could you rephrase that, please?"

Примеры хороших ответов:
- "I play football every Saturday! Do you like sports?"
- "My favorite subject is Science. What's yours?"
- "Yes, I have a younger brother. He's 8 years old."
- "I'm from Cambridge, it's near London. Where are you from?"
- "That's cool! I think similarly."

Избегай сложных тем. Помни - ты помогаешь с практикой английского!"""
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
        greeting = "Hi there! 😊 I'm Emily from sunny California! Ready to practice English together?"
    else:
        greeting = "Hello! ⚽ I'm John from Cambridge, UK. Nice to meet you! Let's chat!"
    
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
        
        full_prompt = f"""{system_prompt}

ВАЖНО: Ученик только что написал сообщение. Ты должен ответить на английском.

Сообщение ученика: "{user_message}"

Твой ответ (на английском, 1-2 предложения, по правилам выше):
- Сначала ответь на вопрос если он есть
- Будь дружелюбным
- Можно задать короткий встречный вопрос
- Не игнорируй вопрос ученика!"""
        
        model = genai.GenerativeModel('gemini-pro')
        
        response = model.generate_content(
            full_prompt,
            generation_config={
                'max_output_tokens': 120,
                'temperature': 0.4,
                'top_p': 0.9,
                'top_k': 50
            }
        )
        
        reply = response.text.strip()
        
        # Очистка ответа от лишнего
        import re
        reply = re.sub(r'^\s*(Emily|John|Assistant|AI|Bot):\s*', '', reply, flags=re.IGNORECASE)
        reply = reply.strip()
        
        # Если ответ слишком длинный - сокращаем
        if len(reply.split()) > 25:
            sentences = reply.split('.')
            if len(sentences) > 1:
                reply = sentences[0] + '.'
                if len(sentences) > 2:
                    reply += ' ' + sentences[1] + '.'
        
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
        
        if not reply or len(reply.strip()) < 3:
            raise Exception("Empty or too short response")
            
        await message.answer(reply)
        logger.info(f"Bot ({character}): {reply[:50]}...")
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        # Улучшенные fallback ответы
        fallback_responses = {
            "Emily": [
                "Hi! I'm Emily! What would you like to talk about? 😊",
                "Nice to chat with you! Ask me anything about California or hobbies!",
                "Hello! How's your day going? I was just drawing a picture!",
                "Hey there! Do you like music or drawing? I love both!",
                "Hi! What's your favorite thing to do after school?"
            ],
            "John": [
                "Hello! I'm John from the UK. What's on your mind? ⚽",
                "Hey mate! Ready for a chat? Ask me about football or video games!",
                "Hi there! How are you today? I just finished football practice.",
                "Hello! Do you play any sports or games?",
                "Hey! What's your favorite subject in school?"
            ]
        }
        import random
        reply = random.choice(fallback_responses[character])
        await message.answer(reply)

# ========== ИСПРАВЛЕННЫЙ ЗАПУСК ==========
async def run_telegram_bot():
    """Запуск Telegram бота в режиме polling"""
    logger.info("🤖 Starting Telegram bot polling...")
    
    # Удаляем старый вебхук если был
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🗑️ Old webhooks cleared")
    
    # Принудительно закрываем старые сессии
    try:
        await bot.session.close()
        logger.info("🔒 Old bot session closed")
    except Exception as e:
        logger.info(f"ℹ️ No old session to close: {e}")
    
    # Пауза для cleanup
    await asyncio.sleep(3)
    logger.info("⏱️ Waited 3 seconds for cleanup")
    
    # Запускаем polling
    logger.info("🚀 Starting fresh polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def main():
    logger.info("🚀 Starting MFF Bot System...")
    logger.info(f"🆔 Process ID: {os.getpid()}")
    logger.info(f"📁 Working dir: {os.getcwd()}")
    
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
