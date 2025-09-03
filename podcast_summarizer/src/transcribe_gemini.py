# -*- coding: utf-8 -*-
from typing import Dict, Any, List, Tuple
from google import genai
from google.genai.errors import ClientError
import subprocess, os, time, tempfile

TRANSCRIBE_PROMPT = {
    "es": "Transcribe verbatim the following audio in Spanish. Return only the transcript text.",
    "en": "Transcribe verbatim the following audio in English. Return only the transcript text.",
}

def _run(cmd): subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def _ffprobe_duration(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",path],
        text=True
    ).strip()
    return float(out)

def split_audio(input_path: str, segment_minutes: int = 20) -> List[Tuple[str, float, float]]:
    dur = _ffprobe_duration(input_path)
    seg = int(segment_minutes*60)
    if dur <= seg:
        return [(input_path, 0.0, dur)]
    tmpdir = tempfile.mkdtemp(prefix="chunks_")
    parts=[]; start=0.0; i=0
    while start < dur - 1:
        end = min(start+seg, dur)
        outp = os.path.join(tmpdir, f"chunk_{i:03d}.mp3")
        _run(["ffmpeg","-y","-ss",str(start),"-to",str(end),"-i",input_path,"-vn","-acodec","libmp3lame",outp])
        parts.append((outp,start,end))
        start = end; i += 1
    return parts

def gemini_transcribe_file(file_path: str, api_key: str, lang: str = "es", model: str = "gemini-1.5-flash") -> str:
    client = genai.Client(api_key=api_key)
    file_obj = client.files.upload(file=file_path)
    prompt = TRANSCRIBE_PROMPT["es" if str(lang).lower().startswith("es") else "en"]
    resp = client.models.generate_content(
        model=model,
        contents=[
            {"role":"user","parts":[{"text":prompt}]},
            {"role":"user","parts":[{"file_data":{"file_uri":file_obj.uri,"mime_type":file_obj.mime_type}}]}
        ]
    )
    return (resp.text or "").strip()

def transcribe_as_segments(mp3_path: str, api_key: str, lang: str = "es", model: str = "gemini-1.5-flash", window_minutes: int = 20) -> Dict[str, Any]:
    chunks = split_audio(mp3_path, segment_minutes=window_minutes)
    segs=[]; texts=[]
    for i,(p,st,en) in enumerate(chunks):
        txt = gemini_transcribe_file(p, api_key=api_key, lang=lang, model=model)
        txt = (txt or "").replace("\r"," ").strip()
        segs.append({"id":i,"start":st,"end":en,"text":txt}); texts.append(txt)
    return {
        "text":"\n".join(texts).strip(),
        "segments":segs,
        "source":"gemini",
        "lang":lang,
        "kind":"asr",
        "meta":{"model": model}
    }
