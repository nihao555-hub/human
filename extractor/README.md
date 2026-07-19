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

### 备选引擎：IndexTTS2

`/tts` 请求加 `"engine": "indextts"` 可切换到 B 站开源的 IndexTTS2（无需 prompt_text，只要参考音频；情感表现力更强）。因其依赖（torch 2.8 / transformers 4.52）与主环境冲突，通过独立 uv 虚拟环境以子进程运行：

```bash
git clone https://github.com/index-tts/index-tts.git ~/index-tts
cd ~/index-tts && uv sync -p python3.10
python3 -c "from modelscope import snapshot_download; snapshot_download('IndexTeam/IndexTTS-2', local_dir='/home/ubuntu/index-tts/checkpoints')"
```

仓库路径可用 `INDEXTTS_DIR` 覆盖。模型约 8GB，加载+推理内存占用大（8GB 内存机器需 ≥12G swap），CPU 上比 CosyVoice2 慢数倍（RTF≈16），更适合 GPU 环境。

## 声纹相似度质检（克隆音色 vs 原音色）

声音克隆后，用说话人验证模型客观衡量“克隆音频”与“原视频参考音频”的音色相似度（余弦相似度，越接近 1 越像同一人）：

```bash
# CLI
python -m extractor.similarity 原视频参考.wav 克隆输出.wav
# {"score": 0.8073, "same_speaker": true, "threshold": 0.5}

# 服务接口（首次调用时加载模型）
curl -X POST http://127.0.0.1:8300/similarity -H "Content-Type: application/json" \
    -d '{"reference": "/path/ref.wav", "cloned": "/path/tts_out.wav"}'
```

采用 3D-Speaker CAM++ 中文说话人验证模型（`campplus.onnx`，与 CosyVoice2 提取音色嵌入用的是同一模型），onnxruntime 本地推理、kaldi fbank 特征，无 sox 依赖，CPU 友好。默认从 `COSYVOICE_MODEL` 目录读取 `campplus.onnx`（即 CosyVoice2-0.5B 内已自带），也可用 `CAMPPLUS_ONNX` 环境变量或 `--model` 指定。需安装 `requirements-tts.txt`（含 onnxruntime / librosa）。

`score` 为两段音频说话人嵌入的余弦相似度，`same_speaker` 按 `threshold`（默认 0.5，可调）判定。适合作为克隆环节的自动质检门槛，也可用来横向对比不同 TTS 引擎（CosyVoice2 / IndexTTS2）的克隆保真度。实测参考：同一说话人的 CosyVoice2 克隆 vs 原音色 ≈ 0.81，不同说话人之间 ≈ 0.09-0.13。

## 原视频对口型（本地 MuseTalk V1.5）

把第三步的配音贴回原视频人脸，使口型与新配音对齐（本地主选 MuseTalk，LatentSync/云端可后续兜底）。

```bash
# 一次性准备（独立虚拟环境，依赖 torch2.0.1/mmcv/mmpose，与主环境隔离）
git clone https://github.com/TMElyralab/MuseTalk.git ~/MuseTalk
cd ~/MuseTalk && python3 -m venv .venv && source .venv/bin/activate
pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt && pip install -U openmim
pip install "setuptools<70" && pip install chumpy==0.70 --no-build-isolation  # 否则 mmpose 装不上
mim install mmengine "mmcv==2.0.1" "mmdet==3.1.0" "mmpose==1.1.0"
bash download_weights.sh   # 注意新版 gdown 需用 `gdown <id> -O ...`（去掉 --id）；huggingface-cli 改用 `hf download`

# CLI
python -m extractor.lipsync 原视频.mp4 配音.wav 输出.mp4
# 服务接口
curl -X POST http://127.0.0.1:8300/lipsync -H "Content-Type: application/json" \
    -d '{"video_path": "/path/src.mp4", "audio_path": "/path/tts_out.wav", "out_path": "outputs/lipsync.mp4"}'
```

仓库路径可用 `MUSETALK_DIR` 覆盖。输入建议 25fps；`bbox_shift` 可微调张口幅度。**MuseTalk 依赖与主环境冲突，故在独立 venv 内以子进程运行**。CPU 上为逐帧生成，非常慢（约每帧 1-2s 面部关键点 + 生成，10s 视频需十几分钟），生产强烈建议 GPU。

## 内存要求

Paraformer-large CPU 推理峰值内存约 6-8GB；内存不足时建议开启 swap 或使用 GPU。
