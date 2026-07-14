# ==========================================
# WebTora 起動ロゴ & 読み込みメッセージ
# ==========================================
import sys
import time

GREEN = "\033[32m"
RESET = "\033[0m"

def _wt_log(msg, delay=0.25):
    print(f"[WebTora] {msg}")
    time.sleep(delay)

def _wt_startup():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(GREEN + r"""
/  |  _  /  |          /  |    /        |                           
$$ | / \ $$ |  ______  $$ |____$$$$$$$$/______    ______   ______   
$$ |/$  \$$ | /      \ $$      \  $$ | /      \  /      \ /      \  
$$ /$$$  $$ |/$$$$$$  |$$$$$$$  | $$ |/$$$$$$  |/$$$$$$  |$$$$$$  | 
$$ $$/$$ $$ |$$    $$ |$$ |  $$ | $$ |$$ |  $$ |$$ |  $$/ /    $$ | 
$$$$/  $$$$ |$$$$$$$$/ $$ |__$$ | $$ |$$ \__$$ |$$ |     /$$$$$$$ | 
$$$/    $$$ |$$       |$$    $$/  $$ |$$    $$/ $$ |     $$    $$ | 
$$/      $$/  $$$$$$$/ $$$$$$$/   $$/  $$$$$$/  $$/       $$$$$$$/  
""" + RESET)

    _wt_log("Boot sequence start")
    _wt_log("Checking runtime environment")
    _wt_log("Loading core modules")
    _wt_log("Preparing system")

_wt_startup()




import threading
import cv2
import mediapipe as mp
import numpy as np
import time
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox  # messageboxを追加
import sys  # sysを追加 (終了用)
from flask import Flask
from pythonosc import udp_client
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math


# ==========================================
# グローバル変数
# ==========================================


osc_enabled = False      
plot_enabled = True      


# 全体の一括調整値 (3軸)
MANUAL_X_OFFSET = 0.0  # 左右
MANUAL_HEIGHT_OFFSET = 0.0  # 上下
MANUAL_Z_OFFSET = 0.0       # 前後


# 動きの滑らかさ (0.0=補正なし 〜 0.99=非常に遅いが滑らか)
SMOOTHING_FACTOR = 0.7


# 部位ごとの個別調整値
tracker_offsets = {}


# スムージング用の前回値保存用
prev_transforms = {}


# 座標データ
pose_points = [np.array([0, 0, 0], dtype=np.float32) for i in range(33)]
pose_world_points = [np.array([0, 0, 0], dtype=np.float32) for i in range(33)]
pose_virtual_points = [np.array([0, 0, 0], dtype=np.float32) for i in range(33)]


# VRC用の座標変換データ (位置 + 回転)
pose_virtual_transforms = {
    "hip":         {"path": "1", "enable": True, "label": "腰 (Hip)"},
    "right_foot":  {"path": "2", "enable": True, "label": "右足 (R Foot)"},
    "left_foot":   {"path": "3", "enable": True, "label": "左足 (L Foot)"},
    "right_knee":  {"path": "4", "enable": True, "label": "右膝 (R Knee)"},
    "left_knee":   {"path": "5", "enable": True, "label": "左膝 (L Knee)"},
    "right_elbow": {"path": "6", "enable": True, "label": "右肘 (R Elbow)"},
    "left_elbow":  {"path": "7", "enable": True, "label": "左肘 (L Elbow)"},
    "chest":       {"path": "8", "enable": True, "label": "胸 (Chest)"},
}


# 初期化
for key in pose_virtual_transforms:
    pose_virtual_transforms[key]["position"] = np.zeros(3)
    pose_virtual_transforms[key]["rotation"] = np.zeros(3) # Euler angles
    tracker_offsets[key] = np.array([0.0, 0.0, 0.0], dtype=np.float32)


# キャリブレーション関連
calibration_enabled = False
calibration_matrix = np.eye(4, dtype=np.float32)
calibration_body_length = 1.0


# しゃがみ対策・スケール関連
calib_screen_scale = 1.0  
calib_base_hip_y = 0.0    




