import argparse
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
import socket
import uuid
import signal
import sys
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()
discovery_service = None  # Global variable to store service instance

class DiscoveryService:
    def __init__(self, service_name, port, local_ip):
        self.zeroconf = Zeroconf()
        self.service_name = service_name
        self.port = port
        self.local_ip = local_ip
        self._devices = []  # 改用下划线前缀的私有变量
        self.info = None
        self.browser = None
        # Add service type definition
        self.service_type = "_lanchat._tcp.local."

    @property
    def devices(self):
        """获取发现的设备列表"""
        return self._devices

    def get_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
        
    def start_advertising(self):
        """Start advertising this service on the network"""
        try:
            self.info = ServiceInfo(
                self.service_type,
                f"{self.service_name}.{self.service_type}",
                addresses=[socket.inet_aton(self.local_ip)],  # Use self.local_ip instead
                port=self.port,
                properties={'version': '1.0'},
            )
            self.zeroconf.register_service(self.info)
            print(f"✅ 服务已注册: {self.service_name} ({self.local_ip}:{self.port})")
        except Exception as e:
            print(f"❌ 服务注册失败: {e}")

    def start_discovery(self):
        """Start discovering other services"""
        try:
            self.browser = ServiceBrowser(self.zeroconf, self.service_type, self)
            print("✅ 服务发现已启动")
        except Exception as e:
            print(f"❌ 服务发现启动失败: {e}")
        
    def add_service(self, zeroconf, type_, name):
        info = zeroconf.get_service_info(type_, name)
        if info:
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            
            # 过滤掉链路本地地址和本机地址
            if ip.startswith("169.254.") or (ip == self.local_ip and port == self.port):
                return
                
            device = {
                "name": name,
                "ip": ip,
                "port": port
            }
            if device not in self._devices:
                self._devices.append(device)
                print(f"[DISCOVERY] 新设备加入: {name} ({ip}:{port})")
                print(f"[STATUS] 当前已发现设备数量: {len(self._devices)}")

    def remove_service(self, zeroconf, type_, name):
        self._devices = [d for d in self._devices if d["name"] != name]
        print(f"[DISCOVERY] 设备离开: {name}")
        print(f"[STATUS] 当前已发现设备数量: {len(self._devices)}")

    def update_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info:
            updated_device = {
                "name": name.split(".")[0],
                "ip": socket.inet_ntoa(info.addresses[0]),
                "port": info.port
            }
            for device in self.devices:
                if device["name"] == updated_device["name"]:
                    device.update(updated_device)
                    self.add_device(updated_device["name"], updated_device["ip"], updated_device["port"])
                    print(f"[UPDATE] 设备信息已更新: {device['name']} ({device['ip']}:{device['port']})")
                    break

    def unregister_service(self):
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()
        print(f"[UNREGISTER] 本机服务已注销: {self.service_name}")

    def stop(self):
        """停止服务发现和广播"""
        self._is_running = False
        if self.browser:
            self.browser.cancel()
        if self.info:
            self.zeroconf.unregister_service(self.info)
        self.zeroconf.close()
        print("✅ 服务发现已停止")

    def add_device(self, name: str, ip: str, port: int):
        """Add discovered device"""
        self.discovered_devices[name] = {
            "name": name,
            "ip": ip,
            "port": port
        }
        
    def remove_device(self, name: str):
        """Remove device when it leaves"""
        if name in self.discovered_devices:
            del self.discovered_devices[name]

def signal_handler(signal, frame, discovery):
    print("\n[EXIT] 正在退出程序...")
    discovery.unregister_service()
    sys.exit(0)

def initialize_discovery(service: DiscoveryService):
    """Initialize the discovery service for the API endpoints"""
    global discovery_service
    discovery_service = service

if __name__ == "__main__":
    # 解析命令行参数（可选）
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="服务端口（可选）")
    args = parser.parse_args()

    # 启动服务
    discovery = DiscoveryService(args.port)
    discovery.start_advertising()
    discovery.start_discovery()

    # 注册信号处理函数
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, discovery))
    signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, discovery))

    print("按 Ctrl+C 或关闭终端退出程序...")
    input("按回车键退出...\n")
    discovery.unregister_service()

# Add FastAPI router for device discovery
@router.get("/devices")
async def get_devices():
    """Get all discovered devices"""
    if discovery_service is None:
        return {"error": "Discovery service not initialized"}
    return discovery_service.devices