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

    # Clean formatting for values
    metadata_val = f"`{metadata}`" if metadata else "❌ Not Set"
    thumbnail_val = "✅ Saved" if thumbnail else "❌ Not Set"
    caption_val = f"`{caption[:40]}...`" if caption and len(caption) > 40 else (f"`{caption}`" if caption else "❌ Not Set")
    prefix_val = f"`{prefix}`" if prefix else "❌ Not Set"
    suffix_val = f"`{suffix}`" if suffix else "❌ Not Set"
    rename_words_val = f"`{rename_words}`" if rename_words else "❌ Not Set"

    text = (
        "⚙️ **U S E R  S E T T I N G S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧲 **Metadata:** {metadata_val}\n"
        f"🖼️ **Thumbnail:** {thumbnail_val}\n"
        f"🧢 **Caption:** {caption_val}\n"
        f"🪅 **Prefix:** {prefix_val}\n"
        f"🦅 **Suffix:** {suffix_val}\n"
        f"📜 **Remove Words:** {rename_words_val}\n\n"
        "**⚡ Toggle Features:**\n"
        f"┣ 🎬 **Sample Video:** {'✅ ON' if sample_video else '❌ OFF'}\n"
        f"┣ 📸 **Screenshot:** {'✅ ON' if screenshot else '❌ OFF'}\n"
        f"┣ 🎧 **Audio Tool:** {'✅ ON' if audio_tool else '❌ OFF'}\n"
        f"┗ 📤 **Output Type:** `{output_type.upper()}`\n\n"
        "👇 *Select a button below to configure:*"
    )
    return text

