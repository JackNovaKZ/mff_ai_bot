import os
import sys
import logging
import threading
import asyncio
import aiohttp
import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from http.server import HTTPServer, BaseHTTPRequestHandler

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
            <p>Telegram: @MFF_english_bot</p>
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

logger.info("=" * 60)
logger.info("🤖 STARTING MFF BOT WITH DEEPSEEK")
logger.info("=" * 60)

if not TOKEN:
    logger.error("❌ Missing TELEGRAM_TOKEN!")
    sys.exit(1)

logger.info(f"✅ Telegram Token: {TOKEN[:10]}...")

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== DeepSeek API функция ==========
async def ask_deepseek(character: str, user_message: str) -> str:
    """Запрашиваем ответ у DeepSeek (меня)"""
    try:
        # Промпт для DeepSeek - ВСЕ КАВЫЧКИ ИСПРАВЛЕНЫ!
        if character == "Emily":
            system_prompt = """Ты Emily Carter, 13 лет из Сан-Диего, Калифорния.
Ты дружелюбная, позитивная, любишь рисование, музыку и сёрфинг.
Ты общаешься с учеником 6 класса, который учит английский.

ВАЖНО: Всегда отвечай на вопросы ученика прямо и чётко!
Отвечай только на английском, коротко (1-2 предложения), дружелюбно.

Примеры:
- "How old are you?" -> "I'm 13 years old!"
- "Where are you from?" -> "I'm from San Diego, California!"
- "What do you like?" -> "I love drawing and surfing!"

Если не понимаешь вопрос, скажи: "Could you ask that differently?""
        else:  # John
            system_prompt = """Ты John Williams, 12 лет из Кембриджа, Англия.
Ты спокойный, терпеливый, любишь футбол, шахматы и видеоигры.
Ты общаешься с учеником 6 класса, который учит английский.

ВАЖНО: Всегда отвечай на вопросы ученика прямо и чётко!
Отвечай только на английском, коротко (1-2 предложения), дружелюбно.

Примеры:
- "How old are you?" -> "I'm 12 years old!"
- "Where are you from?" -> "I'm from Cambridge, England!"
- "What do you like?" -> "I love football and chess!"

Если не понимаешь вопрос, скажи: "Could you rephrase that?""
        
        # Используем DeepSeek API
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 150,
                "temperature": 0.7,
                "stream": False
            }
            
            headers = {
                "Authorization": "Bearer sk-3b6b2e69c99c4c69966e6e64a7a2e9c2",
                "Content-Type": "application/json"
            }
            
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    reply = data["choices"][0]["message"]["content"].strip()
                    
                    # Очистка ответа
                    if reply.startswith(('Emily:', 'John:', 'Assistant:', 'AI:')):
                        reply = reply.split(':', 1)[1].strip()
                    
                    return reply
                else:
                    error_text = await response.text()
                    logger.error(f"DeepSeek API error: {response.status} - {error_text}")
                    raise Exception(f"API error: {response.status}")
                    
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        raise

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
        greeting = "Hello! I'm John from England! ⚽ What would you like to know?"
    
    await callback.answer(f"You chose {character}!")
    await callback.message.answer(greeting)
    logger.info(f"User {user_id} selected {character}")

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
        # Запрос к DeepSeek (мне)
        reply = await ask_deepseek(character, message.text)
        
        if not reply or len(reply.strip()) < 3:
            raise Exception("Empty response")
            
        await message.answer(reply)
        logger.info(f"Bot ({character}): {reply[:50]}...")
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        # Умные fallback ответы
        user_msg = message.text.lower()
        
        if '?' in message.text:
            # Это вопрос - даём осмысленный ответ
            if "how old" in user_msg:
                reply = "I'm 13 years old!" if character == "Emily" else "I'm 12 years old!"
            elif "where" in user_msg or "from" in user_msg:
                reply = "I'm from California, USA!" if character == "Emily" else "I'm from England, UK!"
            elif "name" in user_msg:
                reply = "I'm Emily!" if character == "Emily" else "I'm John!"
            elif "what do you like" in user_msg or "hobby" in user_msg:
                reply = "I love drawing and surfing!" if character == "Emily" else "I love football and chess!"
            elif "do you have" in user_msg or "pet" in user_msg:
                reply = "Yes, I have a dog named Sparky!" if character == "Emily" else "No pets, but I want a dog!"
            else:
                # Общий ответ на другие вопросы
                reply = {
                    "Emily": "That's an interesting question! I think...",
                    "John": "Good question! Let me think about that..."
                }[character]
        else:
            # Не вопрос - обычный ответ
            fallback_responses = {
                "Emily": [
                    "Hi there! How can I help you practice English today?",
                    "Nice to chat! Ask me about my hobbies or school!",
                    "Hello! I'm here to help with English conversation!"
                ],
                "John": [
                    "Hey! Ready for some English practice?",
                    "Hi! What would you like to talk about?",
                    "Hello! Want to chat about sports or games?"
                ]
            }
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
    logger.info("🚀 Starting MFF Bot with DeepSeek...")
    
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
