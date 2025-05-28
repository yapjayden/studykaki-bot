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

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@studykakiSG"
SIGHTENGINE_USER = os.environ["SIGHTENGINE_USER"]
SIGHTENGINE_SECRET = os.environ["SIGHTENGINE_SECRET"]

# List your moderator Telegram user IDs here
MODERATOR_IDS = os.environ["MODERATOR_IDS"].split(",")
MODERATOR_IDS = [int(id.strip()) for id in MODERATOR_IDS]    # Replace with actual IDs

moderation_queue = {}

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Post your question!")

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.text:
        text = message.text.strip()
        if profanity.contains_profanity(text):
            await message.reply_text("❌ Your question contains inappropriate content.")
            return

        keywords = ["what", "why", "how", "when", "who", "where", "does", "is", "can", "should"]
        if not text.endswith("?") and not any(word in text.lower() for word in keywords):
            await message.reply_text("🤖 Please submit a valid question.")
            return

        question_id = str(uuid4())
        moderation_queue[question_id] = {"text": text, "photo": None}

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{question_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{question_id}")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        for mod_id in MODERATOR_IDS:
            await context.bot.send_message(chat_id=mod_id, text=f"New submission:\n\n{text}", reply_markup=markup)

        await message.reply_text("🕒 Your question has been submitted for review!")

    elif message.photo:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_url = file.file_path

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

        # NSFW/weapon filtering
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

        question_id = str(uuid4())
        moderation_queue[question_id] = {"text": None, "photo": photo.file_id}

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{question_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{question_id}")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        for mod_id in MODERATOR_IDS:
            await context.bot.send_photo(chat_id=mod_id, photo=photo.file_id, caption="Image submission pending approval", reply_markup=markup)

        await message.reply_text("🕒 Your image has been submitted for review!")

    else:
        await message.reply_text("❌ Unsupported message type.")

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in MODERATOR_IDS:
        await query.answer("❌ You’re not authorized to moderate.", show_alert=True)
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
    app.add_handler(CallbackQueryHandler(handle_approval))

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())

