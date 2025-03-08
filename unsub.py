import sqlite3
from datetime import datetime
from telegram import Bot
import logging
import asyncio
import time
from tg_bot import CHANNELS, BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    filename="bot_log.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)

async def get_expired_or_no_subscription_subscribers():
    """Получаем всех пользователей с истекшей подпиской."""
    expired_users = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Логика повторных попыток
    retries = 3
    for i in range(retries):
        try:
            with sqlite3.connect('subscribers.db') as conn:
                cursor = conn.cursor()

                # Ищем пользователей, чья дата окончания подписки истекла
                cursor.execute('''
                    SELECT user_id, subscription_end_date
                    FROM subscriptions
                    WHERE subscription_end_date < ?
                ''', (current_date,))

                expired_users = cursor.fetchall()
            break  # Выход из цикла, если запрос выполнен успешно
        except sqlite3.OperationalError as e:
            logging.warning(f"Ошибка при запросе к базе данных (попытка {i + 1} из {retries}): {e}")
            if i < retries - 1:
                time.sleep(3)  # Задержка перед следующей попыткой
            else:
                logging.error("Не удалось получить данные из базы после нескольких попыток.")
                raise
    return expired_users  # Список кортежей (user_id, subscription_end_date)

async def remove_user_from_channels(user_id):
    """Удаляет пользователя из всех каналов (банит, затем снимает бан)."""
    # Логика повторных попыток
    retries = 3
    for i in range(retries):
        try:
            for channel_id in CHANNELS.values():
                # Блокируем пользователя (баним)
                await bot.ban_chat_member(chat_id=channel_id, user_id=user_id)
                # Снимаем бан с пользователя
                await bot.unban_chat_member(chat_id=channel_id, user_id=user_id)
                logging.info(f"Пользователь {user_id} удален из канала {channel_id}")
            break  # Выход из цикла, если запрос выполнен успешно
        except Exception as e:
            logging.warning(f"Ошибка при удалении пользователя {user_id} из канала (попытка {i + 1} из {retries}): {e}")
            if i < retries - 1:
                time.sleep(3)  # Задержка перед следующей попыткой
            else:
                logging.error(f"Не удалось удалить пользователя {user_id} после нескольких попыток.")
                raise

async def clear_subscription_end_date(user_id):
    """Очищаем дату окончания подписки (ставим пустую строку)."""
    # Логика повторных попыток
    retries = 3
    for i in range(retries):
        try:
            with sqlite3.connect('subscribers.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE subscriptions SET subscription_end_date = '' WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
            break  # Выход из цикла, если запрос выполнен успешно
        except sqlite3.OperationalError as e:
            logging.warning(f"Ошибка при обновлении базы данных (попытка {i + 1} из {retries}): {e}")
            if i < retries - 1:
                time.sleep(3)  # Задержка перед следующей попыткой
            else:
                logging.error(f"Не удалось очистить дату окончания подписки для пользователя {user_id} после нескольких попыток.")
                raise

async def daily_task():
    """Задача, которая будет запускаться ежедневно."""
    try:
        expired_users = await get_expired_or_no_subscription_subscribers()

        if not expired_users:
            logging.info("Нет пользователей для удаления.")
            return  # Завершаем выполнение, если никого нет

        # Удаляем пользователей
        for user_id, subscription_end_date in expired_users:
            logging.info(f"Обрабатываем пользователя {user_id}. Подписка до {subscription_end_date}.")
            await remove_user_from_channels(user_id)

        # Обновляем данные в БД
        for user_id, _ in expired_users:
            await clear_subscription_end_date(user_id)

        logging.info("Задача выполнена успешно.")

    except Exception as e:
        logging.error(f"Ошибка при выполнении задачи: {e}")

# Главная асинхронная функция запуска
if __name__ == "__main__":
    asyncio.run(daily_task())  # Запуск задачи через asyncio
