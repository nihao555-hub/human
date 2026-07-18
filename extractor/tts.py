"""声音克隆 TTS：本地 CosyVoice3 零样本克隆（本地主选，云端可另接 MiniMax 兜底）。

依赖官方 FunAudioLLM/CosyVoice 仓库（Apache-2.0），通过环境变量指定：
    COSYVOICE_DIR    CosyVoice 仓库路径（默认 ~/CosyVoice）
    COSYVOICE_MODEL  模型目录（默认 ~/models/Fun-CosyVoice3-0.5B）

按模型目录里的配置文件（cosyvoice3.yaml / cosyvoice2.yaml）自动选择模型版本。

零样本克隆：给一段参考音频（如原视频音频中截取的 5-15s 人声）+ 该段对应文本，
即可用该音色朗读任意新文案。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_DIR = os.path.expanduser("~/CosyVoice")
_DEFAULT_MODEL = os.path.expanduser("~/models/Fun-CosyVoice3-0.5B")

_repo = os.environ.get("COSYVOICE_DIR", _DEFAULT_DIR)
for p in (_repo, os.path.join(_repo, "third_party", "Matcha-TTS")):
    if p not in sys.path:
        sys.path.insert(0, p)


def load_tts(model_dir: str | None = None):
    """加载 CosyVoice 模型（CPU 上约 1-2 分钟），常驻服务可复用。

    根据模型目录里的 yaml 自动选择 CosyVoice3 / CosyVoice2。
    """
    from cosyvoice.cli.cosyvoice import CosyVoice2, CosyVoice3

    model_dir = model_dir or os.environ.get("COSYVOICE_MODEL", _DEFAULT_MODEL)
    is_v3 = os.path.exists(os.path.join(model_dir, "cosyvoice3.yaml"))
    cls = CosyVoice3 if is_v3 else CosyVoice2
    # CosyVoice3 dropped the load_jit argument that CosyVoice2 accepts.
    kwargs = {"load_trt": False, "fp16": False}
    if not is_v3:
        kwargs["load_jit"] = False
    return cls(model_dir, **kwargs)


def clone_speak(
    text: str,
    prompt_audio: str | Path,
    prompt_text: str,
    out_path: str | Path,
    model=None,
) -> Path:
    """用参考音频的音色朗读 text，写出 wav，返回输出路径。

    prompt_audio: 参考音频（16kHz 以上，建议 5-15 秒纯人声）
    prompt_text:  参考音频里说的原话（用于音色对齐）
    """
    import torchaudio

    if model is None:
        model = load_tts()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # CosyVoice3 要求 prompt_text 带 <|endofprompt|> 指令头，CosyVoice2 无需。
    if type(model).__name__ == "CosyVoice3" and "<|endofprompt|>" not in prompt_text:
        prompt_text = "You are a helpful assistant.<|endofprompt|>" + prompt_text

    chunks = []
    for res in model.inference_zero_shot(
        text, prompt_text, str(prompt_audio), stream=False
    ):
        chunks.append(res["tts_speech"])

    import torch

    audio = torch.cat(chunks, dim=1) if len(chunks) > 1 else chunks[0]
    torchaudio.save(str(out_path), audio, model.sample_rate)
    return out_path
