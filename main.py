import customtkinter as ctk
import subprocess
import threading
import time
import re
import os
import sys
import random  # 確保導入 random 以利散步間隔使用
from walking_logic import WalkingEngine # 引用你的新子程式類別

# 設定主題
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TeleportApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 基礎設定
        self.title("iOS 一鍵飛人 PRO - V3.0")
        self.geometry("650x650") # 增加高度以容納新控制項
        
        # 路徑初始化 (解決檔案找不到的問題)
        self.base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.target_file_path = os.path.join(self.base_path, "targets.txt")
        
        self.rsd_ip = None
        self.port = None
        self.targets = self.load_targets()
        self.is_walking = False  # 增加一個變數來控制是否停止散步

        # --- 介面佈局 ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 左側清單欄
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="📍 地點收藏", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=20)

        if self.targets:
            self.target_list = ctk.CTkOptionMenu(self.sidebar, values=[t['name'] for t in self.targets])
            self.target_list.pack(pady=10, padx=20)
        else:
            self.err_label = ctk.CTkLabel(self.sidebar, text="找不到 targets.txt", text_color="red")
            self.err_label.pack(pady=10)

        # 右側主控制區
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.status_label = ctk.CTkLabel(self.main_frame, text="狀態: 🟡 正在初始化隧道...", text_color="yellow")
        self.status_label.pack(pady=10)

        # 立即傳送按鈕
        self.btn_teleport = ctk.CTkButton(self.main_frame, text="🚀 立即傳送", command=self.start_teleport, height=60, font=("Microsoft JhengHei", 18, "bold"))
        self.btn_teleport.pack(pady=20, padx=20, fill="x")

        # 「種花散步」按鈕
        self.btn_walk = ctk.CTkButton(self.main_frame, text="🌸 開始種花散步", 
                                      command=self.start_walking_thread, 
                                      fg_color="#2ecc71", hover_color="#27ae60",
                                      height=40, font=("Microsoft JhengHei", 16))
        self.btn_walk.pack(pady=10, padx=20, fill="x")

        # --- 速度控制區 ---
        self.speed_label = ctk.CTkLabel(self.main_frame, text="速度: 6.0 km/h")
        self.speed_label.pack(pady=(10, 0))
        
        self.speed_slider = ctk.CTkSlider(self.main_frame, from_=1, to=20, number_of_steps=19, command=self.update_speed_event)
        self.speed_slider.set(6)
        self.speed_slider.pack(pady=5, padx=20, fill="x")

        # --- 轉向控制區 (可輸入角度) ---
        self.turn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.turn_frame.pack(pady=10)

        self.angle_label = ctk.CTkLabel(self.turn_frame, text="設定轉向角度:")
        self.angle_label.grid(row=0, column=0, columnspan=2, pady=2)

        self.angle_entry = ctk.CTkEntry(self.turn_frame, width=80, placeholder_text="45")
        self.angle_entry.insert(0, "45") 
        self.angle_entry.grid(row=1, column=0, columnspan=2, pady=5)

        self.btn_left = ctk.CTkButton(self.turn_frame, text="⬅️ 左轉", width=100, command=lambda: self.manual_turn_event("left"))
        self.btn_left.grid(row=2, column=0, padx=5, pady=5)

        self.btn_right = ctk.CTkButton(self.turn_frame, text="右轉 ➡️", width=100, command=lambda: self.manual_turn_event("right"))
        self.btn_right.grid(row=2, column=1, padx=5, pady=5)

        self.log_box = ctk.CTkTextbox(self.main_frame, height=200, font=("Consolas", 12))
        self.log_box.pack(pady=10, padx=20, fill="both", expand=True)

        # 類別變數初始化
        self.engine = None

        # 啟動背景隧道偵測
        self.init_thread = threading.Thread(target=self.init_tunnel, daemon=True)
        self.init_thread.start()

    def load_targets(self):
        targets = []
        if os.path.exists(self.target_file_path):
            with open(self.target_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "," in line:
                        p = line.split(",")
                        if len(p) >= 3:
                            name = p[0].strip()
                            lat = p[1].replace('－', '-').strip()
                            lon = p[2].replace('－', '-').strip()
                            targets.append({"name": name, "lat": lat, "lon": lon})
        return targets

    def log(self, msg):
        self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see("end")

    def init_tunnel(self):
        try:
            self.log("🔑 正在掛載裝置 (auto-mount)...")
            subprocess.run('pymobiledevice3 mounter auto-mount', shell=True, capture_output=True)
            self.log("🔍 啟動隧道服務...")
            proc = subprocess.Popen('pymobiledevice3 remote tunneld', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True, bufsize=1)
            for line in iter(proc.stdout.readline, ''):
                match = re.search(r'--rsd ([\w:]+) (\d+)', line)
                if match:
                    self.rsd_ip = match.group(1)
                    self.port = match.group(2)
                    self.status_label.configure(text=f"狀態: 🟢 隧道就緒 (Port: {self.port})", text_color="lightgreen")
                    self.log(f"✅ 連線成功! IP: {self.rsd_ip}")
                    break
        except Exception as e:
            self.log(f"❌ 發生異常: {str(e)}")

    def start_teleport(self):
        if not self.rsd_ip:
            self.log("⚠️ 請等待隧道連線完成...")
            return
        if not self.targets:
            self.log("⚠️ 座標清單為空，請檢查 targets.txt")
            return
        target_name = self.target_list.get()
        target = next(t for t in self.targets if t['name'] == target_name)
        
        def run():
            self.btn_teleport.configure(state="disabled", text="傳送中...")
            lat = str(target['lat']).strip()
            lon = str(target['lon']).strip()
            self.log(f"📍 目標: {target_name} ({lat}, {lon})")
            cmd = f'pymobiledevice3 developer dvt simulate-location set --rsd {self.rsd_ip} {self.port} -- {lat} {lon}'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                self.log(f"✨ 傳送成功！")
            else:
                self.log(f"❌ 指令錯誤內容: {res.stderr}")
            self.btn_teleport.configure(state="normal", text="🚀 立即傳送")
        threading.Thread(target=run).start()

    def update_speed_event(self, value):
        self.speed_label.configure(text=f"速度: {value:.1f} km/h")
        if self.engine and self.is_walking:
            self.engine.update_speed(value)
            self.log(f"⚡ 速度調整為: {value:.1f} km/h")

    def manual_turn_event(self, side):
        if self.engine and self.is_walking:
            try:
                raw_angle = float(self.angle_entry.get())
                final_angle = -raw_angle if side == "left" else raw_angle
                self.engine.change_direction(final_angle)
                side_text = "left" if side == "left" else "right"
                self.log(f"🔄 轉向成功：向{side_text}轉 {raw_angle}°")
            except ValueError:
                self.log("⚠️ 錯誤：角度請輸入數字！")
        else:
            self.log("⚠️ 請先啟動散步模式再進行轉向")

    def start_walking_thread(self):
        if not self.rsd_ip:
            self.log("⚠️ 請等待隧道連線完成...")
            return
        if self.is_walking:
            self.is_walking = False
            self.btn_walk.configure(text="🌸 開始種花散步", fg_color="#2ecc71")
            self.log("🛑 停止散步。")
        else:
            self.is_walking = True
            self.btn_walk.configure(text="🛑 停止散步", fg_color="#e74c3c")
            threading.Thread(target=self.run_walking_logic, daemon=True).start()

    def run_walking_logic(self):
        try:
            target_name = self.target_list.get()
            target = next(t for t in self.targets if t['name'] == target_name)
            curr_lat = float(target['lat'])
            curr_lon = float(target['lon'])

            initial_speed = self.speed_slider.get()
            # 🌟 修改點：初始化引擎時，直接把起始座標塞進去，讓它內部自我管理
            self.engine = WalkingEngine(start_lat=curr_lat, start_lon=curr_lon, speed_kmh=initial_speed, interval=4)
        
            self.log(f"🚶 載入外部引擎... 時速: {self.engine.speed_kmh} km/h")

            while self.is_walking:
                # 🌟 修改點：呼叫時不再傳入參數，避免 round() 後的數據破壞底層精度
                curr_lat, curr_lon = self.engine.get_next_step()
                
                cmd = f'pymobiledevice3 developer dvt simulate-location set --rsd {self.rsd_ip} {self.port} -- {curr_lat} {curr_lon}'
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log(f"👣 步進中: {curr_lat}, {curr_lon}")
                time.sleep(self.engine.interval)

        except Exception as e:
            self.log(f"❌ 子程式呼叫失敗: {str(e)}")
            self.is_walking = False
            self.btn_walk.configure(text="🌸 開始種花散步", fg_color="#2ecc71")

if __name__ == "__main__":
    app = TeleportApp()
    app.mainloop()