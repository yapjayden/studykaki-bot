# Running StudyKaki Bot on Localhost

This guide explains how to run the StudyKaki Telegram bot locally for development and testing.

## Prerequisites

- **Python 3.11 or higher**
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- An Anthropic API Key (for Claude AI)
- Sightengine API credentials (for NSFW image moderation)
- Telegram account for testing

## Installation

### 1. Clone the repository
```bash
git clone <repo-url>
cd studykaki-bot
```

### 2. Install dependencies

Using pip:
```bash
pip install -r requirements.txt
pip install anthropic
```

Or using uv (if available):
```bash
uv pip install -r requirements.txt
uv pip install anthropic
```

## Configuration

### 1. Create a `.env` file in the project root

```bash
cp .env.example .env  # if available, or create manually
```

### 2. Set up environment variables

Edit the `.env` file and add the following:

```env
BOT_TOKEN=your_telegram_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SIGHTENGINE_USER=your_sightengine_user_id
SIGHTENGINE_SECRET=your_sightengine_secret_key
MODERATOR_IDS=123456789,987654321
```

**Getting your credentials:**

- **BOT_TOKEN**: Contact [@BotFather](https://t.me/botfather) on Telegram to create a new bot
- **ANTHROPIC_API_KEY**: Get from [console.anthropic.com](https://console.anthropic.com)
- **SIGHTENGINE credentials**: Sign up at [sightengine.com](https://sightengine.com)
- **MODERATOR_IDS**: Your Telegram user ID(s) who can approve/reject posts (comma-separated)
  - To find your ID, message [@userinfobot](https://t.me/userinfobot) on Telegram

### 3. Load environment variables

**Linux/macOS:**
```bash
export $(cat .env | xargs)
```

**Windows (PowerShell):**
```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^\w+=' -and -not $_.StartsWith('#')) {
        $name, $value = $_.Split('=', 2)
        Set-Item -Path "env:$name" -Value $value
    }
}
```

## Running the Bot

### Start the bot
```bash
python3 main.py
```

You should see output like:
```
INFO:telegram.ext._application:Application started
```

The bot is now running and listening for Telegram messages.

## Testing Locally

1. **Find your bot**: Search for your bot on Telegram (using the username you set with @BotFather)
2. **Send a test message**: Send a question like "What is photosynthesis?"
3. **Check moderator notifications**: Your moderator account should receive approval requests
4. **Approve/reject**: Use the inline buttons to test moderation workflow

## Troubleshooting

### Bot doesn't respond
- Verify `BOT_TOKEN` is correct
- Ensure bot is running (check terminal output)
- Make sure you're messaging the correct bot

### API errors
- **Anthropic API Error**: Check `ANTHROPIC_API_KEY` is valid and has credits
- **Sightengine Error**: Verify `SIGHTENGINE_USER` and `SIGHTENGINE_SECRET`
- **Telegram API Error**: Ensure `BOT_TOKEN` is still valid (can expire)

### Moderator not receiving notifications
- Check `MODERATOR_IDS` are correct (should be numeric Telegram user IDs)
- Verify the moderator bot is still running
- Ensure bot has permission to send messages to that user

## Key Features to Test

✅ **AI Q&A**: Send a text question and get an instant answer from Claude
✅ **Image Submissions**: Send an image and test the NSFW moderation
✅ **Moderation Flow**: Test approve/reject buttons as a moderator
✅ **Channel Posting**: Verify approved posts go to the channel (if configured)
✅ **Profanity Filter**: Try sending inappropriate text

## Project Structure

```
studykaki-bot/
├── main.py              # Main bot logic
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project configuration
├── Procfile            # Heroku deployment config
└── LOCALHOST_README.md # This file
```

## Stopping the Bot

Press `Ctrl+C` in the terminal where the bot is running.

## Next Steps

- Deploy to Heroku/Railway using the `Procfile`
- Configure the `@studykakiSG` channel for posting
- Add more moderators via `MODERATOR_IDS`
- Customize AI system prompt in `get_ai_answer()` function
