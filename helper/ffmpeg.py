#========================================================================
# Don't Remove Credit Tg - @TDBotDev
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@TDBotDev
# Ask Doubt on telegram https://t.me/TDBotDev
#========================================================================

import time
import os
import asyncio
import aiofiles.os as aos
import json
from PIL import Image
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

async def fix_thumb(thumb):
    width = 0
    height = 0
    try:
        if thumb != None:
            parser = createParser(thumb)
            metadata = extractMetadata(parser)
            if metadata.has("width"):
                width = metadata.get("width")
            if metadata.has("height"):
                height = metadata.get("height")
                
            # Open the image file
            with Image.open(thumb) as img:
                # Convert the image to RGB format and save it back to the same file
                img.convert("RGB").save(thumb)
            
                # Resize the image
                resized_img = img.resize((width, height))
                
                # Save the resized image in JPEG format
                resized_img.save(thumb, "JPEG")
            parser.close()
    except Exception as e:
        print(e)
        thumb = None 
       
    return width, height, thumb
    
async def take_screen_shot(video_file, output_directory, ttl):
    out_put_file_name = f"{output_directory}/{time.time()}.jpg"
    if await aos.path.exists(out_put_file_name):
        await aos.remove(out_put_file_name)
    file_genertor_command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(ttl),
        "-i",
        video_file,
        "-vframes",
        "1",
        out_put_file_name
    ]
    process = await asyncio.create_subprocess_exec(
        *file_genertor_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    if await aos.path.exists(out_put_file_name):
        return out_put_file_name
    return None

async def get_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    try:
        return int(float(stdout.decode().strip()))
    except:
        return 0

async def generate_sample_video(input_path, output_path, duration, start_time=None):
    if start_time is None:
        start_time = max(0, (duration // 2) - 15)

    if await aos.path.exists(output_path):
        await aos.remove(output_path)

    command = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-i", input_path,
        "-t", "30",
        "-map", "0:v:0?",
        "-map", "0:a?",
        "-map", "0:s?",
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,setdar=16/9",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-ignore_unknown",
        "-f", "matroska",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and await aos.path.exists(output_path):
        return True
    else:
        if await aos.path.exists(output_path):
            await aos.remove(output_path)
        print(f"FFmpeg sample error: {stderr.decode()}")
        return False
#==========================≠==================≠======≠==========
async def get_audio_streams(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index:tags=language",
        "-of", "json", file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return []

    try:
        data = json.loads(stdout)
        streams = []
        for i, stream in enumerate(data.get("streams", [])):
            index = i # This is for -map 0:a:i
            lang = stream.get("tags", {}).get("language")
            streams.append({"index": index, "lang": lang})
        return streams
    except Exception as e:
        print(f"Error parsing ffprobe output: {e}")
        return []

async def get_subtitle_streams(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "s",
        "-show_entries", "stream=index:tags=language",
        "-of", "json", file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return []

    try:
        data = json.loads(stdout)
        streams = []
        for i, stream in enumerate(data.get("streams", [])):
            index = i # This is for -map 0:s:i
            lang = stream.get("tags", {}).get("language")
            streams.append({"index": index, "lang": lang})
        return streams
    except Exception as e:
        print(f"Error parsing ffprobe output: {e}")
        return []

async def process_audio_tracks(input_path, selected_audio, selected_subs):
    output_path = f"{input_path}.tmp.mkv"

    # Map video
    cmd = ["ffmpeg", "-y", "-i", input_path, "-map", "0:v?"]

    # Map selected audio streams
    if selected_audio:
        for idx in selected_audio:
            cmd.extend(["-map", f"0:a:{idx}"])
    else:
        cmd.extend(["-map", "0:a?"])

    # Map selected subtitle streams
    if selected_subs:
        for idx in selected_subs:
            cmd.extend(["-map", f"0:s:{idx}"])
    else:
        cmd.extend(["-map", "0:s?"])

    cmd.extend(["-c", "copy", output_path])

    if await aos.path.exists(output_path):
        await aos.remove(output_path)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        await aos.rename(output_path, input_path)
        return True
    else:
        if await aos.path.exists(output_path):
            await aos.remove(output_path)
        print(f"FFmpeg error: {stderr.decode()}")
        return False

#========================================================================
# Don't Remove Credit Tg - @TDBotDev
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@TDBotDev
# Ask Doubt on telegram https://t.me/TDBotDev
#========================================================================
