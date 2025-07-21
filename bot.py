import json
import os
import feedparser
from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import youtube
from telegraph import Telegraph
from dotenv import load_dotenv
import os

CHANNELS_FILE = "channels.json"
user_states = {}  # user_id -> "youtube_adding"

telegraph = Telegraph()
telegraph.create_account(short_name='yt_bot')

def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        return {}
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def add_to_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args

    if args:
        # User sent args directly, add channel immediately
        youtube_link = args[0]
        alias = args[1] if len(args) > 1 else None
        result_msg = await process_youtube_link(youtube_link, alias)
        await update.message.reply_text(result_msg)
    else:
        # No args, enter multi-input mode
        user_states[user_id] = "youtube_adding"
        await update.message.reply_text(
            "Send me YouTube channel URLs now (one per message, optional alias after space). Send /cancel when done."
        )

async def process_youtube_link(youtube_link, alias=None):
    channel_id = youtube.get_channel_id_from_url(youtube_link)
    if not channel_id:
        return "❌ Could not extract channel ID from that URL."

    if not alias:
        alias = youtube.get_channel_name_from_rss(channel_id).lower()

    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    channel_info = {
        "channel_id": channel_id,
        "rss_url": rss_url,
        "channel_name": youtube.get_channel_name_from_rss(channel_id),
        "last_video_id": None
    }

    message = youtube.append_channel_to_json_file(channel_info, alias)
    if "⚠️" in message:
        return message

    return f"✅ Added channel with alias '{alias}' successfully!"

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) != "youtube_adding":
        return  # Not in multi-input mode

    text = update.message.text.strip()
    if text == "/cancel":
        user_states.pop(user_id)
        await update.message.reply_text("Exited YouTube adding mode.")
        return

    parts = text.split()
    youtube_link = parts[0]
    alias = parts[1] if len(parts) > 1 else None

    result_msg = await process_youtube_link(youtube_link, alias)
    await update.message.reply_text(result_msg)

async def fetch_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    alias = args[0].lower() if args else None
    channels = load_channels()

    aliases_to_fetch = channels.keys() if alias is None else [alias]

    messages = []
    for a in aliases_to_fetch:
        ch = channels[a]
        feed = feedparser.parse(ch["rss_url"])

        if not feed.entries:
            messages.append(f"No videos found for alias '{a}'.")
            continue

        latest_video = feed.entries[0]
        latest_video_id = latest_video.yt_videoid if hasattr(latest_video, "yt_videoid") else latest_video.id

        if ch["last_video_id"] == latest_video_id:
            messages.append(f"No new videos for '{a}'.")
        else:
            video_id, date_published = youtube.latest_video(ch['rss_url'])
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            name = ch['channel_name']
            messages.append(f"🎥 New video from {name}:\n{video_url}")
            # update last_video_id
            channels[a]["last_video_id"] = latest_video_id

    # Send all messages back
    await update.message.reply_text("\n\n".join(messages))

async def list_channels_telegraph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channels = load_channels()

    if not channels:
        await update.message.reply_text("You don't have any saved channels yet.")
        return

    html_content = "<h3>Your saved YouTube channels:</h3><ul>"
    for info in channels.values():
        channel_name = info.get("channel_name", "Unknown Name")
        html_content += f"<li>{channel_name}</li>"
    html_content += "</ul>"

    response = telegraph.create_page(
        title='YouTube Channels',
        html_content=html_content
    )
    url = 'https://telegra.ph/' + response['path']

    await update.message.reply_text(f"Here’s your channel list: {url}")

async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help information"),
        BotCommand("about", "About this bot"),
        BotCommand("add_to_youtube", "Add a YouTube channel to track"),
        BotCommand("fetch_from_youtube", "Fetch latest videos from added channels"),
        BotCommand("list_channels_telegraph", "List saved YouTube channels on Telegraph"),
    ])

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Welcome! Please send a movie or series name.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Help: Send a movie or series name to search.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Try sending a movie or series name.")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.pop(user_id, None) == "youtube_adding":
        await update.message.reply_text("Exited YouTube adding mode.")
    else:
        await update.message.reply_text("Nothing to cancel.")

if __name__ == "__main__":
    import asyncio
    import logging
    from telegram.ext import Application

    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("add_to_youtube", add_to_youtube))
    app.add_handler(CommandHandler("fetch_from_youtube", fetch_video))
    app.add_handler(CommandHandler("list_channels_telegraph", list_channels_telegraph))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    print("Bot started...")
    app.post_init = set_commands 
    app.run_polling()
