# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, Tuple
import os, pathlib, time

from .captions import get_youtube_captions, extract_video_id
from .youtube import youtube_to_mp3
from .transcribe_gemini import transcribe_as_segments
from .summarize import summarize_podcast_windows

def get_segments(
    url: Optional[str] = None,
    audio_path: Optional[str] = None,
    lang: str = "es",
    google_api_key: Optional[str] = None,
    out_dir: str = "/outputs",
    gemini_model: str = "gemini-1.5-flash",
    window_minutes: int = 20,
    prefer_captions: bool = True
) -> Dict[str, Any]:
    """
    Devuelve dict unificado {text, segments, source, lang, kind, meta}
    """
    if not url and not audio_path:
        raise ValueError("Debes proporcionar url de YouTube o audio_path (.mp3).")

    # 1) Captions (gratis)
    if url and prefer_captions:
        caps = get_youtube_captions(url, (lang, "en"))
        if caps and caps.get("segments"):
            return caps

    # 2) Fallback Gemini ASR
    if not audio_path:
        audio_path = youtube_to_mp3(url, out_dir=out_dir)
    if not google_api_key:
        raise ValueError("Falta GOOGLE_API_KEY para transcribir con Gemini.")

    asr = transcribe_as_segments(
        mp3_path=audio_path,
        api_key=google_api_key,
        lang=lang,
        model=gemini_model,
        window_minutes=window_minutes
    )
    return asr

def run_pipeline(
    url: Optional[str] = None,
    audio_path: Optional[str] = None,
    lang: str = "es",
    google_api_key: Optional[str] = None,
    out_dir: str = "/outputs",
    gemini_model: str = "gemini-1.5-flash",
    gemma_model: str = "gemma-3-12b-it",
    window_minutes: int = 20,
    per_window_max_chars: int = 6000,
    per_minute_token_budget: int = 12000,
    model_fallbacks: Tuple[str, ...] = ("gemma-3-4b-it",),
    prompts_dir: Optional[str] = None,
    do_summary: bool = True,
) -> Dict[str, Any]:
    """
    Orquesta todo. Si do_summary=True, genera .txt en out_dir y devuelve paths.
    """
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)

    segments_result = get_segments(
        url=url,
        audio_path=audio_path,
        lang=lang,
        google_api_key=google_api_key,
        out_dir=out_dir,
        gemini_model=gemini_model,
        window_minutes=window_minutes,
        prefer_captions=True
    )

    out: Dict[str, Any] = {"segments_result": segments_result}

    if not do_summary:
        return out

    # Resumen
    final_text, per_window, overall = summarize_podcast_windows(
        result=segments_result,
        key_google=google_api_key,
        lang=lang,
        model=gemma_model,
        window_minutes=window_minutes,
        per_window_max_chars=per_window_max_chars,
        per_minute_token_budget=per_minute_token_budget,
        model_fallbacks=model_fallbacks,
        prompts_dir=prompts_dir
    )
    # Guardar .txt
    base_name = None
    if audio_path:
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
    elif url:
        try:
            vid = extract_video_id(url)
            base_name = f"yt_{vid}"
        except Exception:
            base_name = f"yt_{int(time.time())}"
    else:
        base_name = f"summary_{int(time.time())}"

    txt_path = os.path.join(out_dir, f"{base_name}_summary.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(final_text)

    out.update({
        "final_text": final_text,
        "per_window": per_window,
        "overall": overall,
        "summary_path": txt_path
    })
    return out
