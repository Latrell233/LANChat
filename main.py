import threading
import argparse
from discovery import DiscoveryService, router as discovery_router, initialize_discovery
from msg_server import app as message_app
from file_tsf import app as file_app
from fastapi import FastAPI
import uvicorn
import socket
import re
from voice_chat import app as voice_app, voice_service

# 合并多个FastAPI实例
main_app = FastAPI()
main_app.mount("/message", message_app)
main_app.mount("/file", file_app)
main_app.mount("/voice", voice_app)
main_app.include_router(discovery_router, prefix="/discovery")

class ServiceController:
    def __init__(self):
        self.discovery = None
        self.service_port = None
        self.voice_service = voice_service

    def run_discovery(self, port=None):
        # 获取本机IP（优先选择192.168.*）
        self.local_ip = self.get_local_ip()
        if not self.local_ip:
            raise RuntimeError("无法获取有效的局域网IP，请检查网络连接")
        
        # 动态获取端口
        self.service_port = port or self.get_free_port()
        
        # 初始化发现服务
        self.discovery = DiscoveryService(
            f"LANChat_{self.service_port}",
            self.service_port,
            self.local_ip
        )
        # Initialize the discovery service for API endpoints
        initialize_discovery(self.discovery)
        # Start the service
        self.discovery.start_advertising()
        self.discovery.start_discovery()
        print(f"✅ 服务已启动在 {self.local_ip}:{self.service_port}")
        
        # 启动语音服务
        self.voice_service.start_streaming()

    @staticmethod
    def get_local_ip():
        """获取本机局域网IP（优先选择192.168.*）"""
        try:
            hostname = socket.gethostname()
            ip_list = socket.gethostbyname_ex(hostname)[2]
            for ip in ip_list:
                if ip.startswith("192.168."):
                    return ip
            return ip_list[0] if ip_list else None
        except Exception as e:
            print(f"⚠️ 获取IP失败: {e}")
            return None

    @staticmethod
    def get_free_port():
        """动态获取空闲端口"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def cleanup(self):
        """清理资源"""
        try:
            if self.discovery:
                self.discovery.stop()
        except Exception as e:
            print(f"⚠️ 停止发现服务时出错: {e}")
        
        try:
            self.voice_service.stop_streaming()
        except Exception as e:
            print(f"⚠️ 停止语音服务时出错: {e}")
    

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════╗
║             LANChat 局域网聊天工具             ║
╚════════════════════════════════════════════════╝

功能说明:
1. 消息服务
   - WebSocket通信: ws://<IP>:<PORT>/message/ws
   - 支持实时文字聊天

2. 文件传输
   - 上传文件: http://<IP>:<PORT>/file/upload
   - 下载文件: http://<IP>:<PORT>/file/download/<filename>

3. 设备发现
   - 自动发现局域网内其他LANChat设备
   - 实时显示在线设备状态
   
4. 语音通信
   - WebSocket通信: ws://<IP>:<PORT>/voice/ws/<room_id>
   - 支持多人实时语音聊天
   - 使用房间ID隔离不同的语音通道

使用方法:
- 按Ctrl+C可退出程序
- 使用--port参数可指定端口号
""")
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="指定服务端口（可选）")
    args = parser.parse_args()

    # 初始化控制器
    controller = ServiceController()
    
    # 启动发现服务线程
    discovery_thread = threading.Thread(
        target=controller.run_discovery,
        kwargs={"port": args.port}
    )
    discovery_thread.daemon = True
    discovery_thread.start()
    
    # 等待端口确定
    while not controller.service_port:
        pass
    
    # 启动主服务
    print(f"🌐 主服务监听端口: {controller.service_port}")
    
    # 创建命令处理器
    from commands import CommandHandler
    cmd_handler = CommandHandler(controller.local_ip, controller.service_port)
    
    # 启动服务器
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(
            main_app, 
            host="0.0.0.0", 
            port=controller.service_port,
            log_level="info"
        )
    )
    server_thread.daemon = True
    server_thread.start()
    
    # 交互式命令行界面
    try:
        while True:
            cmd = input("\n>>> ").strip()
            if not cmd:
                continue
                
            if cmd.startswith("/"):
                cmd = cmd[1:]
                
            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "help":
                cmd_handler.show_help()
            elif cmd == "chat":  # 新增聊天命令
                cmd_handler.boardcast_start_chat()
            elif cmd == "devices":
                cmd_handler.show_online_devices()
            elif cmd == "voice":
                cmd_handler.create_voice_room()
            elif cmd.startswith("join "):
                room_id = cmd.split(" ", 1)[1]
                cmd_handler.join_voice_room(room_id)
            elif cmd.startswith("upload "):
                parts = cmd.split(" ")
                if len(parts) > 2:
                    # 处理带设备参数的情况
                    file_path = parts[1]
                    target_param = parts[2]
                    cmd_handler.upload_file(file_path, target_param)
                else:
                    # 普通上传
                    file_path = parts[1]
                    cmd_handler.upload_file(file_path)
            elif cmd.startswith("download "):
                file_name = cmd.split(" ", 1)[1]
                source = Prompt.ask("请输入源设备的IP:端口")
                cmd_handler.download_file(file_name, source)
            else:
                print("未知命令，输入 /help 查看帮助")
    
    except KeyboardInterrupt:
        print("\n正在退出...")
    finally:
        controller.cleanup()