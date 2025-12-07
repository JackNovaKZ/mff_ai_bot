import os
import sys
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Получаем переменные
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не найден!")
    sys.exit(1)

logger.info("=" * 60)
logger.info("🚀 ЗАПУСК ПРОСТОГО ТЕСТОВОГО БОТА")
logger.info("=" * 60)

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Простейшая команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"👤 Пользователь {message.from_user.id} отправил /start")
    await message.answer(
        "✅ Бот работает!\n\n"
        "Вы можете:\n"
        "1. Написать что-нибудь - я отвечу эхом\n"
        "2. Отправить /help - помощь\n"
        "3. Отправить /test - тест"
    )

# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Это тестовый бот MFF.\n"
        "Скоро здесь будут Emily и John для практики английского!"
    )

# Команда /test
@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    await message.answer("✅ Тест пройден! Бот отвечает.")

# Эхо-ответ на любые сообщения
@dp.message()
async def echo(message: types.Message):
    user_text = message.text
    logger.info(f"📨 Сообщение от {message.from_user.id}: {user_text[:50]}...")
    
    # Показываем "печатает"
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Имитируем задержку
    await asyncio.sleep(1)
    
    # Отвечаем эхом
    await message.answer(f"Вы написали: {user_text}\n\n(Это тестовый режим. Скоро будут Emily и John!)")

# Запуск бота через polling
async def main():
    logger.info("🤖 Запуск бота...")
    logger.info(f"🔑 Токен: {TOKEN[:10]}...")
    
    try:
        # Удаляем старый вебхук если был
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🗑️ Старые вебхуки удалены")
        
        # Запускаем поллинг
        logger.info("🔄 Начинаю polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
