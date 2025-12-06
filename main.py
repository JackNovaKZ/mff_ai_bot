import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv

# Загружаем переменные окружения (локально)
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Настройки Render
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # пример: https://your-service.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Обработчик команды /start
@dp.message(commands=["start"])
async def start_command(message: types.Message):
    await message.answer("Бот запущен! 🎉\nВыберите персонажа:")

# Настройка webhook
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

# Запуск сервера
if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=PORT
    )
