# LANChat - Local Network Chat Application

## 简介 / Introduction
一款基于 Python 开发的局域网即时通讯工具，支持自动设备发现、文字聊天、语音通话和文件传输功能。
A Python-based LAN instant messaging tool with automatic device discovery, text chat, voice calls, and file transfer capabilities.

## 功能特点 / Features
- 🔍 自动发现：自动发现并显示局域网内其他在线设备
- 💬 文字聊天：基于 UDP 广播的群聊功能
- 🎤 语音通话：支持多人实时语音聊天，可创建独立语音房间
- 📁 文件传输：支持点对点文件传输
- 🌐 跨平台：支持 Windows、Linux 等多个平台

## 系统要求 / Requirements
- Python >= 3.7
- 操作系统 / OS: Windows, Linux
- 网络：设备需在同一局域网内

## 安装步骤 / Installation

### 1. 下载代码 / Download Code
```bash
git clone https://github.com/your-username/LANChat.git
cd LANChat
```

### 2. 创建虚拟环境 / Create Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖 / Install Dependencies
```bash
pip install -r requirements.txt
```

## 使用说明 / Usage Guide

### 启动程序 / Start Application
```bash
python main.py [--port PORT]
```

### 可用命令 / Available Commands
- `/help` - 显示帮助信息
- `/devices` - 显示在线设备列表
- `/chat` - 进入群聊模式
- `/voice` - 创建并加入语音房间
- `/join <room_id>` - 加入指定语音房间
- `/upload <file_path> [-n]` - 上传文件
  - 不带参数：手动选择目标设备
  - `-n`: 选择第 n 个在线设备
- `/download <file_name>` - 下载文件
- `/quit` 或 `/exit` - 退出程序

### 功能说明 / Feature Details

#### 1. 文字聊天 / Text Chat
- 使用 `/chat` 进入群聊
- 输入用户名后自动加入聊天室
- 所有在线用户都能收到消息
- 使用 `/quit` 退出聊天

#### 2. 语音通话 / Voice Chat
- 使用 `/voice` 创建新语音房间
- 使用 `/join <room_id>` 加入已有房间
- 支持多个语音房间独立运行
- 按 Ctrl+C 退出语音通话

#### 3. 文件传输 / File Transfer
- 上传文件：`/upload <file_path> [-n]`
- 下载文件：`/download <filename>`
- 支持自动选择目标设备
- 显示传输进度和状态

## 项目结构 / Project Structure
```
LANChat/
├── main.py          # 主程序入口
├── discovery.py     # 设备发现服务
├── msg_server.py    # 消息广播服务
├── voice_chat.py    # 语音通话服务
├── file_tsf.py      # 文件传输服务
├── commands.py      # 命令处理器
└── requirements.txt # 依赖项列表
```

## 常见问题 / Troubleshooting
1. 设备无法发现
   - 确保设备在同一局域网
   - 检查防火墙设置
   - 验证网络连接状态

2. 语音通话问题
   - 检查麦克风权限
   - 确认音频设备可用
   - 验证 PyAudio 安装正确

3. 文件传输失败
   - 检查文件权限
   - 确认目标路径可写
   - 验证网络连接稳定

## 开发说明 / Development Notes
- 使用 FastAPI 构建 Web 服务
- 采用 UDP 广播实现群聊
- WebSocket 实现语音通话
- HTTP 实现文件传输
- Zeroconf 实现设备发现

## License
MIT License

