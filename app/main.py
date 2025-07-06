from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from config import BOT_TOKEN, ADMIN_CHAT_ID
import logging

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Пример товаров
PRODUCTS = [
    {"id": 1, "name": "Кольцо", "price": 1000},
    {"id": 2, "name": "Серьги", "price": 1500},
    {"id": 3, "name": "Браслет", "price": 2000},
]

user_carts = {}

class CartStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_checkout = State()

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🛒 Каталог"), KeyboardButton("👤 Профиль"), KeyboardButton("Корзина"))
    await message.answer("Добро пожаловать в Trifferi Jewelry!", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🛒 Каталог")
async def catalog(message: types.Message):
    kb = InlineKeyboardMarkup()
    for p in PRODUCTS:
        kb.add(InlineKeyboardButton(f"{p['name']} - {p['price']}₽", callback_data=f"add_{p['id']}"))
    await message.answer("Выберите товар:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    cart = user_carts.setdefault(user_id, [])
    cart.append(product_id)
    await call.answer("Товар добавлен в корзину!")

@dp.message_handler(lambda m: m.text == "Корзина")
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("Ваша корзина пуста.")
        return
    text = "Ваша корзина:\n"
    total = 0
    for pid in cart:
        prod = next((p for p in PRODUCTS if p["id"] == pid), None)
        if prod:
            text += f"{prod['name']} - {prod['price']}₽\n"
            total += prod['price']
    text += f"\nИтого: {total}₽"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Оформить заказ"), KeyboardButton("Очистить корзину"), KeyboardButton("Назад"))
    await message.answer(text, reply_markup=kb)

@dp.message_handler(lambda m: m.text == "Оформить заказ")
async def checkout(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("Корзина пуста!")
        return
    text = "Вы выбрали:\n"
    total = 0
    for pid in cart:
        prod = next((p for p in PRODUCTS if p["id"] == pid), None)
        if prod:
            text += f"{prod['name']} - {prod['price']}₽\n"
            total += prod['price']
    text += f"\nИтого: {total}₽\n\nПодтвердите заказ?"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Подтвердить заказ"), KeyboardButton("Назад"))
    await message.answer(text, reply_markup=kb)

@dp.message_handler(lambda m: m.text == "Подтвердить заказ")
async def confirm_order(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("Корзина пуста!")
        return
    text = "Заказ оформлен! Ожидайте, с вами свяжется админ."
    await message.answer(text)
    # Уведомление админу
    user = message.from_user
    cart_items = [next((p for p in PRODUCTS if p["id"] == pid), None) for pid in cart]
    cart_text = ", ".join([f"{p['name']} ({p['price']}₽)" for p in cart_items if p])
    admin_text = f"Новый заказ!\nПользователь: @{user.username or user.full_name}\nТовары: {cart_text}"
    # Попытка отправить админу по username
    try:
        await bot.send_message(f"@{ADMIN_CHAT_ID}", admin_text)
    except Exception:
        await message.answer("Не удалось уведомить админа.")
    user_carts[user_id] = []

@dp.message_handler(lambda m: m.text == "Очистить корзину")
async def clear_cart(message: types.Message):
    user_id = message.from_user.id
    user_carts[user_id] = []
    await message.answer("Корзина очищена.")

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(message: types.Message):
    user = message.from_user
    text = f"Ваш профиль:\nИмя: {user.full_name}\nUsername: @{user.username or '-'}\nID: {user.id}"
    await message.answer(text)

@dp.message_handler(lambda m: m.text == "Назад")
async def back(message: types.Message):
    await start(message)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
