import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from better_profanity import profanity

BOT_TOKEN = "7766702462:AAEYGsFVZkSd_ZFuiAIe-UNUiV93tH_naYM"
CHANNEL_ID = "@studykakiSG"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Post your question!")

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    if profanity.contains_profanity(question):
        await update.message.reply_text("❌ Your question contains inappropriate content.")
    else:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📝 Anonymous Question:\n\n{question}")
        await update.message.reply_text("✅ Your question has been sent anonymously!")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    profanity.load_censor_words()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())
