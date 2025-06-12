import os
import json
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)

DATA_FILE = 'media_data.json'

# Load or initialize media data
try:
    with open(DATA_FILE, 'r') as f:
        media_data = json.load(f)
except FileNotFoundError:
    media_data = []

# --- Helper Functions ---
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(media_data, f, indent=2)

def count_media_by_type():
    return {
        'photo': sum(1 for m in media_data if m['media_type'] == 'photo'),
        'video': sum(1 for m in media_data if m['media_type'] == 'video'),
        'document': sum(1 for m in media_data if m['media_type'] == 'document')
    }

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📄 List Media", callback_data='list')],
        [InlineKeyboardButton("🔍 Search by Tag", callback_data='search')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats')]
    ]
    await update.message.reply_text(
        "📥 Welcome! Use the buttons below or commands.\n\n"
        "/tag <index> <tags> — Tag media\n"
        "/delete <index> — Delete media",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def list_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not media_data:
        await update.message.reply_text("No media saved yet.")
        return

    text = "📄 Last 10 saved media:\n"
    start_index = max(len(media_data) - 10, 0)
    for i, item in enumerate(media_data[start_index:], start=start_index + 1):
        tags = ', '.join(item['tags']) if item['tags'] else 'None'
        caption = item['caption']
        if len(caption) > 30:
            caption = caption[:27] + '...'
        text += f"{i}. {item['media_type'].title()} | Tags: {tags} | {caption}\n"
    await update.message.reply_text(text)

async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file_id = None
    media_type = None

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
        media_data.append({
            "file_id": file_id,
            "caption": msg.caption or "",
            "media_type": media_type,
            "tags": []
        })
        save_data()
        await update.message.reply_text(f"{media_type.title()} saved! Media #{len(media_data)}.")
    else:
        await update.message.reply_text("Unsupported media. Send a photo, video, or document.")

async def tag_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /tag <index> <tag1> [tag2 ...]")
        return

    try:
        idx = int(args[0]) - 1
        if idx < 0 or idx >= len(media_data):
            await update.message.reply_text("Invalid index.")
            return
        new_tags = args[1:]
        media_data[idx]["tags"].extend(new_tags)
        media_data[idx]["tags"] = list(set(media_data[idx]["tags"]))
        save_data()
        await update.message.reply_text(f"Tags added to media #{idx + 1}: {', '.join(new_tags)}")
    except ValueError:
        await update.message.reply_text("Media index must be a number.")

async def delete_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /delete <index>")
        return

    try:
        idx = int(args[0]) - 1
        if idx < 0 or idx >= len(media_data):
            await update.message.reply_text("Invalid index.")
            return
        deleted = media_data.pop(idx)
        save_data()
        await update.message.reply_text(f"Deleted media #{idx + 1}: {deleted['media_type'].title()}")
    except ValueError:
        await update.message.reply_text("Media index must be a number.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = count_media_by_type()
    total = len(media_data)
    tag_count = sum(len(m['tags']) for m in media_data)
    await update.message.reply_text(
        f"📊 Media Stats:\n"
        f"- Total Media: {total}\n"
        f"- Photos: {counts['photo']}\n"
        f"- Videos: {counts['video']}\n"
        f"- Documents: {counts['document']}\n"
        f"- Total Tags Used: {tag_count}"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /search <tag>")
        return

    tag = args[0].lower()
    results = [m for m in media_data if tag in [t.lower() for t in m['tags']]]
    if not results:
        await update.message.reply_text(f"No media found with tag '{tag}'.")
        return

    text = f"🔍 Media with tag '{tag}':\n"
    for i, item in enumerate(results, start=1):
        caption = item['caption']
        if len(caption) > 30:
            caption = caption[:27] + '...'
        text += f"{i}. {item['media_type'].title()} | {caption}\n"
    await update.message.reply_text(text)

# --- Inline Menu Handler ---
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "list":
        await list_media(query, context)
    elif query.data == "search":
        await query.edit_message_text("Use /search <tag> to find media.")
    elif query.data == "stats":
        await stats(query, context)

# --- Bot Setup ---
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN is missing!")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tag", tag_media))
    app.add_handler(CommandHandler("delete", delete_media))
    app.add_handler(CommandHandler("list", list_media))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_menu))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, save_media))

    print("✅ Bot is running...")
    while True:
        try:
            app.run_polling()
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
