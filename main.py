import os
import logging
import requests
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from better_profanity import profanity

# Environment variables
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@studykakiSG"
SIGHTENGINE_USER = os.environ["SIGHTENGINE_USER"]
SIGHTENGINE_SECRET = os.environ["SIGHTENGINE_SECRET"]

# Logging
logging.basicConfig(level=logging.INFO)

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Post your question!")

# Text and Image Handler
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # TEXT
    if message.text:
        text = message.text.strip()

        if profanity.contains_profanity(text):
            await message.reply_text("❌ Your question contains inappropriate content.")
            return

        keywords = ["what", "why", "how", "when", "who", "where", "does", "is", "can", "should"]
        if not text.endswith("?") and not any(word in text.lower() for word in keywords):
            await message.reply_text("🤖 Please submit a valid question.")
            return

        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📝 Anonymous Question:\n\n{text}")
        await message.reply_text("✅ Your question has been sent anonymously!")

    # IMAGE
    elif message.photo:
        await message.reply_text("🔍 Scanning image for inappropriate content...")

        try:
            photo = message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_url = file.file_path
            print("File URL:", file_url)

            params = {
                'url': file_url,
                'models': 'nudity-2.1,weapon,recreational_drug,medical,offensive-2.0,scam,face-attributes,gore-2.0,qr-content,tobacco,violence,self-harm,gambling',
                'api_user': SIGHTENGINE_USER,
                'api_secret': SIGHTENGINE_SECRET
            }
            r = requests.get('https://api.sightengine.com/1.0/check.json', params=params)
            output = r.json()
            print("Sightengine response:", json.dumps(output, indent=2))

            # Fail-safe: if status not success, exit
            if output.get("status") != "success":
                raise ValueError("Sightengine failed")

            # Safely extract values
            nudity = output.get("nudity", {})
            gore = output.get("gore", {}).get("prob", 0)
            violence = output.get("violence", {}).get("prob", 0)
            selfharm = output.get("self-harm", {}).get("prob", 0)

            # Weapon detection expanded
            weapon_section = output.get("weapon", {})
            weapon_classes = weapon_section.get("classes", {})
            weapon_actions = weapon_section.get("firearm_action", {})
            weapon_types = weapon_section.get("firearm_type", {})

            violations = []
            if (
                nudity.get("sexual_activity", 0) > 0.5 or
                nudity.get("sexual_display", 0) > 0.5 or
                nudity.get("erotica", 0) > 0.5 or
                nudity.get("very_suggestive", 0) > 0.5 or
                nudity.get("suggestive", 0) > 0.5 or
                nudity.get("mildly_suggestive", 0) > 0.5
            ):
                violations.append("nudity")

            # Weapon checks
            if any(score > 0.3 for score in weapon_classes.values()):
                violations.append("weapon")
            if any(score > 0.3 for score in weapon_actions.values()):
                violations.append("weapon-action")
            if any(score > 0.3 for score in weapon_types.values()):
                violations.append("weapon-type")
            
            if gore > 0.5: violations.append("gore")
            if violence > 0.5: violations.append("violence")
            if selfharm > 0.5: violations.append("self-harm")

            if violations:
                await message.reply_text(f"🚫 Image blocked due to: {', '.join(violations)}")
                return

            # Passed: send to channel
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo.file_id,
                caption="📝 Anonymous Image Question"
            )
            await message.reply_text("✅ Your image has been sent anonymously!")

        except Exception as e:
            await message.reply_text("⚠️ Error scanning image. Please try again.")
            print("Error:", e)

    else:
        await message.reply_text("❌ Unsupported message type.")

# Run bot
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