# ==========================================
# ロジック関数
# ==========================================


def update_pose(pose_landmarks, pose_world_landmarks, image_size):
    global pose_virtual_points, pose_points, pose_world_points


    if pose_landmarks is not None:
        for i in range(33):
            landmark = pose_landmarks.landmark[i]
            world_landmark = pose_world_landmarks.landmark[i]
           
            # 画面上の座標 (2D + depth)
            pose_points[i] = np.array(
                [landmark.x - 0.5, (landmark.y - 0.5) * (image_size[1] / image_size[0]), landmark.z],
                dtype=np.float32)
           
            # 現実世界の座標 (3D metric)
            pose_world_points[i] = np.array([world_landmark.x, world_landmark.y, world_landmark.z], dtype=np.float32)


        if calibration_enabled:
            # 1. 回転行列を適用して体の向きを補正
            pose_virtual_points = [calibration_matrix @ np.append(pose_world_points[i], 1.0) for i in range(33)]
           
            # 2. しゃがみ検知と高さ補正
            current_screen_hip_y = (pose_points[23][1] + pose_points[24][1]) / 2.0
            diff_screen_y = current_screen_hip_y - calib_base_hip_y
            height_offset = diff_screen_y * calib_screen_scale
           
            # 全身のポイントを一律に下げる
            for i in range(33):
                pose_virtual_points[i][1] -= height_offset


            # 3. 体の長さ補正 (スケール合わせ)
            modify_virtual_pose()
        else:
            pose_virtual_points = [np.asarray(pose_world_points[i]) for i in range(33)]


        update_virtual_pose()


def modify_virtual_pose():
    def _get_xyz(arr):
        a = np.asarray(arr)
        return a[:3].astype(np.float32) if a.size >= 3 else np.zeros(3, dtype=np.float32)


    chest = (_get_xyz(pose_virtual_points[11]) + _get_xyz(pose_virtual_points[12])) / 2
    hip = (_get_xyz(pose_virtual_points[23]) + _get_xyz(pose_virtual_points[24])) / 2
   
    body_vector = hip - chest
    body_length = np.linalg.norm(body_vector)
   
    if body_length == 0: return


    global calibration_body_length
    body_differential_length = calibration_body_length - body_length
    body_modify_length = (body_vector / body_length) * body_differential_length


    # 上半身の基準に合わせて下半身を伸ばす/縮める
    for i in range(23, 33):
        a = np.asarray(pose_virtual_points[i])
        if a.size >= 3:
            a3 = a[:3] + body_modify_length
            if a.size == 3:
                pose_virtual_points[i] = a3
            else:
                pose_virtual_points[i] = np.concatenate([a3, a[3:4]], axis=0)


def calculate_yaw_from_points(left_pt, right_pt):
    """
    左右の点の位置関係から、Y軸周りの回転(Yaw)を計算する
    """
    # X軸とZ軸の差分を取得
    dx = right_pt[0] - left_pt[0] # 左から右へのベクトル
    dz = right_pt[2] - left_pt[2]
   
    # arctan2で角度を計算 (ラジアン -> 度)
    angle = math.degrees(math.atan2(dz, dx))
   
    # 補正: VRChatではトラッカーが正面を向いているとき、Y回転は0や180になる
    return -angle


