import os
import logging
import asyncio
import httpx
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

genai.configure(api_key=GEMINI_API_KEY)

STREETWEAR_SYSTEM = """אתה מומחה לתוכן ויראלי בטיקטוק בנישת streetwear, ראפ והיפ-הופ.
תמיד תענה בעברית. הסגנון שלך: ישיר, אנרגטי, ויראלי."""

user_states = {}

KEYBOARDS = {
    "main": {
        "inline_keyboard": [
            [{"text": "🎣 Hooks", "callback_data": "hooks"}, {"text": "🔥 כותרות", "callback_data": "titles"}],
            [{"text": "✍️ קפשין + האשטגים", "callback_data": "caption"}, {"text": "💡 רעיונות", "callback_data": "ideas"}],
            [{"text": "🎵 סאונדים ויראליים", "callback_data": "sounds"}, {"text": "📈 טרנדים עכשיו", "callback_data": "trends"}],
        ]
    },
    "back": {
        "inline_keyboard": [[{"text": "🔙 חזור", "callback_data": "back"}]]
    }
}

MODE_PROMPTS = {
    "hooks": "🎣 *Hooks לפתיחת הסרטון*\n\nתאר את הסרטון שלך:\n\n_לדוגמה: outfit check עם ג'קט שחור ונעלי Jordan_",
    "titles": "🔥 *כותרות מושכות*\n\nתאר את הסרטון:\n\n_לדוגמה: unboxing נעליים נדירות_",
    "caption": "✍️ *קפשין + האשטגים*\n\nתאר את הסרטון:\n\n_לדוגמה: haul של בגדים חדשים_",
    "ideas": "💡 *רעיונות לסרטונים*\n\nתגיד נושא כללי:\n\n_לדוגמה: streetwear, sneakers_",
    "sounds": "🎵 *סאונדים ויראליים*\n\nמה הוייב של הסרטון?\n\n_לדוגמה: outfit אגרסיבי, flex_",
    "trends": "📈 *טרנדים עכשיו*\n\nעל מה אתה רוצה לדעת?\n\n_לדוגמה: streetwear, rap, sneakers_",
}

MODE_NAMES = {
    "hooks": "Hooks", "titles": "כותרות", "caption": "קפשין + האשטגים",
    "ideas": "רעיונות", "sounds": "סאונדים ויראליים", "trends": "טרנדים עכשיו",
}

CONTENT_PROMPTS = {
    "hooks": lambda t: f"""צור 5 hooks לטיקטוק לסרטון על: "{t}"
נישת streetwear / ראפ. כל hook מקסימום 10 מילים, מסקרן.
1. [hook]
2. [hook]
3. [hook]
4. [hook]
5. [hook]""",
    "titles": lambda t: f"""צור 5 כותרות לסרטון טיקטוק על: "{t}"
נישת streetwear / ראפ. קצרות, מסקרנות, עם אמוג'י.
1. [כותרת]
2. [כותרת]
3. [כותרת]
4. [כותרת]
5. [כותרת]""",
    "caption": lambda t: f"""כתוב קפשין + האשטגים לסרטון על: "{t}"
קפשין: 2-3 שורות אנרגטיות עם קריאה לפעולה.
---
15 האשטגים רלוונטיים לנישת streetwear/ראפ""",
    "ideas": lambda t: f"""תן 5 רעיונות לסרטוני טיקטוק ויראליים בנושא: "{t}"
נישת streetwear / ראפ.
🎬 [שם]
📋 [תיאור קצר]
🔥 [למה זה יתפוצץ]
---""",
    "sounds": lambda t: f"""חפש בגוגל סאונדים ויראליים עכשיו בטיקטוק לנישת ראפ/streetwear.
ויב הסרטון: "{t}"
המלץ על 5 סאונדים שבוערים עכשיו:
🎵 [שם השיר - אמן]
📈 [למה עובד עכשיו]
---""",
    "trends": lambda t: f"""חפש בגוגל הטרנדים הכי חמים עכשיו בטיקטוק בנושא: "{t}" בנישת streetwear/ראפ.
📈 [שם הטרנד]
📋 [תיאור + איך להצטרף]
🎯 [רמת תחרות: נמוכה/בינונית/גבוהה]
---""",
}


