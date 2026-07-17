# 文案提取模块（链接 → 口播文案）

粘贴社媒视频链接，自动下载音频并本地转写出口播文案。

- 下载/链接解析：[yt-dlp](https://github.com/yt-dlp/yt-dlp)（178k+ stars，活跃维护），支持抖音、B站、TikTok、YouTube 等上千站点
- 中文 ASR：[FunASR](https://github.com/modelscope/FunASR) Paraformer-large（阿里官方，19k+ stars），本地推理，带 VAD、标点、句级时间戳

## 安装

```bash
pip install -r extractor/requirements.txt
```

需要系统已安装 FFmpeg。

## 使用

```bash
python -m extractor.cli "https://www.douyin.com/video/xxxxx" \
    --json transcript.json --srt transcript.srt
```

- 抖音等平台可能需要 Cookie：`--cookies cookies.txt` 或 `--cookies-from-browser chrome`
- GPU 加速：`--device cuda:0`
- 首次运行自动从 ModelScope 下载 Paraformer-large 模型（约 1GB），之后走本地缓存
- 输出：stdout 全文文案；`--json` 含元信息与句级时间戳分段；`--srt` 可直接作为字幕草稿

## 内存要求

Paraformer-large CPU 推理峰值内存约 6-8GB；内存不足时建议开启 swap 或使用 GPU。
