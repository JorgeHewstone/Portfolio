# -*- coding: utf-8 -*-
from typing import Dict, Any, List, Tuple, Optional
from google import genai
from google.genai.errors import ClientError
import math, time, json, re, os, io

# ========= Prompts =========
# Usamos placeholders seguros: [[CONTEXT_BULLETS]] [[T_START]] [[T_END]] [[CHUNK_TEXT]] y [[WINDOWS_JSON]]
# Así no hay conflicto con llaves { } del JSON dentro de los prompts.

# Fallbacks internos por si faltan archivos en /prompts
_FALLBACK_WIN_ES = """Eres analista de tecnología y negocios. Resume el fragmento (200–260 palabras) y añade 3 bullets clave.
Usa el contexto previo solo como guía (no repitas). No inventes.

Contexto previo:
[[CONTEXT_BULLETS]]

Fragmento (tiempo [[T_START]]–[[T_END]]):
\"\"\"[[CHUNK_TEXT]]\"\"\"

Responde SOLO en JSON:
{
  "summary": "texto coherente en español",
  "bullets": ["punto 1", "punto 2", "punto 3"]
}
"""

_FALLBACK_WIN_EN = """You are a tech + business analyst. Summarize the fragment (200–260 words) and add 3 key bullets.
Use prior context only for coherence (do not repeat). No fabrication.

Prior context:
[[CONTEXT_BULLETS]]

Fragment (time [[T_START]]–[[T_END]]):
\"\"\"[[CHUNK_TEXT]]\"\"\"

Reply ONLY as JSON:
{
  "summary": "coherent English text",
  "bullets": ["point 1", "point 2", "point 3"]
}
"""

_FALLBACK_FINAL_ES = """Fusiona estos resúmenes por ventana y produce un OVERALL SUMMARIZE (240–320 palabras) útil para captar ideas, tecnologías, empresas/personas, cambios de paradigma, riesgos y oportunidades. No repitas literal ni inventes.

Resúmenes por ventana (JSON):
[[WINDOWS_JSON]]

Devuelve SOLO el texto del OVERALL SUMMARIZE, en español.
"""

_FALLBACK_FINAL_EN = """Merge these window summaries and produce an OVERALL SUMMARIZE (240–320 words) that captures ideas, technologies, companies/people, paradigm shifts, risks, and opportunities. No repetition or fabrication.

Window summaries (JSON):
[[WINDOWS_JSON]]

Return ONLY the OVERALL SUMMARIZE text in English.
"""

def _read_text(path: str) -> Optional[str]:
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def _load_prompts(prompts_dir: Optional[str], lang: str):
    lang_is_es = str(lang).lower().startswith("es")
    if prompts_dir and os.path.isdir(prompts_dir):
        win = _read_text(os.path.join(prompts_dir, "win_prompt_es.txt" if lang_is_es else "win_prompt_en.txt"))
        final = _read_text(os.path.join(prompts_dir, "final_prompt_es.txt" if lang_is_es else "final_prompt_en.txt"))
    else:
        win = final = None

    if not win:
        win = _FALLBACK_WIN_ES if lang_is_es else _FALLBACK_WIN_EN
    if not final:
        final = _FALLBACK_FINAL_ES if lang_is_es else _FALLBACK_FINAL_EN
    return win, final

def _fill(tpl: str, mapping: Dict[str,str]) -> str:
    # Reemplazo simple de [[PLACEHOLDER]] sin .format()
    for k, v in mapping.items():
        tpl = tpl.replace(f"[[{k}]]", v)
    return tpl

# ========= Utils =========
def _hhmmss(sec):
    sec = max(0, int(sec)); h = sec // 3600; m = (sec % 3600) // 60; s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def _windows_from_segments(segments, window_sec=20*60): 
    if not segments: return []
    total_end = max(float(seg.get("end", 0)) for seg in segments)
    n = max(1, math.ceil(total_end / window_sec))
    wins = []
    for k in range(n):
        ws = k * window_sec; we = min((k+1)*window_sec, total_end)
        txts = [seg.get("text","") for seg in segments if float(seg.get("start",0)) < we and float(seg.get("end",0)) > ws]
        txt = " ".join(t.strip() for t in txts if t and t.strip())
        if txt:
            wins.append({"index": k, "start": ws, "end": we, "text": txt})
    return wins

