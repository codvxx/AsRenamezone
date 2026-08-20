#========================================================================
# Don't Remove Credit Tg - @TDBotDev
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@TDBotDev
# Ask Doubt on telegram https://t.me/TDBotDev
#========================================================================
import math
import time
from datetime import datetime
from pytz import timezone
from config import Config, Txt
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import psutil
import os
import asyncio

active_tasks = {}
last_update_time = {}
task_to_user = {}

class ProgressManager:
    def __init__(self):
        self.user_tasks = {} # {user_id: {task_id: {data}}}
        self.user_messages = {} # {user_id: message_obj}
        self.user_pages = {} # {user_id: current_page}
        self.lock = asyncio.Lock()

    async def add_task(self, user_id, task_id, file_name, has_post_processing=False):
        async with self.lock:
            # Store task_id -> user_id mapping for cancel command
            task_to_user[task_id] = user_id

            # Bring UI to front by deleting old message
            if user_id in self.user_messages:
                try: await self.user_messages[user_id].delete()
                except: pass
                del self.user_messages[user_id]

            if user_id not in self.user_tasks:
                self.user_tasks[user_id] = {}

            self.user_tasks[user_id][task_id] = {
                "file_name": file_name,
                "current": 0,
                "total": 0,
                "start_time": time.time(),
                "status": "Downloading...",
                "type": "dl", # dl or up
                "has_post_processing": has_post_processing
            }
            if user_id not in self.user_pages:
                self.user_pages[user_id] = 1

    async def update_task(self, user_id, task_id, current=None, total=None, status=None, task_type=None):
        async with self.lock:
            if user_id in self.user_tasks and task_id in self.user_tasks[user_id]:
                task = self.user_tasks[user_id][task_id]
                if current is not None: task["current"] = current
                if total is not None: task["total"] = total
                if status is not None: task["status"] = status
                if task_type is not None: task["type"] = task_type

    async def remove_task(self, user_id, task_id, bot=None):
        async with self.lock:
            if task_id in task_to_user:
                del task_to_user[task_id]
            if user_id in self.user_tasks and task_id in self.user_tasks[user_id]:
                del self.user_tasks[user_id][task_id]

        if bot:
            await self.refresh_ui(bot, user_id, force=True)

    def get_progress_bar(self, percentage, status, has_post_processing=False):
        # 20 dots bar:
        # If has_post_processing: 10 (DL) + 1 (Meta) + 1 (Post) + 8 (UL)
        # Else: 10 (DL) + 1 (Meta) + 9 (UL)

        if "Downloading" in status or "Download" in status:
            filled = math.floor(percentage / 10) # 1 dot per 10%
            bar = "⬢" * min(filled, 10) + "⬡" * (20 - min(filled, 10))
        elif "fetching" in status or "setted" in status or "Metadata" in status or "set" in status:
            bar = "⬢" * 11 + "⬡" * 9
        elif "Generating" in status:
            bar = "⬢" * 12 + "⬡" * 8
        elif "uploading" in status or "Upload" in status:
            if has_post_processing:
                filled = math.floor(percentage / 12.5) # 1 dot per 12.5% for 8 dots
                bar = "⬢" * (12 + min(filled, 8)) + "⬡" * (20 - (12 + min(filled, 8)))
            else:
                filled = math.floor(percentage / 11.11) # 1 dot per 11.11% for 9 dots
                bar = "⬢" * (11 + min(filled, 9)) + "⬡" * (20 - (11 + min(filled, 9)))
        else:
            filled_dots = math.floor(percentage / 5)
            bar = "⬢" * min(filled_dots, 20) + "⬡" * (20 - min(filled_dots, 20))
        return bar

    async def refresh_ui(self, bot, user_id, force=False, recreate=False):
        async with self.lock:
            msg_id = f"ui_{user_id}"
            now = time.time()
            if not force and not recreate and (now - last_update_time.get(msg_id, 0)) < 1.0:
                return
            last_update_time[msg_id] = now

            user_tasks = self.user_tasks.get(user_id, {})
            if not user_tasks:
                full_msg = "<b>No active tasks.</b>"
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Refresh ♻️", callback_data=f"refresh_{user_id}")]])

                if user_id in self.user_messages and recreate:
                    try: await self.user_messages[user_id].delete()
                    except: pass
                    del self.user_messages[user_id]

                if user_id not in self.user_messages:
                    try:
                        msg = await bot.send_message(user_id, full_msg, reply_markup=reply_markup)
                        self.user_messages[user_id] = msg
                    except: pass
                else:
                    try: await self.user_messages[user_id].edit(full_msg, reply_markup=reply_markup)
                    except:
                        try:
                            msg = await bot.send_message(user_id, full_msg, reply_markup=reply_markup)
                            self.user_messages[user_id] = msg
                        except: pass
                return

            tasks = list(user_tasks.items())
            total_tasks = len(tasks)
            total_pages = math.ceil(total_tasks / 4)
            current_page = self.user_pages.get(user_id, 1)

            if current_page > total_pages:
                current_page = max(1, total_pages)
                self.user_pages[user_id] = current_page

            start_idx = (current_page - 1) * 4
            end_idx = start_idx + 4
            page_tasks = tasks[start_idx:end_idx]

            full_msg = ""
            for tid, tdata in page_tasks:
                percentage = (tdata["current"] * 100 / tdata["total"]) if tdata["total"] > 0 else 0
                speed = tdata["current"] / (time.time() - tdata["start_time"]) if (time.time() - tdata["start_time"]) > 0 else 0
                eta = (tdata["total"] - tdata["current"]) / speed if speed > 0 else 0

                bar = self.get_progress_bar(percentage, tdata["status"], tdata.get("has_post_processing", False))

                full_msg += Txt.PROGRESS_BAR.format(
                    tdata["file_name"],
                    bar,
                    round(percentage, 2),
                    humanbytes(tdata["total"]),
                    humanbytes(tdata["current"]),
                    round(percentage, 2),
                    humanbytes(speed) + "/s",
                    tdata["status"],
                    TimeFormatter(eta * 1000),
                    user_id,
                    tid
                ) + "\n\n"

            stats = get_bot_stats()
            dl_count = sum(1 for t in user_tasks.values() if t["type"] == "dl")
            up_count = sum(1 for t in user_tasks.values() if t["type"] == "up")

            full_msg += Txt.BOT_STATS.format(
                stats['cpu'], stats['disk_free'], stats['disk_usage'],
                stats['ram'], dl_count, up_count, stats['uptime']
            )

            reply_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Refresh ♻️", callback_data=f"refresh_{user_id}"),
                    InlineKeyboardButton(f"page {current_page}/{total_pages}", callback_data=f"page_{user_id}")
                ]
            ])

            if user_id in self.user_messages and recreate:
                try:
                    await self.user_messages[user_id].delete()
                except:
                    pass
                del self.user_messages[user_id]

            if user_id not in self.user_messages:
                try:
                    msg = await bot.send_message(user_id, full_msg, reply_markup=reply_markup)
                    self.user_messages[user_id] = msg
                except Exception as e:
                    print(f"Error sending UI: {e}")
            else:
                try:
                    await self.user_messages[user_id].edit(full_msg, reply_markup=reply_markup)
                except Exception as e:
                    # If message was deleted or can't be edited, resend
                    try:
                        msg = await bot.send_message(user_id, full_msg, reply_markup=reply_markup)
                        self.user_messages[user_id] = msg
                    except Exception as e2:
                        print(f"Error resending UI: {e2}")

