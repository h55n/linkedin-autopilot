import asyncio
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

async def handler(update, context):
    print('HANDLER STARTED')
    await asyncio.sleep(2)
    print('HANDLER DONE')

async def main():
    app = Application.builder().token('1234:abcd').build()
    app.add_handler(MessageHandler(filters.ALL, handler))
    
    await app.initialize()
    await app.start() # Start the application to consume queue
    
    u = Update.de_json({'update_id': 1, 'message': {'message_id': 1, 'date': 1, 'chat': {'id': 1, 'type': 'private'}, 'text': 'test'}}, app.bot)
    
    print('CALLING PROCESS')
    await app.process_update(u)
    print('PROCESS RETURNED')
    
    # Wait until all tasks are done?
    # the tasks spawned by ConcurrentUpdateProcessor are not exposed easily.
    # Let's see if we can just wait 3 seconds for this test.
    await asyncio.sleep(3)
    
    await app.stop()
    await app.shutdown()
    print('DONE')

if __name__ == "__main__":
    asyncio.run(main())
