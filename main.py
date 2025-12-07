import sys
import os

# Принудительно пишем в stderr - это точно попадет в логи
sys.stderr.write("\n" + "="*60 + "\n")
sys.stderr.write("🚀 ЗАПУСК ТЕСТА\n")
sys.stderr.write("="*60 + "\n\n")

sys.stderr.write(f"Python версия: {sys.version}\n")
sys.stderr.write(f"Текущая директория: {os.getcwd()}\n")
sys.stderr.write(f"Файлы в директории: {os.listdir('.')}\n")

# Проверяем переменные
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

sys.stderr.write(f"\nTELEGRAM_TOKEN: {'ЕСТЬ' if TELEGRAM_TOKEN else 'НЕТ'}\n")
sys.stderr.write(f"OPENAI_API_KEY: {'ЕСТЬ' if OPENAI_API_KEY else 'НЕТ'}\n")

sys.stderr.write("\n" + "="*60 + "\n")
sys.stderr.write("✅ ТЕСТ ЗАВЕРШЕН\n")
sys.stderr.write("="*60 + "\n")

# Принудительно завершаем
sys.exit(0)
