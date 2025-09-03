# -*- coding: utf-8 -*-
from typing import List, Tuple, Dict, Any, Optional
import re, json, pathlib

try:
    # Nueva API
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
    HAS_LIST = hasattr(YouTubeTranscriptApi, "list_transcripts")
except Exception:
    YouTubeTranscriptApi = None  # type: ignore
    HAS_LIST = False
    NoTranscriptFound = Exception  # type: ignore
    TranscriptsDisabled = Exception  # type: ignore

_YT_ID_RE = re.compile(r"(?:v=|/shorts/|/embed/|youtu\.be/)([A-Za-z0-9_-]{11})")

def extract_video_id(url_or_id: str) -> str:
    s = url_or_id.strip()
    if len(s) == 11 and re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
        return s
    m = _YT_ID_RE.search(s) or re.search(r"[?&]v=([A-Za-z0-9_-]{11})", s)
    if not m:
        raise ValueError("No se pudo extraer el video_id desde la URL.")
    return m.group(1)

def _normalize_segments(captions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    n = len(captions)
    for i, c in enumerate(captions):
        start = float(c.get("start", 0.0))
        dur = c.get("duration", 0.0)
        if not dur or float(dur) <= 0.0:
            next_start = float(captions[i+1]["start"]) if i < n-1 else start + 2.0
            dur = max(0.01, next_start - start)
        end = start + float(dur)
        text = str(c.get("text", "")).replace("\n", " ").strip()
        out.append({"id": i, "start": start, "end": end, "text": text})
    return out

def get_youtube_captions(url_or_id: str, lang_priority: Tuple[str, ...] = ("es", "en")) -> Optional[Dict[str, Any]]:
    """
    Devuelve dict unificado o None si no hay captions.
    Prioriza: manual lang_priority -> auto lang_priority -> cualquier manual -> cualquier auto.
    """
    if YouTubeTranscriptApi is None:
        return None
    vid = extract_video_id(url_or_id)
    try:
        if HAS_LIST:
            tr_list = YouTubeTranscriptApi.list_transcripts(vid)

            segs = lang = kind = None
            # manual prioritarios
            for lg in lang_priority:
                try:
                    t = tr_list.find_transcript([lg])
                    segs = t.fetch(); lang = t.language_code; kind = "manual"; break
                except Exception: pass
            # auto prioritarios
            if segs is None:
                for lg in lang_priority:
                    try:
                        t = tr_list.find_generated_transcript([lg])
                        segs = t.fetch(); lang = t.language_code; kind = "auto"; break
                    except Exception: pass
            # cualquier manual
            if segs is None:
                for t in tr_list:
                    if not getattr(t, "is_generated", False):
                        segs = t.fetch(); lang = t.language_code; kind = "manual"; break
            # cualquier auto
            if segs is None:
                for t in tr_list:
                    if getattr(t, "is_generated", False):
                        segs = t.fetch(); lang = t.language_code; kind = "auto"; break

            if segs is None:
                return None
        else:
            # API antigua: intenta get_transcript por prioridad
            segs = None; lang = None; kind = "unknown"
            for lg in lang_priority:
                try:
                    segs = YouTubeTranscriptApi.get_transcript(vid, languages=[lg])
                    lang = lg; break
                except Exception:
                    continue
            if segs is None:
                return None

        segments = _normalize_segments(segs)
        text_all = " ".join(s["text"] for s in segments).strip()
        return {
            "text": text_all,
            "segments": segments,
            "source": "captions",
            "lang": lang or lang_priority[0],
            "kind": kind or "manual",
            "meta": {"video_id": vid}
        }
    except (NoTranscriptFound, TranscriptsDisabled):
        return None
    except Exception:
        return None
