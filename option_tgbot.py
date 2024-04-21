import asyncio
import logging
import sys
import numpy as np
from scipy.stats import norm

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

def black_scholes_call(S, X, T, r, sigma):
    d1 = (np.log(S / X) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call_price = S * norm.cdf(d1) - X * np.exp(-r * T) * norm.cdf(d2)
    return call_price

TOKEN = "6878136453:AAGFt8JE2yhBSi9Z_105_bXcYeZK7eCsdB4"

form_router = Router()


class Form(StatesGroup):
    agree = State()
    S = State()
    X = State()
    T = State()
    r = State()
    sigma = State()


@form_router.message(CommandStart())
async def process_agree(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.agree)
    await message.answer(
        "Если что ты сам виноват",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Согласен"),
                    KeyboardButton(text="Пошел вон"),
                ]
            ],
            resize_keyboard=True,
        ),
    )

@form_router.message(Form.agree, F.text.casefold() == "пошел вон")
async def process_dont_agree(message: Message, state: FSMContext) -> None:
    await state.get_data()
    await state.clear()
    await message.answer(
        "Сам иди, дурачок",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.agree, F.text.casefold() == "согласен")
async def process_like_agree(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.S)

    await message.answer(
        "S - текущая цена базового актива",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.agree)
async def process_unknown_write(message: Message) -> None:
    await message.reply("Отвечай по делу, чорт")

@form_router.message(Form.S)
async def process_S(message: Message, state: FSMContext) -> None:
    await state.update_data(S=message.text)
    await state.set_state(Form.X)

    await message.answer(
        "X - страйк-цена",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.X)
async def process_X(message: Message, state: FSMContext) -> None:
    await state.update_data(X=message.text)
    await state.set_state(Form.T)

    await message.answer(
        "T - время до истечения срока действия опциона",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.T)
async def process_T(message: Message, state: FSMContext) -> None:
    await state.update_data(T=message.text)
    await state.set_state(Form.r)

    await message.answer(
        "r - безрисковая процентная ставка",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.r)
async def process_r(message: Message, state: FSMContext) -> None:
    await state.update_data(r=message.text)
    await state.set_state(Form.sigma)

    await message.answer(
        "sigma - волатильность базового актива",
        reply_markup=ReplyKeyboardRemove(),
    )
    
@form_router.message(Form.sigma)
async def process_sigma(message: Message, state: FSMContext) -> None:
    await state.update_data(sigma=message.text)

    # Получаем данные из контекста FSM
    data = await state.get_data()
    S = float(data.get('S'))  # Преобразуем значение из контекста в число
    X = float(data.get('X'))
    T = float(data.get('T'))
    r = float(data.get('r'))
    sigma = float(data.get('sigma'))

    # Печатаем данные перед началом расчета
    print(f"S = {S}, X = {X}, T = {T}, r = {r}, sigma = {sigma}")

    if None not in (S, X, T, r, sigma):
        # Вызываем функцию black_scholes_call для вычисления стоимости опциона
        call_price = black_scholes_call(S, X, T, r, sigma)

        # Отправляем ответ пользователю
        await message.answer(f"Стоимость опциона по модели Блэка-Шоулза: {call_price}")

async def main():
    bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(form_router)


    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())