async def tg(method: str, **kwargs):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{TELEGRAM_API}/{method}", json=kwargs)
        return r.json()


async def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    return await tg("sendMessage", **kwargs)


async def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="Markdown"):
    kwargs = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    return await tg("editMessageText", **kwargs)


async def answer_callback(callback_id):
    await tg("answerCallbackQuery", callback_query_id=callback_id)


def generate_sync(mode: str, user_input: str) -> str:
    use_search = mode in ("sounds", "trends")
    tools = "google_search" if use_search else None
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        tools=tools,
        system_instruction=STREETWEAR_SYSTEM,
    )
    response = model.generate_content(CONTENT_PROMPTS[mode](user_input))
    return response.text


async def generate(mode: str, user_input: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_sync, mode, user_input)


async def handle_update(update: dict):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            await send_message(
                chat_id,
                "👋 היי! אני הבוט של טיק טוק - אלירן\n\nאני עוזר לך לייצר תוכן ויראלי לטיקטוק בנישת streetwear & ראפ 🔥\n\n🌐 מחובר לגוגל בזמן אמת!\n\nבחר מה תרצה לייצר:",
                reply_markup=KEYBOARDS["main"]
            )
            return

        if text == "/help":
            await send_message(
                chat_id,
                "🎯 *מה אני יכול לעשות:*\n\n🎣 *Hooks* — טקסטים לפתיחת הסרטון\n🔥 *כותרות* — כותרות שמושכות צפיות\n✍️ *קפשין + האשטגים* — טקסט לפוסט\n💡 *רעיונות* — רעיונות לסרטונים חדשים\n🎵 *סאונדים* — סאונדים ויראליים עכשיו\n📈 *טרנדים* — מה בוער ברגע זה\n\nפשוט לחץ כפתור ותאר לי את הסרטון 🚀",
                reply_markup=KEYBOARDS["main"]
            )
            return

        state = user_states.get(user_id)
        if not state:
            await send_message(chat_id, "בחר קודם מה תרצה לייצר 👇", reply_markup=KEYBOARDS["main"])
            return

        mode = state["mode"]
        is_search = mode in ("sounds", "trends")
        thinking_text = "🌐 מחפש בגוגל..." if is_search else f"⏳ מייצר {MODE_NAMES[mode]}..."
        sent = await send_message(chat_id, thinking_text)
        msg_id = sent["result"]["message_id"]

        try:
            result = await generate(mode, text)
            user_states.pop(user_id, None)
            prefix = "🌐 " if is_search else ""
            await edit_message(
                chat_id, msg_id,
                f"✅ {prefix}*{MODE_NAMES[mode]}:*\n\n{result}\n\n---\nרוצה עוד?",
                reply_markup=KEYBOARDS["main"]
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            await edit_message(chat_id, msg_id, "❌ הייתה שגיאה. נסה שוב.", reply_markup=KEYBOARDS["main"])

    elif "callback_query" in update:
        cb = update["callback_query"]
        user_id = cb["from"]["id"]
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        data = cb["data"]

        await answer_callback(cb["id"])

        if data == "back":
            user_states.pop(user_id, None)
            await edit_message(chat_id, msg_id, "בחר מה תרצה לייצר:", reply_markup=KEYBOARDS["main"])
        else:
            user_states[user_id] = {"mode": data}
            await edit_message(chat_id, msg_id, MODE_PROMPTS[data], reply_markup=KEYBOARDS["back"])


async def poll():
    offset = 0
    logger.info("Bot started polling!")
    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                r = await client.post(
                    f"{TELEGRAM_API}/getUpdates",
                    json={"offset": offset, "timeout": 30}
                )
                data = r.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        asyncio.create_task(handle_update(update))
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(poll())
