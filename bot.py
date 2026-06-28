import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

STREETWEAR_SYSTEM = """אתה מומחה לתוכן ויראלי בטיקטוק בנישת streetwear, ראפ והיפ-הופ.
אתה מכיר לעומק את הטרנדים, הסאונדים הויראליים, והאסתטיקה של הנישה.
תמיד תענה בעברית אלא אם מבקשים אחרת.
הסגנון שלך: ישיר, אנרגטי, ויראלי. אין מקום לתוכן משעמם."""

user_states = {}


def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎣 Hooks", callback_data="hooks"),
            InlineKeyboardButton("🔥 כותרות", callback_data="titles"),
        ],
        [
            InlineKeyboardButton("✍️ קפשין + האשטגים", callback_data="caption"),
            InlineKeyboardButton("💡 רעיונות", callback_data="ideas"),
        ],
        [
            InlineKeyboardButton("🎵 סאונדים ויראליים", callback_data="sounds"),
            InlineKeyboardButton("📈 טרנדים עכשיו", callback_data="trends"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 היי! אני הבוט של טיק טוק - אלירן\n\n"
        "אני עוזר לך לייצר תוכן ויראלי לטיקטוק בנישת streetwear & ראפ 🔥\n\n"
        "🌐 מחובר לגוגל בזמן אמת!\n\n"
        "בחר מה תרצה לייצר:"
    )
    await update.message.reply_text(welcome, reply_markup=get_main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🎯 *מה אני יכול לעשות:*\n\n"
        "🎣 *Hooks* — טקסטים לפתיחת הסרטון (3 שניות ראשונות)\n"
        "🔥 *כותרות* — כותרות שמושכות צפיות\n"
        "✍️ *קפשין + האשטגים* — טקסט לפוסט + האשטגים\n"
        "💡 *רעיונות* — רעיונות לסרטונים חדשים\n"
        "🎵 *סאונדים* — סאונדים ויראליים עכשיו\n"
        "📈 *טרנדים עכשיו* — מה בוער ברגע זה בטיקטוק\n\n"
        "🌐 הבוט מחובר לגוגל בזמן אמת!\n\n"
        "פשוט לחץ על כפתור ותאר לי את הסרטון 🚀"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    mode = query.data
    user_states[user_id] = {"mode": mode}

    prompts = {
        "hooks": "🎣 *Hooks לפתיחת הסרטון*\n\nתאר לי את הסרטון שלך ואני אכתוב לך 5 hooks שיעצרו אנשים בסקרול:\n\n_לדוגמה: outfit check עם ג'קט שחור ונעלי Jordan_",
        "titles": "🔥 *כותרות מושכות*\n\nתאר לי את הסרטון ואני אכתוב לך 5 כותרות שמביאות צפיות:\n\n_לדוגמה: unboxing נעליים נדירות שקניתי ב-2000₪_",
        "caption": "✍️ *קפשין + האשטגים*\n\nתאר לי את הסרטון ואני אכתוב קפשין + 15 האשטגים מנוצחים:\n\n_לדוגמה: haul של בגדים חדשים מהחנות_",
        "ideas": "💡 *רעיונות לסרטונים*\n\nתגיד לי נושא כללי ואני אתן לך 5 רעיונות ויראליים:\n\n_לדוגמה: streetwear, sneakers, rap outfits_",
        "sounds": "🎵 *סאונדים ויראליים*\n\nתגיד לי מה הוייב של הסרטון ואני אחפש מה בוער עכשיו:\n\n_לדוגמה: outfit אגרסיבי, flex, chill streetwear_",
        "trends": "📈 *טרנדים עכשיו*\n\nאני אחפש בגוגל מה בוער ברגע זה בטיקטוק.\n\nתגיד לי על מה אתה רוצה לדעת:\n\n_לדוגמה: streetwear, rap, sneakers_",
    }

    await query.edit_message_text(
        prompts[mode],
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="back")]]),
    )


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states.pop(user_id, None)
    await query.edit_message_text(
        "בחר מה תרצה לייצר:",
        reply_markup=get_main_keyboard()
    )


