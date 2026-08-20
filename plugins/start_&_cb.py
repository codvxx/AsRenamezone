from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from helper.database import db
from config import Config, Txt
from helper.utils import parse_limit, active_tasks, progress_manager
import humanize
import math
import asyncio


@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    if client.name != "SnowRenamer":
        return

    if message.from_user.id in Config.BANNED_USERS:
        await message.reply_text("Sorry, You are banned.")
        return

    user = message.from_user
    await db.add_user(client, message)
    button = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            '⛅ ᴜᴘᴅᴀᴛᴇs', url='https://t.me/TDBotDev')
    ], [
        InlineKeyboardButton('❄️ ᴀʙᴏᴜᴛ', callback_data='about'),
        InlineKeyboardButton('❗ ʜᴇʟᴘ', callback_data='help')
    ]])
    if Config.START_PIC:
        await message.reply_photo(Config.START_PIC, caption=Txt.START_TXT.format(user.mention), reply_markup=button)
    else:
        await message.reply_text(text=Txt.START_TXT.format(user.mention), reply_markup=button, disable_web_page_preview=True)


@Client.on_message(filters.private & (filters.document | filters.audio | filters.video))
async def rename_start(client, message):
    if client.name != "SnowRenamer":
        return
    user_id = message.from_user.id

    file = getattr(message, message.media.value)
    filename = file.file_name
    filesize = humanize.naturalsize(file.file_size)

    limit = parse_limit(Config.RENAME_LIMIT)
    if file.file_size > limit:
        return await message.reply_text(f"❌ File size exceeds allowed limit ({Config.RENAME_LIMIT})")

    try:
        text = f"""**__ᴡʜᴀᴛ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴍᴇ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ғɪʟᴇ.?__**\n\n**ғɪʟᴇ ɴᴀᴍᴇ** : `{filename}`\n\n**ғɪʟᴇ sɪᴢᴇ** : `{filesize}`"""
        buttons = [[InlineKeyboardButton("📝 sᴛᴀʀᴛ ʀᴇɴᴀᴍᴇ 📝", callback_data="rename")],
                   [InlineKeyboardButton("✖️ ᴄᴀɴᴄᴇʟ ✖️", callback_data="close")]]
        await message.reply_text(text=text, reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup(buttons))
    except FloodWait as e:
        await asyncio.sleep(e.value)
        text = f"""**__What do you want me to do with this file.?__**\n\n**File Name** : `{filename}`\n\n**File Size** : `{filesize}`"""
        buttons = [[InlineKeyboardButton("📝 sᴛᴀʀᴛ ʀᴇɴᴀᴍᴇ 📝", callback_data="rename")],
                   [InlineKeyboardButton("✖️ ᴄᴀɴᴄᴇʟ ✖️", callback_data="close")]]
        await message.reply_text(text=text, reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup(buttons))
    except:
        pass


from helper.utils import parse_limit, active_tasks, progress_manager, task_to_user

@Client.on_message(filters.private & filters.regex("^/cancel_"))
async def cancel_handler(client, message):
    if client.name != "SnowRenamer":
        return
    try:
        # /cancel_task_{message_id}
        task_id = message.text.replace("/cancel_", "")
        user_id = task_to_user.get(task_id)

        if user_id:
            # Global cancel flag first to stop processing ASAP
            active_tasks[task_id] = "cancel"
            active_tasks[user_id] = "cancel"

            # Update UI state
            await progress_manager.remove_task(user_id, task_id, client)

            await message.reply_text("<b>Your task is successfully cancelled 😸</b>")
        else:
            # Fallback for /cancel_{user_id}
            data = message.text.split("_")
            if len(data) > 1:
                user_id = int(data[1])
                active_tasks[user_id] = "cancel"
                await message.reply_text("<b>Your task is successfully cancelled 😸</b>")
    except Exception as e:
        print(f"Cancel error: {e}")

@Client.on_message(filters.private & filters.command("progress"))
async def progress_cmd(client, message):
    if client.name != "SnowRenamer":
        return
    user_id = message.from_user.id
    await progress_manager.refresh_ui(client, user_id, force=True, recreate=True)

@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    if client.name != "SnowRenamer":
        return
    data = query.data
    user_id = query.from_user.id

    if data.startswith("refresh_"):
        uid = int(data.split("_")[1])
        await progress_manager.refresh_ui(client, uid, force=True)
        await query.answer("Refreshed ♻️")
        return

    elif data.startswith("page_"):
        uid = int(data.split("_")[1])
        async with progress_manager.lock:
            if uid in progress_manager.user_tasks:
                total_tasks = len(progress_manager.user_tasks[uid])
                total_pages = math.ceil(total_tasks / 4)
                current_page = progress_manager.user_pages.get(uid, 1)
                new_page = current_page + 1
                if new_page > total_pages:
                    new_page = 1
                progress_manager.user_pages[uid] = new_page

        await progress_manager.refresh_ui(client, uid, force=True)
        await query.answer(f"Page {progress_manager.user_pages.get(uid, 1)}")
        return

    elif data == "progress":
        await progress_manager.refresh_ui(client, user_id, force=True, recreate=True)
        await query.answer("Progress Updated 🚀")
        return


    if data == "start":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    '⛅ Uᴩᴅᴀᴛᴇꜱ', url='https://t.me/TDBotDev')
            ], [
                InlineKeyboardButton('❄️ ᴀʙᴏᴜᴛ', callback_data='about'),
                InlineKeyboardButton('❗ ʜᴇʟᴘ', callback_data='help')
            ]])
        )
    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✘ ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("⟪ ʙᴀᴄᴋ", callback_data="start")
            ]])
        )
    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT.format(client.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✘ ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("⟪ ʙᴀᴄᴋ", callback_data="start")
            ]])
        )

    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
        except:
            try: await query.message.delete()
            except: pass

    query.continue_propagation()
