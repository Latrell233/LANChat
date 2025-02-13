import threading
import argparse
from discovery import DiscoveryService
from msg_server import app as message_app
from file_tsf import app as file_app
from fastapi import FastAPI
import uvicorn
import socket

# 合并多个FastAPI实例
main_app = FastAPI()
main_app.mount("/message", message_app)
main_app.mount("/file", file_app)

class ServiceController:
    def __init__(self):
        self.discovery = None
        self.service_port = None

    def run_discovery(self, port=None):
        # 获取本机IP（优先选择192.168.*）
        self.local_ip = self.get_local_ip()
        if not self.local_ip:
            raise RuntimeError("无法获取有效的局域网IP，请检查网络连接")
        
        # 动态获取端口
        self.service_port = port or self.get_free_port()
        
        # 初始化发现服务
        self.discovery = DiscoveryService(
            service_name=f"LANChat_{self.service_port}",  # 唯一服务名
            port=self.service_port,
            local_ip=self.local_ip
        )
        self.discovery.start_advertising()
        self.discovery.start_discovery()
        print(f"✅ 服务已启动在 {self.local_ip}:{self.service_port}")

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

if __name__ == "__main__":
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
    uvicorn.run(
        main_app, 
        host="0.0.0.0", 
        port=controller.service_port,  # 使用统一端口
        log_level="debug"
    )