progress_manager = ProgressManager()

async def progress_for_pyrogram(current, total, ud_type, message, start, user_id=None, current_file_name="File", total_files=1, processed_files_size=0, total_all_files_size=0):
    task_id = f"task_{message.id}"
    if active_tasks.get(task_id) == "cancel":
        await progress_manager.remove_task(user_id, task_id, message._client)
        raise Exception("Task Cancelled")

    # We use a global progress_manager
    # Ensure task is registered
    if user_id:
        if user_id not in progress_manager.user_tasks or task_id not in progress_manager.user_tasks[user_id]:
            await progress_manager.add_task(user_id, task_id, current_file_name)

        await progress_manager.update_task(
            user_id, task_id,
            current=current,
            total=total,
            task_type="dl" if "Download" in ud_type else "up",
            status="📥 Downloading..." if "Download" in ud_type else "📤 Uploading..."
        )
        if current == total:
            pass
        await progress_manager.refresh_ui(message._client, user_id)

def get_bot_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent
    disk_free = humanbytes(disk.free)
    uptime = TimeFormatter((time.time() - Config.BOT_UPTIME) * 1000)
    return {
        'cpu': cpu,
        'ram': ram,
        'disk_usage': disk_usage,
        'disk_free': disk_free,
        'uptime': uptime
    }

