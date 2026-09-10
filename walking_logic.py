# walking_logic.py
import random
import math

class WalkingEngine:
    def __init__(self, start_lat, start_lon, speed_kmh=6.0, interval=4):
        # 記憶最初的起點，並建立內部高精度座標變數
        self.current_lat = float(start_lat)
        self.current_lon = float(start_lon)
        
        self.speed_kmh = speed_kmh
        self.interval = interval
        
        # 隨機生成一個初始方向角度 (弧度)
        self.angle = random.uniform(0, 2 * math.pi)
        
        # 計算基礎步進長度
        self.update_speed(speed_kmh)

    def update_speed(self, new_speed):
        """根據時速更新標準位移長度"""
        self.speed_kmh = new_speed
        # (時速 / 3.6) * 間隔時間 / 地球緯度一度的距離
        self.move_step = (new_speed / 3.6) * self.interval / 111320

    def change_direction(self, degree):
        """旋轉角度 (正數為右轉，負數為左轉)"""
        self.angle += math.radians(degree)
        self.angle = self.angle % (2 * math.pi)

    def get_next_step(self):
        """完全由內部座標累加，不接收外部帶入的 lat, lon，徹底避免精度淹沒"""
        # 加上微幅的真人抖動
        jitter = random.uniform(0.98, 1.02)
        current_step = self.move_step * jitter
        
        # 計算本次位移量
        dir_lat = current_step * math.cos(self.angle)
        dir_lon = current_step * math.sin(self.angle)
        
        # 內部高精度變數直接累加，不經過外部 round() 破壞精度
        self.current_lat += dir_lat
        self.current_lon += dir_lon
        
        # 回傳給主程式發送用的格式 (限制在小數點後 6 位)
        return round(self.current_lat, 6), round(self.current_lon, 6)