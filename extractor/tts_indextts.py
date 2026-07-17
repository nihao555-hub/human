"""IndexTTS2 零样本声音克隆（B 站开源，独立 uv 虚拟环境运行）。

IndexTTS2 依赖 torch 2.8 / transformers 4.52，与主环境（FunASR/CosyVoice）冲突，
因此通过 `uv run` 在其自带 .venv 中以子进程方式调用：
    INDEXTTS_DIR  IndexTTS 仓库路径（默认 ~/index-tts，其内含 checkpoints/ 模型）

相比 CosyVoice2 无需 prompt_text（只要参考音频），情感表现力更强，但模型更大（CPU 更慢）。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DEFAULT_DIR = os.path.expanduser("~/index-tts")

_INFER_SNIPPET = """
import sys
from indextts.infer_v2 import IndexTTS2

text, prompt_audio, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
tts = IndexTTS2(
    cfg_path="checkpoints/config.yaml",
    model_dir="checkpoints",
    use_fp16=False,
    use_cuda_kernel=False,
    use_deepspeed=False,
)
tts.infer(spk_audio_prompt=prompt_audio, text=text, output_path=out_path)
"""


def clone_speak_indextts(
    text: str,
    prompt_audio: str | Path,
    out_path: str | Path,
    timeout: int = 3600,
) -> Path:
    """用参考音频音色朗读 text（IndexTTS2），写出 wav，返回输出路径。"""
    repo = os.environ.get("INDEXTTS_DIR", _DEFAULT_DIR)
    out_path = Path(out_path).absolute()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [
            "uv", "run", "--no-sync", "python", "-c", _INFER_SNIPPET,
            text, str(Path(prompt_audio).absolute()), str(out_path),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"IndexTTS2 推理失败: {proc.stderr[-2000:]}")
    if not out_path.exists():
        raise RuntimeError(f"IndexTTS2 未产出音频: {out_path}")
    return out_path
