import os
import sys
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import OpenAI

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Получаем переменные
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logger.info("=" * 60)
logger.info("🚀 ЗАПУСК MFF БОТА (POLLING MODE)")
logger.info("=" * 60)

# Инициализация
client = OpenAI(api_key=OPENAI_API_KEY)
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
    logger.info(f"User {message.from_user.id} sent /start")
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

# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    logger.info(f"User {user_id} message: {message.text}")
    
    # Проверяем, выбран ли персонаж
    if user_id not in user_sessions:
        await message.answer("Please choose a character first with /start")
        return
    
    # Показываем "печатает..."
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    character = user_sessions[user_id]
    
    try:
        # Запрос к OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": CHARACTERS[character]},
                {"role": "user", "content": message.text}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        reply = response.choices[0].message.content
        await message.answer(reply)
        
        logger.info(f"Bot reply: {reply[:50]}...")
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await message.answer("Sorry, I'm having connection issues. Try again in a moment!")

# Запуск поллинга
async def main():
    logger.info("🤖 Запуск бота в режиме polling...")
    logger.info("📱 Отправьте /start боту в Telegram")
    
    # Удаляем вебхук если был
    await bot.delete_webhook(drop_pending_updates=True)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