def update_virtual_pose():
    def _get_xyz(p):
        a = np.asarray(p)
        return a[:3].astype(np.float32) if a.size >= 3 else np.zeros(3, dtype=np.float32)


    # --- 位置の更新 ---
    r_hip = _get_xyz(pose_virtual_points[24])
    l_hip = _get_xyz(pose_virtual_points[23])
    pose_virtual_transforms["hip"]["position"] = (r_hip + l_hip) / 2.0


    r_shoulder = _get_xyz(pose_virtual_points[12])
    l_shoulder = _get_xyz(pose_virtual_points[11])
    pose_virtual_transforms["chest"]["position"] = (r_shoulder + l_shoulder) / 2.0


    pose_virtual_transforms["left_elbow"]["position"]  = _get_xyz(pose_virtual_points[13])
    pose_virtual_transforms["right_elbow"]["position"] = _get_xyz(pose_virtual_points[14])
    pose_virtual_transforms["left_knee"]["position"]   = _get_xyz(pose_virtual_points[25])
    pose_virtual_transforms["right_knee"]["position"]  = _get_xyz(pose_virtual_points[26])
    pose_virtual_transforms["left_foot"]["position"]   = _get_xyz(pose_virtual_points[27])
    pose_virtual_transforms["right_foot"]["position"]  = _get_xyz(pose_virtual_points[28])


    # --- 回転(ねじれ)の更新 ---
    # 腰のねじれ (左腰 -> 右腰)
    hip_yaw = calculate_yaw_from_points(l_hip, r_hip)
    pose_virtual_transforms["hip"]["rotation"] = np.array([0, hip_yaw, 0], dtype=np.float32)


    # 胸のねじれ (左肩 -> 右肩)
    chest_yaw = calculate_yaw_from_points(l_shoulder, r_shoulder)
    pose_virtual_transforms["chest"]["rotation"] = np.array([0, chest_yaw, 0], dtype=np.float32)


def update_calibration_parameter():
    global calibration_enabled, calibration_body_length, calibration_matrix
    global calib_screen_scale, calib_base_hip_y


    calibration_enabled = True
    print("Calibration: Executing...")


    calibration_body_length = np.linalg.norm(
        (pose_world_points[11] + pose_world_points[12]) / 2 - (pose_world_points[23] + pose_world_points[24]) / 2)


    screen_body_len = np.linalg.norm(
        (pose_points[11] + pose_points[12]) / 2 - (pose_points[23] + pose_points[24]) / 2)
   
    if screen_body_len > 0:
        calib_screen_scale = calibration_body_length / screen_body_len
    else:
        calib_screen_scale = 1.0
   
    calib_base_hip_y = (pose_points[23][1] + pose_points[24][1]) / 2.0


    top_point = (pose_world_points[7] + pose_world_points[8]) / 2
    bottom_point = (pose_world_points[29] + pose_world_points[30]) / 2


    y_axis = np.array([0, 1, 0], dtype=np.float32)
    vec = top_point - bottom_point
    norm = np.linalg.norm(vec)
    if norm == 0: return


    y_slop = vec / norm
    y_slop_cos = y_axis @ y_slop
    y_slop_axis = np.cross(y_slop, y_axis)
    y_slop_sin = np.linalg.norm(y_slop_axis)
   
    if y_slop_sin > 0:
        y_slop_axis /= y_slop_sin


    ys_x, ys_y, ys_z = y_slop_axis
    ys_c = y_slop_cos
    ys_s = y_slop_sin
    ys_t = 1.0 - ys_c


    y_slop_mat = np.eye(4, dtype=np.float32)
    y_slop_mat[:3, :3] = np.array([
        [ys_t * ys_x * ys_x + ys_c, ys_t * ys_x * ys_y - ys_s * ys_z, ys_t * ys_x * ys_z + ys_s * ys_y],
        [ys_t * ys_x * ys_y + ys_s * ys_z, ys_t * ys_y * ys_y + ys_c, ys_t * ys_y * ys_z - ys_s * ys_x],
        [ys_t * ys_x * ys_z - ys_s * ys_y, ys_t * ys_y * ys_z + ys_s * ys_x, ys_t * ys_z * ys_z + ys_c]
    ], dtype=np.float32)


    modify_coordination_system_mat = np.eye(4, dtype=np.float32)
    modify_coordination_system_mat[0, 0] = -1


    calibration_matrix = modify_coordination_system_mat @ y_slop_mat
    print("Calibration: Done.")


def delayed_calibration():
    time.sleep(3)
    update_calibration_parameter()




# ==========================================
# OSC送信 & スムージング処理
# ==========================================


vrchat_client = udp_client.SimpleUDPClient("127.0.0.1", 9000)