def humanbytes(size):
    if not size:
        return "0 B"
    power = 1024
    Dic_powerN = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    n = 0
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}"


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        (f"{days}d ") if days else ""
    ) + (
        (f"{hours}h ") if hours else ""
    ) + (
        (f"{minutes}m ") if minutes else ""
    ) + (
        (f"{seconds}s ") if seconds else ""
    )
    return tmp.strip() if tmp else "0s"


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)


async def send_log(b, u):
    if Config.LOG_CHANNEL is not None:
        curr = datetime.now(timezone("Asia/Kolkata"))
        date = curr.strftime("%d %B, %Y")
        time_str = curr.strftime("%I:%M:%S %p")
        await b.send_message(
            Config.LOG_CHANNEL,
            f"**--Nᴇᴡ Uꜱᴇʀ Sᴛᴀʀᴛᴇᴅ Tʜᴇ Bᴏᴛ--**\n\n"
            f"Uꜱᴇʀ: {u.mention}\nIᴅ: `{u.id}`\nUɴ: @{u.username}\n\n"
            f"Dᴀᴛᴇ: {date}\nTɪᴍᴇ: {time_str}\n\nBy: {b.mention}",
        )

def clean_filename(filename):
    cleaned = filename.replace(' .', '.').replace('. ', '.').replace('..', '.').replace('  ', ' ')
    return cleaned.strip('. ')

def apply_rename_words(filename, rename_words):
    if not rename_words:
        return filename

    words = [word.strip() for word in rename_words.split(',')]
    for word in words:
        if not word:
            continue
        filename = filename.replace(word, "")
        dotted_word = word.replace(" ", ".")
        filename = filename.replace(dotted_word, "")

    return clean_filename(filename)

def parse_limit(limit_str):
    if not limit_str:
        return 0

    limit_str = limit_str.upper().strip()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]B)$', limit_str)
    if not match:
        try:
            return int(limit_str)
        except ValueError:
            return 0

    value = float(match.group(1))
    unit = match.group(2)

    units = {
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4
    }

    return int(value * units[unit])


def add_prefix_suffix(input_string, prefix='', suffix=''):
    pattern = r'(?P<filename>.*?)(\.\w+)?$'
    match = re.search(pattern, input_string)
    if match:
        filename = match.group('filename')
        extension = match.group(2) or ''

        filename = clean_filename(filename)

        final_name = filename
        if prefix:
            final_name = f"{prefix} {final_name}"
        if suffix:
            final_name = f"{final_name} {suffix}"

        return f"{final_name}{extension}".replace("  ", " ").strip()
    else:
        return input_string

#========================================================================
# Don't Remove Credit Tg - @TDBotDev
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@TDBotDev
# Ask Doubt on telegram https://t.me/TDBotDev
#========================================================================
