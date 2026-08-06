import asyncio
import os
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def my_handler(update, context):
    print("Handler started")
    time.sleep(5)
    print("Handler finished")

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, my_handler))
    await app.initialize()
    
    update = Update.de_json({"update_id": 1, "message": {"message_id": 1, "date": 1, "chat": {"id": int(os.getenv("TELEGRAM_CHAT_ID")), "type": "private"}, "text": "1 test"}}, app.bot)
    
    print("Before process_update")
    t0 = time.time()
    await app.process_update(update)
    print(f"After process_update, took {time.time()-t0:.2f}s")
    
    print("Sleeping 0.1s")
    await asyncio.sleep(0.1)
    print("Exiting main")

asyncio.run(main())
