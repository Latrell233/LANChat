import argparse
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
import socket
import uuid
import signal
import sys

class DiscoveryService:
    def __init__(self, service_name, port, local_ip):
        self.devices = []
        self.zeroconf = Zeroconf()
        self.service_type = "_lanmsg._tcp.local."
        # 自动生成设备名称，基于主机名和随机后缀
        # hostname = socket.gethostname()
        # self.service_name = f"{hostname}_{uuid.uuid4().hex[:4]}"
        self.service_name = service_name
        self.port = port
        self.local_ip = local_ip
        self.port = port if port else self.get_free_port()
        self.service_info = None
        
    def get_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
        
    def start_advertising(self):
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        self.service_info = ServiceInfo(
            self.service_type,
            f"{self.service_name}.{self.service_type}",
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={'version': '1.0'},
        )
        self.zeroconf.register_service(self.service_info)
        print(f"✅ 服务已注册: {self.service_name} ({self.local_ip}:{self.port})")        
    def start_discovery(self):
        browser = ServiceBrowser(self.zeroconf, self.service_type, self)
        
    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info:
            device = {
                "name": name.split(".")[0],
                "ip": socket.inet_ntoa(info.addresses[0]),
                "port": info.port
            }
            if device not in self.devices:
                self.devices.append(device)
                print(f"[DISCOVERY] 新设备加入: {device['name']} ({device['ip']}:{device['port']})")
                print(f"[STATUS] 当前已发现设备数量: {len(self.devices)}")
        
    def remove_service(self, zeroconf, service_type, name):
        device_name = name.split(".")[0]
        # 查找并移除设备
        self.devices = [device for device in self.devices if device["name"] != device_name]
        print(f"[DISCOVERY] 设备离开: {device_name}")
        print(f"[STATUS] 当前已发现设备数量: {len(self.devices)}")

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
                    print(f"[UPDATE] 设备信息已更新: {device['name']} ({device['ip']}:{device['port']})")
                    break

    def unregister_service(self):
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()
        print(f"[UNREGISTER] 本机服务已注销: {self.service_name}")

def signal_handler(signal, frame, discovery):
    print("\n[EXIT] 正在退出程序...")
    discovery.unregister_service()
    sys.exit(0)

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