def apply_smoothing(key, target_pos, target_rot):
    global prev_transforms
   
    if not np.isfinite(target_pos).all():
        if key in prev_transforms:
            return prev_transforms[key]["position"], prev_transforms[key]["rotation"]
        else:
            return target_pos, target_rot


    if key not in prev_transforms:
        prev_transforms[key] = {
            "position": target_pos,
            "rotation": target_rot
        }
        return target_pos, target_rot


    prev_pos = prev_transforms[key]["position"]
    prev_rot = prev_transforms[key]["rotation"]
   
    alpha = SMOOTHING_FACTOR
   
    # 位置の補間
    smoothed_pos = prev_pos * alpha + target_pos * (1.0 - alpha)
   
    # 回転の補間 (単純線形補間)
    smoothed_rot = prev_rot * alpha + target_rot * (1.0 - alpha)
   
    prev_transforms[key]["position"] = smoothed_pos
    prev_transforms[key]["rotation"] = smoothed_rot


    return smoothed_pos, smoothed_rot


def send_pose_to_vrchat():
    if not osc_enabled:
        return


    for key, value in pose_virtual_transforms.items():
        if not value["enable"]: continue


        raw_pos = value["position"]
        raw_rot = value["rotation"]
       
        # 1. スムージング処理
        smoothed_pos, smoothed_rot = apply_smoothing(key, raw_pos, raw_rot)


        # 2. オフセット適用
        final_pos = smoothed_pos.copy()
       
        # 全体補正 (X, Y, Z)
        final_pos[0] += MANUAL_X_OFFSET       # 左右
        final_pos[1] += MANUAL_HEIGHT_OFFSET # 上下
        final_pos[2] += MANUAL_Z_OFFSET       # 前後


        # 個別補正
        if key in tracker_offsets:
            offset = tracker_offsets[key]
            final_pos[0] += offset[0]
            final_pos[1] += offset[1]
            final_pos[2] += offset[2]


        # 回転データ (度数法)
        rot_send = smoothed_rot.tolist()


        try:
            vrchat_client.send_message(f"/tracking/trackers/{value['path']}/position", final_pos.tolist())
            vrchat_client.send_message(f"/tracking/trackers/{value['path']}/rotation", rot_send)
        except:
            pass


def run_analyze_pose():
    mp_pose = mp.solutions.pose
    cap = cv2.VideoCapture(0)


    # MediaPipe設定
    with mp_pose.Pose(
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as pose:
       
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                time.sleep(0.01)
                continue


            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = pose.process(image)


            if results.pose_landmarks and results.pose_world_landmarks:
                update_pose(results.pose_landmarks, results.pose_world_landmarks, (image.shape[0], image.shape[1]))
                send_pose_to_vrchat()
           
            if not threading.main_thread().is_alive():
                break


    cap.release()




# ==========================================
# Flask (Web)
# ==========================================


app = Flask(__name__)


@app.route('/connect')
def calibration_mode():
    threading.Thread(target=delayed_calibration).start()
    return "OK: Calibration starting in 3s."


def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)




# ==========================================
# GUI (Tkinter)
# ==========================================


