# Seeed Studio AI Bot (ReachyMini Chat)

这是一个基于 [Pipecat](https://github.com/pipecat-ai/pipecat) 引擎构建的实时语音交互机器人。本项目针对 Seeed Studio 进行了品牌定制，并配备了炫酷的引导页。

## 核心特性
- **实时语音交互**: 使用 Deepgram (STT)、GLM-4 (LLM) 和 Cartesia (TTS)。
- **品牌定制界面**: 已经过二次开发的 UI，包含 Seeed Studio 专属引导页。
- **高性能**: 基于 WebRTC 传输协议，提供极低延迟的对话体验。

## 快速开始

### 1. 环境准备
确保你的系统中安装了 `uv` (现代 Python 包管理器)。如果未安装，请访问 [uv 官网](https://astral.sh/uv/)。

### 2. 安装依赖
在项目根目录下执行：
```bash
uv sync
```

### 3. 配置环境变量
拷贝示例环境文件并填写你的 API Key：
```bash
cp .env.example .env
```
编辑 `.env` 文件，填入：
- `DEEPGRAM_API_KEY`
- `OPENAI_API_KEY` (或 GLM 兼容 Key)
- `OPENAI_API_BASE` (GLM 接口地址)
- `CARTESIA_API_KEY`

### 4. 运行项目
启动服务：
```bash
uv run bot.py
```
启动成功后，在浏览器访问：
[http://localhost:7860/client](http://localhost:7860/client)

## 二次开发

### 修改 UI
前端静态资源存放在 `custom_ui` 目录下。你可以修改 `custom_ui/index.html` 来调整引导页或对话界面的布局。

### 修改品牌名称
本项目包含一个 `rename_ui.py` 脚本，可快速批量修改 UI 中的品牌描述：
```bash
python3 rename_ui.py
```

## 技术架构
本项目采用模块化管道设计：
- **STT**: Deepgram
- **LLM**: GLM-4 (通过 OpenAI 兼容接口)
- **TTS**: Cartesia
- **Transport**: Daily / WebRTC
