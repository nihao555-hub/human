# 开发 PRD：Human IP Studio 本地 AI 口播智能体

## 1. 文档目的

本文面向开发人员，用于把两份飞书参考资料中的产品流程和公开问题转化为可实施的软件需求、模块边界、接口、数据结构、任务状态和验收标准。

参考资料：

1. 旗博士口播智能体 3.0 详细使用教程

   https://xa8k8qzrnlp.feishu.cn/docx/JlAOdfKjfogpkExyXYxcofJ0nBb
2. 免费超级 IP 智能体（内测版）

   https://5x-class.feishu.cn/wiki/SEbcwBFO0iS98ekvBwHc0KTzndf

## 2. 开发目标

实现一款本地优先的桌面端 AI 口播视频工具，用户可以完成：

```text
输入主题 / 文案 / 对标视频
  -> 提取或生成文案
  -> 本地声音克隆 / TTS
  -> 本地数字人对口型
  -> 本地字幕识别与排版
  -> 封面编辑
  -> 本地导出 MP4
```

开发必须优先解决参考产品暴露出的高频问题：

- 抖音不同链接格式解析失败。
- API Key 配置复杂、错误不可读。
- 手机录制音频格式不兼容。
- 对口型长时间排队或无法停止。
- 29 秒以上视频失败率上升。
- 字幕繁体、错字、断句、换行、导出溢出。
- 预览和最终导出不一致。
- 导出视频黑屏、发灰、倒放。
- 封面模板弱、标题不能生成、文字编辑受限。
- 任务失败后需要从头开始。
- 缺少一键清空、成功 / 失败提醒和明确进度。

## 3. 技术约束

### 3.1 部署约束

- 语言模型允许调用 API。
- ASR、TTS、声音克隆、对口型、字幕、封面渲染、视频合成、项目数据和任务队列必须本地运行。
- 默认不上传用户声音、肖像、原视频和生成视频。
- Windows 为 MVP 首发平台。
- macOS Apple Silicon 在 V1 支持。
- MVP 不从零训练基础模型，只集成和封装现有模型。

### 3.2 建议技术栈

| 层 | 建议方案 | 说明 |
| --- | --- | --- |
| 桌面端 | Electron + React + TypeScript | 开发生态成熟，适合媒体预览和跨平台 |
| UI 状态 | Zustand + TanStack Query | 区分本地 UI 状态和 Runtime 服务状态 |
| 本地 Runtime | Python 3.11 + FastAPI + Pydantic | 统一封装本地模型和音视频任务 |
| 数据库 | SQLite | 存储项目、素材、任务、模型和配置元数据 |
| 任务执行 | SQLite 持久化队列 + 独立 Python Worker | App 重启后可恢复，模型崩溃不拖垮 UI |
| 音视频 | FFmpeg / ffprobe | 转码、抽帧、字幕、音视频合成、导出 |
| ASR | faster-whisper 或 SenseVoice | 本地字幕识别和文案兜底 |
| TTS | CosyVoice2/3 | 本地 TTS 和声音克隆 |
| 对口型 | MuseTalk 作为 MVP；LatentSync 作为高质量档候选 | 统一通过 Adapter 调用 |
| 人脸检测 | MediaPipe 或商用友好替代 | 避免非商用 InsightFace 权重 |
| 日志 | Python structlog / 标准 logging + Electron 日志 | 用户日志和调试日志分离 |

技术选型可替换，但模块接口和验收标准不得随模型实现变化。

## 4. MVP 范围

### 4.1 必做 P0

- 设备体检。
- 本地模型管理。
- 项目和素材管理。
- 文案输入、对标视频文案提取、LLM 文案改写。
- 本地 ASR。
- 本地声音克隆 / TTS。
- 本地视频对口型。
- 字幕生成、编辑和样式。
- 封面模板。
- MP4 导出。
- 持久化任务队列。
- 取消、失败重试、阶段重跑。
- 中文错误诊断。
- 基础质量检查。

### 4.2 V1 P1

- 批量任务。
- 1 分钟以上视频分段处理。
- 多模型质量档。
- 账号人设库。
- 本地知识库。
- 时间线编辑。
- BGM 和画中画。
- macOS Apple Silicon。
- 多平台规格导出。

