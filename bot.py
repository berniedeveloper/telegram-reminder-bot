import os
import json
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

# Define the file path for storing media data
DATA_FILE = 'media_data.json'

# Load existing media data or initialize an empty list
try:
    with open(DATA_FILE, 'r') as file:
        media_data = json.load(file)
except FileNotFoundError:
    media_data = []

# Define the start command with a custom keyboard menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["\U0001F4C4 List Media", "\U0001F4DD Tag Media"],
        ["\U0001F4E4 Send Media"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_message = (
        "\U0001F44B Welcome to the Media Bot!\n"
        "Use the buttons below or the corresponding slash commands:\n"
        "- /list: View recent saved media\n"
        "- /tag <index> <tag1> [tag2...]: Tag media files\n"
        "- /start: Redisplay this menu"
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# Handle incoming media files and save their metadata
async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file_id = None
    media_type = None

    # Identify the type of media and extract its file_id
    if msg.photo:
        file_id = msg.photo[-1].file_id
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

        # Persist data to file
        with open(DATA_FILE, 'w') as file:
            json.dump(media_data, file, indent=2)

        await update.message.reply_text(f"\u2705 {media_type.title()} saved successfully as media #{len(media_data)}.")
    else:
        await update.message.reply_text("\u274C Unsupported media type. Please send a photo, video, or document.")

# Command handler to tag media items by index
async def tag_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("\u2139 Usage: /tag <index> <tag1> [tag2 ...]")
        return

    try:
        index = int(args[0]) - 1
        if index < 0 or index >= len(media_data):
            await update.message.reply_text("\u26A0 Invalid media index.")
            return

        new_tags = args[1:]
        media_data[index]['tags'].extend(new_tags)
        media_data[index]['tags'] = list(set(media_data[index]['tags']))  # Ensure uniqueness

        with open(DATA_FILE, 'w') as file:
            json.dump(media_data, file, indent=2)

        await update.message.reply_text(f"\u2714 Tags added to media #{index + 1}: {', '.join(new_tags)}")
    except ValueError:
        await update.message.reply_text("\u274C Invalid index. Please provide a numeric value.")

# Display the list of recently saved media files
async def list_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not media_data:
        await update.message.reply_text("\u2139 No media saved yet.")
        return

    response = "\U0001F4CB Last 10 Saved Media:\n"
    start_index = max(len(media_data) - 10, 0)
    for i, item in enumerate(media_data[start_index:], start=start_index + 1):
        tags = ', '.join(item['tags']) if item['tags'] else 'None'
        caption_preview = (item['caption'][:27] + '...') if len(item['caption']) > 30 else item['caption']
        response += f"{i}. Type: {item['media_type'].title()}, Tags: {tags}, Caption: {caption_preview}\n"

    await update.message.reply_text(response)

# Handle channel posts (optional, for broadcasted content)
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.photo:
        await message.reply_text("\U0001F4F7 Photo received in channel!")
    elif message.video:
        await message.reply_text("\U0001F4FD Video received in channel!")
    elif message.document:
        await message.reply_text("\U0001F4C4 Document received in channel!")
    else:
        await message.reply_text("\U0001F4DD Non-media message received in channel.")

# Respond to menu selections from the custom keyboard
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "\U0001F4C4 List Media":
        await list_media(update, context)
    elif text == "\U0001F4DD Tag Media":
        await update.message.reply_text("\u2139 To tag media, use the command:\n/tag <index> <tag1> [tag2...]")
    elif text == "\U0001F4E4 Send Media":
        await update.message.reply_text("\u2139 Please send a photo, video, or document now.")
    else:
        await update.message.reply_text("\u2753 Unrecognized option. Use the menu or /start to begin.")

# Main function to launch the bot
def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("\u274C Error: BOT_TOKEN environment variable is not set.")
        return

    app = ApplicationBuilder().token(bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tag", tag_media))
    app.add_handler(CommandHandler("list", list_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, save_media))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, handle_channel_post))

    print("\u2705 Bot is up and running...")

    while True:
        try:
            app.run_polling()
        except Exception as error:
            print(f"\u26A0 Bot encountered an error: {error}")
            print("\u23F3 Restarting bot in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    main()
