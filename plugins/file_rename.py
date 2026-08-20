import random
from helper.ffmpeg import fix_thumb, take_screen_shot, get_audio_streams, get_subtitle_streams, process_audio_tracks, generate_sample_video, get_duration
from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.utils import progress_for_pyrogram, convert, humanbytes, apply_rename_words, clean_filename, active_tasks, progress_manager
from helper.database import db
from PIL import Image
import asyncio
import os
import aiofiles.os as aos
import time
from helper.utils import add_prefix_suffix
from config import Config


audio_selection_data = {}


def get_audio_markup(user_id, audio_streams, subtitle_streams, selected_audio, selected_subs):
    buttons = []
    max_len = max(len(audio_streams), len(subtitle_streams))
    for i in range(max_len):
        row = []
        if i < len(audio_streams):
            s = audio_streams[i]
            idx = s["index"]
            lang = s["lang"]
            text = f"Audio {idx + 1}"
            if lang: text += f" ({lang})"
            if idx in selected_audio: text = f"✅ {text}"
            row.append(InlineKeyboardButton(text, callback_data=f"audio_toggle_{idx}"))
        else:
            row.append(InlineKeyboardButton("✘", callback_data="none"))
        if i < len(subtitle_streams):
            s = subtitle_streams[i]
            idx = s["index"]
            lang = s["lang"]
            text = f"Sub {idx + 1}"
            if lang: text += f" ({lang})"
            if idx in selected_subs: text = f"✅ {text}"
            row.append(InlineKeyboardButton(text, callback_data=f"sub_toggle_{idx}"))
        else:
            row.append(InlineKeyboardButton("✘", callback_data="none"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Keep All Audio & Subs", callback_data="audio_keep_all")])
    buttons.append([InlineKeyboardButton("Done", callback_data="audio_done")])
    return InlineKeyboardMarkup(buttons)


@Client.on_callback_query(filters.regex("^(audio_toggle_|sub_toggle_|audio_keep_all|audio_done)"))
async def audio_selection_callback(bot, query):
    if bot.name != "SnowRenamer":
        return
    user_id = query.from_user.id
    if user_id not in audio_selection_data:
        return await query.answer("Selection session expired.", show_alert=True)

    data = query.data
    user_data = audio_selection_data[user_id]

    if data.startswith("audio_toggle_"):
        idx = int(data.split("_")[-1])
        if idx in user_data["selected_audio"]:
            user_data["selected_audio"].remove(idx)
        else:
            user_data["selected_audio"].add(idx)

        await query.message.edit_reply_markup(
            reply_markup=get_audio_markup(user_id, user_data["streams"], user_data.get("subtitle_streams", []), user_data["selected_audio"], user_data["selected_subs"])
        )
        await query.answer()

    elif data.startswith("sub_toggle_"):
        idx = int(data.split("_")[-1])
        if idx in user_data["selected_subs"]:
            user_data["selected_subs"].remove(idx)
        else:
            user_data["selected_subs"].add(idx)

        await query.message.edit_reply_markup(
            reply_markup=get_audio_markup(user_id, user_data["streams"], user_data.get("subtitle_streams", []), user_data["selected_audio"], user_data["selected_subs"])
        )
        await query.answer()

    elif data == "audio_keep_all":
        user_data["selected_audio"] = set()
        user_data["selected_subs"] = set()
        user_data["event"].set()
        await query.answer("Keeping all audio and subtitle tracks.")

    elif data == "audio_done":
        user_data["event"].set()
        await query.answer("Selection finalized.")
    elif data == "none":
        await query.answer()


# Define a function to handle the 'rename' callback


@Client.on_callback_query(filters.regex('rename'))
async def rename(bot, update):
    if bot.name != "SnowRenamer":
        return

    await update.answer()
    user_id = update.from_user.id

    # Send ONLY one ForceReply (no duplicate caption edit)
    prompt_msg = await update.message.reply(
        "__ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ..__",
        reply_markup=ForceReply(selective=True)
    )

    try:
        response = await bot.listen(chat_id=update.message.chat.id, user_id=user_id, filters=filters.text, timeout=60)
        new_name = response.text
        await response.delete()
        # Also delete the "Select The Output File Type" message if it exists
        try:
            await update.message.delete()
        except:
            pass
    except Exception as e:
        print(f"Rename listen error: {e}")
        try: await update.message.edit(f"⚠️ Error: {e}")
        except: pass
        return
    finally:
        try:
            await prompt_msg.delete()
        except:
            pass

    file = update.message.reply_to_message
    media = getattr(file, file.media.value)

    if not "." in new_name:
        if "." in media.file_name:
            extn = media.file_name.rsplit('.', 1)[-1]
        else:
            extn = "mkv"
        new_name = new_name + "." + extn

    output_type = await db.get_output_type(user_id)
    # Check if we should override audio to audio if it's already audio
    if file.media == MessageMediaType.AUDIO:
        output_type = "audio"

    # Directly trigger upload logic
    await doc(bot, update, new_name, output_type)

# Define the function to handle the 'upload'


@Client.on_callback_query(filters.regex("upload"))
async def doc(bot, update, new_name_from_rename=None, output_type_from_rename=None):
    if bot.name != "SnowRenamer":
        return

    user_id = update.message.chat.id
    ms = update.message
    task_id = f"task_{ms.id}"

    path = None
    file_path = None
    metadata_path = None
    ph_path = None
    sample_path = None
    should_delete_ms = True

    try:
        # Creating Directory for Metadata
        if not await aos.path.isdir("Metadata"):
            try: await aos.mkdir("Metadata")
            except: pass
        if not await aos.path.isdir("downloads"):
            try: await aos.mkdir("downloads")
            except: pass

        # Extracting necessary information
        prefix = await db.get_prefix(user_id)
        suffix = await db.get_suffix(user_id)
        rename_words = await db.get_rename_words(user_id)
        _screenshot = await db.get_screenshot(user_id)
        _sample_video = await db.get_sample_video(user_id)
        has_post_processing = bool(_screenshot or _sample_video)

        if new_name_from_rename:
            new_filename_ = new_name_from_rename
        else:
            new_name = update.message.text or update.message.caption
            new_filename_ = new_name.split(":")[-1].replace("`", "").strip()

        try:
            new_filename_ = apply_rename_words(new_filename_, rename_words)
            new_filename = add_prefix_suffix(new_filename_, prefix, suffix)
        except Exception as e:
            should_delete_ms = False
            return await ms.edit(f"⚠️ Something went wrong: {e}")

        file_path = f"downloads/{new_filename}"
        file = update.message.reply_to_message

        active_tasks[user_id] = "active"
        await progress_manager.add_task(user_id, task_id, new_filename, has_post_processing=has_post_processing)
        await progress_manager.refresh_ui(bot, user_id, force=True)

        try:
            path = await bot.download_media(
                message=file,
                file_name=file_path,
                progress=progress_for_pyrogram,
                progress_args=("Download Started", ms, time.time(), user_id, new_filename)
            )
        except Exception as e:
            should_delete_ms = False
            if str(e) == "Task Cancelled":
                return
            await progress_manager.remove_task(user_id, task_id, bot)
            return await ms.edit(f"Download Error: {e}")

        if not path or not await aos.path.exists(path):
            should_delete_ms = False
            await progress_manager.remove_task(user_id, task_id, bot)
            return await ms.edit("❌ Download failed. File not found.")

        # Audio selection logic
        _audio_tool = await db.get_audio_tool(user_id)
        if _audio_tool:
            try:
                audio_streams = await get_audio_streams(path)
                subtitle_streams = await get_subtitle_streams(path)

                if len(audio_streams) > 1 or len(subtitle_streams) > 0:
                    audio_selection_data[user_id] = {
                        "streams": audio_streams,
                        "subtitle_streams": subtitle_streams,
                        "selected_audio": set(),
                        "selected_subs": set(),
                        "event": asyncio.Event()
                    }

                    await progress_manager.update_task(user_id, task_id, status="Fetching Metadata...")
                    await progress_manager.refresh_ui(bot, user_id)

                    sel_msg = await bot.send_message(
                        user_id,
                        "**Sᴇʟᴇᴄᴛ Aᴜᴅɪᴏ & Sᴜʙᴛɪᴛʟᴇ Tʀᴀᴄᴋꜱ Tᴏ Kᴇᴇᴩ**\n\nIf Done without selection, all tracks will be kept.",
                        reply_markup=get_audio_markup(user_id, audio_streams, subtitle_streams, set(), set())
                    )

                    try:
                        await asyncio.wait_for(audio_selection_data[user_id]["event"].wait(), timeout=300)
                    except:
                        pass

                    selected_audio = list(audio_selection_data[user_id]["selected_audio"])
                    selected_subs = list(audio_selection_data[user_id]["selected_subs"])
                    if selected_audio or selected_subs:
                        await process_audio_tracks(path, selected_audio, selected_subs)

                    try: await sel_msg.delete()
                    except: pass
            except Exception as e:
                print(f"Audio tool error: {e}")
            finally:
                audio_selection_data.pop(user_id, None)

        _bool_metadata = await db.get_metadata(user_id)
        if _bool_metadata:
            metadata_path = f"Metadata/{new_filename}"
            metadata = await db.get_metadata_code(user_id)
            if metadata:
                await progress_manager.update_task(user_id, task_id, status="Fetching Metadata...")
                await progress_manager.refresh_ui(bot, user_id)

                if await aos.path.exists(metadata_path):
                    await aos.remove(metadata_path)

                cmd = [
                    "ffmpeg", "-y", "-i", path, "-map", "0",
                    "-c:s", "copy", "-c:a", "copy", "-c:v", "copy",
                    "-metadata", f"title={metadata}",
                    "-metadata", f"author={metadata}",
                    "-metadata:s:s", f"title={metadata}",
                    "-metadata:s:a", f"title={metadata}",
                    "-metadata:s:v", f"title={metadata}",
                    metadata_path
                ]

                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    if process.returncode == 0:
                        await progress_manager.update_task(user_id, task_id, status="Metadata set ✅")
                    else:
                        _bool_metadata = False # Fallback to original path
                except:
                    _bool_metadata = False
                await progress_manager.refresh_ui(bot, user_id)

        duration = await get_duration(path)
        media = getattr(file, file.media.value)
        c_caption = await db.get_caption(user_id)
        c_thumb = await db.get_thumbnail(user_id)

        if c_caption:
            try:
                caption = c_caption.format(filename=new_filename, filesize=humanbytes(media.file_size), duration=convert(duration))
            except Exception as e:
                caption = f"**{new_filename}**\n\nCaption Error: {e}"
        else:
            caption = f"**{new_filename}**"

        width, height, ph_path = 0, 0, None
        if media.thumbs or c_thumb:
            try:
                if c_thumb:
                    ph_path = await bot.download_media(c_thumb)
                else:
                    ph_path = await take_screen_shot(path, "downloads", random.randint(0, max(0, duration - 1)))

                if ph_path:
                    width, height, ph_path = await fix_thumb(ph_path)
            except Exception as e:
                print(f"Thumbnail error: {e}")
                ph_path = None

        type = output_type_from_rename or update.data.split("_")[1]
        upload_path = metadata_path if (_bool_metadata and await aos.path.exists(metadata_path)) else path

        await progress_manager.update_task(user_id, task_id, status="uploading...", task_type="up", current=0)
        client_to_use = bot.premium_app if (media.file_size > 2000 * 1024 * 1024 and bot.premium_app and bot.premium_app.is_connected) else bot

        try:
            if type == "document":
                filw = await client_to_use.send_document(
                    Config.LOG_CHANNEL,
                    document=upload_path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started", ms, time.time(), user_id, new_filename))
            elif type == "video":
                filw = await client_to_use.send_video(
                    Config.LOG_CHANNEL,
                    video=upload_path,
                    caption=caption,
                    thumb=ph_path,
                    width=width,
                    height=height,
                    duration=duration,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started", ms, time.time(), user_id, new_filename))
            elif type == "audio":
                filw = await client_to_use.send_audio(
                    Config.LOG_CHANNEL,
                    audio=upload_path,
                    caption=caption,
                    thumb=ph_path,
                    duration=duration,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started", ms, time.time(), user_id, new_filename))

            await bot.copy_message(user_id, filw.chat.id, filw.id)
        except Exception as e:
            should_delete_ms = False
            if "CHAT_ADMIN_REQUIRED" in str(e) or "CHAT_WRITE_FORBIDDEN" in str(e):
                return await ms.edit("Sumthing when wrong please contact owner @Solofox_9\n\n⚠️ Please report wat happened fix soon as owner 🙏🏼")
            return await ms.edit(f"Upload Error: {e}")

        # Post-processing
        if _screenshot and duration > 0:
            await progress_manager.update_task(user_id, task_id, status="Generating Screenshots....")
            await progress_manager.refresh_ui(bot, user_id)
            for i in range(5):
                ss_path = await take_screen_shot(path, "downloads", random.randint(0, max(0, duration - 1)))
                if ss_path:
                    try:
                        filw = await bot.send_photo(Config.LOG_CHANNEL, photo=ss_path)
                        await bot.copy_message(user_id, filw.chat.id, filw.id)
                    except: pass
                    if await aos.path.exists(ss_path): await aos.remove(ss_path)

        if _sample_video and duration > 5:
            await progress_manager.update_task(user_id, task_id, status="Generating Sample Video....")
            await progress_manager.refresh_ui(bot, user_id)
            sample_path = f"downloads/sample_{new_filename}.mkv"
            if await generate_sample_video(upload_path, sample_path, duration):
                try:
                    filw = await bot.send_video(Config.LOG_CHANNEL, video=sample_path, caption="<code>sample video</code>")
                    await bot.copy_message(user_id, filw.chat.id, filw.id)
                except: pass

    except Exception as e:
        should_delete_ms = False
        print(f"General Error in doc: {e}")
        try: await ms.edit(f"Something went wrong: {e}")
        except: pass
    finally:
        await progress_manager.remove_task(user_id, task_id, bot)
        active_tasks.pop(user_id, None)
        active_tasks.pop(task_id, None)
        for p in [path, file_path, metadata_path, ph_path, sample_path]:
            if p and await aos.path.exists(p):
                try: await aos.remove(p)
                except: pass
        if should_delete_ms:
            try: await ms.delete()
            except: pass
