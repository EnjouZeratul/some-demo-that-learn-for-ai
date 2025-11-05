这是用于学习使用NEXT.JS的，将agent_emo WEB化的尝试。

如果你需要使用 请先下载我的\jiuye\Agent_demo文件夹 并且用我导出的conda环境文件正确配置环境（包括你自己的deep seek API）

在power shell中输入

```
cd D:\
mkdir jiuye_nextjs && cd jiuye_nextjs
npx create-next-app@latest agent-web --typescript --tailwind --app（一路enter默认配置即可）
cd agent-web
npm run dev
```

之后将我本地上传的文件分别对应放入D:\jiuye_nextjs\agent-web\app\page.tsx，D:\jiuye_nextjs\agent-web\app\api\chat\route.ts，D:\jiuye\Agent_demo\api_server.py 这几个路径。

随后在power shell里面进入你的配置环境

```powershell
#安装FastAPI: 

pip install fastapi uvicorn

cd D:\jiuye_nextjs\agent-web（这是我的路径 你可以根据自己的需求具体修改）

npm run dev

运行API服务器: python api_server.py
```



使用任何浏览器或可以打开网址的工具打开 http://localhost:3000/

后面的版本是整理以后更清晰的readme。以及英文的readme。



制作于2025/11/5

最后更新于2025/11/5





# AI Agent Web Demo / AI Agent 网页演示

[English](#english) | [中文](#chinese)

## <a name="english"></a>English

A web-based interface for AI Agent built with Next.js, showcasing real-time AI interactions with tool calling capabilities. This is a learning project to explore Next.js development while creating a practical AI application.

### Features
- Real-time AI chat with streaming responses
- Tool calling visualization
- Cost tracking per message
- Persistent conversation history
- Export chat logs (JSON/Markdown)

### Prerequisites
1. Download the `Agent_demo` folder from `\jiuye\Agent_demo`
2. Set up conda environment using the provided environment file
3. Configure your DeepSeek API key

### Installation

#### 1. Create Next.js Project
```powershell
cd D:\
mkdir jiuye_nextjs && cd jiuye_nextjs
npx create-next-app@latest agent-web --typescript --tailwind --app
# Press Enter for all default options
cd agent-web
```

#### 2. Setup Files

Place the provided files into these locations:

- `page.tsx` → `D:\jiuye_nextjs\agent-web\app\page.tsx`
- `route.ts` → `D:\jiuye_nextjs\agent-web\app\api\chat\route.ts`
- `api_server.py` → `D:\jiuye\Agent_demo\api_server.py`

#### 3. Start Services

```powershell
# Terminal 1: Backend

conda activate your_env
pip install fastapi uvicorn
cd D:\jiuye\Agent_demo
python api_server.py

# Terminal 2: Frontend

cd D:\jiuye_nextjs\agent-web
npm run dev
```

### Usage

Open http://localhost:3000 in your browser.

## <a name="chinese"></a>中文

这是用于学习使用Next.js的项目，将agent_demo WEB化的尝试。通过这个项目探索了实时AI对话、工具调用可视化、成本追踪等功能的实现。

### 功能特点

- 实时AI对话与流式响应
- 工具调用可视化显示
- 每条消息的成本追踪
- 持久化对话历史
- 导出聊天记录（JSON/Markdown格式）

### 前置要求

1. 下载 `\jiuye\Agent_demo` 文件夹
2. 使用导出的conda环境文件配置环境
3. 配置你的DeepSeek API密钥

### 安装步骤

#### 1. 创建Next.js项目

```
cd D:\
mkdir jiuye_nextjs && cd jiuye_nextjs
npx create-next-app@latest agent-web --typescript --tailwind --app

# 一路Enter使用默认配置

cd agent-web
```

#### 2. 放置文件

将提供的文件分别放入以下路径：

- `page.tsx` → `D:\jiuye_nextjs\agent-web\app\page.tsx`
- `route.ts` → `D:\jiuye_nextjs\agent-web\app\api\chat\route.ts`
- `api_server.py` → `D:\jiuye\Agent_demo\api_server.py`

#### 3. 启动服务

```powershell
# 终端1：后端服务

conda activate your_env
pip install fastapi uvicorn
cd D:\jiuye\Agent_demo
python api_server.py

# 终端2：前端服务

cd D:\jiuye_nextjs\agent-web
npm run dev
```

### 使用方法

在浏览器中打开 http://localhost:3000 即可使用。