### 4.3 MVP 不做

- 云端账号体系和 SaaS 后台。
- 多租户。
- 从零训练 ASR、TTS 或对口型模型。
- 全自动绕过平台审核的发布。
- 多人实时协作。
- 局域网多机 GPU 调度。
- 完整专业剪辑软件能力。

## 5. 系统架构

```text
Electron Desktop
  ├─ Renderer: React UI
  ├─ Main Process
  │   ├─ Python Runtime 生命周期
  │   ├─ 文件选择 / 系统通知
  │   ├─ 安装包 / 更新
  │   └─ 安全 IPC
  └─ Preload API

Python Local Runtime
  ├─ FastAPI
  ├─ Project Service
  ├─ Asset Service
  ├─ Job Service
  ├─ Model Manager
  ├─ LLM Adapter
  ├─ Extractor Adapter
  ├─ ASR Adapter
  ├─ TTS Adapter
  ├─ LipSync Adapter
  ├─ Subtitle Service
  ├─ Cover Service
  ├─ Export Service
  └─ Quality Check Service

Local Worker
  ├─ 按显存和模型类型串行 / 限流执行
  ├─ 记录阶段进度
  ├─ 接收取消信号
  └─ 保存中间产物

Local Storage
  ├─ SQLite
  ├─ projects/
  ├─ assets/
  ├─ models/
  ├─ cache/
  ├─ exports/
  └─ logs/
```

## 6. 进程职责

### 6.1 Electron Renderer

只负责：

- 页面渲染。
- 用户输入。
- 媒体预览。
- 调用 Preload 暴露的安全 API。
- 展示 Runtime 任务状态。

禁止：

- 直接读取任意本地文件。
- 保存 API Key 明文。
- 直接执行 shell 命令。
- 在 Renderer 中加载 Python 模型。

### 6.2 Electron Main

负责：

- 启动、检测、停止 Python Runtime。
- 选择文件和目录。
- 系统通知。
- 窗口管理。
- 安全 IPC。
- App 退出时通知 Runtime 正常关闭。

### 6.3 Python Runtime

负责：

- 业务 API。
- 项目与素材元数据。
- API Key 加密存储。
- 模型 Adapter。
- 任务创建、查询、重试、取消。
- 音视频预检和质量检查。

### 6.4 Worker

负责：

- 执行长任务。
- 启动和回收模型进程。
- 读取取消标志。
- 定时更新进度和心跳。
- 写入中间产物。
- 捕获 stdout、stderr、退出码和显存错误。

## 7. 推荐仓库结构

```text
human/
├── apps/
│   └── desktop/
│       ├── src/main/
│       ├── src/preload/
│       └── src/renderer/
├── runtime/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── services/
│   │   ├── adapters/
│   │   └── workers/
│   ├── tests/
│   └── pyproject.toml
├── packages/
│   ├── shared-types/
│   └── ui/
├── scripts/
│   ├── download-models/
│   ├── benchmark/
│   └── packaging/
├── fixtures/
│   ├── audio/
│   ├── video/
│   ├── images/
│   └── golden/
└── docs/
```

## 8. 数据存储规范

### 8.1 本地目录

默认数据目录：

```text
{APP_DATA}/human-ip-studio/
├── app.db
├── config/
│   ├── app.json
│   └── encrypted-secrets.bin
├── models/
├── projects/{project_id}/
│   ├── project.json
│   ├── assets/
│   ├── intermediates/
│   ├── previews/
│   └── exports/
├── cache/
└── logs/
```

要求：

- 不把绝对路径写入可分享的项目文件；使用项目相对路径。
- 素材入库后计算 SHA-256，避免重复复制。
- 中间产物按任务 ID 分目录。
- App 设置页支持清理缓存，但不得删除源素材和最终导出。

### 8.2 核心实体

#### Project

