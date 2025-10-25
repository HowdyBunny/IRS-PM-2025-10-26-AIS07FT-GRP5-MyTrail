# Whisper Flask 服务

该项目基于 Flask 和 Hugging Face Transformers，加载目录中的已微调 Whisper 模型，并通过 REST API 对上传音频进行转写。

## 本地文件结构

- `whisper-en-finetuned/`：微调好的 Whisper 模型目录（已提供）
- `app.py`：Flask 应用入口，提供 `/health` 和 `/transcribe` 两个端点
- `requirements.txt`：Python 依赖
- `Dockerfile`：生成可部署镜像

## 构建与运行（Docker）

```bash
docker build -t whisper-flask .
docker run --rm -p 5000:5000 whisper-flask
```

镜像中已安装 `libsox-fmt-mp3`、`ffmpeg` 与 `libsndfile1`，服务在解码不支持的格式时会自动调用 `ffmpeg` 转换，因此可直接处理常见的 MP3/WAV 等音频格式。

容器启动后，服务暴露在 `http://localhost:5000`。

## API 调用示例

### 健康检查

```bash
curl http://localhost:5000/health
```

### 转写音频

```bash
curl -X POST \
     -F "file=@/path/to/audio.wav" \
     -F "language=en" \
     -F "task=transcribe" \
     http://localhost:5000/transcribe
```

请求参数说明：

- `file`（必填）：音频文件，支持常见格式（wav、mp3 等）
- `language`（可选）：ISO-639-1 语言码，例如 `en`、`zh`。为空时使用模型默认语言。
- `task`（可选）：`transcribe`（默认）或 `translate`。

返回结果示例：

```json
{
  "language": "en",
  "task": "transcribe",
  "text": "hello world"
}
```

## 本地直接运行（非容器）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export WHISPER_MODEL_DIR=whisper-en-finetuned
python app.py
```

默认监听 `0.0.0.0:5000`。
