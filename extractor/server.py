"""常驻 HTTP 服务：启动时加载一次 FunASR 模型，之后每条链接仅需下载+转写。

启动:
    uvicorn extractor.server:app --host 127.0.0.1 --port 8300

调用:
    curl -X POST http://127.0.0.1:8300/extract \
        -H "Content-Type: application/json" \
        -d '{"url": "https://www.douyin.com/video/xxxx", "cookies_file": "cookies.txt"}'

返回 JSON 含全文、句级时间戳分段与 SRT 文本。
"""

from __future__ import annotations

import dataclasses
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .downloader import download_audio
from .rewriter import rewrite as rewrite_text
from .similarity import DEFAULT_THRESHOLD, load_sv, speaker_similarity
from .transcriber import load_model, transcribe
from .tts import clone_speak, load_tts
from .tts_indextts import clone_speak_indextts

_state: dict = {}
_lock = threading.Lock()  # FunASR 模型非线程安全，串行化推理


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = os.environ.get("EXTRACTOR_DEVICE", "cpu")
    _state["model"] = load_model(device)
    yield
    _state.clear()


app = FastAPI(title="文案提取服务", lifespan=lifespan)


class ExtractRequest(BaseModel):
    url: str
    cookies_file: str | None = None
    cookies_from_browser: str | None = None
    rewrite: str | None = None  # 改写要求，提供则同时返回 rewritten


class RewriteRequest(BaseModel):
    text: str
    instruction: str
    model: str | None = None


class TtsRequest(BaseModel):
    text: str
    prompt_audio: str  # 参考音频路径（5-15s 纯人声）
    prompt_text: str | None = None  # 参考音频对应的原话（cosyvoice 必填，indextts 不需）
    out_path: str = "outputs/tts.wav"
    engine: str = "cosyvoice"  # cosyvoice / indextts


class SimilarityRequest(BaseModel):
    reference: str  # 参考音频路径（原视频截取的人声）
    cloned: str  # 克隆产出的音频路径
    threshold: float = DEFAULT_THRESHOLD


@app.get("/healthz")
def healthz():
    return {"status": "ok", "model_loaded": "model" in _state}


@app.post("/extract")
def extract(req: ExtractRequest):
    try:
        dl = download_audio(
            req.url,
            out_dir=os.environ.get("EXTRACTOR_OUT_DIR", "downloads"),
            cookies_file=req.cookies_file,
            cookies_from_browser=req.cookies_from_browser,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"下载失败: {e}")

    with _lock:
        transcript = transcribe(dl.audio_path, model=_state["model"])

    rewritten = None
    if req.rewrite:
        try:
            rewritten = rewrite_text(transcript.text, req.rewrite)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"改写失败: {e}")

    return {
        "url": dl.webpage_url,
        "platform": dl.platform,
        "title": dl.title,
        "duration": dl.duration,
        "uploader": dl.uploader,
        "text": transcript.text,
        "segments": [dataclasses.asdict(s) for s in transcript.segments],
        "srt": transcript.to_srt(),
        "rewritten": rewritten,
    }


@app.post("/tts")
def tts(req: TtsRequest):
    if req.engine == "indextts":
        try:
            out = clone_speak_indextts(req.text, req.prompt_audio, req.out_path)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"audio_path": str(out), "engine": "indextts"}

    if not req.prompt_text:
        raise HTTPException(status_code=400, detail="cosyvoice 引擎需提供 prompt_text")
    with _lock:
        if "tts" not in _state:
            _state["tts"] = load_tts()  # 首次调用时加载（CPU 约 1-2 分钟）
        try:
            out = clone_speak(
                req.text, req.prompt_audio, req.prompt_text, req.out_path,
                model=_state["tts"],
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=422, detail=str(e))
    return {"audio_path": str(out), "engine": "cosyvoice"}


@app.post("/similarity")
def similarity(req: SimilarityRequest):
    with _lock:
        if "sv" not in _state:
            _state["sv"] = load_sv()  # 首次调用时加载说话人验证模型
        try:
            result = speaker_similarity(
                req.reference, req.cloned,
                pipe=_state["sv"], threshold=req.threshold,
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@app.post("/rewrite")
def rewrite(req: RewriteRequest):
    try:
        return {"rewritten": rewrite_text(req.text, req.instruction, model=req.model)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"改写失败: {e}")