```json
{
  "id": "uuid",
  "name": "string",
  "status": "draft|processing|ready|failed",
  "persona_id": "uuid|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### Asset

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "type": "video|audio|image|text|subtitle|cover|export",
  "relative_path": "string",
  "sha256": "string",
  "duration_ms": 0,
  "width": 0,
  "height": 0,
  "codec": "string|null",
  "metadata": {}
}
```

#### Job

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "type": "extract|rewrite|asr|tts|lipsync|subtitle|cover|export|quality_check",
  "status": "queued|preparing|running|canceling|canceled|failed|succeeded",
  "progress": 0,
  "stage": "string",
  "params": {},
  "artifacts": [],
  "error_code": "string|null",
  "error_message": "string|null",
  "created_at": "datetime",
  "started_at": "datetime|null",
  "finished_at": "datetime|null"
}
```

#### ModelInstallation

```json
{
  "id": "string",
  "adapter": "asr|tts|lipsync|image",
  "version": "string",
  "status": "missing|downloading|ready|corrupted|unsupported",
  "path": "string",
  "sha256": "string",
  "size_bytes": 0,
  "minimum_vram_mb": 0
}
```

## 9. 任务状态机

```text
queued
  -> preparing
  -> running
      -> succeeded
      -> failed
      -> canceling -> canceled
```

规则：

- 只有 `queued`、`failed`、`canceled` 可以重试。
- 重试创建新 Job，旧 Job 保留。
- 每 2 秒更新一次心跳；30 秒无心跳标记为异常。
- 取消任务时先发软终止，10 秒后仍未退出再强制结束子进程。
- 任务成功后必须校验产物存在且可被 ffprobe 读取。
- App 重启后，原 `running` 任务改为 `failed`，错误码为 `JOB_INTERRUPTED`，允许从当前阶段重试。

## 10. 本地 API

统一前缀：`/api/v1`

### 10.1 系统与设备

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/system/health` | Runtime 健康状态 |
| GET | `/system/capabilities` | CPU、GPU、显存、内存、磁盘、CUDA、FFmpeg |
| POST | `/system/benchmark` | 运行短基准测试 |
| GET | `/system/logs` | 获取脱敏用户日志 |

### 10.2 模型

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/models` | 模型列表和安装状态 |
| POST | `/models/{id}/install` | 下载 / 安装 |
| POST | `/models/{id}/verify` | 校验文件 |
| DELETE | `/models/{id}` | 卸载 |
| POST | `/models/{id}/warmup` | 预热 |

### 10.3 项目与素材

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/projects` | 项目列表 |
| POST | `/projects` | 新建项目 |
| GET | `/projects/{id}` | 项目详情 |
| PATCH | `/projects/{id}` | 更新项目 |
| DELETE | `/projects/{id}` | 删除项目 |
| POST | `/projects/{id}/assets/import` | 导入素材 |
| GET | `/assets/{id}/probe` | 音视频预检 |

### 10.4 文案

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/scripts/extract` | 从链接或视频提取文案 |
| POST | `/scripts/generate` | 从主题生成文案 |
| POST | `/scripts/rewrite` | 改写文案 |
| POST | `/scripts/check` | 敏感词和结构检查 |

### 10.5 生成任务

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/jobs/asr` | 创建 ASR 任务 |
| POST | `/jobs/tts` | 创建 TTS 任务 |
| POST | `/jobs/lipsync` | 创建对口型任务 |
| POST | `/jobs/subtitle` | 创建字幕任务 |
| POST | `/jobs/cover` | 创建封面渲染任务 |
| POST | `/jobs/export` | 创建导出任务 |
| POST | `/jobs/pipeline` | 创建完整流水线 |
| GET | `/jobs/{id}` | 查询任务 |
| POST | `/jobs/{id}/cancel` | 取消任务 |
| POST | `/jobs/{id}/retry` | 重试任务 |

### 10.6 实时事件

WebSocket：`/api/v1/events`

事件格式：

```json
{
  "event": "job.progress",
  "timestamp": "datetime",
  "data": {
    "job_id": "uuid",
    "status": "running",
    "progress": 42,
    "stage": "lipsync.render",
    "message": "正在生成第 126/300 帧",
    "eta_seconds": 95
  }
}
```

## 11. 模型 Adapter 规范

