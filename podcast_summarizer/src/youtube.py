# -*- coding: utf-8 -*-
import subprocess, pathlib, re, time
from typing import Optional

def safe_filename(s: str) -> str:
    s = re.sub(r"[^\w\-. ]", "_", (s or "episode")).strip()
    return (s[:120] or "episode").strip("_")

def youtube_to_mp3(url: str, out_dir: str = "/outputs", title_hint: Optional[str] = None) -> str:
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    base = safe_filename(title_hint or f"yt_{int(time.time())}")
    out = str(pathlib.Path(out_dir) / (base + ".%(ext)s"))
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "--restrict-filenames",
        "--no-playlist",
        "-o", out,
        url,
    ]
    subprocess.check_call(cmd)
    return str(pathlib.Path(out_dir) / (base + ".mp3"))