class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WebTora(Demo)")
        self.root.geometry("600x980") # 少し高さを広げました


        # ウィンドウを閉じるイベント(Xボタン)をフック
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


        # --- メインフレーム ---
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)


        # 1. コントロール
        ctrl_frame = ttk.LabelFrame(main_frame, text="メイン操作", padding=10)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)


        self.btn_osc = tk.Button(ctrl_frame, text="OSC通信を開始 (Web URLを開く)",
                                 bg="#cccccc", font=("Helvetica", 11, "bold"),
                                 command=self.toggle_osc_and_open_web)
        self.btn_osc.pack(fill=tk.X, pady=2)
       
        self.btn_calib = tk.Button(ctrl_frame, text="再キャリブレーション (直立で3秒待機)",
                                   bg="#17a2b8", fg="white", font=("Helvetica", 11),
                                   command=self.start_calibration)
        self.btn_calib.pack(fill=tk.X, pady=2)


        # --- 追加: プログラム終了ボタン ---
        self.btn_exit = tk.Button(ctrl_frame, text="プログラム終了",
                                  bg="#dc3545", fg="white", font=("Helvetica", 11, "bold"),
                                  command=self.on_closing)
        self.btn_exit.pack(fill=tk.X, pady=(10, 2))
        # ---------------------------------


        self.lbl_calib_status = ttk.Label(ctrl_frame, text="", foreground="red")
        self.lbl_calib_status.pack()


        # 2. トラッカー有効化
        trackers_frame = ttk.LabelFrame(main_frame, text="トラッカー ON/OFF", padding=10)
        trackers_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)


        self.tracker_vars = {}
        idx = 0
        for key, info in pose_virtual_transforms.items():
            var = tk.BooleanVar(value=True)
            self.tracker_vars[key] = var
            cb = tk.Checkbutton(trackers_frame, text=info["label"], variable=var,
                                command=lambda k=key: self.update_tracker_enable(k))
            row = idx // 2
            col = idx % 2
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            idx += 1


        # 3. 全体設定・位置調整 (3軸対応)
        global_adj_frame = ttk.LabelFrame(main_frame, text="全体の設定・位置調整", padding=10)
        global_adj_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)


        self.scale_smooth = tk.Scale(global_adj_frame, from_=0.0, to=0.95, resolution=0.01,
                                     orient=tk.HORIZONTAL, label="動きの滑らかさ", command=self.update_smoothing)
        self.scale_smooth.set(SMOOTHING_FACTOR)
        self.scale_smooth.pack(fill=tk.X, pady=(0, 10))


        # --- 位置調整スライダー群 ---
        self.scale_x = tk.Scale(global_adj_frame, from_=-2.0, to=2.0, resolution=0.01,
                                orient=tk.HORIZONTAL, label="左右 (X) オフセット", command=self.update_offsets)
        self.scale_x.set(0.0)
        self.scale_x.pack(fill=tk.X)


        self.scale_h = tk.Scale(global_adj_frame, from_=-2.0, to=2.0, resolution=0.01,
                                orient=tk.HORIZONTAL, label="上下 (Y) オフセット", command=self.update_offsets)
        self.scale_h.set(0.0)
        self.scale_h.pack(fill=tk.X)


        self.scale_z = tk.Scale(global_adj_frame, from_=-2.0, to=2.0, resolution=0.01,
                                orient=tk.HORIZONTAL, label="前後 (Z) オフセット", command=self.update_offsets)
        self.scale_z.set(0.0)
        self.scale_z.pack(fill=tk.X)


        # 4. 個別の位置調整
        detail_frame = ttk.LabelFrame(main_frame, text="部位ごとの微調整", padding=10)
        detail_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)


        self.target_tracker_key = tk.StringVar()
        tracker_labels = [pose_virtual_transforms[k]["label"] for k in pose_virtual_transforms]
        self.label_to_key = {v["label"]: k for k, v in pose_virtual_transforms.items()}
       
        self.cb_selector = ttk.Combobox(detail_frame, textvariable=self.target_tracker_key, values=tracker_labels, state="readonly")
        if tracker_labels:
            self.cb_selector.current(0)
        self.cb_selector.pack(fill=tk.X, pady=5)
        self.cb_selector.bind("<<ComboboxSelected>>", self.on_tracker_selected)


        self.detail_scale_x = tk.Scale(detail_frame, from_=-0.5, to=0.5, resolution=0.01, orient=tk.HORIZONTAL, label="左右調整", command=self.on_detail_slide)
        self.detail_scale_x.pack(fill=tk.X)
        self.detail_scale_y = tk.Scale(detail_frame, from_=-0.5, to=0.5, resolution=0.01, orient=tk.HORIZONTAL, label="上下調整", command=self.on_detail_slide)
        self.detail_scale_y.pack(fill=tk.X)
        self.detail_scale_z = tk.Scale(detail_frame, from_=-0.5, to=0.5, resolution=0.01, orient=tk.HORIZONTAL, label="前後調整", command=self.on_detail_slide)
        self.detail_scale_z.pack(fill=tk.X)


    # --- イベントハンドラ ---


    def on_closing(self):
        """プログラム終了時の確認処理"""
        if messagebox.askyesno("確認", "プログラムを終了しますか？"):
            self.root.destroy()
            sys.exit()


    def on_tracker_selected(self, event):
        label = self.cb_selector.get()
        key = self.label_to_key[label]
        offset = tracker_offsets[key]
        self.detail_scale_x.set(offset[0])
        self.detail_scale_y.set(offset[1])
        self.detail_scale_z.set(offset[2])


    def on_detail_slide(self, _=None):
        label = self.cb_selector.get()
        if not label: return
        key = self.label_to_key[label]
        tracker_offsets[key] = np.array([float(self.detail_scale_x.get()), float(self.detail_scale_y.get()), float(self.detail_scale_z.get())], dtype=np.float32)


    def update_tracker_enable(self, key):
        pose_virtual_transforms[key]["enable"] = self.tracker_vars[key].get()


    def update_offsets(self, _=None):
        global MANUAL_X_OFFSET, MANUAL_HEIGHT_OFFSET, MANUAL_Z_OFFSET
        MANUAL_X_OFFSET = float(self.scale_x.get())
        MANUAL_HEIGHT_OFFSET = float(self.scale_h.get())
        MANUAL_Z_OFFSET = float(self.scale_z.get())
   
    def update_smoothing(self, _=None):
        global SMOOTHING_FACTOR
        SMOOTHING_FACTOR = float(self.scale_smooth.get())


    def toggle_osc_and_open_web(self):
        global osc_enabled
        osc_enabled = not osc_enabled
        if osc_enabled:
            self.btn_osc.config(text="OSC通信中 (クリックで停止)", bg="#28a745", fg="white")
            url = "http://127.0.0.1:5000/connect"
            webbrowser.open(url)
        else:
            self.btn_osc.config(text="OSC通信を開始", bg="#cccccc", fg="black")


    def toggle_plot(self):
        global plot_enabled
        plot_enabled = self.var_plot.get()


    def start_calibration(self):
        self.calib_count = 3
        self.update_calib_countdown()


    def update_calib_countdown(self):
        if self.calib_count > 0:
            self.lbl_calib_status.config(text=f"計測開始まで: {self.calib_count}秒...")
            self.calib_count -= 1
            self.root.after(1000, self.update_calib_countdown)
        else:
            self.lbl_calib_status.config(text="キャリブレーション実行中...")
            update_calibration_parameter()
            self.lbl_calib_status.config(text="完了しました！", foreground="green")
            self.root.after(2000, lambda: self.lbl_calib_status.config(text=""))


    def update_plot_loop(self):
        if self.var_plot.get():
            self.ax.cla()
            self.ax.set_xlim3d(-0.8, 0.8)
            self.ax.set_ylim3d(-0.8, 0.8)
            self.ax.set_zlim3d(-0.8, 1.5)
            # 現在の位置を表示
            xs, ys, zs = [], [], []
            for k, v in pose_virtual_transforms.items():
                if not v["enable"]: continue
                p = v["position"]
                if k in prev_transforms: p = prev_transforms[k]["position"]
               
                # 全体オフセット適用後の位置を表示
                xs.append(p[0] + MANUAL_X_OFFSET)
                ys.append(p[2] + MANUAL_Z_OFFSET)
                zs.append(p[1] + MANUAL_HEIGHT_OFFSET)
               
            self.ax.scatter(xs, ys, zs, c='blue', marker='o')
            self.canvas.draw()
        self.root.after(100, self.update_plot_loop)


if __name__ == "__main__":
    t_pose = threading.Thread(target=run_analyze_pose, daemon=True)
    t_pose.start()
    t_flask = threading.Thread(target=run_flask, daemon=True)
    t_flask.start()
    root = tk.Tk()
    app_gui = AppGUI(root)
    root.mainloop()