所有本地模型实现统一接口：

```python
class ModelAdapter:
    def inspect(self) -> ModelCapability: ...
    def validate_input(self, request: Request) -> ValidationResult: ...
    def prepare(self, request: Request, workspace: Path) -> PreparedInput: ...
    def run(self, prepared: PreparedInput, reporter: ProgressReporter) -> Artifact: ...
    def validate_output(self, artifact: Artifact) -> ValidationResult: ...
    def unload(self) -> None: ...
```

要求：

- Adapter 不直接修改数据库。
- Adapter 只在自己的任务工作目录写文件。
- Adapter 必须定期上报进度。
- Adapter 必须响应取消信号。
- 模型相关异常转换为统一错误码。
- 同类模型可替换，UI 不依赖具体模型实现。

## 12. 模块需求

### 12.1 设备体检

检测：

- 操作系统和版本。
- CPU、内存、磁盘。
- NVIDIA GPU、显存、驱动、CUDA。
- FFmpeg / ffprobe。
- Python Runtime。
- 模型文件。

输出档位：

| 档位 | 条件 | 默认策略 |
| --- | --- | --- |
| 不支持 | 无可用 GPU 或磁盘不足 | 只允许文案和素材管理 |
| 最低 | RTX 3060 12GB / 16GB RAM | 快速档、限制并发 |
| 推荐 | RTX 4070/4080 / 32GB RAM | 标准档 |
| 高质量 | RTX 4090 24GB / 64GB RAM | 高质量档和批量 |

验收：

- 设备问题必须给出中文建议。
- 不允许只显示 Python traceback。
- 体检结果可导出为诊断 JSON。

### 12.2 模型管理

需求：

- 模型清单包含版本、下载地址、SHA-256、体积、最低显存。
- 支持断点下载。
- 下载后自动校验。
- 支持镜像下载地址。
- 模型损坏时允许重新校验和修复。
- 模型更新不得自动删除旧模型。

### 12.3 抖音文案提取

支持输入：

- 手机分享文本中的短链。
- `douyin.com/video/{id}`。
- `douyin.com/jingxuan?modal_id={id}`。
- 用户页中带 `modal_id` 的链接。
- 本地视频文件。

处理顺序：

```text
规范化输入
  -> 提取 URL
  -> 识别 URL 类型
  -> 解析视频元数据 / 获取可用媒体
  -> 获取已有字幕
  -> 无字幕则本地 ASR
```

兜底：

- 在线链接失败时提示用户导入本地视频。
- 不把“解析失败”和“LLM 改写失败”合并成一个错误。
- 解析器应插件化，平台规则变化时可单独更新。

验收：

- 测试集中的四种链接格式均可识别。
- 不支持的链接在 5 秒内返回明确错误。
- 解析失败不会导致 App 崩溃。

### 12.4 LLM 文案

支持：

- OpenAI-compatible API。
- 自定义 Base URL、模型名、API Key。
- 连接测试。
- 文案生成、改写、标题、话题、CTA。
- Prompt 参数：目标人群、时长、口吻、领域、禁用词。
- 输出 JSON Schema 校验。

安全：

- API Key 本地加密。
- 日志中只显示 Key 后四位。
- Prompt 缓存不得包含 Key。

验收：

- API 失败区分 401、429、超时、格式错误。
- 输出不符合 Schema 时自动修复一次。
- 用户可查看和编辑最终文案。

### 12.5 ASR 和字幕识别

输入：

- wav、mp3、m4a、mp4。
- 自动转为标准 PCM。

输出：

- 原文。
- 分句。
- 每句开始 / 结束时间。
- 可选词级时间戳。
- 语言和置信度。

要求：

- 中文默认输出简体。
- 支持用户用原始文案做强制对齐，减少错字。
- 低置信度句子在 UI 标记。

验收：

- 手机录制音频可自动转码。
- 字幕可导出 SRT 和 ASS。
- 预览与导出字幕内容一致。

### 12.6 TTS / 声音克隆

输入：

- 文案。
- 授权声音样本。
- 语速、停顿、情绪、音量。

预处理：

