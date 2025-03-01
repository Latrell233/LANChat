import click
import requests
import websockets
import asyncio
import json
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import print as rprint
import pyperclip
from voice_chat import VoiceChatService
from rich.prompt import Prompt
import threading
from msg_server import MessageBroadcaster  
import re

console = Console()

class CommandHandler:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_base_url = f"ws://{host}:{port}"
        self.chat_task = None
        self.username = None
        try:
            self.message_broadcaster = MessageBroadcaster()  # 不再需要指定端口
        except Exception as e:
            rprint(f"[red]初始化消息广播器失败: {e}[/red]")
            raise

    async def ws_handle_chat(self):
        """处理聊天消息"""
        uri = f"{self.ws_base_url}/message/ws"
        async with websockets.connect(uri) as ws:
            rprint("[green]✓[/green] 已连接到聊天室")
            # 接收消息的任务
            async def receive_messages():
                while True:
                    try:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        rprint(f"\n[bold blue]{data['username']}[/bold blue]: {data['message']}")
                        print(">>> ", end='', flush=True)
                    except Exception as e:
                        rprint(f"[red]接收消息错误: {e}[/red]")
                        break

            # 发送消息的任务
            async def send_messages():
                while True:
                    try:
                        message = await asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: input(">>> ")
                        )
                        if message.lower() in ['/quit', '/exit']:
                            break
                        # 发送消息时包含用户名
                        await ws.send_json({
                            "username": self.username,
                            "message": message
                        })
                    except Exception as e:
                        rprint(f"[red]发送消息错误: {e}[/red]")
                        break

            try:
                # 发送加入聊天室的通知
                await ws.send_json({
                    "username": "system",
                    "message": f"{self.username} 加入了聊天室"
                })
                
                # 并行运行收发消息
                await asyncio.gather(
                    receive_messages(),
                    send_messages()
                )
            except Exception as e:
                rprint(f"[red]聊天室连接错误: {e}[/red]")
            finally:
                # 发送离开聊天室的通知
                try:
                    await ws.send_json({
                        "username": "system",
                        "message": f"{self.username} 离开了聊天室"
                    })
                except:
                    pass

    def boardcast_start_chat(self):
        """启动聊天客户端"""
        if not self.username:
            self.username = Prompt.ask("请输入你的用户名")
            
        def handle_message(message: dict, addr):
            username = message.get('username', 'Unknown')
            msg = message.get('message', '')
            if username != self.username:  # 不显示自己的消息
                rprint(f"\n[bold blue]{username}[/bold blue]: {msg}")
                print(">>> ", end='', flush=True)
                
        self.message_broadcaster.start(handle_message)
        rprint("[green]✓[/green] 已加入聊天室")
        
        # 发送加入通知
        self.message_broadcaster.broadcast({
            "username": "system",
            "message": f"{self.username} 加入了聊天室"
        })
        
        try:
            while True:
                message = input(">>> ")
                if message.lower() in ['/quit', '/exit']:
                    break
                    
                self.message_broadcaster.broadcast({
                    "username": self.username,
                    "message": message
                })
        finally:
            # 发送离开通知
            self.message_broadcaster.broadcast({
                "username": "system",
                "message": f"{self.username} 离开了聊天室"
            })
            self.message_broadcaster.stop()

    def show_online_devices(self):
        """显示在线设备列表"""
        try:
            response = requests.get(f"{self.base_url}/discovery/devices")
            if response.status_code == 200:
                devices = response.json()
                
                table = Table(title="在线设备")
                table.add_column("设备名称")
                table.add_column("IP地址")
                table.add_column("端口")
                
                if not devices:
                    rprint("[yellow]当前没有发现其他设备[/yellow]")
                    return
                    
                for device in devices:
                    table.add_row(
                        device['name'], 
                        device['ip'], 
                        str(device['port'])
                    )
                console.print(table)
            else:
                rprint(f"[red]获取设备列表失败: {response.status_code}[/red]")
        except Exception as e:
            rprint(f"[red]获取设备列表出错: {e}[/red]")

    def create_voice_room(self):
        """创建并加入语音房间"""
        import random
        import string
        room_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        ws_url = f"{self.ws_base_url}/voice/ws/{room_id}"
        rprint(f"[green]✓[/green] 语音房间已创建！")
        rprint(f"房间ID: {room_id}")
        rprint(f"WebSocket URL: {ws_url}")
        
        # 自动加入创建的房间
        self.join_voice_room(room_id)

    def join_voice_room(self, ws_room_url):
        """加入语音房间"""
        ws_room_url=ws_room_url.split("/")
        
        ip,port=ws_room_url[2].split(":")
        
        room_id = ws_room_url[-1]
        rprint(f"[green]✓[/green] 正在连接语音房间...")
        rprint(f"房间ID: {room_id}")
        rprint(f"WebSocket URL: {ws_room_url}")
        # 启动语音客户端
        try:
            asyncio.run(VoiceChatService.connect_voice_chat(ip, port, room_id))
        except KeyboardInterrupt:
            rprint("[yellow]已断开语音连接[/yellow]")
        except Exception as e:
            rprint(f"[red]连接语音房间失败: {e}[/red]")

    def get_target_device(self, param: str = None) -> tuple:
        """获取目标设备的IP和端口
        param: 可以是设备序号(-n)或IP:端口格式
        return: (ip, port) or None
        """
        try:
            response = requests.get(f"{self.base_url}/discovery/devices")
            if response.status_code != 200:
                rprint(f"[red]获取设备列表失败: {response.status_code}[/red]")
                return None
                
            devices = response.json()
            if not devices:
                rprint("[yellow]当前没有发现其他设备[/yellow]")
                return None
                
            # 只有一个设备时自动选择
            if len(devices) == 1:
                device = devices[0]
                rprint(f"[green]自动选择唯一在线设备: {device['ip']}:{device['port']}[/green]")
                return (device['ip'], device['port'])
                
            # 处理设备序号参数
            if param and param.startswith('-'):
                try:
                    idx = int(param[1:]) - 1
                    if 0 <= idx < len(devices):
                        device = devices[idx]
                        return (device['ip'], device['port'])
                    else:
                        rprint(f"[red]设备序号超出范围 (1-{len(devices)})[/red]")
                        return None
                except ValueError:
                    pass
            
            # 显示设备列表供选择
            table = Table(title="在线设备")
            table.add_column("序号")
            table.add_column("设备名称")
            table.add_column("IP地址")
            table.add_column("端口")
            
            for idx, device in enumerate(devices, 1):
                table.add_row(
                    str(idx),
                    device['name'],
                    device['ip'],
                    str(device['port'])
                )
            console.print(table)
            
            choice = Prompt.ask("请选择目标设备序号或输入 IP:端口")
            
            # 处理输入
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(devices):
                    device = devices[idx]
                    return (device['ip'], device['port'])
            elif ':' in choice:
                ip, port = choice.split(':')
                return (ip, int(port))
                
            rprint("[red]无效的选择[/red]")
            return None
            
        except Exception as e:
            rprint(f"[red]获取设备列表出错: {e}[/red]")
            return None

    def upload_file(self, file_path: str, target_param: str = None):
        """上传文件
        file_path: 文件路径
        target_param: 目标设备参数，可以是序号(-n)或IP:端口
        """
        try:
            target = self.get_target_device(target_param)
            if not target:
                return
                
            ip, port = target
            
            with open(file_path, "rb") as file:
                files = {"file": file}
                url = f"http://{ip}:{port}/file/upload"
                response = requests.post(url, files=files)
                
                if response.status_code == 200:
                    rprint(f"[green]✓[/green] 文件上传成功！")
                else:
                    rprint(f"[red]文件上传失败: {response.status_code}[/red]")
                    
        except FileNotFoundError:
            rprint(f"[red]文件不存在: {file_path}[/red]")
        except Exception as e:
            rprint(f"[red]文件上传出错: {e}[/red]")

    def show_help(self):
        """显示帮助信息"""
        help_table = Table(title="命令帮助")
        help_table.add_column("命令", style="cyan")
        help_table.add_column("说明")
        help_table.add_column("用法")
        
        commands = [
            ("chat", "进入群聊模式", "/chat"),
            ("voice", "创建语音房间", "/voice"),
            ("join", "加入语音房间", "/join <房间ID>"),
            ("devices", "显示在线设备", "/devices"),
            ("upload", "上传文件", "/upload <文件路径>"),
            ("download", "下载文件", "/download <文件名>"),
            ("help", "显示此帮助", "/help"),
            ("quit", "退出程序", "/quit"),
        ]
        
        for cmd, desc, usage in commands:
            help_table.add_row(cmd, desc, usage)
            
        console.print(help_table)