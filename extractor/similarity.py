"""声纹相似度质检：比较克隆语音与参考（原视频）音色的相似度。

用 3D-Speaker CAM++ 说话人验证模型提取两段音频的说话人嵌入并计算余弦相似度，
分数越接近 1 越像同一个人，可作为声音克隆环节的自动质检指标，也可用于横向对比
不同 TTS 引擎（CosyVoice2 / IndexTTS2）的克隆保真度。

复用 CosyVoice2 已内置的 `campplus.onnx`（与 CosyVoice 提取音色嵌入用的是同一模型），
通过 onnxruntime 推理，特征用 kaldi fbank（无 sox 依赖，CPU 友好）。默认从
COSYVOICE_MODEL 目录读取，也可用 CAMPPLUS_ONNX 环境变量或 --model 指定。

用法:
    python -m extractor.similarity 原视频参考.wav 克隆输出.wav
    # 或作为库: from extractor.similarity import speaker_similarity
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# CAM++ 嵌入余弦相似度的经验判定阈值：>= 视为同一说话人（可按业务调整）
DEFAULT_THRESHOLD = 0.5


def _default_onnx() -> str:
    base = os.environ.get(
        "COSYVOICE_MODEL", os.path.expanduser("~/models/CosyVoice2-0.5B")
    )
    return os.path.join(base, "campplus.onnx")


@dataclass
class SimilarityResult:
    score: float  # 余弦相似度，范围约 [-1, 1]，越大越像同一人
    same_speaker: bool  # score >= threshold
    threshold: float

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "same_speaker": self.same_speaker,
            "threshold": self.threshold,
        }


def load_sv(onnx_path: str | None = None):
    """加载 CAM++ 说话人嵌入模型（onnxruntime），常驻服务可复用。"""
    import onnxruntime

    onnx_path = onnx_path or os.environ.get("CAMPPLUS_ONNX") or _default_onnx()
    if not os.path.exists(onnx_path):
        raise FileNotFoundError(
            f"找不到 CAM++ 模型 {onnx_path}；请下载 CosyVoice2-0.5B（内含 campplus.onnx），"
            "或用 CAMPPLUS_ONNX 环境变量指定 campplus.onnx 路径。"
        )
    opts = onnxruntime.SessionOptions()
    opts.intra_op_num_threads = 1
    return onnxruntime.InferenceSession(
        onnx_path, sess_options=opts, providers=["CPUExecutionProvider"]
    )


def embed(audio_path: str | Path, sess=None):
    """提取单段音频的说话人嵌入向量（numpy），音频自动转 16k 单声道。"""
    import librosa
    import numpy as np
    import torch
    import torchaudio.compliance.kaldi as kaldi

    if sess is None:
        sess = load_sv()
    samples, _ = librosa.load(str(audio_path), sr=16000, mono=True)
    wav = torch.from_numpy(samples).unsqueeze(0)
    feat = kaldi.fbank(wav, num_mel_bins=80, dither=0, sample_frequency=16000)
    feat = feat - feat.mean(dim=0, keepdim=True)
    emb = sess.run(None, {sess.get_inputs()[0].name: feat.unsqueeze(0).numpy()})[0]
    return np.asarray(emb, dtype="float64").flatten()


def _cosine(a, b) -> float:
    import numpy as np

    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def speaker_similarity(
    reference: str | Path,
    cloned: str | Path,
    sess=None,
    threshold: float = DEFAULT_THRESHOLD,
) -> SimilarityResult:
    """计算参考音频与克隆音频的音色余弦相似度。

    reference: 原视频截取的参考人声（或任意目标音色）
    cloned:    声音克隆产出的音频
    """
    for p in (reference, cloned):
        if not Path(p).exists():
            raise FileNotFoundError(f"音频不存在: {p}")
    if sess is None:
        sess = load_sv()
    score = _cosine(embed(reference, sess), embed(cloned, sess))
    return SimilarityResult(
        score=score, same_speaker=score >= threshold, threshold=threshold
    )


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="声纹相似度：克隆音频 vs 参考音色")
    parser.add_argument("reference", help="参考音频（原视频截取的人声）")
    parser.add_argument("cloned", help="克隆产出的音频")
    parser.add_argument("--model", dest="onnx_path", help="campplus.onnx 路径")
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD, help="同一说话人判定阈值"
    )
    parser.add_argument("--json", dest="json_path", help="结果 JSON 输出路径")
    args = parser.parse_args(argv)

    print("加载 CAM++ 说话人验证模型...", file=sys.stderr)
    sess = load_sv(args.onnx_path)
    result = speaker_similarity(
        args.reference, args.cloned, sess=sess, threshold=args.threshold
    )
    payload = result.to_dict()
    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
