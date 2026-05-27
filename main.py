# main.py
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.switch import Switch
import threading
import socket
import struct
import random
import time
import requests
import os

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

class ByeByeDPIPro(App):
    def build(self):
        self.bypass = TLSBypass()
        self.doh = DoHResolver()
        self.active = False
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=5)
        
        self.status = Label(
            text="Статус: Остановлен\nTLS обход: выкл",
            size_hint_y=0.15,
            font_size='16sp'
        )
        layout.add_widget(self.status)
        
        switch_box = BoxLayout(size_hint_y=0.1)
        switch_label = Label(text="Активировать обход:", size_hint_x=0.6)
        self.switch = Switch(active=False)
        self.switch.bind(active=self.toggle_bypass)
        switch_box.add_widget(switch_label)
        switch_box.add_widget(self.switch)
        layout.add_widget(switch_box)
        
        methods_label = Label(
            text="Методы: Фрагментация | Split | Fake | TFO | DoH",
            size_hint_y=0.08,
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        layout.add_widget(methods_label)
        
        test_btn = Button(
            text="Проверить YouTube / Discord / Roblox",
            size_hint_y=0.1
        )
        test_btn.bind(on_press=self.test_connectivity)
        layout.add_widget(test_btn)
        
        self.log_text = Label(
            text="Лог:\nГотов к работе",
            size_hint_y=0.5,
            halign='left',
            valign='top',
            font_size='12sp'
        )
        self.log_text.bind(size=self.log_text.setter('text_size'))
        layout.add_widget(self.log_text)
        
        return layout
    
    def toggle_bypass(self, instance, value):
        if value:
            success = self.bypass.start_bypass()
            if success:
                self.active = True
                self.status.text = "Статус: АКТИВЕН\nФрагментация + Split + Fake + TFO"
                self.log("Обход запущен.")
            else:
                self.switch.active = False
                self.log("Ошибка запуска.")
        else:
            self.bypass.stop_bypass()
            self.active = False
            self.status.text = "Статус: Остановлен\nTLS обход: выкл"
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
    ByeByeDPIPro().run()
