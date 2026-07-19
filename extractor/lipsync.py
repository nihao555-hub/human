"""原视频对口型：本地 MuseTalk V1.5（本地主选，LatentSync/云端可后续兜底）。

把第三步生成的配音贴回原视频人脸，使口型与新配音对齐。

MuseTalk 依赖（torch 2.0.1 / mmcv / mmpose / tensorflow）与主环境（FunASR/CosyVoice）
严重冲突，因此通过其独立虚拟环境以子进程方式调用官方 `scripts.inference`：
    MUSETALK_DIR  MuseTalk 仓库路径（默认 ~/MuseTalk，内含 .venv、models/、data/）

CPU 上为逐帧生成，速度较慢（约实时的数十倍），生产建议 GPU。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_DEFAULT_DIR = os.path.expanduser("~/MuseTalk")


def _model_paths(repo: str, version: str) -> tuple[str, str]:
    if version == "v15":
        return "models/musetalkV15/unet.pth", "models/musetalkV15/musetalk.json"
    return "models/musetalk/pytorch_model.bin", "models/musetalk/musetalk.json"


def lipsync(
    video_path: str | Path,
    audio_path: str | Path,
    out_path: str | Path,
    version: str = "v15",
    bbox_shift: int = 0,
    ffmpeg_path: str = "/usr/bin",
    timeout: int = 7200,
) -> Path:
    """用 MuseTalk 让原视频人脸口型对齐驱动音频，写出 mp4，返回输出路径。

    video_path: 含人脸的原视频（建议 25fps）
    audio_path: 驱动音频（第三步的配音）
    version:    v15（默认，V1.5）或 v1（V1.0）
    bbox_shift: 嘴部区域上下微调（影响张口幅度，见 MuseTalk BBOX_SHIFT 文档）
    """
    repo = os.environ.get("MUSETALK_DIR", _DEFAULT_DIR)
    venv_py = os.path.join(repo, ".venv", "bin", "python")
    if not os.path.exists(venv_py):
        raise RuntimeError(f"未找到 MuseTalk 虚拟环境: {venv_py}（请先安装 MuseTalk）")

    video_path = Path(video_path).absolute()
    audio_path = Path(audio_path).absolute()
    out_path = Path(out_path).absolute()
    for p in (video_path, audio_path):
        if not p.exists():
            raise FileNotFoundError(f"输入不存在: {p}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    unet_path, unet_config = _model_paths(repo, version)

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = os.path.join(tmp, "task.yaml")
        result_dir = os.path.join(tmp, "results")
        # 配置里的 bbox_shift 仅在非零时写入（0 走默认）
        lines = [
            "task_0:",
            f'  video_path: "{video_path}"',
            f'  audio_path: "{audio_path}"',
        ]
        if bbox_shift:
            lines.append(f"  bbox_shift: {bbox_shift}")
        Path(cfg_path).write_text("\n".join(lines) + "\n", encoding="utf-8")

        proc = subprocess.run(
            [
                venv_py, "-m", "scripts.inference",
                "--inference_config", cfg_path,
                "--result_dir", result_dir,
                "--unet_model_path", unet_path,
                "--unet_config", unet_config,
                "--version", version,
                "--ffmpeg_path", ffmpeg_path,
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"MuseTalk 推理失败: {proc.stderr[-2000:]}")

        produced = sorted(
            Path(result_dir).rglob("*.mp4"), key=lambda p: p.stat().st_mtime
        )
        if not produced:
            raise RuntimeError(f"MuseTalk 未产出视频。stderr: {proc.stderr[-1000:]}")
        # shutil.move 处理跨文件系统（/tmp 与目标目录不同盘）情形，Path.replace 会失败
        shutil.move(str(produced[-1]), str(out_path))
    return out_path


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="原视频对口型（MuseTalk）")
    parser.add_argument("video", help="含人脸的原视频")
    parser.add_argument("audio", help="驱动音频（配音）")
    parser.add_argument("out", help="输出 mp4 路径")
    parser.add_argument("--version", default="v15", choices=["v15", "v1"])
    parser.add_argument("--bbox-shift", type=int, default=0)
    args = parser.parse_args(argv)

    out = lipsync(
        args.video, args.audio, args.out,
        version=args.version, bbox_shift=args.bbox_shift,
    )
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