async def get_settings_buttons(user_id):
    sample_video = await db.get_sample_video(user_id)
    screenshot = await db.get_screenshot(user_id)
    audio_tool = await db.get_audio_tool(user_id)
    output_type = await db.get_output_type(user_id)

    # Clean, symmetrical grid layout
    buttons = [
        [InlineKeyboardButton(f"📂 Output Type: {output_type.upper()}", callback_data=f"settings_toggle_output_{user_id}")],
        [InlineKeyboardButton("🧲 Metadata", callback_data=f"settings_metadata_main_{user_id}"),
         InlineKeyboardButton("🧢 Caption", callback_data=f"settings_caption_{user_id}")],
        [InlineKeyboardButton("🪅 Prefix", callback_data=f"settings_prefix_{user_id}"),
         InlineKeyboardButton("🦅 Suffix", callback_data=f"settings_suffix_{user_id}")],
        [InlineKeyboardButton("🖼️ Thumbnail", callback_data=f"settings_thumb_main_{user_id}"),
         InlineKeyboardButton("📜 Remove Words", callback_data=f"settings_remw_main_{user_id}")],
        [InlineKeyboardButton(f"🎬 Sample Video {'✅' if sample_video else '❌'}", callback_data=f"settings_sample_video_{user_id}"),
         InlineKeyboardButton(f"📸 Screenshot {'✅' if screenshot else '❌'}", callback_data=f"settings_screenshot_{user_id}")],
        [InlineKeyboardButton(f"🎧 Audio Tool {'✅' if audio_tool else '❌'}", callback_data=f"settings_audio_tool_{user_id}")],
        [InlineKeyboardButton("❌ Close Menu", callback_data=f"settings_close_{user_id}")]
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
        if thumb: await query.message.reply_photo(photo=thumb, caption="🖼️ **Your Custom Thumbnail**")
        else: await query.answer("❌ No thumbnail found!", show_alert=True)
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
    
    text = (
        "🧲 **M E T A D A T A  S E T T I N G S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Value:** `{metadata if metadata else '❌ Not Set'}`\n"
        f"**Status:** {'✅ Enabled' if _bool_metadata else '❌ Disabled'}\n\n"
        "💡 *Description:* This is usually your channel name. It will be injected into the metadata of the processed video file."
    )
    buttons = [
        [InlineKeyboardButton(f"Toggle Status: {'✅ ON' if _bool_metadata else '❌ OFF'}", callback_data=f"settings_toggle_metadata_{user_id}")],
        [InlineKeyboardButton("✏️ Edit Metadata" if metadata else "➕ Add Metadata", callback_data=f"settings_setmeta_{user_id}")]
    ]
    if metadata: buttons[1].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"settings_delmeta_{user_id}"))
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("❌ Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_metadata_flow(client, query, user_id):
    text = (
        "🧲 **S E T  M E T A D A T A**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the text you want to use for the metadata.\n"
        "💡 *Example:* `@AS_cinemaa`\n\n"
        "⏱️ *Timeout:* 60 seconds."
    )
    buttons = [[InlineKeyboardButton("🚫 Cancel", callback_data=f"settings_stopmeta_{user_id}")]]
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
    text = (
        "🖼️ **T H U M B N A I L  S E T T I N G S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Status:** {'✅ Custom Thumbnail Saved' if thumb else '❌ No Custom Thumbnail'}\n\n"
        "💡 *Description:* This image will be applied as the cover/thumbnail for your uploaded files."
    )
    buttons = []
    if thumb: buttons.append([InlineKeyboardButton("👁️ View Thumbnail", callback_data=f"settings_viewthumb_{user_id}")])
    buttons.append([InlineKeyboardButton("✏️ Change Thumbnail" if thumb else "➕ Add Thumbnail", callback_data=f"settings_setthumb_{user_id}")])
    if thumb: buttons[-1].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"settings_delthumb_{user_id}"))
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("❌ Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_thumbnail_flow(client, query, user_id):
    text = (
        "🖼️ **S E T  T H U M B N A I L**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Send an image (photo) to save it as your custom thumbnail.\n\n"
        "⏱️ *Timeout:* 60 seconds."
    )
    buttons = [[InlineKeyboardButton("🚫 Cancel", callback_data=f"settings_stopthumb_{user_id}")]]
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
    text = (
        "🪅 **P R E F I X  S E T T I N G S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Value:** `{prefix if prefix else '❌ Not Set'}`\n\n"
        "💡 *Description:* The prefix is text added to the very beginning of the renamed file."
    )
    buttons = [[InlineKeyboardButton("✏️ Change Prefix" if prefix else "➕ Add Prefix", callback_data=f"settings_setprefix_{user_id}")]]
    if prefix: buttons[0].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"settings_delprefix_{user_id}"))
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("❌ Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_prefix_flow(client, query, user_id):
    text = (
        "🪅 **S E T  P R E F I X**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the text you want to use as a prefix.\n"
        "💡 *Example:* `[ @AS_cinemaa ]`\n\n"
        "⏱️ *Timeout:* 60 seconds."
    )
    buttons = [[InlineKeyboardButton("🚫 Cancel", callback_data=f"settings_stopprefix_{user_id}")]]
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
    text = (
        "🦅 **S U F F I X  S E T T I N G S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Value:** `{suffix if suffix else '❌ Not Set'}`\n\n"
        "💡 *Description:* The suffix is text added to the very end of the renamed file (before the extension)."
    )
    buttons = [[InlineKeyboardButton("✏️ Change Suffix" if suffix else "➕ Add Suffix", callback_data=f"settings_setsuffix_{user_id}")]]
    if suffix: buttons[0].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"settings_delsuffix_{user_id}"))
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("❌ Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_suffix_flow(client, query, user_id):
    text = (
        "🦅 **S E T  S U F F I X**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the text you want to use as a suffix.\n"
        "💡 *Example:* `[ @AS_cinemaa ]`\n\n"
        "⏱️ *Timeout:* 60 seconds."
    )
    buttons = [[InlineKeyboardButton("🚫 Cancel", callback_data=f"settings_stopsuffix_{user_id}")]]
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
    text = (
        "🧢 **C A P T I O N  S E T T I N G S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Value:**\n`{caption if caption else '❌ Not Set'}`\n\n"
        "💡 *Description:* This is the custom caption that will be sent alongside your video/document."
    )
    buttons = [[InlineKeyboardButton("✏️ Change Caption" if caption else "➕ Add Caption", callback_data=f"settings_setcap_{user_id}")]]
    if caption: buttons[0].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"settings_delcap_{user_id}"))
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("❌ Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_caption_flow(client, query, user_id):
    text = (
        "🧢 **S E T  C A P T I O N**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Send your custom caption format.\n"
        "💡 *Hint:* You can use `{filename}`, `{filesize}`, and `{duration}` variables.\n\n"
        "⏱️ *Timeout:* 60 seconds."
    )
    buttons = [[InlineKeyboardButton("🚫 Cancel", callback_data=f"settings_stopcap_{user_id}")]]
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
    text = (
        "📜 **R E M O V E  W O R D S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Words to Remove:**\n`{rename_words if rename_words else '❌ Not Set'}`\n\n"
        "💡 *Description:* Specify any words or strings you want automatically deleted from the original filename."
    )
    buttons = [[InlineKeyboardButton("✏️ Edit Words" if rename_words else "➕ Set Words", callback_data=f"settings_setremw_{user_id}")]]
    if rename_words: buttons[0].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"settings_delremw_{user_id}"))
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"settings_main_{user_id}"), InlineKeyboardButton("❌ Close", callback_data=f"settings_close_{user_id}")])
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def set_rename_flow(client, query, user_id):
    text = (
        "📜 **S E T  R E M O V E  W O R D S**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the words you want stripped from filenames (separated by spaces or commas).\n\n"
        "⏱️ *Timeout:* 60 seconds."
    )
    buttons = [[InlineKeyboardButton("🚫 Cancel", callback_data=f"settings_stopremw_{user_id}")]]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=user_id, filters=filters.text, timeout=60)
        if response:
            await db.set_rename_words(user_id, response.text)
            try: await response.delete()
            except: pass
    except ListenerTimeout: pass
    await rename_settings_menu(client, query, user_id)
