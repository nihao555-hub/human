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
from .transcriber import load_model, transcribe

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


@app.post("/rewrite")
def rewrite(req: RewriteRequest):
    try:
        return {"rewritten": rewrite_text(req.text, req.instruction, model=req.model)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"改写失败: {e}")
