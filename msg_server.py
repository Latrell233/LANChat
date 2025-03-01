from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import socket
import json
import threading
from typing import Callable, Optional
from rich import print as rprint

app = FastAPI()

# 允许跨域（用于后续前端集成）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageBroadcaster:
    BROADCAST_PORT = 25896  # 固定的广播接收端口

    def __init__(self):
        self.running = False
        self.receive_callback: Optional[Callable] = None
        
        # 创建UDP socket用于接收广播
        self.receive_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receive_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.receive_sock.bind(('', self.BROADCAST_PORT))
        
        # 创建UDP socket用于发送广播
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        rprint(f"[green]✓[/green] 消息广播服务启动在端口 {self.BROADCAST_PORT}")

    def start(self, callback: Callable):
        """启动广播服务"""
        self.running = True
        self.receive_callback = callback
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
    def stop(self):
        """停止广播服务"""
        self.running = False
        self.receive_sock.close()
        self.send_sock.close()
        
    def broadcast(self, message: dict):
        """广播消息"""
        try:
            data = json.dumps(message).encode('utf-8')
            self.send_sock.sendto(data, ('<broadcast>', self.BROADCAST_PORT))
        except Exception as e:
            rprint(f"[red]广播消息失败: {e}[/red]")
            
    def _receive_loop(self):
        """接收消息循环"""
        while self.running:
            try:
                data, addr = self.receive_sock.recvfrom(4096)
                message = json.loads(data.decode('utf-8'))
                if self.receive_callback:
                    self.receive_callback(message, addr)
            except Exception as e:
                if self.running:
                    rprint(f"[red]接收消息错误: {e}[/red]")

broadcaster = MessageBroadcaster()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # 广播接收到的消息
            await broadcaster.broadcast(data, websocket)
    except Exception as e:
        print(f"WebSocket连接错误: {e}")
    finally:
        broadcaster.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)