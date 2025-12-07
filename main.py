import os
import sys

# Принудительно пишем в stderr - Render всегда это показывает
sys.stderr.write("\n" + "="*60 + "\n")
sys.stderr.write("🔥 ТЕСТОВЫЙ ЗАПУСК - ЭТО ДОЛЖНО БЫТЬ ВИДНО!\n")
sys.stderr.write("="*60 + "\n\n")

# Простая проверка
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("OPENAI_API_KEY")

sys.stderr.write(f"TELEGRAM_TOKEN: {'✅ УСТАНОВЛЕН' if TOKEN else '❌ ОТСУТСТВУЕТ'}\n")
sys.stderr.write(f"OPENAI_API_KEY: {'✅ УСТАНОВЛЕН' if API_KEY else '❌ ОТСУТСТВУЕТ'}\n")

sys.stderr.write("\n📋 Список файлов в папке:\n")
try:
    for f in os.listdir('.'):
        sys.stderr.write(f"  - {f}\n")
except Exception as e:
    sys.stderr.write(f"  ❌ Ошибка: {e}\n")

sys.stderr.write("\n" + "="*60 + "\n")
sys.stderr.write("✅ Тест завершен\n")
sys.stderr.write("="*60 + "\n")

# Простой HTTP сервер чтобы Render не закрывал процесс
if TOKEN and API_KEY:
    sys.stderr.write("\n🚀 Все переменные есть! Можно запускать бота...\n")
    
    # Импортируем и запускаем бота
    try:
        from aiogram import Bot, Dispatcher, types
        from aiogram.filters import Command
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler
        from aiohttp import web
        
        bot = Bot(token=TOKEN)
        dp = Dispatcher()
        
        @dp.message(Command("start"))
        async def start(message: types.Message):
            await message.answer("Привет! Бот работает! 🎉")
        
        app = web.Application()
        handler = SimpleRequestHandler(dp, bot)
        handler.register(app, path="/webhook")
        
        # Устанавливаем вебхук
        import asyncio
        async def setup():
            await bot.set_webhook("https://mff-ai-bot-5.onrender.com/webhook")
            sys.stderr.write("✅ Вебхук установлен!\n")
        
        asyncio.run(setup())
        
        sys.stderr.write("🤖 Бот готов к работе! Отправьте /start в Telegram\n")
        web.run_app(app, host='0.0.0.0', port=10000)
        
    except Exception as e:
        sys.stderr.write(f"❌ Ошибка при запуске бота: {e}\n")
        # Держим процесс alive
        import time
        time.sleep(300)
else:
    sys.stderr.write("\n⚠️  Добавьте переменные в Render Dashboard\n")
    # Держим процесс alive
    import time
    time.sleep(300)