def _strip_code_fences(t: str) -> str:
    t = t.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?", "", t).strip()
        t = re.sub(r"```$", "", t).strip()
    return t

def _parse_json_text(t: str):
    t = _strip_code_fences(t)
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}\s*$", t, re.S)
        if m: return json.loads(m.group(0))
        raise

def _truncate(s: str, max_chars: int) -> str:
    if len(s) <= max_chars: return s
    cut = s.rfind(". ", 0, max_chars)
    if cut == -1: cut = s.rfind("\n", 0, max_chars)
    if cut == -1: cut = max_chars
    return s[:cut].strip()

# ========= Token budgeting / retry =========
class TokenBudget:
    def __init__(self, client, model, tokens_per_minute=14000):
        self.client = client
        self.model = model
        self.budget = tokens_per_minute
        self.window_start = time.time()
        self.used = 0

    def _reset_if_needed(self):
        if time.time() - self.window_start >= 60:
            self.window_start = time.time()
            self.used = 0

    def count(self, contents: str) -> int:
        try:
            r = self.client.models.count_tokens(model=self.model, contents=contents)
            return int(r.total_tokens)
        except Exception:
            return max(1, len(contents) // 4)

    def ensure(self, contents: str):
        self._reset_if_needed()
        need = self.count(contents)
        remaining = self.budget - self.used
        if need > self.budget:
            return False, need
        if need > remaining:
            sleep_s = 60 - (time.time() - self.window_start)
            if sleep_s > 0:
                time.sleep(sleep_s)
            self.window_start = time.time()
            self.used = 0
        self.used += need
        return True, need

def _gen_with_retry(client, model, contents, budget: TokenBudget, max_retries=3):
    ok, need = budget.ensure(contents)
    if not ok:
        raise ValueError(f"Prompt too large for per-minute budget (~{need} tokens). Truncate input.")
    delay_from_server = None
    for _ in range(max_retries):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except ClientError as e:
            msg = getattr(e, "message", "") or str(e)
            if "RESOURCE_EXHAUSTED" in msg or getattr(e, "code", None) == 429:
                retry_secs = 4
                try:
                    details = e.details or []
                    for d in details:
                        if isinstance(d, dict) and d.get("@type","").endswith("RetryInfo"):
                            retry_secs = int(d.get("retryDelay","4s").rstrip("s"))
                            break
                except Exception:
                    pass
                time.sleep(delay_from_server or retry_secs)
                delay_from_server = max(retry_secs * 1.5, 4)
                continue
            raise
    raise RuntimeError("LLM retry limit reached.")

def _windows_from_segments_sliding(
    segments: list,
    window_sec: int = 20*60,
    overlap_sec: int = 5*60
):
    """
    Genera ventanas deslizantes con solapamiento.
    Ej: total=50m, window=20m, overlap=5m -> [0-20], [15-35], [30-50]
    """
    if not segments:
        return []
    if overlap_sec < 0 or overlap_sec >= window_sec:
        raise ValueError("overlap_sec debe ser >= 0 y < window_sec")

    total_end = max(float(seg.get("end", 0)) for seg in segments)

    wins = []
    start = 0.0
    step = window_sec - overlap_sec  # cuánto avanzo cada vez

    while start < total_end:
        end = min(start + window_sec, total_end)
        txts = [
            seg.get("text", "")
            for seg in segments
            if float(seg.get("start", 0)) < end and float(seg.get("end", 0)) > start
        ]
        txt = " ".join(t.strip() for t in txts if t and t.strip())
        if txt:
            wins.append({"index": len(wins), "start": start, "end": end, "text": txt})

        # si ya llegamos al final, corta
        if end >= total_end:
            break
        start += step

    return wins


# ========= Public API =========
def summarize_podcast_windows(
    result: Dict[str, Any],
    key_google: str,
    lang: str = "es",
    model: str = "gemma-3-12b-it",
    window_minutes: int = 20,
    overlap_minutes: int = 5,
    per_window_max_chars: int = 6000,
    per_minute_token_budget: int = 12000,
    model_fallbacks: Tuple[str, ...] = ("gemma-3-4b-it",),
    prompts_dir: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], str]:
    """
    result: dict con 'segments' [{start,end,text}, ...]
    Devuelve: (final_text, summaries_por_ventana, overall_text)
    """
    client = genai.Client(api_key=key_google)
    win_tpl, final_tpl = _load_prompts(prompts_dir, lang)
    segments = result.get("segments", [])
    window_sec   = int(window_minutes * 60)
    overlap_sec  = int(overlap_minutes * 60)
    windows = _windows_from_segments_sliding(
        segments,
        window_sec=window_sec,
        overlap_sec=overlap_sec
    )


    budget = TokenBudget(client, model, tokens_per_minute=per_minute_token_budget)

    summaries = []
    prev_bullets: List[str] = []

    # Ventanas
    for w in windows:
        chunk_text = _truncate(w["text"], per_window_max_chars)
        context_bullets = "\n".join(f"- {b}" for b in prev_bullets[:3]) if prev_bullets else "(sin contexto / no context)"
        prompt = _fill(win_tpl, {
            "CONTEXT_BULLETS": context_bullets,
            "T_START": _hhmmss(w["start"]),
            "T_END": _hhmmss(w["end"]),
            "CHUNK_TEXT": chunk_text
        })

        obj = None
        last_exc = None
        for mdl in [model] + [m for m in model_fallbacks if m != model]:
            budget.model = mdl
            try:
                resp = _gen_with_retry(client, mdl, prompt, budget)
                obj = _parse_json_text(resp.text)
                break
            except ValueError:
                # prompt grande -> recortar y reintentar una vez
                chunk_text = _truncate(chunk_text, max(2000, len(chunk_text)//2))
                prompt = _fill(win_tpl, {
                    "CONTEXT_BULLETS": context_bullets,
                    "T_START": _hhmmss(w["start"]),
                    "T_END": _hhmmss(w["end"]),
                    "CHUNK_TEXT": chunk_text
                })
                try:
                    resp = _gen_with_retry(client, mdl, prompt, budget)
                    obj = _parse_json_text(resp.text)
                    break
                except Exception as e2:
                    last_exc = e2
                    continue
            except Exception as e:
                last_exc = e
                continue
        if obj is None:
            raise last_exc or RuntimeError("Failed to summarize a window.")

        bullets = [b.strip() for b in obj.get("bullets", []) if isinstance(b, str) and b.strip()]
        summaries.append({
            "index": w["index"],
            "start": w["start"],
            "end": w["end"],
            "start_hms": _hhmmss(w["start"]),
            "end_hms": _hhmmss(w["end"]),
            "summary": (obj.get("summary") or "").strip(),
            "bullets": bullets[:3]
        })
        if bullets:
            prev_bullets = bullets

    # Overall (compacto: bullets + excerpt)
    compact = []
    for s in summaries:
        excerpt = _truncate(s["summary"], 700)
        compact.append({
            "index": s["index"]+1,
            "time": f'{s["start_hms"]}-{s["end_hms"]}',
            "bullets": s["bullets"],
            "excerpt": excerpt
        })
    windows_json = json.dumps(compact, ensure_ascii=False, indent=2)
    final_prompt = _fill(final_tpl, {"WINDOWS_JSON": windows_json})

    overall = None
    last_exc = None
    for mdl in [model] + [m for m in model_fallbacks if m != model]:
        budget.model = mdl
        try:
            resp = _gen_with_retry(client, mdl, final_prompt, budget)
            overall = resp.text.strip()
            break
        except Exception as e:
            last_exc = e
            continue
    if overall is None:
        raise last_exc or RuntimeError("Failed to build overall summary.")

    # Ensamble final
    lines = []
    lines.append("1. Overall summarize\n")
    lines.append(overall.strip())
    lines.append("")
    for i, s in enumerate(summaries, start=2):
        lines.append(f"{i}. Resumen {s['index']+1} ({s['start_hms']}–{s['end_hms']})\n")
        lines.append(s["summary"].strip())
        if s["bullets"]:
            lines.append("\nBullets:")
            for b in s["bullets"]:
                lines.append(f"- {b}")
        lines.append("")
    final_text = "\n".join(lines).strip()
    return final_text, summaries, overall
