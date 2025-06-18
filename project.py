import asyncio
import sys
from os import getenv
from pathlib import Path
import random

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from baza import create_db, get_random_questions, get_all_answers
from custom_commands import my_commands

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()
user_data = {}

@dp.message(CommandStart())
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
            ]
        ]
    )
    await message.answer(
        f"👋 Assalomu alaykum {message.from_user.username}!\n\n"
        "Iltimos, tilni tanlang / Пожалуйста, выберите язык:",
        reply_markup=keyboard
    )

@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    uid = message.from_user.id
    user_data.pop(uid, None)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Yana boshlash", callback_data="start_again")]
        ]
    )
    await message.answer(
        "⛔ Bot to‘xtatildi. Qayta ishga tushirish uchun tugmani bosing.",
        reply_markup=keyboard
    )

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data

    if data == "start_again":
        user_data.pop(uid, None)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
                    InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
                ]
            ]
        )
        await callback.message.answer(
            f"👋 Assalomu alaykum {callback.from_user.username}!\n\n"
            "Iltimos, tilni tanlang / Пожалуйста, выберите язык:",
            reply_markup=keyboard
        )
        return
    if not Path("questions.db").is_file():
        await callback.message.answer("⚠ Ma'lumotlar bazasi topilmadi!")
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    if data.startswith("lang_"):
        user_data[uid] = {"lang": data.split("_")[1]}
        await ask_direction(callback.message, uid)

    elif data.startswith("dir_"):
        user_data[uid]["direction"] = data.split("_")[1]
        await ask_question_count(callback.message, uid)

    elif data.startswith("count_"):
        q_count = int(data.split("_")[1])
        lang = user_data[uid]["lang"]
        direction = user_data[uid]["direction"]
        questions = get_random_questions(direction, lang, q_count)
        if not questions:
            await callback.message.answer("⚠ Savollar topilmadi!")
            await callback.message.edit_reply_markup(reply_markup=None)
            return
        user_data[uid].update({
            "q_count": q_count,
            "q_index": 0,
            "score": 0,
            "questions": questions
        })
        await send_question(callback.message, uid)

    elif data.startswith("ans_"):
        user_ans = data.split("_", 1)[1]
        if uid not in user_data or "current_answer" not in user_data[uid]:
            await callback.message.answer("⚠ Testni qaytadan boshlang!")
            await callback.message.edit_reply_markup(reply_markup=None)
            return

        correct = user_data[uid]["current_answer"]
        if user_ans == correct:
            user_data[uid]["score"] += 1
            await callback.message.answer("✅ To'g'ri javob!")
        else:
            await callback.message.answer(f"❌ Noto'g'ri. To'g'ri javob: {correct}")

        user_data[uid]["q_index"] += 1
        await send_question(callback.message, uid)

    elif data == "restart_quiz":
        await start_command(callback.message)

    else:
        await callback.message.answer("❓ Noma'lum buyruq!")

    await callback.message.edit_reply_markup(reply_markup=None)

async def ask_direction(message: types.Message, uid: int):
    if uid not in user_data or "lang" not in user_data[uid]:
        await message.answer("⚠ Iltimos, tilni tanlang!")
        return

    lang = user_data[uid]["lang"]
    text = "qiziqtirgan yo'nalishni tanlang:" if lang == "uz" else "Выберите направление:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💻 Web dasturlash" if lang == "uz" else "💻 Web программирование",
                    callback_data="dir_web"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Davlat Poytaxtlari" if lang == "uz" else "🌍 Столицы стран",
                    callback_data="dir_capitals"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚽ Futbol o'yinlari" if lang == "uz" else "⚽ Футбол",
                    callback_data="dir_football"
                )
            ]
        ]
    )
    await message.answer(text, reply_markup=keyboard)

async def ask_question_count(message: types.Message, uid: int):
    if uid not in user_data or "lang" not in user_data[uid]:
        await message.answer("⚠ Iltimos, tilni tanlang!")
        return

    lang = user_data[uid]["lang"]
    text = "Nechta savol tanlaysiz?" if lang == "uz" else "Сколько вопросов хотите?"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="3", callback_data="count_3"),
                InlineKeyboardButton(text="5", callback_data="count_5"),
                InlineKeyboardButton(text="10", callback_data="count_10")
            ]
        ]
    )
    await message.answer(text, reply_markup=keyboard)

async def send_question(message: types.Message, uid: int):
    if uid not in user_data or "direction" not in user_data[uid] or "q_count" not in user_data[uid]:
        await message.answer("⚠ Testni qaytadan boshlang!")
        return

    if user_data[uid]["q_index"] >= user_data[uid]["q_count"]:
        score = user_data[uid]["score"]
        total = user_data[uid]["q_count"]
        lang = user_data[uid]["lang"]
        text = f"✅ Test tugadi! Natija: {score}/{total}" if lang == "uz" else f"✅ Тест завершен! Результат: {score}/{total}"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Qaytadan boshlash" if lang == "uz" else "🔄 Начать заново",
                        callback_data="restart_quiz"
                    )
                ]
            ]
        )
        await message.answer(text, reply_markup=keyboard)
        return

    direction = user_data[uid]["direction"]
    lang = user_data[uid]["lang"]
    q = user_data[uid]["questions"][user_data[uid]["q_index"]]
    user_data[uid]["current_answer"] = q.answer

    options = [q.answer]
    all_answers = get_all_answers(direction)
    if q.answer in all_answers:
        all_answers.remove(q.answer)
    if len(all_answers) >= 3:
        options.extend(random.sample(all_answers, 3))
    else:
        options.extend(all_answers)
    random.shuffle(options)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"ans_{opt}")] for opt in options
        ]
    )

    await message.answer(f"{user_data[uid]['q_index'] + 1}. {q.text}", reply_markup=keyboard)

async def main():
    if not Path("questions.db").is_file():
        create_db()

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())