import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN") or "9120927217:AAFp_9mD55SS1SBdKNppE8VsNPEART20jL4"
API_KEY = os.getenv("API_KEY") or "ИН_ҶО_КАЛИДИ_API_РО_ГУЗОРЕД"

API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL_NAME = "gemini-3.8-flash"

LANG_NAMES = {"tg": "Тоҷикӣ", "ru": "Русский", "en": "English"}

UI_TEXT = {
    "tg": {
        "choose_lang": "Забонро интихоб кунед / Выберите язык / Choose language:",
        "lang_set": "✅ Забони бот ба **Тоҷикӣ** иваз шуд. Саволатонро нависед:",
        "cleared": "🗑 Таърихи сӯҳбат тоза шуд.",
        "sys": "Ту ёвари зеҳни сунъии дӯстона ва дақиқ ҳастӣ. Ҳамеша бо забони тоҷикӣ ҷавоб деҳ.",
    },
    "ru": {
        "choose_lang": "Выберите язык / Забонро интихоб кунед / Choose language:",
        "lang_set": "✅ Язык бота изменён на **Русский**. Напишите ваш вопрос:",
        "cleared": "🗑 История диалога очищена.",
        "sys": "Ты дружелюбный и точный ИИ-ассистент. Всегда отвечай на русском языке.",
    },
    "en": {
        "choose_lang": "Choose language / Выберите язык / Забонро интихоб кунед:",
        "lang_set": "✅ Bot language set to **English**. Write your question:",
        "cleared": "🗑 Chat history cleared.",
        "sys": "You are a friendly and accurate AI assistant. Always reply in English.",
    },
}

user_lang = {}
user_interactions = {}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


def get_lang(uid: int) -> str:
    return user_lang.get(uid, "tg")


def lang_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        types.InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="lang_tg"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    )
    return kb


def main_keyboard(lang: str) -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "ru":
        kb.row("🌍 Язык", "🗑 Очистить")
    elif lang == "en":
        kb.row("🌍 Language", "🗑 Clear")
    else:
        kb.row("🌍 Забон", "🗑 Тоза кардан")
    return kb


async def ask_ai(uid: int, prompt: str) -> str:
    lang = get_lang(uid)
    headers = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "input": prompt,
        "system_instruction": UI_TEXT[lang]["sys"],
        "store": True,
    }
    if uid in user_interactions:
        payload["previous_interaction_id"] = user_interactions[uid]

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=headers, json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                return f"⚠️ {data.get('error', {}).get('message', 'API error')}"
            if "id" in data:
                user_interactions[uid] = data["id"]
            texts = [
                item.get("text", "")
                for item in data.get("outputs", [])
                if isinstance(item, dict) and item.get("text")
            ]
            return "\n".join(texts).strip() or "No response."


@dp.message_handler(commands=["start", "lang"])
async def cmd_start(message: types.Message):
    await message.answer(
        UI_TEXT[get_lang(message.from_user.id)]["choose_lang"],
        reply_markup=lang_keyboard(),
    )


@dp.callback_query_handler(lambda c: c.data in ("lang_ru", "lang_tg", "lang_en"))
async def process_lang(callback: types.CallbackQuery):
    code = callback.data.split("_")[1]
    uid = callback.from_user.id
    user_lang[uid] = code
    user_interactions.pop(uid, None)
    await callback.answer(LANG_NAMES[code])
    await callback.message.answer(
        UI_TEXT[code]["lang_set"],
        parse_mode="Markdown",
        reply_markup=main_keyboard(code),
    )


@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: types.Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    text = message.text.strip()

    if text in ("🌍 Забон", "🌍 Язык", "🌍 Language"):
        await message.answer(UI_TEXT[lang]["choose_lang"], reply_markup=lang_keyboard())
        return
    if text in ("🗑 Тоза кардан", "🗑 Очистить", "🗑 Clear"):
        user_interactions.pop(uid, None)
        await message.answer(UI_TEXT[lang]["cleared"], reply_markup=main_keyboard(lang))
        return

    await types.ChatActions.typing()
    reply = await ask_ai(uid, text)
    for i in range(0, len(reply), 4000):
        await message.answer(reply[i : i + 4000])


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
