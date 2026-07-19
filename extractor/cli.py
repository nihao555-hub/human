"""命令行入口：粘贴社媒链接 → 下载音频 → FunASR 转写 → 输出文案。

用法:
    python -m extractor.cli "https://www.douyin.com/video/xxxx" \
        [--cookies cookies.txt] [--cookies-from-browser chrome] \
        [--json out.json] [--srt out.srt]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from .downloader import download_audio
from .transcriber import transcribe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="社媒链接 → 口播文案提取")
    parser.add_argument("url", help="视频链接或包含链接的分享文本")
    parser.add_argument("--cookies", help="Netscape 格式 cookies.txt 路径")
    parser.add_argument("--cookies-from-browser", help="从浏览器读取 Cookie，如 chrome")
    parser.add_argument("--out-dir", default="downloads", help="音频下载目录")
    parser.add_argument("--device", default="cpu", help="推理设备: cpu / cuda:0")
    parser.add_argument("--json", dest="json_path", help="结果 JSON 输出路径")
    parser.add_argument("--srt", dest="srt_path", help="SRT 字幕输出路径")
    parser.add_argument(
        "--rewrite", dest="rewrite_instruction",
        help="改写要求（需设置 DEEPSEEK_API_KEY），如：改写成更口语化的带货风格"
    )
    args = parser.parse_args(argv)

    print(f"[1/2] 下载音频: {args.url}", file=sys.stderr)
    dl = download_audio(
        args.url,
        out_dir=args.out_dir,
        cookies_file=args.cookies,
        cookies_from_browser=args.cookies_from_browser,
    )
    print(
        f"      {dl.platform} | {dl.title} | {dl.duration}s -> {dl.audio_path}",
        file=sys.stderr,
    )

    print("[2/2] FunASR 转写中（首次运行需下载模型）...", file=sys.stderr)
    transcript = transcribe(dl.audio_path, device=args.device)

    rewritten = None
    if args.rewrite_instruction:
        from .rewriter import rewrite

        print("[3/3] DeepSeek 改写中...", file=sys.stderr)
        rewritten = rewrite(transcript.text, args.rewrite_instruction)

    if args.json_path:
        payload = {
            "url": dl.webpage_url,
            "platform": dl.platform,
            "title": dl.title,
            "duration": dl.duration,
            "uploader": dl.uploader,
            "text": transcript.text,
            "segments": [dataclasses.asdict(s) for s in transcript.segments],
        }
        if rewritten is not None:
            payload["rewritten"] = rewritten
        Path(args.json_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"JSON 已写入 {args.json_path}", file=sys.stderr)
    if args.srt_path:
        Path(args.srt_path).write_text(transcript.to_srt(), encoding="utf-8")
        print(f"SRT 已写入 {args.srt_path}", file=sys.stderr)

    print(transcript.text)
    if rewritten is not None:
        print("\n===== 改写后 =====\n", file=sys.stderr)
        print(rewritten)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