- 自动裁剪长静音。
- 检测噪声和音量。
- 转为模型所需采样率。
- 样本过短、过长或无人声时阻止任务。

生成策略：

- 文案先分段。
- 每段独立生成。
- 单段失败可重试。
- 最终拼接时保留可配置停顿。

验收：

- 30 秒文案能生成完整音频。
- 生成期间可取消。
- 不出现参考产品反馈中的音频 18 秒后重新播放问题。
- 输出音频可被 ffprobe 正常读取。

### 12.7 视频对口型

输入预检：

- 视频可解码。
- 帧率、分辨率和旋转信息正确。
- 至少检测到一个稳定人脸。
- 音频可解码。
- 音频时长和视频循环策略明确。

MVP 策略：

- 30 秒以内单段处理。
- 视频短于音频时默认循环，但必须让用户确认。
- 保留原视频色彩空间和帧顺序。
- 音频和视频输出时长误差 ≤ 100ms。

长视频策略：

- V1 将音频按句子或固定时长分段。
- 每段独立生成。
- 合并时做边界过渡检查。

验收：

- 不允许只显示“排队中”而无进度。
- Worker 能报告准备、抽帧、推理、合成四个阶段。
- 取消后 10 秒内释放 GPU 进程。
- 生成视频无黑屏、倒放、严重掉帧。

### 12.8 字幕排版

支持：

- 字体、字号、颜色、描边、阴影、背景。
- 位置和安全区。
- 每行最大字数。
- 最大行数。
- 逐句编辑。
- 单句重新对齐。
- 开关字幕。

导出前检查：

- 字幕是否超出安全区。
- 是否存在无法显示的字体。
- 是否存在空字幕或时间重叠。
- 预览分辨率和导出分辨率使用同一套排版计算。

验收：

- 第一条字幕和后续字幕使用同一换行规则。
- 预览和导出截图像素级位置误差 ≤ 2px。
- 默认模板不出现文字超出 9:16 画面。

### 12.9 封面

支持：

- 视频关键帧选择。
- 导入人物图、背景图、产品图。
- 标题、副标题、贴纸。
- 文字拖拽、缩放、旋转、对齐。
- 保存模板。
- 9:16、1:1、16:9。

验收：

- 封面预览和导出一致。
- 文字不超出安全区。
- 可关闭封面生成。
- 标题可由 LLM 生成后手动修改。

### 12.10 视频导出

默认输出：

- 容器：MP4。
- 视频：H.264。
- 音频：AAC。
- 分辨率：1080x1920。
- 帧率：沿用源视频或统一 25/30fps。
- 音频采样率：48kHz。

导出流水线：

```text
验证所有输入
  -> 统一帧率 / 旋转 / 色彩空间
  -> 合成音频
  -> 烧录或外挂字幕
  -> 合成 BGM / 画中画
  -> 编码
  -> ffprobe 校验
  -> 质量检查
```

验收：

- 最终视频可在 Windows、Chrome、手机播放器打开。
- 不出现黑屏、灰白、无声、音画不同步。
- 导出失败保留 FFmpeg 命令和脱敏日志。

### 12.11 质量检查

MVP 检查：

- 输出文件存在。
- 视频和音频流存在。
- 时长差。
- 黑帧比例。
- 音量过低或削波。
- 字幕溢出。
- 分辨率和旋转。
- 首尾静音。

V1 检查：

- 唇形同步评分。
- 人脸遮挡。
- 画面闪烁。
- 字幕置信度。
- 封面安全区。

质量结果：

```json
{
  "passed": false,
  "score": 72,
  "issues": [
    {
      "code": "SUBTITLE_OVERFLOW",
      "severity": "error",
      "message": "第 12 条字幕超出右侧安全区",
      "suggestion": "减小字号或增加每行字数限制"
    }
  ]
}
```

## 13. 错误码

