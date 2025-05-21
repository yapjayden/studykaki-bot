import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from better_profanity import profanity

# Load bot token from Railway environment variable
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@studykakiSG"  # Replace with your actual channel username or chat ID
DEEP_AI_KEY = os.environ["DEEP_AI_KEY"]

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
        await message.reply_text("🔍 Scanning image for NSFW content...")

        # 1. Get Telegram file URL
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_url = file.file_path

        # 2. Send image to DeepAI NSFW Detector
        try:
            response = requests.post(
                "https://api.deepai.org/api/nsfw-detector",
                data={"image": file_url},
                headers={"api-key": DEEP_AI_KEY}
            )
            result = response.json()
            nsfw_score = result["output"]["nsfw_score"]

            if nsfw_score >= 0.6:
                await message.reply_text("🚫 NSFW image detected. Not sent.")
                return
        except Exception as e:
            await message.reply_text("⚠️ Error scanning image. Please try again.")
            return

        # 3. Safe image → send to channel
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photo.file_id,
            caption="📝 Anonymous Image Question"
        )
        await message.reply_text("✅ Your image has been sent anonymously!")


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
