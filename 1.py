from ast import parse
import decimal
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

import time
from typing import Dict, Optional
import urllib
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from urllib import parse


# Путь к вашим файлам
AUDIO_FILE = 'start_grisha.opus'
SASHA_AUDIO = 'sasha.opus'

# Данные мерчанта Robokassa
MERCHANT_LOGIN = "onepercent"
MERCHANT_PASSWORD_1 = "srbGBD6x4ZoTOl7pJL69"
MERCHANT_PASSWORD_2 = "T6XAvZ94G8drrHOCeMx1"
ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"
RETURN_URL = "https://t.me/OnlyOnePrecent_bot"
PRICE = decimal.Decimal("1499.00")
BOT_TOKEN = '7510014005:AAHxbLaHcWlDEx95MkHsqc_y2mrX6NStYU4'
DESCRIPTION = "Подписка на 1%"
number = 0

# IDs каналов
CHANNELS = {
    "1% модули и ДЗ": -1002379716169,
    "1% плюшки": -1002491815911,
    "1% чат общения": -1002435800153,
    "1% отчеты по ДЗ, чат-рехаб, медитации": -1002268923269
}

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Подключение к базе данных и создание таблицы
def create_db():
    """Создаём таблицу для хранения подписок, если она не существует."""
    with sqlite3.connect('subscribers.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                number TEXT NOT NULL,
                subscription_end_date TEXT NOT NULL
            )
        ''')
        conn.commit()

# Функция для добавления или обновления подписки
def add_or_update_subscription(user_id, number):
    """Добавляет новую подписку или обновляет существующую"""
    with sqlite3.connect('subscribers.db') as conn:
        cursor = conn.cursor()

        # Получаем текущую дату окончания подписки
        cursor.execute('''SELECT subscription_end_date FROM subscriptions WHERE user_id = ?''', (user_id,))
        result = cursor.fetchone()

        if result:
            # Если подписка существует, проверяем, активна ли она
            old_end_date = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            
            if old_end_date > datetime.now():
                # Если подписка активна, прибавляем 30 дней
                new_subscription_end_date = old_end_date + timedelta(days=30)
            else:
                # Если подписка истекла, устанавливаем новую дату с текущего дня
                new_subscription_end_date = datetime.now() + timedelta(days=30)

            # Обновляем подписку в базе данных
            cursor.execute('''UPDATE subscriptions SET number = ?, subscription_end_date = ? WHERE user_id = ?''',
                           (number, new_subscription_end_date.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            logger.info(f"Обновлена подписка для пользователя {user_id}. Новая дата окончания: {new_subscription_end_date}")
        else:
            # Если подписки нет, добавляем новую с датой окончания через 30 дней
            new_subscription_end_date = datetime.now() + timedelta(days=30)
            cursor.execute('''INSERT INTO subscriptions (user_id, number, subscription_end_date) VALUES (?, ?, ?)''',
                           (user_id, number, new_subscription_end_date.strftime('%Y-%m-%d %H:%M:%S')))
            logger.info(f"Добавлена новая подписка для пользователя {user_id} с number {number}. Дата окончания: {new_subscription_end_date}")

create_db()

# Функция для проверки даты окончания подписки
def get_subscription_end_date(user_id):
    """Возвращает дату окончания подписки для пользователя"""
    with sqlite3.connect('subscribers.db') as conn:
        cursor = conn.cursor()

        cursor.execute('''
        SELECT subscription_end_date FROM subscriptions WHERE user_id = ?
        ''', (user_id,))

        result = cursor.fetchone()

    if result:
        print(result[0]) 
        # Преобразуем строку из result[0] в объект datetime
        return datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
    else:
        return None
#/
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отправка приветственного голосового сообщения с кнопками."""
    keyboard = [
        [InlineKeyboardButton("Познакомиться с Сашей", callback_data='sasha')],
        [InlineKeyboardButton("Что тебя ждет в 1%?", callback_data='what_to_expect')],
        [InlineKeyboardButton("Личный канал Гриши", url='https://t.me/+Y3KPtsHzQAQyNjM6')],  # Замените на ссылку
        [InlineKeyboardButton("Личный канал Саши", url='https://t.me/sashamyslit')],  # Замените на ссылку
        [InlineKeyboardButton("Вступить в 1%", callback_data='join_1_percent')],
        [InlineKeyboardButton("Хелп", callback_data='help')]
    ]
    
    try:
        # Отправляем голосовое сообщение и прикрепляем кнопки
        with open(AUDIO_FILE, 'rb') as audio:
            await update.message.reply_voice(
                audio,
                caption=">Начни с голосового сообщения",  # Текст, который будет отображаться к голосовому сообщению
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке голосового сообщения: {e}")
#/
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет подписку пользователя и выдает ссылки только на недостающие каналы"""
    user_id = update.message.from_user.id
    
    # Проверяем, есть ли пользователь в базе данных
    subscription_end_date = get_subscription_end_date(user_id)

    if not subscription_end_date:
        message = "*Тебя нет в 1%*\\.\\.\\.\n\n""Исправь это ↷"
        keyboard = [
            [InlineKeyboardButton("Вступить в 1%", callback_data='join_1_percent')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="MarkdownV2")
        return  # Завершаем выполнение функции, т.к. подписки нет

    # Если подписка есть, продолжаем обработку
    missing_channels = {}

    # Проверяем, на какие каналы пользователь НЕ подписан
    for title, chat_id in CHANNELS.items():
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                missing_channels[title] = chat_id
        except Exception as e:
            print(f"Ошибка проверки подписки на {title}: {e}")
            missing_channels[title] = chat_id  # Все равно добавляем, если не можем проверить

    # Если подписка есть
    message = f"✅ *Подписка активна до:* `{subscription_end_date.strftime('%d.%m.%Y')}`\n\n"

    if missing_channels:
        # Генерируем ссылки ТОЛЬКО для недостающих каналов
        invite_links = {}
        for title, chat_id in missing_channels.items():
            try:
                invite_link = await context.bot.create_chat_invite_link(
                    chat_id,
                    member_limit=1,
                    expire_date=int(datetime.now().timestamp()) + 600  # 10 минут
                )
                invite_links[title] = invite_link.invite_link
            except Exception as e:
                print(f"Ошибка создания ссылки для {title}: {e}")
                invite_links[title] = "Ошибка при генерации ссылки"

        # Добавляем ссылки в сообщение
        message += "*Забыл подписаться на ↷*\n\n"
        for title, link in invite_links.items():
            # Экранируем дефисы в названии канала перед вставкой в сообщение
            escaped_title = title.replace('-', r'\-')  # Экранируем дефис
            message += f"➙ [{escaped_title}]({link})\n\n"
    
    else:
        message += "✅ *Ты подписан на все нужные каналы\\!*"

    await update.message.reply_text(message, parse_mode="MarkdownV2")

def calculate_signature(
    merchant_login: str,
    cost: decimal.Decimal,
    number: int,
    receipt: dict,
    merchant_password_1: str,
    additional_params: Optional[Dict[str, str]] = None
) -> str:
    """Генерация подписи MD5 с учетом чека (Receipt) и дополнительных параметров (например, user_id)."""
    
    # Сериализуем чек в JSON
    receipt_json = json.dumps(receipt, ensure_ascii=False)
    
    # URL-кодируем чек
    encoded_receipt = urllib.parse.quote(receipt_json, safe='')

    # Формируем базовую строку для подписи
    base_string = f"{merchant_login}:{cost:.2f}:{number}:{encoded_receipt}:{merchant_password_1}"

    # Если есть дополнительные параметры, добавляем их
    if additional_params:
        sorted_params = sorted(additional_params.items())
        for key, value in sorted_params:
            base_string += f":{key}={value}"

    # Генерация MD5-хеш
    return hashlib.md5(base_string.encode()).hexdigest()

def get_expiration_date(seconds: int = 10) -> str:
    """Возвращает строку с датой истечения через заданное количество секунд в формате ISO 8601."""
    expiration_time = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return expiration_time.strftime('%Y-%m-%dT%H:%M:%S') + '.0000000+00:00'

def generate_payment_link(
    merchant_login: str,
    merchant_password_1: str,
    cost: decimal.Decimal,
    number: int,
    description: str,
    receipt: dict,
    user_id: int,
    expiration_date: Optional[str] = None,
    robokassa_payment_url: str = ROBOKASSA_URL
) -> str:
    """Генерация ссылки для перенаправления клиента на оплату."""

    # Дополнительные параметры, включая user_id
    additional_params = {
        'Shp_user_id': user_id  # Передаем user_id как пользовательский параметр
    }

    # Генерация подписи с дополнительными параметрами
    signature = calculate_signature(
        merchant_login,
        cost,
        number,
        receipt,
        merchant_password_1,
        additional_params  # Передаем дополнительные параметры
    )

    # Параметры для запроса
    data = {
        'MerchantLogin': merchant_login,
        'OutSum': cost,
        'InvId': number,
        'Description': description,
        'SignatureValue': signature,
        'IsTest': 0,  # Не в тестовом режиме
        'Receipt': urllib.parse.quote(json.dumps(receipt, ensure_ascii=False), safe=''),
    }

    # Если передан expiration_date, добавляем его в параметры
    if expiration_date:
        data['ExpirationDate'] = expiration_date

    # Добавляем дополнительные параметры в строку
    for param, value in additional_params.items():
        data[param] = value

    # Генерация ссылки
    return f'{robokassa_payment_url}?{urllib.parse.urlencode(data)}'

async def pay(update, context) -> None:
    """Генерация ссылки на оплату и отправка пользователю."""

    user_id = update.callback_query.from_user.id  # Получаем user_id пользователя

    merchant_login = "onepercent"
    merchant_password_1 = "srbGBD6x4ZoTOl7pJL69"
    cost = decimal.Decimal(PRICE)  # Сумма платежа
    description = f"Подписка на 1% для {user_id}"  # Описание

    # Данные для фискализации
    receipt_data = {
        "items": [
            {
                "name": "Подписка 1%",
                "quantity": 1,
                "sum": float(PRICE),
                "payment_method": "full_payment",
                "payment_object": "service",
                "tax": "none"
            }
        ]
    }

    # Генерация срока действия счета (10 минут)
    expiration_date = get_expiration_date(seconds=10 * 60)

    # Генерация ссылки для оплаты
    payment_link = generate_payment_link(
        merchant_login=merchant_login,
        merchant_password_1=merchant_password_1,
        cost=cost,
        number=number,
        description=description,
        receipt=receipt_data,
        user_id=user_id,
        expiration_date=expiration_date  # Передаем срок действия счета
    )

    # Создание клавиатуры с кнопками
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить", web_app=WebAppInfo(url=payment_link))],
        [InlineKeyboardButton("Условия оплаты", url='https://telegra.ph/Platezhnye-usloviya-02-22')],
        [InlineKeyboardButton("Описание продукта", url="https://telegra.ph/Opisanie-produkta-02-22")],
        [InlineKeyboardButton("Оферта", url="https://telegra.ph/PUBLICHNAYA-OFERTA-02-22")]
    ]

    # Отправка сообщения с кнопками
    await update.callback_query.message.reply_text(
        "💰 Доступ стоит 1499₽ на 30 дней\\.\n\n"
        "_Оплачивая подписку, ты соглашаешься с условиями_\\.\n\n"
        ">После оплаты подожди немного, пока платеж в обработке\\.\\.\\.",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def successful_payment(number, user_id):
    """Обрабатывает успешную оплату, обновляет подписку и отправляет сообщение с ссылками"""
    
    # Добавляем или обновляем подписку
    add_or_update_subscription(user_id, number)

    # Генерируем ссылки для каналов
    invite_links = await generate_invite_links()

    # Создаем сообщение с текстом и ссылками на каналы
    message = (
        "*ВСЕ\\. ТЫ ПОЧТИ С НАМИ, ПОЗДРАВЛЯЮ\\!*\n\n"
        "*Что делать дальше?*\n\n"
        ">*Подпишись на все, что ниже ↷*\n\n"
        f"➙ [1% модули и ДЗ]({invite_links['1% модули и ДЗ']})\n\n"
        f"➙ [1% плюшки]({invite_links['1% плюшки']})\n\n"
        f"➙ [1% чат общения]({invite_links['1% чат общения']})\n\n"
        f"➙ [1% отчеты по ДЗ, чат\\-рехаб, медитации]({invite_links['1% отчеты по ДЗ, чат-рехаб, медитации']})\n\n"
        ">*Теперь у тебя должны быть 4 канала/групп от 1%\\. Точно 4? Тогда погнали дальше, ты почти в семье :\\)*\n\n"
        ">||Если ссылки не работают — жми *«Проверить подписку»* в меню бота, оно находится в левом нижнем углу\\. Если и так не работают — пишите @sunsleamm, оперативно поможем\\.||\n\n"
        "*ВСЕ\\. ДОБРО ПОЖАЛОВАТЬ В 1%\\!*"
    )

    bot = Bot(token='7579057272:AAFn1jALhoGKIrXtB1y_4md3rM68upLdvz0')  # Создайте объект бота
    try:
        # Отправляем сообщение пользователю по его user_id
        await bot.send_message(chat_id=user_id, text=message, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

async def generate_invite_links():
    """Генерирует одноразовые ссылки для всех каналов."""
    bot = Bot(token='7579057272:AAFn1jALhoGKIrXtB1y_4md3rM68upLdvz0')  # Создаем объект бота
    invite_links = {}
    expire_time = int(time.time()) + 600  # Срок действия 10 минут

    for title, chat_id in CHANNELS.items():
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id,
                member_limit=1,
                expire_date=expire_time
            )
            invite_links[title] = invite_link.invite_link
        except Exception as e:
            invite_links[title] = "Ошибка при генерации ссылки"
            print(f"Ошибка создания ссылки для {title}: {e}")

    return invite_links

async def button_handler(update, context):
    """Обрабатывает нажатие на кнопку."""
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие

    # Изначальная кнопка
    keyboard_original = [
        [InlineKeyboardButton("Познакомиться с Сашей", callback_data='sasha')],
        [InlineKeyboardButton("Что тебя ждет в 1%?", callback_data='what_to_expect')],
        [InlineKeyboardButton("Личный канал Гриши", url='https://t.me/+Y3KPtsHzQAQyNjM6')],
        [InlineKeyboardButton("Личный канал Саши", url='https://t.me/sashamyslit')],
        [InlineKeyboardButton("Вступить в 1%", callback_data='join_1_percent')],
        [InlineKeyboardButton("Хелп", callback_data='help')]
    ]

    # Модифицированная кнопка с ожиданием
    keyboard_loading_sasha = [
        [InlineKeyboardButton("Секундочку...", callback_data='waiting')],  # Кнопка с эмодзи "Ожидание"
        [InlineKeyboardButton("Что тебя ждет в 1%?", callback_data='what_to_expect')],
        [InlineKeyboardButton("Личный канал Гриши", url='https://t.me/+Y3KPtsHzQAQyNjM6')],
        [InlineKeyboardButton("Личный канал Саши", url='https://t.me/sashamyslit')],
        [InlineKeyboardButton("Вступить в 1%", callback_data='join_1_percent')],
        [InlineKeyboardButton("Хелп", callback_data='help')]
    ]

    keyboard_loading_1_percent = [
        [InlineKeyboardButton("Познакомиться с Сашей", callback_data='sasha')],
        [InlineKeyboardButton("Секундочку...", callback_data='waiting')],  # Кнопка с эмодзи "Ожидание"
        [InlineKeyboardButton("Личный канал Гриши", url='https://t.me/+Y3KPtsHzQAQyNjM6')],
        [InlineKeyboardButton("Личный канал Саши", url='https://t.me/sashamyslit')],
        [InlineKeyboardButton("Вступить в 1%", callback_data='join_1_percent')],
        [InlineKeyboardButton("Хелп", callback_data='help')]
    ]

    try:
        if query.data == 'sasha':
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard_loading_sasha))
            # Отправляем голосовое сообщение и текст в одном сообщении
            with open(SASHA_AUDIO, 'rb') as sasha_audio:
                # Создаем клавиатуру с кнопкой "Вступить в 1%"
                keyboard = [
                    [InlineKeyboardButton("Вступить в 1%", callback_data='join_1_percent')]  # Кнопка вступления
                ]
                await query.message.reply_voice(
                    sasha_audio, 
                    caption="> Знакомство с Сашей",  # Текст как цитата
                    parse_mode="MarkdownV2",  # Устанавливаем MarkdownV2 для поддержки цитат
                    reply_markup=InlineKeyboardMarkup(keyboard)  # Добавляем клавиатуру с кнопкой
                )
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard_original))
        
        elif query.data == 'what_to_expect':
            try:
                # Меняем только нажатую кнопку
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard_loading_1_percent))
                
                # Отправляем видео с новой подписью
                await context.bot.send_video(
                    chat_id=query.message.chat.id,  # Чат, в который отправляем
                    video='https://t.me/videoprogrev/2',  # URL видео из другого канала
                    caption="Что тебя ждет в 1%?",  # Новая подпись
                    parse_mode="MarkdownV2",  # Поддержка Markdown для форматирования
                    reply_markup=InlineKeyboardMarkup([  # Кнопка для вступления
                        [InlineKeyboardButton("Вступить в 1%", callback_data='join_1_percent')]
                    ])
                )
            except Exception as e:
                # Логируем ошибку
                logging.error(f"Ошибка при обработке кнопки: {e}")
                
            # Возвращаем оригинальные кнопки
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard_original))

        elif query.data == 'join_1_percent':
            await pay(update, context)
        
        elif query.data == 'help':
            await query.message.reply_text(
                "🔍 *Изучи перед обращением в поддержку*\n\n"
                "• Ссылки на каналы *единоразовые* и активны *10 минут*\\.\n\n"
                "• Команда /subscribe ↷\n\n"
                "   \\- Проверка подписки\n"
                "   \\- Получение ссылок на каналы\n\n"
                "💳 *Ничего не происходит через 30 сек\\. после оплаты ↷*\n\n"
                "\\- Нет чека на почте — оплата не прошла\\.\n"
                "\\- Если уверен, что оплатил, отправь эл\\.почту, скрин оплаты или банковский чек ➙ **@sunsleamm**, разберемся\\.\n\n"
                "📩 Для других вопросов пишите в поддержку *@sunsleamm*\\.",
                parse_mode="MarkdownV2"
            ) 

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки: {e}")

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))

    # Обработчик для кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