def needs_web_search(mode: str) -> bool:
    return mode in ("sounds", "trends")


async def generate_content(mode: str, user_input: str) -> str:
    use_search = needs_web_search(mode)

    if use_search:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            tools="google_search",
            system_instruction=STREETWEAR_SYSTEM,
        )
    else:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=STREETWEAR_SYSTEM,
        )

    prompts = {
        "hooks": f"""צור 5 hooks שונים לטיקטוק לסרטון על: "{user_input}"
הסרטון הוא בנישת streetwear / ראפ / היפ-הופ.
כל hook מקסימום 10 מילים, מסקרן, עוצר סקרול.
פרמט:
1. [hook]
2. [hook]
3. [hook]
4. [hook]
5. [hook]""",

        "titles": f"""צור 5 כותרות לסרטון טיקטוק על: "{user_input}"
הסרטון הוא בנישת streetwear / ראפ.
הכותרות צריכות להיות קצרות, מסקרנות, עם אמוג'י אם מתאים.
פרמט:
1. [כותרת]
2. [כותרת]
3. [כותרת]
4. [כותרת]
5. [כותרת]""",

        "caption": f"""כתוב קפשין + האשטגים לסרטון טיקטוק על: "{user_input}"
נישת streetwear / ראפ / היפ-הופ.

קפשין: 2-3 שורות אנרגטיות עם קריאה לפעולה.
---
15 האשטגים רלוונטיים - שלב גדולים וניש""",

        "ideas": f"""תן 5 רעיונות לסרטוני טיקטוק ויראליים בנושא: "{user_input}"
נישת streetwear / ראפ / היפ-הופ.

פרמט לכל רעיון:
🎬 [שם הסרטון]
📋 [תיאור קצר]
🔥 [למה זה יתפוצץ]
---""",

        "sounds": f"""חפש בגוגל אילו סאונדים ושירים ויראליים עכשיו בטיקטוק לנישת ראפ/היפ-הופ/streetwear.
הוייב של הסרטון: "{user_input}"

המלץ על 5 סאונדים אמיתיים שבוערים עכשיו:
🎵 [שם השיר - אמן]
📈 [למה הסאונד הזה עובד עכשיו]
---""",

        "trends": f"""חפש בגוגל מה הטרנדים הכי חמים עכשיו בטיקטוק בנושא: "{user_input}" בנישת streetwear/ראפ.

תן דוח טרנדים עדכני:
📈 [שם הטרנד]
📋 [תיאור + איך להצטרף]
🎯 [רמת תחרות: נמוכה/בינונית/גבוהה]
---""",
    }

    response = model.generate_content(prompts[mode])
    return response.text


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    if user_id not in user_states:
        await update.message.reply_text(
            "בחר קודם מה תרצה לייצר 👇",
            reply_markup=get_main_keyboard()
        )
        return

    mode = user_states[user_id].get("mode")
    if not mode:
        await update.message.reply_text("בחר קודם מה תרצה לייצר 👇", reply_markup=get_main_keyboard())
        return

    mode_names = {
        "hooks": "Hooks",
        "titles": "כותרות",
        "caption": "קפשין + האשטגים",
        "ideas": "רעיונות",
        "sounds": "סאונדים ויראליים",
        "trends": "טרנדים עכשיו",
    }

    search_modes = {"sounds", "trends"}
    is_search = mode in search_modes
    thinking_text = "🌐 מחפש בגוגל..." if is_search else f"⏳ מייצר {mode_names.get(mode, 'תוכן')}..."
    thinking_msg = await update.message.reply_text(thinking_text)

    try:
        result = await generate_content(mode, user_input)
        user_states.pop(user_id, None)

        prefix = "🌐 " if is_search else ""
        await thinking_msg.edit_text(
            f"✅ {prefix}*{mode_names.get(mode)}:*\n\n{result}\n\n---\nרוצה עוד?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await thinking_msg.edit_text(
            "❌ הייתה שגיאה. נסה שוב.",
            reply_markup=get_main_keyboard()
        )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot running with Gemini + Google Search!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
