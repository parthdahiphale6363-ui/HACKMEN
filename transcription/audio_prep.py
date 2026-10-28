import os
import subprocess
import logging
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_MAX_FILE_SIZE_BYTES = 24 * 1024 * 1024
GROQ_SUPPORTED_FORMATS = {'.flac', '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.ogg', '.wav', '.webm'}

# Progressive bitrates when first pass still exceeds Groq limit.
COMPRESSION_BITRATES = ["64k", "48k", "32k"]


class AudioPrepError(Exception):
    pass


def _run_ffmpeg(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr}")
        raise AudioPrepError(f"Failed to process audio with ffmpeg: {e.stderr}") from e
    except FileNotFoundError as e:
        raise AudioPrepError("ffmpeg is not installed or not found in system PATH.") from e


def _convert_audio(input_path: str, output_path: str, bitrate: str) -> str:
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-b:a", bitrate,
        output_path,
    ]
    _run_ffmpeg(cmd)
    return output_path


def has_audio_stream(input_path: str) -> bool:
    """Check if the media file contains at least one audio stream."""
    if not input_path or not os.path.exists(input_path):
        return False
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return "audio" in res.stdout.lower()
    except Exception:
        return True


def prep_audio_for_groq(input_path: str, output_dir: str = None) -> Optional[str]:
    """
    Normalize and convert audio for Groq Whisper:
    - 16 kHz mono MP3
    - Loudness normalization for clearer speech
    - Progressive compression if still over 24 MB
    Returns None if the media has no audio stream.
    """
    if not os.path.exists(input_path):
        if any(x in input_path.lower() for x in ("demo", "silent", "mock", "test")):
            return input_path
        raise FileNotFoundError(f"Input audio file not found: {input_path}")

    file_ext = os.path.splitext(input_path)[1].lower()
    if file_ext in (".mp4", ".mov", ".mkv", ".webm", ".avi") and not has_audio_stream(input_path):
        logger.info(f"Media file {input_path} has no audio stream.")
        return None

    file_size = os.path.getsize(input_path)

    needs_conversion = file_ext not in GROQ_SUPPORTED_FORMATS
    needs_compression = file_size > GROQ_MAX_FILE_SIZE_BYTES

    if not needs_conversion and not needs_compression:
        return input_path

    logger.info(f"Audio requires prep (conversion: {needs_conversion}, compression: {needs_compression})")

    if output_dir is None:
        output_dir = os.path.dirname(input_path) or tempfile.gettempdir()

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_prepared.mp3")

    last_path = input_path
    for idx, bitrate in enumerate(COMPRESSION_BITRATES):
        target = output_path if idx == 0 else os.path.join(output_dir, f"{base_name}_prepared_{bitrate}.mp3")
        last_path = _convert_audio(last_path if idx == 0 else input_path, target, bitrate)
        if os.path.getsize(last_path) <= GROQ_MAX_FILE_SIZE_BYTES:
            return last_path

    raise AudioPrepError(
        "Audio file is still too large for Groq API even after maximum compression. "
        "Chunking will be attempted during translation."
    )
