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
        await message.reply_text("🔍 Image received. Sending anonymously...")

        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=message.photo[-1].file_id,
            caption="📝 Anonymous Image Question"
        )
        await message.reply_text("✅ Your image has been sent anonymously!")

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
