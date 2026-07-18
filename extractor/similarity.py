"""声纹相似度质检：比较克隆语音与参考（原视频）音色的相似度。

用 3D-Speaker CAM++ 说话人验证模型（iic/speech_campplus_sv_zh-cn_16k-common，
与现有 FunASR/ModelScope 生态一致，模型约 28MB，CPU 友好）提取两段音频的说话人
嵌入并计算余弦相似度。分数越接近 1 越像同一个人，可作为声音克隆环节的自动质检指标。

用法:
    python -m extractor.similarity 原视频参考.wav 克隆输出.wav
    # 或作为库: from extractor.similarity import speaker_similarity
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SV_MODEL = "iic/speech_campplus_sv_zh-cn_16k-common"
# CAM++ zh 常用判定阈值：>= 视为同一说话人（可按业务调整）
DEFAULT_THRESHOLD = 0.35


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


def load_sv(device: str = "cpu"):
    """加载说话人验证模型（首次运行自动下载），常驻服务可复用。"""
    from modelscope.pipelines import pipeline

    return pipeline(task="speaker-verification", model=SV_MODEL, device=device)


def embed(audio_path: str | Path, pipe=None, device: str = "cpu"):
    """提取单段音频的说话人嵌入向量（numpy）。"""
    import numpy as np

    if pipe is None:
        pipe = load_sv(device)
    res = pipe([str(audio_path)], output_emb=True)
    return np.asarray(res["embs"][0], dtype="float64")


def _cosine(a, b) -> float:
    import numpy as np

    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def speaker_similarity(
    reference: str | Path,
    cloned: str | Path,
    pipe=None,
    device: str = "cpu",
    threshold: float = DEFAULT_THRESHOLD,
) -> SimilarityResult:
    """计算参考音频与克隆音频的音色余弦相似度。

    reference: 原视频截取的参考人声（或任意目标音色）
    cloned:    声音克隆产出的音频
    """
    for p in (reference, cloned):
        if not Path(p).exists():
            raise FileNotFoundError(f"音频不存在: {p}")
    if pipe is None:
        pipe = load_sv(device)
    score = _cosine(embed(reference, pipe), embed(cloned, pipe))
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
    parser.add_argument("--device", default="cpu", help="推理设备: cpu / cuda:0")
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD, help="同一说话人判定阈值"
    )
    parser.add_argument("--json", dest="json_path", help="结果 JSON 输出路径")
    args = parser.parse_args(argv)

    print("加载说话人验证模型（首次运行需下载）...", file=sys.stderr)
    result = speaker_similarity(
        args.reference, args.cloned, device=args.device, threshold=args.threshold
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
