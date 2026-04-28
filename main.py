import os
import logging
import requests
import json
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from better_profanity import profanity
import anthropic

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@studykakiSG"
SIGHTENGINE_USER = os.environ["SIGHTENGINE_USER"]
SIGHTENGINE_SECRET = os.environ["SIGHTENGINE_SECRET"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# List your moderator Telegram user IDs here
MODERATOR_IDS = os.environ["MODERATOR_IDS"].split(",")
MODERATOR_IDS = [int(id.strip()) for id in MODERATOR_IDS]

moderation_queue = {}
# Stores pending AI responses waiting for user decision
# { question_id: { "text": ..., "photo": ..., "ai_answer": ... } }
ai_pending = {}

logging.basicConfig(level=logging.INFO)

# Use AsyncAnthropic so API calls don't block the bot event loop
anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def get_ai_answer(question: str) -> str:
    """Call Claude to answer a student question (non-blocking)."""
    try:
        message = await anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=(
                "You are a helpful study assistant for Singaporean students. "
                "Answer questions clearly and concisely. Use simple language suitable for students. "
                "Where relevant, reference the Singapore curriculum (O-levels, A-levels, IB, polytechnic, university). "
                "If the question is ambiguous, give a helpful general answer. "
                "Keep answers under 300 words. Do not use excessive markdown — keep it readable in a Telegram message."
            ),
            messages=[{"role": "user", "content": question}]
        )
        return message.content[0].text
    except Exception as e:
        logging.error(f"Anthropic API error: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *StudyKaki*!\n\n"
        "Send me your study question and I'll try to answer it right away. "
        "If you're not satisfied, you can post it anonymously to the channel for others to help! 📚",
        parse_mode="Markdown"
    )


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.text:
        text = message.text.strip()

        # --- Profanity check ---
        if profanity.contains_profanity(text):
            await message.reply_text("❌ Your question contains inappropriate content.")
            return

        # --- Basic question validation ---
        keywords = ["what", "why", "how", "when", "who", "where", "does", "is", "can", "should"]
        if not text.endswith("?") and not any(word in text.lower() for word in keywords):
            await message.reply_text("🤖 Please submit a valid question.")
            return

        # --- Try AI answer first ---
        thinking_msg = await message.reply_text("🤔 Let me think about that...")
        ai_answer = await get_ai_answer(text)

        question_id = str(uuid4())
        ai_pending[question_id] = {"text": text, "photo": None, "ai_answer": ai_answer}

        if ai_answer:
            keyboard = [
                [
                    InlineKeyboardButton("✅ That helped!", callback_data=f"ai_satisfied:{question_id}"),
                    InlineKeyboardButton("📢 Post to channel", callback_data=f"ai_post:{question_id}")
                ]
            ]
            markup = InlineKeyboardMarkup(keyboard)

            await thinking_msg.delete()
            await message.reply_text(
                f"🤖 *StudyKaki AI Answer:*\n\n{ai_answer}\n\n"
                "─────────────────\n"
                "_Was this helpful? Or would you like to post your question to the channel for more input?_",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            # AI failed — fall through to moderation queue directly
            await thinking_msg.delete()
            await message.reply_text("⚠️ AI couldn't generate an answer. Sending your question for review...")
            await submit_to_moderation(context, question_id, text, None)

    elif message.photo:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_url = file.file_path

        # --- Sightengine NSFW check ---
        params = {
            'url': file_url,
            'models': 'nudity-2.1,weapon,recreational_drug,medical,offensive-2.0,scam,face-attributes,gore-2.0,qr-content,tobacco,violence,self-harm,gambling',
            'api_user': SIGHTENGINE_USER,
            'api_secret': SIGHTENGINE_SECRET
        }
        r = requests.get('https://api.sightengine.com/1.0/check.json', params=params)
        output = r.json()
        if output.get("status") != "success":
            await message.reply_text("⚠️ Error scanning image.")
            return

        nudity = output.get("nudity", {})
        weapon = output.get("weapon", {})
        inappropriate = False
        if any(nudity.get(k, 0) > 0.3 for k in ["sexual_activity", "sexual_display", "erotica", "very_suggestive", "suggestive", "mildly_suggestive"]):
            inappropriate = True
        if any(v > 0.3 for v in weapon.get("classes", {}).values()) or \
           any(v > 0.3 for v in weapon.get("firearm_action", {}).values()) or \
           any(v > 0.3 for v in weapon.get("firearm_type", {}).values()):
            inappropriate = True

        if inappropriate:
            await message.reply_text("🚫 This image contains inappropriate content.")
            return

        # --- Image: skip AI, go straight to moderation with AI caption option ---
        # Optionally: extract text from image via OCR and feed to AI — skipped for now
        question_id = str(uuid4())
        ai_pending[question_id] = {"text": None, "photo": photo.file_id, "ai_answer": None}

        keyboard = [
            [
                InlineKeyboardButton("📢 Post to channel", callback_data=f"ai_post:{question_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"ai_satisfied:{question_id}")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        await message.reply_photo(
            photo=photo.file_id,
            caption=(
                "📷 *Image received!*\n\n"
                "AI answers work best with text questions. "
                "Would you like to post this image to the channel for others to help?\n\n"
                "_Note: your submission will be reviewed before posting._"
            ),
            parse_mode="Markdown",
            reply_markup=markup
        )

    else:
        await message.reply_text("❌ Unsupported message type. Please send text or an image.")


async def handle_ai_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's choice after seeing the AI answer."""
    query = update.callback_query
    await query.answer()

    action, qid = query.data.split(":", 1)

    if qid not in ai_pending:
        await query.edit_message_text("⏳ This session has expired. Please resend your question.")
        return

    data = ai_pending.pop(qid)

    if action == "ai_satisfied":
        # User is happy with AI answer — done
        if data["photo"]:
            await query.edit_message_caption("✅ Glad to help! Feel free to ask another question anytime. 📚")
        else:
            await query.edit_message_text(
                f"🤖 *StudyKaki AI Answer:*\n\n{data['ai_answer']}\n\n─────────────────\n✅ _Glad that helped! Feel free to ask another question anytime._",
                parse_mode="Markdown"
            )

    elif action == "ai_post":
        # User wants to post to channel — send to moderation
        question_id = str(uuid4())
        moderation_queue[question_id] = {"text": data["text"], "photo": data["photo"]}

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{question_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{question_id}")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        # Notify moderators
        for mod_id in MODERATOR_IDS:
            if data["text"]:
                mod_text = f"📬 New submission for review:\n\n{data['text']}"
                if data["ai_answer"]:
                    mod_text += f"\n\n🤖 _AI already answered — user wants more input._"
                await context.bot.send_message(chat_id=mod_id, text=mod_text, reply_markup=markup, parse_mode="Markdown")
            elif data["photo"]:
                await context.bot.send_photo(
                    chat_id=mod_id,
                    photo=data["photo"],
                    caption="📬 Image submission pending approval",
                    reply_markup=markup
                )

        # Update message for user
        if data["photo"]:
            await query.edit_message_caption("🕒 Your image has been submitted for review! It'll be posted anonymously once approved.")
        else:
            await query.edit_message_text(
                f"🤖 *StudyKaki AI Answer:*\n\n{data['ai_answer']}\n\n─────────────────\n🕒 _Your question has been submitted for review and will be posted anonymously once approved!_",
                parse_mode="Markdown"
            )


async def submit_to_moderation(context, question_id, text, photo):
    """Helper to push directly to moderation queue (used when AI fails)."""
    moderation_queue[question_id] = {"text": text, "photo": photo}
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{question_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{question_id}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    for mod_id in MODERATOR_IDS:
        if text:
            await context.bot.send_message(chat_id=mod_id, text=f"New submission:\n\n{text}", reply_markup=markup)
        elif photo:
            await context.bot.send_photo(chat_id=mod_id, photo=photo, caption="Image submission pending approval", reply_markup=markup)


async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Moderator approves or rejects a post."""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in MODERATOR_IDS:
        await query.answer("❌ You're not authorized to moderate.", show_alert=True)
        return

    action, qid = query.data.split(":")
    if qid not in moderation_queue:
        await query.answer("⏳ Already reviewed or expired.", show_alert=True)
        return

    data = moderation_queue.pop(qid)
    if action == "approve":
        if data["text"]:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📝 Anonymous Question:\n\n{data['text']}")
            await query.edit_message_text("✅ Approved and posted.")
        elif data["photo"]:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data["photo"], caption="📝 Anonymous Image Question")
            await query.edit_message_caption("✅ Approved and posted.")
    else:
        if data["photo"]:
            await query.edit_message_caption("❌ Rejected.")
        else:
            await query.edit_message_text("❌ Rejected.")


async def main():
    profanity.load_censor_words()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_question))

    # AI decision handler (must come before general approval handler)
    app.add_handler(CallbackQueryHandler(handle_ai_decision, pattern=r"^ai_(satisfied|post):"))
    app.add_handler(CallbackQueryHandler(handle_approval, pattern=r"^(approve|reject):"))

    await app.run_polling()


if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())
