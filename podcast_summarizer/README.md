
# 🎙️ Podcast Summarizer

API en **FastAPI** que resume podcasts de **YouTube** o **archivos de audio locales**.

* Primero intenta usar **subtítulos oficiales de YouTube** (gratis).
* Si no existen, transcribe con **Gemini (Google GenAI)**.
* Luego genera resúmenes por ventanas (con opción de **solapamiento**) usando **Gemma**.
* Los resultados se guardan en **outputs/** como `.txt`.

---

## ⚡️ Características

* `POST /segments` → Devuelve solo la **transcripción**.
* `POST /summarize` → Transcribe + genera **resumen global + resúmenes por ventanas**.
* Ventanas con **solapamiento configurable** (ej: 20 min con solape de 5 min → \[0–20], \[15–35], \[30–50] …).
* Soporta tanto **YouTube URLs** como **archivos .mp3** locales.
* Listo para correr con **Docker**, sin dependencias manuales.

---

## 📂 Estructura del proyecto

```text
podcast-summarizer/
│
├── app/
│   └── api.py              # Endpoints FastAPI
│
├── src/
│   ├── captions.py         # Captions de YouTube
│   ├── youtube.py          # Descarga MP3 con yt-dlp
│   ├── transcribe_gemini.py# Fallback de transcripción (Gemini)
│   ├── summarize.py        # Resumen con Gemma
│   └── pipeline.py         # Orquestador
│
├── prompts/                # Prompts editables para los resúmenes
│   ├── win_prompt_es.txt
│   ├── final_prompt_es.txt
│   └── ...
│
├── inputs/                 # Audios locales montados en Docker
├── outputs/                # Resultados (resúmenes en .txt)
├── requirements.txt
├── Dockerfile
├── README.md
└── .gitignore
```

---

## 🐳 Uso con Docker

### 1. Instalar Docker

Descarga **Docker Desktop** desde 👉 [https://www.docker.com/get-started/](https://www.docker.com/get-started/).

Comprueba que funciona:

```bash
docker --version
```

### 2. Construir la imagen

En la carpeta del proyecto:

```bash
docker build -t podcast-summarizer .
```

### 3. Ejecutar el contenedor

```bash
# Linux / macOS
docker run --rm -p 8000:8000 \
  -e GOOGLE_API_KEY="TU_API_KEY" \
  -e PROMPTS_DIR="/app/prompts" \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/outputs:/app/outputs \
  podcast-summarizer
```

```powershell
# Windows PowerShell
docker run --rm -p 8000:8000 `
  -e GOOGLE_API_KEY="TU_API_KEY" `
  -e PROMPTS_DIR="/app/prompts" `
  -v ${PWD}\inputs:/app/inputs `
  -v ${PWD}\outputs:/app/outputs `
  podcast-summarizer
```

👉 Abre `http://localhost:8000/docs` en tu navegador para ver la **UI interactiva de FastAPI**.

---

## 🔑 Variables de entorno

* `GOOGLE_API_KEY` → **Obligatoria** si quieres transcribir con Gemini o resumir con Gemma.
* `PROMPTS_DIR` → carpeta de prompts (por defecto `/app/prompts`).

Ejemplo de `.env.example`:

```env
GOOGLE_API_KEY=tu_api_key
GEMINI_MODEL=gemini-1.5-flash
GEMMA_MODEL=gemma-3-12b-it
DEFAULT_LANG=es
WINDOW_MINUTES=20
OVERLAP_MINUTES=5
PROMPTS_DIR=prompts
```

---

## 📡 Endpoints principales

### 🔹 `POST /segments`

Devuelve solo la transcripción.

**Body ejemplo (YouTube):**

```json
{
  "url": "https://www.youtube.com/watch?v=abc123",
  "lang": "es"
}
```

**Body ejemplo (audio local):**

```json
{
  "audio_path": "/app/inputs/mi_audio.mp3",
  "lang": "es"
}
```

---

### 🔹 `POST /summarize`

Hace transcripción + resúmenes por ventanas + resumen global.

**Body ejemplo:**

```json
{
  "url": "https://www.youtube.com/watch?v=abc123",
  "lang": "es",
  "window_minutes": 20,
  "overlap_minutes": 5,
  "do_summary": true
}
```

Respuesta (ejemplo):

```json
{
  "final_text": "1. Overall summarize ...",
  "summary_path": "/app/outputs/yt_abc123_summary.txt",
  "per_window": [...],
  "overall": "...",
  "segments_result": {...}
}
```

---

## 📂 Carpeta de resultados

Todos los resúmenes en `.txt` se guardan en:

```
outputs/
├── yt_abc123_summary.txt
└── mi_audio_summary.txt
```

---

## 📄 Tips

* **Subir audios locales:** coloca tus `.mp3` en `inputs/` antes de correr Docker (`-v inputs:/app/inputs`).
* **Editar prompts:** modifica los archivos en `prompts/` sin tocar el código.
* **Logs opcionales:** puedes agregar un volumen `-v $(pwd)/logs:/app/logs` si luego implementas logging.
* **Sin Docker:** también puedes correr localmente con `uvicorn app.api:app --reload`, instalando dependencias de `requirements.txt` + `ffmpeg`.

---

## 🧪 Roadmap

* [ ] Endpoint `POST /upload` para subir audios directamente.
* [ ] Logs de tokens/tiempo por petición.
* [ ] Frontend web minimalista sobre `/summarize`.


