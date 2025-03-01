import pyaudio
import asyncio
import websockets

from fastapi import FastAPI, WebSocket
from typing import Dict, Set, Optional

app = FastAPI()

# 音频参数配置
CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000

class VoiceChatService:
    def __init__(self):
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        self._audio = pyaudio.PyAudio()
        self._input_stream: Optional[pyaudio.Stream] = None
        self._output_stream: Optional[pyaudio.Stream] = None
        self._is_streaming = False

    def start_streaming(self):
        """启动音频流"""
        self._input_stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        self._output_stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK
        )
        self._is_streaming = True

    def stop_streaming(self):
        """停止音频流"""
        self._is_streaming = False
        if self._input_stream:
            self._input_stream.stop_stream()
            self._input_stream.close()
        if self._output_stream:
            self._output_stream.stop_stream()
            self._output_stream.close()
        self._audio.terminate()

    async def connect(self, websocket: WebSocket, room_id: str):
        """处理新的WebSocket连接"""
        await websocket.accept()
        if room_id not in self._active_connections:
            self._active_connections[room_id] = set()
        self._active_connections[room_id].add(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        """处理WebSocket断开连接"""
        if room_id in self._active_connections:
            self._active_connections[room_id].remove(websocket)
            if not self._active_connections[room_id]:
                del self._active_connections[room_id]

    async def broadcast(self, audio_data: bytes, room_id: str, sender: WebSocket):
        """广播音频数据到房间内其他用户"""
        if room_id in self._active_connections:
            for connection in self._active_connections[room_id]:
                if connection != sender:
                    try:
                        await connection.send_bytes(audio_data)
                    except Exception:
                        continue
    async def connect_voice_chat(server_ip, port, room_id):
        # 创建 WebSocket 连接
        uri = f"ws://{server_ip}:{port}/voice/ws/{room_id}"
        
        async with websockets.connect(uri) as websocket:
            print(f"已连接到语音聊天室: {room_id}")
            
            # 初始化音频
            audio = pyaudio.PyAudio()
            input_stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=8000,
                input=True,
                frames_per_buffer=256
            )
            output_stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=8000,
                output=True,
                frames_per_buffer=256
            )
            
            try:
                while True:
                    # 从麦克风读取音频数据
                    audio_data = input_stream.read(256)
                    # 发送到服务器
                    await websocket.send(audio_data)
                    
                    # 接收其他用户的音频数据
                    received_data = await websocket.recv()
                    # 播放接收到的音频
                    output_stream.write(received_data)
                    
            except KeyboardInterrupt:
                print("正在断开连接...")
            finally:
                input_stream.stop_stream()
                input_stream.close()
                output_stream.stop_stream()
                output_stream.close()
                audio.terminate()

# 创建全局语音服务实例
voice_service = VoiceChatService()

@app.websocket("/ws/{room_id}")
async def voice_chat_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket端点处理语音通信"""
    await voice_service.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_bytes()
            await voice_service.broadcast(data, room_id, websocket)
    except Exception:
        voice_service.disconnect(websocket, room_id)