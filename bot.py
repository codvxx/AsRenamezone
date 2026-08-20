#========================================================================
# Don't Remove Credit Tg - @TDBotDev
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@TDBotDev
# Ask Doubt on telegram https://t.me/TDBotDev
#========================================================================

import asyncio

# Initialize event loop at the absolute top (Line 1-3)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import logging
import logging.config
import warnings
import sys
from pytz import timezone
from datetime import datetime
from aiohttp import web

# Safely import pyromod and pyrogram AFTER loop initialization
import pyromod
from pyrogram import Client, idle, __version__
from pyrogram.raw.all import layer
from config import Config

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="SnowRenamer",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=300,
            plugins={"root": "plugins"},
            sleep_threshold=15,
        )
        self.premium_app = None

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        self.force_channel = Config.FORCE_SUB

        if Config.FORCE_SUB:
            try:
                self.invitelink = await self.export_chat_invite_link(Config.FORCE_SUB)
            except Exception as e:
                logging.warning(f"Force sub error: {e}")
                self.force_channel = None

        if Config.STRING_SESSION:
            self.premium_app = Client(
                name="PremiumApp",
                api_id=Config.STRING_API_ID,
                api_hash=Config.STRING_API_HASH,
                session_string=Config.STRING_SESSION,
                no_updates=True
            )
            await self.premium_app.start()

        from plugins.web_support import web_server
        runner = web.AppRunner(await web_server())
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", Config.PORT).start()

        logging.info(f"{me.first_name} ✅✅ BOT started successfully ✅✅")

        for admin_id in Config.ADMIN:
            try:
                await self.send_message(admin_id, f"**__{me.first_name} Iꜱ Sᴛᴀʀᴛᴇᴅ.....✨️__**")
            except:
                pass

        if Config.LOG_CHANNEL:
            try:
                curr = datetime.now(timezone("Asia/Kolkata"))
                date = curr.strftime('%d %B, %Y')
                time_str = curr.strftime('%I:%M:%S %p')
                await self.send_message(Config.LOG_CHANNEL, f"**__{me.mention} Iꜱ Rᴇsᴛᴀʀᴛᴇᴅ !!**\n\n📅 Dᴀᴛᴇ : `{date}`\n⏰ Tɪᴍᴇ : `{time_str}`\n🌐 Tɪᴍᴇᴢᴏɴᴇ : `Asia/Kolkata`\n🤖 Vᴇʀsɪᴏɴ : `v{__version__} (Layer {layer})`</b>")
            except:
                logging.error("Pʟᴇᴀꜱᴇ Mᴀᴋᴇ Tʜɪꜱ Iꜱ Aᴅᴍɪɴ Iɴ Yᴏᴜʀ Lᴏɢ Cʜᴀɴɴᴇʟ")

    async def stop(self, *args):
        if self.premium_app:
            await self.premium_app.stop()
        await super().stop()
        logging.info("Bot Stopped 🙄")

async def main():
    bot = Bot()
    await bot.start()
    await idle()
    await bot.stop()

if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="There is no current event loop")
    try:
        # Use existing loop for asyncio.run() context if needed, but asyncio.run creates its own.
        # However, to maintain the initialized loop:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

#========================================================================
# Don't Remove Credit Tg - @TDBotDev
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@TDBotDev
# Ask Doubt on telegram https://t.me/TDBotDev
#========================================================================
