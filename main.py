import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from better_profanity import profanity

# Load bot token from Railway environment variable
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@studykakiSG"  # Replace with your actual channel username or chat ID
SIGHTENGINE_USER = os.environ["SIGHTENGINE_USER"]
SIGHTENGINE_SECRET = os.environ["SIGHTENGINE_SECRET"]

# Setup logging
logging.basicConfig(level=logging.INFO)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Post your question!")

# Handle both text and image questions
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # TEXT HANDLING
    if message.text:
        text = message.text.strip()

        if profanity.contains_profanity(text):
            await message.reply_text("❌ Your question contains inappropriate content.")
            return

        question_keywords = ["what", "why", "how", "when", "who", "where", "does", "is", "can", "should"]
        if not text.endswith("?") and not any(word in text.lower() for word in question_keywords):
            await message.reply_text("🤖 Please submit a valid question.")
            return

        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📝 Anonymous Question:\n\n{text}")
        await message.reply_text("✅ Your question has been sent anonymously!")

    # IMAGE HANDLING
    elif message.photo:
        await message.reply_text("🔍 Scanning image for inappropriate content...")

        try:
            photo = message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

            # Sightengine NSFW + other content models
            params = {
                'url': file_url,
                'models': 'nudity-2.1,weapon,recreational_drug,medical,offensive-2.0,scam,face-attributes,gore-2.0,qr-content,tobacco,violence,self-harm,gambling',
                'api_user': SIGHTENGINE_USER,
                'api_secret': SIGHTENGINE_SECRET
            }
            r = requests.get('https://api.sightengine.com/1.0/check.json', params=params)
            output = r.json()

            # Check for violations
            violations = []
            if output.get("nudity", {}).get("raw", 0) > 0.5:
                violations.append("nudity")
            if output.get("weapon", 0) > 0.5:
                violations.append("weapon")
            if output.get("gore", 0) > 0.5:
                violations.append("gore")
            if output.get("violence", 0) > 0.5:
                violations.append("violence")
            if output.get("self-harm", 0) > 0.5:
                violations.append("self-harm")

            if violations:
                await message.reply_text(f"🚫 Image blocked due to: {', '.join(violations)}")
                return

            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo.file_id,
                caption="📝 Anonymous Image Question"
            )
            await message.reply_text("✅ Your image has been sent anonymously!")

        except Exception as e:
            await message.reply_text("⚠️ Error scanning image. Please try again.")
            print(e)

    else:
        await message.reply_text("❌ Unsupported message type.")


# Bot setup and run
async def main():
    profanity.load_censor_words()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_question))

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())
