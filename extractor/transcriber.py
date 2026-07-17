"""基于 FunASR Paraformer-large 的中文语音转写。

首次运行会从 ModelScope 自动下载模型（约 1GB），之后走本地缓存。
输出带句级时间戳的分段结果，可直接用于字幕强制对齐的输入文案。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MODEL = "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
VAD_MODEL = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
PUNC_MODEL = "iic/punc_ct-transformer_cn-en-common-vocab471067-large"


@dataclass
class Segment:
    start: float  # 秒
    end: float
    text: str


@dataclass
class Transcript:
    text: str
    segments: list[Segment]

    def to_srt(self) -> str:
        lines = []
        for i, seg in enumerate(self.segments, 1):
            lines.append(str(i))
            lines.append(f"{_ts(seg.start)} --> {_ts(seg.end)}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_model(device: str = "cpu"):
    """加载 FunASR 模型（约 40s），常驻服务可复用以避免每次重新加载。"""
    from funasr import AutoModel

    return AutoModel(
        model=MODEL,
        vad_model=VAD_MODEL,
        punc_model=PUNC_MODEL,
        device=device,
        disable_update=True,
    )


def transcribe(audio_path: str | Path, device: str = "cpu", model=None) -> Transcript:
    """转写音频，返回全文与带时间戳分段。可传入已加载的模型。"""
    if model is None:
        model = load_model(device)
    results = model.generate(
        input=str(audio_path),
        sentence_timestamp=True,
        batch_size_s=300,
    )

    segments: list[Segment] = []
    texts: list[str] = []
    for res in results:
        texts.append(res.get("text", ""))
        for sent in res.get("sentence_info", []):
            segments.append(
                Segment(
                    start=sent["start"] / 1000.0,
                    end=sent["end"] / 1000.0,
                    text=sent["text"].strip(),
                )
            )
    return Transcript(text="".join(texts), segments=segments)