| 错误码 | 场景 | 用户提示 |
| --- | --- | --- |
| `SYSTEM_GPU_UNAVAILABLE` | 无可用 GPU | 当前设备不支持视频模型，可继续使用文案功能 |
| `SYSTEM_DISK_INSUFFICIENT` | 空间不足 | 至少需要 X GB 可用空间 |
| `MODEL_MISSING` | 模型未安装 | 请先安装对应模型 |
| `MODEL_CHECKSUM_FAILED` | 模型损坏 | 模型校验失败，请重新下载 |
| `SOURCE_URL_UNSUPPORTED` | 链接不支持 | 请更换链接或导入本地视频 |
| `SOURCE_EXTRACT_FAILED` | 平台解析失败 | 无法获取视频，请下载后本地导入 |
| `LLM_UNAUTHORIZED` | API Key 错误 | API Key 无效，请检查配置 |
| `LLM_RATE_LIMITED` | API 限流 | 请求过于频繁，请稍后重试 |
| `AUDIO_FORMAT_INVALID` | 音频无法解码 | 将自动尝试转码；仍失败时请更换文件 |
| `VOICE_SAMPLE_INVALID` | 样本不合格 | 声音样本过短、噪声过大或无人声 |
| `FACE_NOT_FOUND` | 未检测到人脸 | 请上传正面、清晰、无遮挡的人物视频 |
| `LIPSYNC_OOM` | 显存不足 | 请使用快速档、降低分辨率或关闭其他程序 |
| `JOB_INTERRUPTED` | App 异常退出 | 上次任务被中断，可从当前阶段重试 |
| `EXPORT_FFMPEG_FAILED` | 导出失败 | 视频合成失败，已保存诊断日志 |
| `SUBTITLE_OVERFLOW` | 字幕超出画面 | 请调整字号、位置或换行 |

## 14. 安全与合规

- API Key 必须使用系统安全存储或本地加密文件。
- 日志不得出现完整 API Key、用户隐私文本或绝对路径中的用户名。
- 声音克隆前要求确认拥有授权。
- 肖像生成前要求确认拥有授权。
- 提供 AI 生成标识 / 水印开关。
- 记录素材来源和授权确认时间。
- 禁止内置冒充公众人物、诈骗、伪造证据等模板。
- 商业发布前逐一复核模型代码和权重许可证。

## 15. 性能与资源要求

### 15.1 性能目标

| 项目 | RTX 3060 12GB | RTX 4090 24GB |
| --- | ---: | ---: |
| 30 秒 ASR | ≤ 60 秒 | ≤ 20 秒 |
| 30 秒 TTS | ≤ 90 秒 | ≤ 30 秒 |
| 30 秒对口型 | ≤ 12 分钟 | ≤ 6 分钟 |
| 30 秒字幕与导出 | ≤ 3 分钟 | ≤ 1.5 分钟 |
| 完整流水线 | ≤ 18 分钟 | ≤ 9 分钟 |

以上为 MVP 目标值，最终以选定模型 benchmark 为准。

### 15.2 资源控制

- 默认同一时间只运行一个 GPU 重任务。
- ASR、TTS、对口型可配置是否常驻显存。
- 模型切换时主动卸载旧模型。
- 显存不足前先做估算，不直接启动高质量任务。
- Worker 退出后检查并清理子进程。

## 16. 测试计划

### 16.1 单元测试

- URL 规范化和链接类型识别。
- 任务状态机。
- 文案分段。
- 字幕换行和安全区计算。
- 错误映射。
- 配置加密和日志脱敏。

### 16.2 集成测试

- FFmpeg 转码、抽帧、拼接、导出。
- ASR Adapter。
- TTS Adapter。
- LipSync Adapter。
- 模型下载和校验。
- 取消任务和进程回收。
- App 重启后任务恢复。

### 16.3 Golden Samples

仓库必须保存一套可合法使用的测试样例：

- 10 秒普通话音频。
- 30 秒普通话音频。
- 10 秒正面人物视频。
- 30 秒正面人物视频。
- 横屏、竖屏、带旋转 metadata 的视频。
- 手机录制 mp3/m4a。
- 无人脸、多人脸、遮挡人脸视频。
- 长字幕、英文字幕、中英文混合字幕。

Golden 测试记录：

- 产物是否可播放。
- 时长。
- 分辨率。
- 黑帧比例。
- 音量。
- 字幕是否溢出。
- 耗时和峰值显存。

