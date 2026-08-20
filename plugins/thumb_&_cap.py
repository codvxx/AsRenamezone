from pyrogram import Client, filters
from helper.database import db


@Client.on_message(filters.private & filters.command('set_caption'))
async def add_caption_handler(client, message):
    if client.name != "SnowRenamer":
        return
    if client.name != "SnowRenamer":
        return
    if len(message.command) == 1:
        return await message.reply_text("**__Gɪᴠᴇ Tʜᴇ Cᴀᴩᴛɪᴏɴ__\n\nExᴀᴍᴩʟᴇ: `/set_caption {filename}\n\n💾 Sɪᴢᴇ: {filesize}\n\n⏰ Dᴜʀᴀᴛɪᴏɴ: {duration}`**")
    caption = message.text.split(" ", 1)[1]
    await db.set_caption(message.from_user.id, caption=caption)
    await message.reply_text("__**✅ Cᴀᴩᴛɪᴏɴ Sᴀᴠᴇᴅ**__", reply_to_message_id=message.id)


@Client.on_message(filters.private & filters.command('del_caption'))
async def delete_caption_handler(client, message):
    if client.name != "SnowRenamer":
        return
    if client.name != "SnowRenamer":
        return
    caption = await db.get_caption(message.from_user.id)
    if not caption:
        return await message.reply_text("__**😔 Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Aɴy Cᴀᴩᴛɪᴏɴ**__")
    await db.set_caption(message.from_user.id, caption=None)
    await message.reply_text("__**❌️ Cᴀᴩᴛɪᴏɴ Dᴇʟᴇᴛᴇᴅ**__")


@Client.on_message(filters.private & filters.command(['see_caption', 'view_caption']))
async def see_caption_handler(client, message):
    if client.name != "SnowRenamer":
        return
    if client.name != "SnowRenamer":
        return
    caption = await db.get_caption(message.from_user.id)
    if caption:
        await message.reply_text(f"**Yᴏᴜ'ʀᴇ Cᴀᴩᴛɪᴏɴ:**\n\n`{caption}`")
    else:
        await message.reply_text("__**😔 Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Aɴy Cᴀᴩᴛɪᴏɴ**__")


@Client.on_message(filters.private & filters.command(['view_thumb', 'viewthumb']))
async def viewthumb_handler(client, message):
    if client.name != "SnowRenamer":
        return
    if client.name != "SnowRenamer":
        return
    thumb = await db.get_thumbnail(message.from_user.id)
    if thumb:
        await client.send_photo(chat_id=message.chat.id, photo=thumb)
    else:
        await message.reply_text("😔 __**Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Aɴy Tʜᴜᴍʙɴᴀɪʟ**__")


@Client.on_message(filters.private & filters.command(['del_thumb', 'delthumb']))
async def removethumb_handler(client, message):
    if client.name != "SnowRenamer":
        return
    if client.name != "SnowRenamer":
        return
    await db.set_thumbnail(message.from_user.id, file_id=None)
    await message.reply_text("❌️ __**Tʜᴜᴍʙɴᴀɪʟ Dᴇʟᴇᴛᴇᴅ**__")


@Client.on_message(filters.private & filters.photo)
async def addthumbs_handler(client, message):
    if client.name != "SnowRenamer":
        return
    if client.name != "SnowRenamer":
        return
    SnowDev = await message.reply_text("Please Wait ...", reply_to_message_id=message.id)
    await db.set_thumbnail(message.from_user.id, file_id=message.photo.file_id)
    await SnowDev.edit("✅️ __**Tʜᴜᴍʙɴᴀɪʟ Sᴀᴠᴇᴅ**__")
