import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when audio cannot be extracted from a video URL or path."""
    pass


def _find_ffmpeg_dir() -> Optional[str]:
    """Locate the directory containing ffmpeg/ffprobe binaries."""
    # 1. Explicit env var — can be a directory OR the ffmpeg.exe path itself
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path:
        if os.path.isfile(env_path):
            return os.path.dirname(env_path)
        if os.path.isdir(env_path):
            return env_path

    # 2. Already on PATH
    ffmpeg_on_path = shutil.which("ffmpeg")
    if ffmpeg_on_path:
        return os.path.dirname(ffmpeg_on_path)

    # 3. Common winget install location
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    winget_base = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(winget_base):
        for pkg_dir in os.listdir(winget_base):
            if "FFmpeg" in pkg_dir or "ffmpeg" in pkg_dir:
                for root, dirs, files in os.walk(os.path.join(winget_base, pkg_dir)):
                    lower_files = [f.lower() for f in files]
                    if "ffmpeg.exe" in lower_files and "ffprobe.exe" in lower_files:
                        return root

    # 4. Chocolatey / Scoop / common manual install locations
    candidate_dirs = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "ffmpeg", "bin"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "ffmpeg", "bin"),
        os.path.join(os.environ.get("USERPROFILE", ""), "scoop", "shims"),
        r"C:\ffmpeg\bin",
        r"C:\tools\ffmpeg\bin",
    ]
    for d in candidate_dirs:
        if d and os.path.isdir(d):
            lower_files = [f.lower() for f in os.listdir(d)]
            if "ffmpeg.exe" in lower_files:
                return d

    return None


def _find_cookie_file() -> Optional[str]:
    """Locate optional cookies.txt file or load cookies from environment variable for yt-dlp authentication."""
    # 1. Direct path in environment variable
    env_cookie = os.environ.get("COOKIES_FILE") or os.environ.get("YOUTUBE_COOKIES_PATH")
    if env_cookie and os.path.isfile(env_cookie):
        return env_cookie

    # 2. Raw cookie content passed via environment variable (ideal for Railway / cloud containers)
    env_content = os.environ.get("YOUTUBE_COOKIES") or os.environ.get("COOKIES_CONTENT")
    if env_content and len(env_content.strip()) > 20:
        try:
            import base64
            clean_content = env_content.strip()
            # Handle potential base64 encoding
            if not ("\n" in clean_content or "\t" in clean_content):
                try:
                    decoded = base64.b64decode(clean_content).decode("utf-8")
                    if "youtube.com" in decoded or "# Netscape" in decoded:
                        clean_content = decoded
                except Exception:
                    pass
            temp_cookie_path = os.path.join(tempfile.gettempdir(), "railway_yt_cookies.txt")
            with open(temp_cookie_path, "w", encoding="utf-8") as f:
                f.write(clean_content)
            logger.info(f"Loaded cookies from YOUTUBE_COOKIES environment variable into {temp_cookie_path}")
            return temp_cookie_path
        except Exception as e:
            logger.warning(f"Failed to write YOUTUBE_COOKIES env var to file: {e}")

    # 3. Candidate files in working directory or repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate_paths = [
        os.path.join(os.getcwd(), "cookies.txt"),
        os.path.join(repo_root, "cookies.txt"),
        os.path.join(repo_root, "youtube_cookies.txt"),
        os.path.join(repo_root, "backend", "cookies.txt"),
    ]
    for p in candidate_paths:
        if os.path.isfile(p):
            return p
    return None


@dataclass
class ExtractionResult:
    audio_path: str
    video_path: Optional[str] = None
    title: Optional[str] = None
    duration_seconds: Optional[float] = None
    is_temporary: bool = False


def _is_local_media(path_or_url: str) -> bool:
    """Treat existing local paths or test mock paths as direct audio/video inputs."""
    if os.path.isfile(path_or_url):
        return True
    path_lower = path_or_url.lower()
    if not (path_lower.startswith("http://") or path_lower.startswith("https://") or path_lower.startswith("www.")):
        return True
    return False


def _build_ydl_opts(
    output_template: str,
    ffmpeg_dir: Optional[str],
    cookie_file: Optional[str],
    player_clients: Optional[list] = None,
    keep_video: bool = True,
) -> dict:
    """Build yt-dlp options dictionary with optimal bypass parameters."""
    opts = {
        "format": "best[height<=480][ext=mp4]/bestvideo[height<=480]+bestaudio/best[height<=480]/bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 60,
        "retries": 10,
        "fragment_retries": 10,
        "source_address": "0.0.0.0",  # Force IPv4 (datacenter IPv6 blocks are widespread)
        "keepvideo": keep_video,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "noplaylist": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Sec-Fetch-Mode": "navigate",
        },
        "sleep_interval": 1,
        "max_sleep_interval": 3,
        "age_limit": None,
    }

    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir

    if cookie_file:
        opts["cookiefile"] = cookie_file
        logger.info(f"Using cookies file: {cookie_file}")

    node_bin = shutil.which("node")
    if node_bin:
        opts["js_runtimes"] = {"node": {}}

    if player_clients:
        opts["extractor_args"] = {
            "youtube": {
                "player_client": player_clients,
            }
        }

    return opts


def extract_audio(url_or_path: str, output_dir: str = None) -> ExtractionResult:
    """
    Extract audio from a video URL via yt-dlp, or pass through a local media file.
    Applies multi-strategy fallback to bypass YouTube sign-in requirements and rate limits.
    """
    if _is_local_media(url_or_path):
        logger.info(f"Using local media file: {url_or_path}")
        ext = os.path.splitext(url_or_path)[1].lower() if "." in url_or_path else ""
        is_video = ext in (".mp4", ".mov", ".mkv", ".webm", ".avi")
        return ExtractionResult(
            audio_path=url_or_path,
            video_path=url_or_path if (is_video and os.path.isfile(url_or_path)) else None,
            is_temporary=False,
        )

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="video_factcheck_")

    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    try:
        import yt_dlp
    except ImportError as e:
        raise ExtractionError("yt-dlp is not installed. Run: pip install yt-dlp") from e

    ffmpeg_dir = _find_ffmpeg_dir()
    if ffmpeg_dir:
        current_path = os.environ.get("PATH", "")
        if ffmpeg_dir not in current_path:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
            logger.info(f"Prepended {ffmpeg_dir} to PATH for this process")
    else:
        logger.warning(
            "ffmpeg not found — yt-dlp postprocessing will likely fail. "
            "Install ffmpeg or set the FFMPEG_PATH environment variable."
        )

    cookie_file = _find_cookie_file()

    # Define fallback strategies for YouTube client negotiation
    strategies = [
        # Strategy 1: Modern mobile/web client stack (bypasses most PO token and sign-in gates)
        ["android", "ios", "mweb", "web"],
        # Strategy 2: TV & mobile fallback
        ["tv", "mweb", "android"],
        # Strategy 3: Standard yt-dlp default client negotiation
        None,
    ]

    last_exception = None
    for idx, clients in enumerate(strategies, start=1):
        try:
            ydl_opts = _build_ydl_opts(
                output_template=output_template,
                ffmpeg_dir=ffmpeg_dir,
                cookie_file=cookie_file,
                player_clients=clients,
            )
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_or_path, download=True)
                audio_path = ydl.prepare_filename(info)
                base, _ = os.path.splitext(audio_path)
                mp3_path = base + ".mp3"
                if os.path.exists(mp3_path):
                    audio_path = mp3_path
                elif not os.path.exists(audio_path):
                    raise ExtractionError("yt-dlp finished but no audio file was found.")

                video_path = None
                for vext in (".mp4", ".webm", ".mkv", ".mov"):
                    cand = base + vext
                    if os.path.isfile(cand):
                        video_path = cand
                        break

                # Additional check across output directory for video file matching video id
                if not video_path and os.path.isdir(output_dir):
                    v_id = info.get("id") or ""
                    for f in os.listdir(output_dir):
                        if (v_id and v_id in f) and any(f.lower().endswith(ext) for ext in (".mp4", ".webm", ".mkv", ".mov", ".avi")):
                            video_path = os.path.join(output_dir, f)
                            break

                duration = info.get("duration")
                title = info.get("title")
                logger.info(f"Successfully extracted media using strategy #{idx} to audio={audio_path}, video={video_path}")
                return ExtractionResult(
                    audio_path=audio_path,
                    video_path=video_path,
                    title=title,
                    duration_seconds=float(duration) if duration else None,
                    is_temporary=True,
                )
        except Exception as e:
            last_exception = e
            logger.warning(f"Extraction strategy #{idx} failed: {e}. Trying fallback...")
            continue

    # If all extraction strategies failed, parse and present a clean error
    import re as _re
    raw = _re.sub(r'\x1b\[[0-9;]*m', '', str(last_exception))
    err_msg = raw.lower()

    if "private" in err_msg or "unauthorized" in err_msg:
        msg = "This video is private. Please ensure the video is public."
    elif "sign in to confirm your age" in err_msg or "confirm your age" in err_msg or "age-gated" in err_msg:
        msg = (
            "This video is age-restricted and requires YouTube sign-in. "
            "To analyze it, place a exported 'cookies.txt' in the project directory or upload the audio/video file directly."
        )
    elif "geo-restricted" in err_msg or "not available in your country" in err_msg:
        msg = "This video is geo-blocked/geo-restricted and cannot be downloaded from this location."
    elif "deleted" in err_msg or "not exist" in err_msg or "removed" in err_msg or "404" in err_msg:
        msg = "This video does not exist or has been deleted/removed."
    elif "403" in err_msg or "forbidden" in err_msg or "unable to download video data" in err_msg:
        msg = (
            "YouTube blocked the download (HTTP 403 Forbidden). "
            "This usually happens when YouTube flags automated requests. "
            "Try another public YouTube Shorts video, or place a 'cookies.txt' file in the project directory."
        )
    elif "sign in" in err_msg or "login" in err_msg:
        msg = (
            "YouTube requires sign-in to access this video (bot check or restriction). "
            "Try another public YouTube Shorts video, or place a 'cookies.txt' file in the project folder to enable authenticated access."
        )
    else:
        msg = f"Failed to extract audio from URL: {raw}"

    raise ExtractionError(msg) from last_exception

