import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from helper.database import db
from config import Config
from pyromod.exceptions import ListenerTimeout

async def get_settings_text(user_id):
    metadata = await db.get_metadata_code(user_id)
    thumbnail = await db.get_thumbnail(user_id)
    caption = await db.get_caption(user_id)
    prefix = await db.get_prefix(user_id)
    suffix = await db.get_suffix(user_id)
    sample_video = await db.get_sample_video(user_id)
    screenshot = await db.get_screenshot(user_id)
    audio_tool = await db.get_audio_tool(user_id)
    rename_words = await db.get_rename_words(user_id)
    output_type = await db.get_output_type(user_id)

    metadata_val = f"`{metadata}`" if metadata else "Not Exists"
    thumbnail_val = "Exists" if thumbnail else "Not Exists"
    caption_val = f"`{caption[:40]}...`" if caption and len(caption) > 40 else (f"`{caption}`" if caption else "Not Exists")
    prefix_val = f"`{prefix}`" if prefix else "Not Exists"
    suffix_val = f"`{suffix}`" if suffix else "Not Exists"
    rename_words_val = f"`{rename_words}`" if rename_words else "Not Exists"

    text = (
        "<b><u> ⚙️ User Settings </u></b>\n\n"
        f"<b>🧲 Metadata</b>   : {metadata_val}\n"
        f"<b>🖼️ Thumbnail</b>  : {thumbnail_val}\n"
        f"<b>🧢 Caption</b>    : {caption_val}\n"
        f"<b>🪅 Prefix</b>     : {prefix_val}\n"
        f"<b>🦅 Suffix</b>     : {suffix_val}\n"
        f"<b>📜 Remove Words</b> : {rename_words_val}\n"
        f"<b>🎬 Sample Video</b> : {'✅' if sample_video else ''}\n"
        f"<b>📸 Screenshot</b> : {'✅' if screenshot else ''}\n"
        f"<b>🎧 Audio Tool</b> : {'✅' if audio_tool else ''}\n"
        f"<b>📤 Output Type</b> : {output_type}\n\n"
        "<b>📜 Select a below buttons to edit.</b>"
    )
    return text

