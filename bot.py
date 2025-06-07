import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

DATA_FILE = 'media_data.json'

# Load or initialize media data
try:
    with open(DATA_FILE, 'r') as f:
        media_data = json.load(f)
except FileNotFoundError:
    media_data = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me photos, videos, or documents and I will save them.\n"
        "Use /tag <index> <tag1> [tag2 ...] to tag a saved media.\n"
        "Use /list to see recent saved media."
    )

async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file_id = None
    media_type = None

    if msg.photo:
        file_id = msg.photo[-1].file_id  # highest quality photo
        media_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        media_type = "video"
    elif msg.document:
        file_id = msg.document.file_id
        media_type = "document"

    if file_id and media_type:
        media_item = {
            "file_id": file_id,
            "caption": msg.caption or "",
            "media_type": media_type,
            "tags": []
        }
        media_data.append(media_item)
        with open(DATA_FILE, 'w') as f:
            json.dump(media_data, f, indent=2)
        await update.message.reply_text(f"{media_type.title()} saved! It is media #{len(media_data)}.")
    else:
        await update.message.reply_text("Unsupported media type. Please send photos, videos, or documents.")

async def tag_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /tag <media_index> <tag1> [tag2 ...]")
        return

    try:
        idx = int(args[0]) - 1  # zero-based index
        if idx < 0 or idx >= len(media_data):
            await update.message.reply_text("Invalid media index.")
            return
        new_tags = args[1:]
        media_data[idx]["tags"].extend(new_tags)
        media_data[idx]["tags"] = list(set(media_data[idx]["tags"]))  # unique tags

        with open(DATA_FILE, 'w') as f:
            json.dump(media_data, f, indent=2)

        await update.message.reply_text(f"Added tags to media #{idx+1}: {', '.join(new_tags)}")
    except ValueError:
        await update.message.reply_text("The media index must be a number.")

async def list_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not media_data:
        await update.message.reply_text("No media saved yet.")
        return

    text = "Last 10 saved media:\n"
    start_index = max(len(media_data) - 10, 0)
    for i, item in enumerate(media_data[start_index:], start=start_index + 1):
        tags = ', '.join(item['tags']) if item['tags'] else 'None'
        caption_preview = (item['caption'][:27] + '...') if len(item['caption']) > 30 else item['caption']
        text += f"{i}. Type: {item['media_type'].title()}, Tags: {tags}, Caption: {caption_preview}\n"

    await update.message.reply_text(text)

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.photo:
        await message.reply_text("📸 Photo received in channel!")
    elif message.video:
        await message.reply_text("📹 Video received in channel!")
    elif message.document:
        await message.reply_text("📄 Document received in channel!")
    else:
        await message.reply_text("📝 Non-media message received in channel.")

def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ Error: BOT_TOKEN environment variable is missing!")
        return

    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, save_media))
    app.add_handler(CommandHandler("tag", tag_media))
    app.add_handler(CommandHandler("list", list_media))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, handle_channel_post))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
