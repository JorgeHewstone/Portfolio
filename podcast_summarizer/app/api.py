# app/api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
import os

from src.pipeline import get_segments, run_pipeline

# --------- Modelos de request/response ---------

class SegmentsReq(BaseModel):
    url: Optional[str] = Field(default=None, description="YouTube URL")
    audio_path: Optional[str] = Field(default=None, description="Ruta a un .mp3 accesible por el contenedor")
    lang: Literal["es", "en"] = Field(default="es")
    window_minutes: int = Field(default=20, ge=1, description="Tamaño de ventana para chunking/transcripción")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Modelo de transcripción Gemini")
    google_api_key: Optional[str] = Field(default=None, description="API key de Gemini (opcional; si no, se usa la de entorno)")

class SummarizeReq(BaseModel):
    # Entrada (igual que SegmentsReq)
    url: Optional[str] = Field(default=None, description="YouTube URL")
    audio_path: Optional[str] = Field(default=None, description="Ruta a un .mp3 accesible por el contenedor")
    lang: Literal["es", "en"] = Field(default="es")
    google_api_key: Optional[str] = Field(default=None, description="API key de Gemini (opcional; si no, se usa la de entorno)")

    # Transcripción
    window_minutes: int = Field(default=20, ge=1)
    gemini_model: str = Field(default="gemini-1.5-flash")

    # Resumen
    gemma_model: str = Field(default="gemma-3-12b-it", description="Modelo para resumir")
    overlap_minutes: int = Field(default=5, ge=0, description="Solapamiento entre ventanas del resumen")
    per_window_max_chars: int = Field(default=6000, ge=500, description="Corte de texto por ventana antes de enviar a LLM")
    per_minute_token_budget: int = Field(default=12000, ge=1000, description="Presupuesto de tokens/min para rate-limit")
    prompts_dir: Optional[str] = Field(default="prompts", description="Carpeta con prompts .txt")
    do_summary: bool = Field(default=True, description="Si false, solo devuelve transcripción")

class HealthResp(BaseModel):
    status: str
    have_google_key_env: bool

# --------- App ---------
app = FastAPI(title="YT Summarizer", version="1.0.0", docs_url="/docs", redoc_url="/redoc")


# --------- Helpers ---------
def _resolve_google_key(body_key: Optional[str]) -> Optional[str]:
    """
    Prioriza la API key recibida en el body;
    si no viene, usa la variable de entorno GOOGLE_API_KEY.
    """
    return body_key or os.getenv("GOOGLE_API_KEY")


def _validate_source(req_url: Optional[str], req_audio_path: Optional[str]):
    if not req_url and not req_audio_path:
        raise HTTPException(
            status_code=400,
            detail="Debes enviar 'url' de YouTube o 'audio_path' (ruta de un .mp3)."
        )


# --------- Endpoints ---------

@app.get("/", response_model=HealthResp, tags=["system"])
def root():
    """Salud del servicio."""
    return HealthResp(status="ok", have_google_key_env=bool(os.getenv("GOOGLE_API_KEY")))


@app.post("/segments", tags=["transcription"])
def segments(req: SegmentsReq) -> Dict[str, Any]:
    """
    Devuelve la transcripción unificada:
    {
      text, segments, source(captions|gemini), lang, kind, meta
    }
    """
    _validate_source(req.url, req.audio_path)

    google_key = _resolve_google_key(req.google_api_key)

    try:
        result = get_segments(
            url=req.url,
            audio_path=req.audio_path,
            lang=req.lang,
            google_api_key=google_key,
            window_minutes=req.window_minutes,
            gemini_model=req.gemini_model,
            prefer_captions=True,         # primero intentará captions de YouTube
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {e}")


@app.post("/summarize", tags=["summarize"])
def summarize(req: SummarizeReq) -> Dict[str, Any]:
    """
    Orquesta todo: (captions -> gemini) -> resumen por ventanas (con solapamiento).
    Devuelve:
      {
        segments_result, final_text, per_window, overall, summary_path
      }
    """
    _validate_source(req.url, req.audio_path)

    google_key = _resolve_google_key(req.google_api_key)
    if req.do_summary and not google_key:
        # si hará resumen, igual necesitamos la key para el overall con Gemma (vía Google GenAI)
        # (Si en tu entorno Gemma vive en otra API distinta, ajusta esta validación)
        raise HTTPException(
            status_code=400,
            detail="Falta GOOGLE_API_KEY (en el body o como variable de entorno) para el resumen."
        )

    try:
        res = run_pipeline(
            url=req.url,
            audio_path=req.audio_path,
            lang=req.lang,
            google_api_key=google_key,
            gemini_model=req.gemini_model,
            gemma_model=req.gemma_model,
            window_minutes=req.window_minutes,
            overlap_minutes=req.overlap_minutes,
            per_window_max_chars=req.per_window_max_chars,
            per_minute_token_budget=req.per_minute_token_budget,
            prompts_dir=req.prompts_dir,
            do_summary=req.do_summary,
            out_dir="/app/outputs",       # asegura ruta consistente dentro del contenedor
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Summarization failed: {e}")
