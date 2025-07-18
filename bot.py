import json
import os
import feedparser
from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import youtube

CHANNELS_FILE = "channels.json"

def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        return {}
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def add_to_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /add_to_youtube <channel_url> [alias]")
        return

    youtube_link = args[0]
    alias = args[1] if len(args) > 1 else None

    channel_id = youtube.get_channel_id_from_url(youtube_link)

    if not alias:
        # use channel_id as alias if none provided
        alias = youtube.get_channel_name_from_rss(channel_id).lower()

    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    channel_info = {
        "channel_id": channel_id,
        "rss_url": rss_url,
        "channel_name": youtube.get_channel_name_from_rss(channel_id),
        "last_video_id": None  # Initialize last_video_id as None
    }
    message = youtube.append_channel_to_json_file(channel_info, alias)
    if "⚠️" in message:
        await update.message.reply_text(message)
        return
    # Save the updated channels to JSON file
    await update.message.reply_text(f"Added channel with alias {alias} successfully!")

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


async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help information"),
        BotCommand("about", "About this bot"),
        BotCommand("add_to_youtube", "Add a YouTube channel to track"),
        BotCommand("fetch_from_youtube", "Fetch latest videos from added channels"),
    ])

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Welcome! Please send a movie or series name.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Help: Send a movie or series name to search.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Try sending a movie or series name.")

if __name__ == "__main__":
    import asyncio
    import logging
    from telegram.ext import Application

    TOKEN = "7958605710:AAEPJxGN_lie6MZaStMO-njYxvCUucNeQ14"

    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("add_to_youtube", add_to_youtube))
    app.add_handler(CommandHandler("fetch_from_youtube", fetch_video))

    print("Bot started...")
    app.post_init = set_commands 
    app.run_polling()