### 16.4 硬件矩阵

MVP 最少覆盖：

- Windows 10 + RTX 3060 12GB。
- Windows 11 + RTX 4070/4080。
- Windows 11 + RTX 4090。

V1 增加：

- macOS Apple Silicon。
- 集成显卡 / 无 NVIDIA GPU 的降级模式。

## 17. 开发阶段

### 阶段 0：技术验证，3-5 天

目标：只验证模型与音视频链路。

任务：

- [ ] FFmpeg 预检和转码。
- [ ] ASR Demo。
- [ ] CosyVoice Demo。
- [ ] MuseTalk / 候选对口型 Demo。
- [ ] 30 秒端到端脚本。
- [ ] RTX 3060 / 4090 benchmark。
- [ ] 开源许可证初筛。

退出条件：

- 30 秒视频可完整生成。
- 输出无黑屏、无倒放、可播放。
- 记录耗时、显存、已知问题。

### 阶段 1：桌面骨架，3-5 天

- [ ] Electron + React 工程。
- [ ] Python Runtime 启停。
- [ ] `/system/health`。
- [ ] SQLite 初始化。
- [ ] 项目和素材导入。
- [ ] 任务列表和 WebSocket 事件。

### 阶段 2：文案与音频，3-5 天

- [ ] LLM 配置。
- [ ] 文案生成和改写。
- [ ] 抖音链接规范化。
- [ ] 本地 ASR 兜底。
- [ ] 声音样本预检。
- [ ] TTS 分段生成和试听。

### 阶段 3：对口型与字幕，5-8 天

- [ ] 视频预检。
- [ ] 对口型 Adapter。
- [ ] 进度和 ETA。
- [ ] 取消和进程回收。
- [ ] 字幕识别、编辑、样式。
- [ ] 字幕溢出检查。

### 阶段 4：封面、导出与质量检查，4-6 天

- [ ] 视频抽帧。
- [ ] 封面模板编辑。
- [ ] FFmpeg 导出。
- [ ] 黑帧、音量、时长、字幕检查。
- [ ] 中文错误诊断。
- [ ] Windows 安装包。

MVP 总周期目标：2-4 周。

## 18. Definition of Done

一个模块只有同时满足以下条件才算完成：

- 接口实现并有类型定义。
- 常见错误映射为统一错误码。
- 长任务支持进度和取消。
- 输出产物经过校验。
- 有单元或集成测试。
- 有一条 Golden Sample 通过记录。
- 日志已脱敏。
- 文档中记录模型版本和许可证。
- Windows RTX 3060 12GB 与 RTX 4090 至少验证一个档位。

## 19. MVP 总验收

- [ ] 用户安装后可完成设备体检。
- [ ] 缺失模型可下载、校验和修复。
- [ ] 用户可输入主题或导入视频生成文案。
- [ ] 抖音链接失败时可通过本地视频 ASR 兜底。
- [ ] 手机音频可自动转码并用于声音克隆。
- [ ] 30 秒人物视频可完成本地对口型。
- [ ] 任务展示真实阶段、进度和 ETA。
- [ ] 任务可取消，GPU 进程能释放。
- [ ] 字幕可编辑且预览与导出一致。
- [ ] 封面可使用视频帧并编辑文字。
- [ ] MP4 可在电脑和手机播放器正常播放。
- [ ] 导出视频无黑屏、倒放、发灰和明显音画不同步。
- [ ] App 重启后可看到旧任务和中间产物。
- [ ] API Key 未出现在日志中。

## 20. 开发前待确认

1. MVP 是否只支持 Windows，还是必须同步支持 macOS。
2. 对口型 MVP 首选 MuseTalk、VideoReTalking 还是其他模型。
3. 最低显卡要求是否坚持 RTX 3060 12GB。
4. 抖音链接解析是否允许集成下载器，还是只支持用户导入本地视频。
5. MVP 是否需要 BGM、画中画和多平台自动发布。
6. LLM API 首发需要支持哪些供应商。
7. 是否需要用户登录、授权码和离线许可证。
8. 模型文件由安装包附带、首次启动下载，还是用户自行配置。
