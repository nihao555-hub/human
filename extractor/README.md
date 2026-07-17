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

## 常驻服务（推荐，快约 3 倍）

CLI 每次运行需重新加载模型（约 40s）。常驻服务启动时加载一次，之后每条链接仅需下载+转写（约 15-20s）：

```bash
uvicorn extractor.server:app --host 127.0.0.1 --port 8300
```

```bash
curl -X POST http://127.0.0.1:8300/extract \
    -H "Content-Type: application/json" \
    -d '{"url": "https://www.douyin.com/video/xxxxx", "cookies_file": "cookies.txt"}'
```

返回 JSON 含 `text`（全文）、`segments`（句级时间戳）、`srt`（字幕文本）。健康检查：`GET /healthz`。

## 文案改写（DeepSeek API）

设置环境变量 `DEEPSEEK_API_KEY` 后，可按自定义要求改写提取出的文案（LLM 为流程中唯一使用 API 的环节）：

```bash
# CLI：提取 + 改写一步到位
python -m extractor.cli "<链接>" --rewrite "改写成更口语化的风格，突出悬念"

# 服务：单独改写已有文案
curl -X POST http://127.0.0.1:8300/rewrite \
    -H "Content-Type: application/json" \
    -d '{"text": "原始文案...", "instruction": "改写要求..."}'
# 或在 /extract 请求中带上 "rewrite": "改写要求"，一次返回原文+改写稿
```

可通过 `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` 切换到其他 OpenAI 兼容供应商（如通义千问）。

## 声音克隆 TTS（本地 CosyVoice2）

零样本声音克隆：参考音频（原视频中 5-15s 纯人声）+ 对应原话 → 用该音色朗读任意新文案。

```bash
# 一次性准备
git clone --recurse-submodules https://github.com/FunAudioLLM/CosyVoice.git ~/CosyVoice
pip install -r extractor/requirements-tts.txt
python3 -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice2-0.5B', local_dir='/home/ubuntu/models/CosyVoice2-0.5B')"

# 服务接口（首次调用时加载模型）
curl -X POST http://127.0.0.1:8300/tts -H "Content-Type: application/json" \
    -d '{"text": "要朗读的新文案", "prompt_audio": "/path/ref.wav", "prompt_text": "参考音频里的原话", "out_path": "outputs/tts.wav"}'
```

路径可用 `COSYVOICE_DIR` / `COSYVOICE_MODEL` 环境变量覆盖。注意 `transformers` 必须为 4.51.x（5.x 不兼容）。CPU 推理较慢（约 7-8x 实时）；MiniMax 等云端 TTS 可作为速度兜底后续接入。

## 内存要求

Paraformer-large CPU 推理峰值内存约 6-8GB；内存不足时建议开启 swap 或使用 GPU。