async def get_settings_buttons(user_id):
    sample_video = await db.get_sample_video(user_id)
    screenshot = await db.get_screenshot(user_id)
    audio_tool = await db.get_audio_tool(user_id)
    output_type = await db.get_output_type(user_id)

    buttons = [
        [InlineKeyboardButton(f"Oᴜᴛᴩᴜᴛ file type {output_type.capitalize()}", callback_data=f"settings_toggle_output_{user_id}")],
        [InlineKeyboardButton("Metadata", callback_data=f"settings_metadata_main_{user_id}"),
         InlineKeyboardButton("Caption", callback_data=f"settings_caption_{user_id}")],
        [InlineKeyboardButton("Thumbnail", callback_data=f"settings_thumb_main_{user_id}"),
         InlineKeyboardButton(f"Sample Video{' ✅' if sample_video else ''}", callback_data=f"settings_sample_video_{user_id}")],
        [InlineKeyboardButton(f"Screenshot{' ✅' if screenshot else ''}", callback_data=f"settings_screenshot_{user_id}"),
         InlineKeyboardButton(f"Audio Tool{' ✅' if audio_tool else ''}", callback_data=f"settings_audio_tool_{user_id}")],
        [InlineKeyboardButton("Prefix", callback_data=f"settings_prefix_{user_id}"),
         InlineKeyboardButton("Suffix", callback_data=f"settings_suffix_{user_id}")],
        [InlineKeyboardButton("📜 Remove words 📜", callback_data=f"settings_remw_main_{user_id}")],
        [InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")]
    ]
    return InlineKeyboardMarkup(buttons)

@Client.on_message(filters.private & filters.command("settings"))
async def settings_cmd(client, message):
    if client.name != "SnowRenamer":
        return
    user_id = message.from_user.id
    await message.reply_text(text=await get_settings_text(user_id), reply_markup=await get_settings_buttons(user_id))

@Client.on_callback_query(filters.regex("^settings_"))
async def settings_callback(client: Client, query: CallbackQuery):
    if client.name != "SnowRenamer":
        return
    await query.answer()
    data = query.data
    user_id = int(data.split("_")[-1])
    if query.from_user.id != user_id: return

    if data.startswith("settings_main_"):
        await query.message.edit_text(text=await get_settings_text(user_id), reply_markup=await get_settings_buttons(user_id))
    elif data.startswith("settings_toggle_metadata_"):
        _bool_metadata = await db.get_metadata(user_id)
        await db.set_metadata(user_id, not _bool_metadata)
        await metadata_settings_menu(client, query, user_id)
    elif data.startswith("settings_metadata_main_"): await metadata_settings_menu(client, query, user_id)
    elif data.startswith("settings_setmeta_"): await set_metadata_flow(client, query, user_id)
    elif data.startswith("settings_delmeta_"):
        await db.set_metadata_code(user_id, None)
        await metadata_settings_menu(client, query, user_id)
    elif data.startswith("settings_stopmeta_"):
        client.stop_listening(chat_id=query.message.chat.id, user_id=user_id)
    elif data.startswith("settings_thumb_main_"): await thumbnail_settings_menu(client, query, user_id)
    elif data.startswith("settings_setthumb_"): await set_thumbnail_flow(client, query, user_id)
    elif data.startswith("settings_delthumb_"):
        await db.set_thumbnail(user_id, None)
        await thumbnail_settings_menu(client, query, user_id)
    elif data.startswith("settings_stopthumb_"):
        client.stop_listening(chat_id=query.message.chat.id, user_id=user_id)
    elif data.startswith("settings_viewthumb_"):
        thumb = await db.get_thumbnail(user_id)
        if thumb: await query.message.reply_photo(photo=thumb, caption="**Yᴏᴜʀ Cᴜsᴛᴏᴍ Tʜᴜᴍʙɴᴀɪɪʟ**")
        else: await query.answer("No thumbnail found!", show_alert=True)
    elif data.startswith("settings_caption_"): await caption_settings_menu(client, query, user_id)
    elif data.startswith("settings_setcap_"): await set_caption_flow(client, query, user_id)
    elif data.startswith("settings_delcap_"):
        await db.set_caption(user_id, None)
        await caption_settings_menu(client, query, user_id)
    elif data.startswith("settings_stopcap_"):
        client.stop_listening(chat_id=query.message.chat.id, user_id=user_id)
    elif data.startswith("settings_prefix_"): await prefix_settings_menu(client, query, user_id)
    elif data.startswith("settings_setprefix_"): await set_prefix_flow(client, query, user_id)
    elif data.startswith("settings_delprefix_"):
        await db.set_prefix(user_id, None)
        await prefix_settings_menu(client, query, user_id)
    elif data.startswith("settings_stopprefix_"):
        client.stop_listening(chat_id=query.message.chat.id, user_id=user_id)
    elif data.startswith("settings_suffix_"): await suffix_settings_menu(client, query, user_id)
    elif data.startswith("settings_setsuffix_"): await set_suffix_flow(client, query, user_id)
    elif data.startswith("settings_delsuffix_"):
        await db.set_suffix(user_id, None)
        await suffix_settings_menu(client, query, user_id)
    elif data.startswith("settings_stopsuffix_"):
        client.stop_listening(chat_id=query.message.chat.id, user_id=user_id)
    elif data.startswith("settings_sample_video_"):
        await db.set_sample_video(user_id, not await db.get_sample_video(user_id))
        await query.message.edit_reply_markup(reply_markup=await get_settings_buttons(user_id))
    elif data.startswith("settings_screenshot_"):
        await db.set_screenshot(user_id, not await db.get_screenshot(user_id))
        await query.message.edit_reply_markup(reply_markup=await get_settings_buttons(user_id))
    elif data.startswith("settings_audio_tool_"):
        await db.set_audio_tool(user_id, not await db.get_audio_tool(user_id))
        await query.message.edit_reply_markup(reply_markup=await get_settings_buttons(user_id))
    elif data.startswith("settings_toggle_output_"):
        current_type = await db.get_output_type(user_id)
        new_type = "video" if current_type == "document" else "document"
        await db.set_output_type(user_id, new_type)
        await query.message.edit_text(text=await get_settings_text(user_id), reply_markup=await get_settings_buttons(user_id))
    elif data.startswith("settings_remw_main_"): await rename_settings_menu(client, query, user_id)
    elif data.startswith("settings_setremw_"): await set_rename_flow(client, query, user_id)
    elif data.startswith("settings_delremw_"):
        await db.set_rename_words(user_id, None)
        await rename_settings_menu(client, query, user_id)
    elif data.startswith("settings_stopremw_"):
        client.stop_listening(chat_id=query.message.chat.id, user_id=user_id)
    elif data.startswith("settings_close_"):
        try: await query.message.delete()
        except: pass

# --- HELPER FUNCTIONS ---

async def metadata_settings_menu(client, query, user_id):
    metadata = await db.get_metadata_code(user_id)
    _bool_metadata = await db.get_metadata(user_id)
    text = f"㊂ <b><u> Metadata Settings : </u></b>\n\n <b>➲ Rename Filename Metadata : </b> `{metadata}`" if metadata else "㊂ <b><u> Metadata Settings : </u></b>\n\n<b>➲ Rename Filename Metadata : </b> Not Exists"
    text += f"\n\n<b>➲ Metadata Status : </b> {'Enabled ✅' if _bool_metadata else 'Disabled ❌'}"
    text += "\n\n <b>➲ Description : </b> Your channel name that should be used while editing metadata of the file"
    buttons = [
        [InlineKeyboardButton(f"Metadata Status : {'✅' if _bool_metadata else '❌'}", callback_data=f"settings_toggle_metadata_{user_id}")],
        [InlineKeyboardButton("Change Metadata" if metadata else "Set Metadata", callback_data=f"settings_setmeta_{user_id}")]
    ]
    if metadata: buttons[1].append(InlineKeyboardButton("↺ Delete", callback_data=f"settings_delmeta_{user_id}"))
    buttons.append([InlineKeyboardButton("↩ Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_metadata_flow(client, query, user_id):
    metadata_val = await db.get_metadata_code(user_id) or "Not Exists"
    text = f"㊂ <b><u> Metadata Settings : </u></b>\n\n<b>➲ Send File Metadata : </b> {metadata_val}\n\n<b>➲ Description : </b> Your channel name that should be used while editing metadata of the file\n\nSend File Metadata\n<b>➲ Timeout: </b> 60 sec"
    buttons = [[InlineKeyboardButton("Stop Change", callback_data=f"settings_stopmeta_{user_id}")]]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=user_id, filters=filters.text, timeout=60)
        if response:
            await db.set_metadata_code(user_id, response.text)
            try: await response.delete()
            except: pass
    except ListenerTimeout: pass
    await metadata_settings_menu(client, query, user_id)

async def thumbnail_settings_menu(client, query, user_id):
    thumb = await db.get_thumbnail(user_id)
    text = f"㊂ <b><u> Thumbnail Settings : </u></b> \n\n<b>➲ Custom Thumbnail : </b> {'Exists' if thumb else 'Not Exists'} \n\n<b>➲ Description : </b> Custom Thumbnail to appear on the Rename files uploaded by the bot"
    buttons = []
    if thumb: buttons.append([InlineKeyboardButton("View Thumbnail", callback_data=f"settings_viewthumb_{user_id}")])
    buttons.append([InlineKeyboardButton("Change Thumbnail" if thumb else "Set Thumbnail", callback_data=f"settings_setthumb_{user_id}")])
    if thumb: buttons[-1].append(InlineKeyboardButton("↺ Delete", callback_data=f"settings_delthumb_{user_id}"))
    buttons.append([InlineKeyboardButton("↩ Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_thumbnail_flow(client, query, user_id):
    text = "㊂ <b><u> Thumbnail Settings : </u></b>\n\n<b>➲ Description : </b> Custom Thumbnail to appear on the Rename files uploaded by the bot\n\nSend a photo to save it as custom thumbnail.\n\n<b>➲ Timeout : </b> 60 sec"
    buttons = [[InlineKeyboardButton("Stop Change", callback_data=f"settings_stopthumb_{user_id}")]]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=user_id, filters=filters.photo, timeout=60)
        if response:
            await db.set_thumbnail(user_id, response.photo.file_id)
            try: await response.delete()
            except: pass
    except ListenerTimeout: pass
    await thumbnail_settings_menu(client, query, user_id)

async def prefix_settings_menu(client, query, user_id):
    prefix = await db.get_prefix(user_id)
    text = f"㊂ <b><u> Prefix Settings : </u></b>\n\n<b>➲ Rename Filename Prefix : </b> {prefix if prefix else 'Not Exists'}\n\n<b>➲ Description : </b> Rename Filename Prefix is the Start Part attached with the Filename of the Rename Files"
    buttons = [[InlineKeyboardButton("Change Prefix" if prefix else "Set Prefix", callback_data=f"settings_setprefix_{user_id}")]]
    if prefix: buttons[0].append(InlineKeyboardButton("↺ Delete", callback_data=f"settings_delprefix_{user_id}"))
    buttons.append([InlineKeyboardButton("↩ Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_prefix_flow(client, query, user_id):
    text = "㊂ <b><u> Prefix Settings : </u></b> \n\n<b>➲ Description : </b> Rename File Prefix is the Front Part attacted with the Filename of the Rename Files.\n\n<b>➲ Example : </b> [ @Team_TD_Links ]\n\n<b>➲ Timeout : </b> 60 sec"
    buttons = [[InlineKeyboardButton("Stop Change", callback_data=f"settings_stopprefix_{user_id}")]]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=user_id, filters=filters.text, timeout=60)
        if response:
            await db.set_prefix(user_id, response.text)
            try: await response.delete()
            except: pass
    except ListenerTimeout: pass
    await prefix_settings_menu(client, query, user_id)

async def suffix_settings_menu(client, query, user_id):
    suffix = await db.get_suffix(user_id)
    text = f"㊂ <b><u> Suffix Settings : </u></b>\n\n<b>➲ Rename Filename Suffix : </b>{suffix if suffix else 'Not Exists'}\n\n<b>➲ Description : </b> Rename Filename Suffix is the End Part attached with the Filename of the Rename Files"
    buttons = [[InlineKeyboardButton("Change Suffix" if suffix else "Set Suffix", callback_data=f"settings_setsuffix_{user_id}")]]
    if suffix: buttons[0].append(InlineKeyboardButton("↺ Delete", callback_data=f"settings_delsuffix_{user_id}"))
    buttons.append([InlineKeyboardButton("↩ Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_suffix_flow(client, query, user_id):
    text = "㊂ <b><u> Suffix Settings : </u></b>\n\n<b>➲ Description : </b> Rename File Suffix is the End Part attached with the Filename of the Rename Files\n\n<b>➲ Example: </b> [ @Team_TD_Links ].mkv\n\nSend Rename Filename Suffix.\n\n<b>➲ Timeout: </b> 60 sec"
    buttons = [[InlineKeyboardButton("Stop Change", callback_data=f"settings_stopsuffix_{user_id}")]]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=user_id, filters=filters.text, timeout=60)
        if response:
            await db.set_suffix(user_id, response.text)
            try: await response.delete()
            except: pass
    except ListenerTimeout: pass
    await suffix_settings_menu(client, query, user_id)

async def caption_settings_menu(client, query, user_id):
    caption = await db.get_caption(user_id)
    text = f"㊂ <b><u> Caption Settings : </u></b>\n\n<b>➲ Custom Caption : </b> {caption if caption else 'Not Exists'}\n\n<b>➲ Description : </b> Custom Caption to appear on the Rename files uploaded by the bot"
    buttons = [[InlineKeyboardButton("Change Caption" if caption else "Set Caption", callback_data=f"settings_setcap_{user_id}")]]
    if caption: buttons[0].append(InlineKeyboardButton("↺ Delete", callback_data=f"settings_delcap_{user_id}"))
    buttons.append([InlineKeyboardButton("↩ Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_caption_flow(client, query, user_id):
    text = "㊂ <b><u> Caption Settings : </u></b>\n\n<b>➲ Description : </b> Rename Caption is the Custom Caption on the Rename Files Uploaded by the bot\n\n<b>➲ Example : </b> Caption You can add HTML tags (Or) Your channel name.\n\n<b>➲ Timeout : </b> 60 sec"
    buttons = [[InlineKeyboardButton("Stop Change", callback_data=f"settings_stopcap_{user_id}")]]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=user_id, filters=filters.text, timeout=60)
        if response:
            await db.set_caption(user_id, response.text)
            try: await response.delete()
            except: pass
    except ListenerTimeout: pass
    await caption_settings_menu(client, query, user_id)

async def rename_settings_menu(client, query, user_id):
    rename_words = await db.get_rename_words(user_id)
    if not rename_words:
        text = (
            "<b><u>㊂ Remove Words Settings :</u></b>\n\n"
            "<b>➲ Filename Remove Words :</b> Not Exists\n\n"
            "<b>➲ Description :</b> Remove Words is combination of extra word used for removing or manipulating Filename of the Rename Files"
        )
        buttons = [
            [InlineKeyboardButton("Set Remove Words", callback_data=f"settings_setremw_{user_id}")],
            [InlineKeyboardButton("↩ Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")]
        ]
    else:
        text = (
            "㊂<b><u> Remove Words Settings :</b></u>\n\n"
            f"<b>➲  Filename Remove Words : </b> {rename_words}\n\n"
            "<b>➲ Description : </b> Remove Words is combination of extra word used for removing or manipulating Filename of the Rename Files"
        )
        buttons = [
            [InlineKeyboardButton("Change Remove Words", callback_data=f"settings_setremw_{user_id}"), InlineKeyboardButton("↺ Delete", callback_data=f"settings_delremw_{user_id}")],
            [InlineKeyboardButton("Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("Close", callback_data=f"settings_close_{user_id}")]
        ]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_rename_flow(client, query, user_id):
    rename_words = await db.get_rename_words(user_id)
    text = (
        "<b><u>㊂ Remove Words Settings :</u></b>\n\n"
        f"<b>➲ Filename Remove Words :</b> {rename_words if rename_words else 'Not Exists'}\n\n"
        "<b>➲ Description :</b> Remove Words is combination of extra word used for removing or manipulating Filename of the Rename Files\n\n"
        "<b>➲ Timeout :</b> 60 sec"
    )
    buttons = [
        [InlineKeyboardButton("Stop Changes", callback_data=f"settings_stopremw_{user_id}")]
    ]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=user_id, filters=filters.text, timeout=60)
        if response:
            await db.set_rename_words(user_id, response.text)
            try: await response.delete()
            except: pass
    except ListenerTimeout: pass
    await rename_settings_menu(client, query, user_id)
