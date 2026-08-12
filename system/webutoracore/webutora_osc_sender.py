# ==========================================
# WebTora 起動ロゴ & 読み込みメッセージ
# ==========================================
import sys
import time

GREEN = "\033[32m"
RESET = "\033[0m"

def _wt_log(msg, delay=0.25):
    print(f"[WebTora-β] {msg}")
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
import os
import subprocess
import traceback
import datetime
import importlib.metadata
import platform

# Windows Media Foundation のハードウェア変換が原因で
# 一部Webカメラが開けない環境への対策。cv2 import より前に設定する。
if sys.platform.startswith("win"):
    os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")

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

# Webカメラ設定
CAMERA_INDEX = 0
CAMERA_BACKEND_MODE = "自動 (推奨)"
CAMERA_AUTO_SEARCH = True
CAMERA_RECONNECT_REQUEST = threading.Event()
CAMERA_STOP_REQUEST = threading.Event()
camera_status_lock = threading.Lock()
camera_status = "カメラ初期化待ち"
camera_connected = False
camera_active_index = None
camera_active_backend = ""
camera_debug_info = ""

WEBTORA_VERSION = "WebTora-β 0.4.0-beta1 / booth-support-v8-auto-position"
GPT_SUPPORT_SETUP_FILENAME = "GPT_SUPPORT_SETUP.txt"
GPT_DIAGNOSTICS_FILENAME = "WEBTORA_GPT_DIAGNOSTICS.txt"

def _package_version(name):
    try:
        return importlib.metadata.version(name)
    except Exception as e:
        return f"unavailable ({type(e).__name__}: {e})"

def _support_package_root():
    # subst(W:\等)で起動中でも、元の配布ルートを返す。
    root = os.environ.get("WEBTORA_PACKAGE_ROOT", "").strip()
    if root:
        return os.path.abspath(root)
    original = os.environ.get("WEBTORA_ORIGINAL_DIR", "").strip()
    if original:
        return os.path.abspath(os.path.join(original, os.pardir))
    return os.path.abspath(os.path.join(os.getcwd(), os.pardir))

def _support_dir():
    path = os.environ.get("WEBTORA_SUPPORT_DIR", "").strip()
    if path:
        return os.path.abspath(path)
    return os.path.join(_support_package_root(), "support")

def _ai_support_dir():
    path = os.environ.get("WEBTORA_AI_DIR", "").strip()
    if path:
        return os.path.abspath(path)
    return os.path.join(_support_dir(), "AI")


def build_gpt_diagnostics_text():
    with camera_status_lock:
        status = camera_status
        connected = camera_connected
        active_index = camera_active_index
        active_backend = camera_active_backend

    mp_path = getattr(mp, "__file__", "unknown")
    pose_graph = os.path.join(
        os.path.dirname(mp_path) if mp_path and mp_path != "unknown" else "",
        "modules", "pose_landmark", "pose_landmark_cpu.binarypb")

    original_dir = os.environ.get("WEBTORA_ORIGINAL_DIR", "not set")
    package_root = os.environ.get("WEBTORA_PACKAGE_ROOT", "not set")
    lines = [
        "WebTora-β GPT diagnostics",
        "=======================",
        f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"Product version: {WEBTORA_VERSION}",
        "",
        "[Runtime]",
        f"Platform: {sys.platform}",
        f"OS platform detail: {platform.platform() if 'platform' in globals() else sys.platform}",
        f"Python: {sys.version.replace(chr(10), ' ')}",
        f"Python executable: {sys.executable}",
        f"sys.prefix: {sys.prefix}",
        f"Current working directory: {os.getcwd()}",
        f"Original WebTora directory: {original_dir}",
        f"Package root: {package_root}",
        f"Support dir: {_support_dir()}",
        f"AI support dir: {_ai_support_dir()}",
        f"WEBTORA_SUBST_ACTIVE: {os.environ.get('WEBTORA_SUBST_ACTIVE', 'not set')}",
        f"WEBTORA_SUBST_DRIVE: {os.environ.get('WEBTORA_SUBST_DRIVE', 'not set')}",
        "",
        "[Package versions]",
        f"numpy: {getattr(np, '__version__', _package_version('numpy'))}",
        f"mediapipe: {getattr(mp, '__version__', _package_version('mediapipe'))}",
        f"opencv (cv2): {getattr(cv2, '__version__', _package_version('opencv-contrib-python'))}",
        f"opencv-contrib-python distribution: {_package_version('opencv-contrib-python')}",
        f"opencv-python distribution: {_package_version('opencv-python')}",
        f"python-osc: {_package_version('python-osc')}",
        f"Flask: {_package_version('Flask')}",
        f"matplotlib: {_package_version('matplotlib')}",
        "",
        "[MediaPipe resources]",
        f"MediaPipe module path: {mp_path}",
        f"Pose graph path: {pose_graph}",
        f"Pose graph exists: {os.path.exists(pose_graph)}",
        "",
        "[Camera state]",
        f"Status: {status}",
        f"Connected flag: {connected}",
        f"Requested camera index: {CAMERA_INDEX}",
        f"Active camera index: {active_index}",
        f"Requested backend: {CAMERA_BACKEND_MODE}",
        f"Active backend: {active_backend}",
        f"Auto search: {CAMERA_AUTO_SEARCH}",
        "",
        "[Camera / MediaPipe diagnostic details]",
        camera_debug_info or "No detailed camera diagnostics have been recorded yet.",
        "",
        "",
        "[Setup markers]",
        f"v8 marker exists: {os.path.exists(os.path.join(os.getcwd(), '.webtora_setup_v8_complete'))}",
        "",
        "[Expected requirements]",
        "Python 3.10.x 64bit",
        "numpy==1.26.4",
        "mediapipe==0.10.18",
        "opencv-contrib-python==4.11.0.86",
        "python-osc==1.9.3",
        "Flask==3.1.2",
        "matplotlib==3.10.8",
        "",
        "[User note for GPT]",
        "Read support/AI/GPT_SUPPORT_SETUP.txt together with this file. Diagnose from the recorded facts first.",
        "Prefer support/REPAIR_WEBTORA.bat and support/CAMERA_TEST.bat before changing source code or global Python packages.",
    ]

    # Windows camera device enumeration is useful, but some PCs make Get-PnpDevice hang.
    # Keep it optional and time-limited so diagnostics generation itself does not freeze.
    if sys.platform.startswith("win"):
        lines.extend(["", "[Windows camera devices]"])
        try:
            ps = (
                "Get-PnpDevice | Where-Object { "
                "$_.Class -in @('Camera','Image') -or $_.FriendlyName -match 'camera|webcam' "
                "} | Select-Object -ExpandProperty FriendlyName"
            )
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=4,
                encoding="utf-8", errors="replace")
            names = [x.strip() for x in completed.stdout.splitlines() if x.strip()]
            lines.extend([f"- {name}" for name in names] or ["No camera device names returned."])
            if completed.stderr.strip():
                lines.append("PowerShell stderr: " + completed.stderr.strip())
        except Exception as e:
            lines.append(f"Device enumeration failed: {type(e).__name__}: {e}")

    return "\n".join(lines) + "\n"

def _write_last_error_log(kind, message):
    try:
        path = os.path.join(os.getcwd(), "webtora_last_error.log")
        with open(path, "a", encoding="utf-8-sig") as f:
            f.write("\n" + "=" * 72 + "\n")
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} [{kind}]\n")
            f.write(message.rstrip() + "\n")
    except Exception:
        pass

def _webtora_excepthook(exc_type, exc_value, exc_tb):
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _write_last_error_log("main-thread", text)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

def _webtora_thread_excepthook(args):
    text = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    _write_last_error_log(f"thread:{getattr(args.thread, 'name', 'unknown')}", text)
    try:
        threading.__excepthook__(args)
    except Exception:
        pass

sys.excepthook = _webtora_excepthook
if hasattr(threading, "excepthook"):
    threading.excepthook = _webtora_thread_excepthook


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

# 位置自動調節用。
# v8のトラッカー姿勢計算は変更せず、画面上の腰中心の左右移動だけを
# 全身移動量として復元する。
auto_x_tracking_enabled = False
calib_base_screen_hip_x = 0.0
auto_x_translation = 0.0
AUTO_X_SMOOTH = 0.82
AUTO_X_LIMIT = 1.5

# 最後に全身姿勢を取得できた時刻。自動調節の安全確認に使用。
last_pose_timestamp = 0.0




# ==========================================
# ロジック関数
# ==========================================


def update_pose(pose_landmarks, pose_world_landmarks, image_size):
    global pose_virtual_points, pose_points, pose_world_points, last_pose_timestamp
    global auto_x_translation


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

        last_pose_timestamp = time.time()

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

            # 4. Tポーズで記録した腰中心を基準に、左右の全身移動だけ復元する。
            # MediaPipeのworld_landmarksは腰中心基準なので、画面座標を併用する。
            # トラッカー各部位の算出式・番号・回転処理は一切変更しない。
            if auto_x_tracking_enabled:
                hip_screen = (pose_points[23] + pose_points[24]) / 2.0
                target_x = (float(hip_screen[0]) - calib_base_screen_hip_x) * calib_screen_scale
                target_x = float(np.clip(target_x, -AUTO_X_LIMIT, AUTO_X_LIMIT))
                auto_x_translation = (
                    auto_x_translation * AUTO_X_SMOOTH
                    + target_x * (1.0 - AUTO_X_SMOOTH)
                )

                for i in range(33):
                    a = np.asarray(pose_virtual_points[i], dtype=np.float32)
                    if a.size >= 3:
                        a = a.copy()
                        a[0] += auto_x_translation
                        pose_virtual_points[i] = a
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


def auto_adjust_position_from_tpose():
    """
    v8の既存キャリブレーションをそのまま使い、Tポーズ時に
    高さと左右基準だけを自動設定する。

    - 姿勢/回転: v8既存 update_calibration_parameter() を使用
    - 高さ: 足首・かかと・つま先から床面を推定してY=0へ合わせる
    - 左右: Tポーズ時の腰中心をX基準として記録し、その後の横移動を追従
    - 前後: 変更しない
    """
    global MANUAL_X_OFFSET, MANUAL_HEIGHT_OFFSET, prev_transforms
    global auto_x_tracking_enabled, calib_base_screen_hip_x, auto_x_translation

    age = time.time() - last_pose_timestamp
    if last_pose_timestamp <= 0 or age > 1.0:
        return False, "姿勢を取得できていません。頭から足先までカメラに映っているか確認してください。", None

    try:
        shoulder_l = np.asarray(pose_world_points[11], dtype=np.float32)
        shoulder_r = np.asarray(pose_world_points[12], dtype=np.float32)
        wrist_l = np.asarray(pose_world_points[15], dtype=np.float32)
        wrist_r = np.asarray(pose_world_points[16], dtype=np.float32)
        hip_l = np.asarray(pose_world_points[23], dtype=np.float32)
        hip_r = np.asarray(pose_world_points[24], dtype=np.float32)

        shoulder_center = (shoulder_l + shoulder_r) / 2.0
        hip_center = (hip_l + hip_r) / 2.0
        torso_len = float(np.linalg.norm(shoulder_center - hip_center))
        shoulder_width = float(np.linalg.norm(shoulder_l - shoulder_r))
        arm_span = float(np.linalg.norm(wrist_l - wrist_r))

        if torso_len < 0.08 or shoulder_width < 0.08:
            return False, "全身姿勢を安定して取得できませんでした。カメラから少し離れて試してください。", None

        # Tポーズ判定: 腕幅と、手首が肩付近の高さにあるかを見る。
        wrist_l_screen = pose_points[15]
        wrist_r_screen = pose_points[16]
        shoulder_l_screen = pose_points[11]
        shoulder_r_screen = pose_points[12]
        wrist_height_error = max(
            abs(float(wrist_l_screen[1] - shoulder_l_screen[1])),
            abs(float(wrist_r_screen[1] - shoulder_r_screen[1]))
        )
        if arm_span < shoulder_width * 2.0 or wrist_height_error > 0.24:
            return False, "Tポーズを確認できませんでした。両手を肩の高さまで横に広げて、もう一度STARTを押してください。", None

        # ここはv8の既存キャリブレーションをそのまま利用する。
        update_calibration_parameter()

        transformed = [
            (calibration_matrix @ np.append(np.asarray(p, dtype=np.float32), 1.0))[:3]
            for p in pose_world_points
        ]

        # 足首・かかと・つま先の6点から床の高さを推定。
        floor_y = float(np.median([float(transformed[i][1]) for i in (27, 28, 29, 30, 31, 32)]))

        MANUAL_X_OFFSET = 0.0
        MANUAL_HEIGHT_OFFSET = float(np.clip(-floor_y, -2.0, 2.0))

        hip_screen = (pose_points[23] + pose_points[24]) / 2.0
        calib_base_screen_hip_x = float(hip_screen[0])
        auto_x_translation = 0.0
        auto_x_tracking_enabled = True

        # 前回スムージング値を捨て、位置調節直後の大きな補間ズレを防ぐ。
        prev_transforms.clear()

        return True, "高さと左右位置の自動調節が完了しました。", (MANUAL_X_OFFSET, MANUAL_HEIGHT_OFFSET)
    except Exception as exc:
        return False, f"位置自動調節に失敗しました: {type(exc).__name__}: {exc}", None


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


def _set_camera_status(message, connected=False, active_index=None, backend_name=""):
    """カメラスレッドからGUIへ状態を渡す。"""
    global camera_status, camera_connected, camera_active_index, camera_active_backend
    with camera_status_lock:
        camera_status = message
        camera_connected = connected
        if active_index is not None or not connected:
            camera_active_index = active_index
        camera_active_backend = backend_name if connected else ""


def _camera_backend_candidates(mode):
    """指定モードに応じたOpenCVバックエンド候補を返す。"""
    candidates = []

    # 以前動いていた cv2.VideoCapture(0) と同じ挙動を最優先にする。
    if mode in ("自動 (推奨)", "OpenCV Auto"):
        candidates.append((cv2.CAP_ANY, "OpenCV Auto"))

    if sys.platform.startswith("win"):
        if mode in ("自動 (推奨)", "DirectShow") and hasattr(cv2, "CAP_DSHOW"):
            candidates.append((cv2.CAP_DSHOW, "DirectShow"))
        if mode in ("自動 (推奨)", "Media Foundation") and hasattr(cv2, "CAP_MSMF"):
            candidates.append((cv2.CAP_MSMF, "Media Foundation"))

    # Windows以外・未知の指定でも最低限Autoを試す。
    if not candidates:
        candidates.append((cv2.CAP_ANY, "OpenCV Auto"))

    # 重複除去
    seen = set()
    result = []
    for item in candidates:
        if item[0] not in seen:
            seen.add(item[0])
            result.append(item)
    return result


def _read_camera_frame(cap, wait_seconds, compat_profiles=False):
    """
    open 済みのカメラから有効な1フレームを取得する。
    汎用USB UVCカメラ向けに、必要なら互換性の高い映像設定も試す。
    """
    profiles = [("default", None)]
    if compat_profiles:
        profiles.extend([
            ("640x480 MJPG 30fps", (640, 480, 30, "MJPG")),
            ("1280x720 MJPG 30fps", (1280, 720, 30, "MJPG")),
            ("640x480 30fps", (640, 480, 30, None)),
        ])

    profile_notes = []
    for profile_name, settings in profiles:
        if settings is not None:
            width, height, fps, fourcc = settings
            try:
                if fourcc:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_FPS, fps)
            except Exception:
                pass

        # USBカメラは設定変更後に数フレーム失敗する場合がある。
        deadline = time.time() + wait_seconds
        while time.time() < deadline and not CAMERA_STOP_REQUEST.is_set():
            success, candidate = cap.read()
            if success and candidate is not None and getattr(candidate, "size", 0) > 0:
                return candidate, profile_name, profile_notes
            time.sleep(0.05)

        profile_notes.append(f"{profile_name}: 映像取得失敗")

    return None, None, profile_notes


def _open_camera(index, mode="自動 (推奨)", warmup_seconds=2.5, compat_profiles=True):
    """
    Webカメラを開く。
    1) 元のWebToraと同じ cv2.VideoCapture(index)
    2) Windowsでは DirectShow / Media Foundation
    3) 汎用USBカメラ用の 640x480 MJPG 等
    の順で試す。
    """
    attempts = []

    for backend, backend_name in _camera_backend_candidates(mode):
        cap = None
        try:
            if backend == cv2.CAP_ANY:
                cap = cv2.VideoCapture(index)
            else:
                cap = cv2.VideoCapture(index, backend)

            if cap is None or not cap.isOpened():
                attempts.append(f"{backend_name}: open失敗")
                if cap is not None:
                    cap.release()
                continue

            frame, profile_name, profile_notes = _read_camera_frame(
                cap,
                wait_seconds=warmup_seconds,
                compat_profiles=compat_profiles,
            )
            attempts.extend([f"{backend_name} / {x}" for x in profile_notes])

            if frame is None:
                cap.release()
                continue

            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            return cap, backend_name, profile_name, attempts

        except Exception as e:
            attempts.append(f"{backend_name}: {type(e).__name__}: {e}")
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    return None, None, None, attempts

def _camera_search_order(preferred_index, auto_search):
    """優先番号を先頭にして、必要なら0～9を自動探索する。"""
    if not auto_search:
        return [preferred_index]
    order = [preferred_index]
    order.extend(i for i in range(10) if i != preferred_index)
    return order


def run_analyze_pose():
    """
    Webカメラを解析し続ける。
    カメラ初期化とMediaPipe初期化を分離し、どちらで失敗したか診断可能にする。
    """
    global CAMERA_INDEX, camera_debug_info

    cap = None
    pose = None
    opened_index = None
    opened_mode = None
    opened_backend = None
    opened_profile = None
    consecutive_read_failures = 0
    fatal_error = False

    camera_debug_info = (
        f"Thread: started\n"
        f"OpenCV: {getattr(cv2, '__version__', 'unknown')}\n"
        f"MediaPipe: {getattr(mp, '__version__', 'unknown')}\n"
        f"Python: {sys.version.split()[0]}\n"
        f"Platform: {sys.platform}\n"
    )
    _set_camera_status("カメラスレッド起動。Webカメラを探しています...", False)

    try:
        while not CAMERA_STOP_REQUEST.is_set():
            requested_index = CAMERA_INDEX
            requested_mode = CAMERA_BACKEND_MODE
            auto_search = CAMERA_AUTO_SEARCH

            if (cap is None or not cap.isOpened() or
                    CAMERA_RECONNECT_REQUEST.is_set() or
                    opened_index != requested_index or
                    opened_mode != requested_mode):
                CAMERA_RECONNECT_REQUEST.clear()

                if cap is not None:
                    cap.release()
                    cap = None
                if pose is not None:
                    try:
                        pose.close()
                    except Exception:
                        pass
                    pose = None

                found = False
                error_notes = []
                search_order = _camera_search_order(requested_index, auto_search)

                for index in search_order:
                    if CAMERA_STOP_REQUEST.is_set():
                        break

                    _set_camera_status(f"カメラ {index} を確認中...", False)
                    test_mode = requested_mode if index == requested_index else "OpenCV Auto"
                    candidate, backend_name, profile_name, attempts = _open_camera(
                        index,
                        test_mode,
                        warmup_seconds=(1.2 if index == requested_index else 0.35),
                        compat_profiles=(index == requested_index),
                    )
                    error_notes.extend([f"#{index} {x}" for x in attempts])

                    if candidate is not None:
                        cap = candidate
                        CAMERA_INDEX = index
                        opened_index = index
                        opened_mode = requested_mode
                        opened_backend = backend_name
                        opened_profile = profile_name
                        consecutive_read_failures = 0
                        found = True
                        _set_camera_status(
                            f"カメラ接続済み: {index} / {backend_name} / {profile_name} — 姿勢AIを初期化中...",
                            True, index, backend_name)
                        camera_debug_info = (
                            f"Thread: running\n"
                            f"OpenCV: {cv2.__version__}\n"
                            f"MediaPipe: {getattr(mp, '__version__', 'unknown')}\n"
                            f"Python: {sys.version.split()[0]}\n"
                            f"Platform: {sys.platform}\n"
                            f"Runtime path: {os.getcwd()}\n"
                            f"MediaPipe module: {getattr(mp, '__file__', 'unknown')}\n"
                            f"Camera index: {index}\n"
                            f"Backend: {backend_name}\n"
                            f"Video profile: {profile_name}\n"
                            f"Auto search: {auto_search}\n"
                        )
                        print(f"Camera: index={index}, backend={backend_name}, profile={profile_name}")
                        break

                if not found:
                    _set_camera_status(
                        "Webカメラを開けません。番号・接続方式・他アプリの使用状況を確認してください。",
                        False)
                    camera_debug_info = (
                        f"Thread: running, camera open failed\n"
                        f"OpenCV: {cv2.__version__}\n"
                        f"MediaPipe: {getattr(mp, '__version__', 'unknown')}\n"
                        f"Python: {sys.version.split()[0]}\n"
                        f"Platform: {sys.platform}\n"
                        f"Preferred index: {requested_index}\n"
                        f"Mode: {requested_mode}\n"
                        f"Auto search: {auto_search}\n"
                        + "Attempts:\n- " + ("\n- ".join(error_notes) if error_notes else "no attempts recorded")
                    )
                    if error_notes:
                        print("Camera open attempts: " + " | ".join(error_notes))
                    time.sleep(2.0)
                    continue

                # カメラ接続後にMediaPipeを初期化する。
                # ここで失敗しても「カメラ停止」で上書きせず、本当の例外を残す。
                try:
                    mp_pose = mp.solutions.pose
                    pose = mp_pose.Pose(
                        model_complexity=1,
                        smooth_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5,
                    )
                except Exception as e:
                    fatal_error = True
                    tb = traceback.format_exc()
                    camera_debug_info += (
                        "\nMediaPipe initialization FAILED:\n"
                        f"{type(e).__name__}: {e}\n"
                        f"{tb}"
                    )
                    _set_camera_status(
                        "カメラ自体は接続できましたが、姿勢AI(MediaPipe)の初期化に失敗しました。診断情報をコピーしてください。",
                        False)
                    print(tb)
                    break

                _set_camera_status(
                    f"接続済み: カメラ {opened_index} / {opened_backend} / {opened_profile}",
                    True, opened_index, opened_backend)

            success, image = cap.read()
            if not success or image is None:
                consecutive_read_failures += 1
                if consecutive_read_failures >= 20:
                    _set_camera_status("映像が途切れました。自動再接続中...", False)
                    cap.release()
                    cap = None
                    if pose is not None:
                        try:
                            pose.close()
                        except Exception:
                            pass
                        pose = None
                    time.sleep(0.4)
                else:
                    time.sleep(0.02)
                continue

            consecutive_read_failures = 0

            try:
                image.flags.writeable = False
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = pose.process(image_rgb)
            except Exception as e:
                fatal_error = True
                tb = traceback.format_exc()
                camera_debug_info += (
                    "\nPose processing FAILED:\n"
                    f"{type(e).__name__}: {e}\n"
                    f"{tb}"
                )
                _set_camera_status(
                    "カメラ映像は取得できましたが、姿勢解析でエラーが発生しました。診断情報をコピーしてください。",
                    False)
                print(tb)
                break

            if results.pose_landmarks and results.pose_world_landmarks:
                update_pose(
                    results.pose_landmarks,
                    results.pose_world_landmarks,
                    (image.shape[0], image.shape[1]))
                send_pose_to_vrchat()

    except Exception as e:
        fatal_error = True
        tb = traceback.format_exc()
        camera_debug_info += (
            "\nCamera thread FAILED:\n"
            f"{type(e).__name__}: {e}\n"
            f"{tb}"
        )
        _set_camera_status(
            f"カメラ処理エラー: {type(e).__name__}: {e}",
            False)
        print(tb)
    finally:
        if pose is not None:
            try:
                pose.close()
            except Exception:
                pass
        if cap is not None:
            cap.release()

        # 本当のエラー表示を「カメラ停止」で潰さない。
        if CAMERA_STOP_REQUEST.is_set() and not fatal_error:
            _set_camera_status("カメラ停止", False)



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
        self.root.title("WebTora-β")
        self.root.geometry("680x760")
        self.root.minsize(560, 520)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._setup_style()
        self._build_scroll_area()
        self._build_header()
        self._build_main_controls()
        self._build_camera_controls()
        self._build_support_controls()
        self._build_tracker_controls()
        self._build_global_adjustments()
        self._build_detail_adjustments()

        self.root.after(200, self.update_camera_status)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Yu Gothic UI", 18, "bold"))
        style.configure("Sub.TLabel", font=("Yu Gothic UI", 9))
        style.configure("Section.TLabelframe.Label", font=("Yu Gothic UI", 10, "bold"))

    def _build_scroll_area(self):
        outer = ttk.Frame(self.root)
        outer.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.main_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        self.main_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Windows / macOS / Linux のホイールに対応。
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _on_frame_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        self.canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

    def _section(self, title):
        frame = ttk.LabelFrame(self.main_frame, text=title, padding=12, style="Section.TLabelframe")
        frame.pack(fill=tk.X, padx=14, pady=6)
        return frame

    def _build_header(self):
        header = ttk.Frame(self.main_frame, padding=(16, 14, 16, 4))
        header.pack(fill=tk.X)
        ttk.Label(header, text="WebTora-β", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Webカメラから姿勢を推定し、VRChatへOSCトラッカーを送信します。",
            style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

    def _build_main_controls(self):
        frame = self._section("かんたんセットアップ")
        ttk.Label(
            frame,
            text="① カメラ接続を確認  →  ② 位置自動調節  →  ③ OSC通信を開始",
            font=("Yu Gothic UI", 10, "bold"), wraplength=650
        ).pack(fill=tk.X, pady=(0, 10))

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)

        self.btn_calib = tk.Button(
            row, text="位置自動調節", bg="#2b8a9b", fg="white",
            font=("Yu Gothic UI", 11, "bold"), command=self.open_auto_position_dialog)
        self.btn_calib.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=7)

        self.btn_osc = tk.Button(
            row, text="OSC通信を開始", bg="#dddddd",
            font=("Yu Gothic UI", 11, "bold"), command=self.toggle_osc_and_open_web)
        self.btn_osc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), ipady=7)

        self.lbl_calib_status = ttk.Label(
            frame, text="最初の1回と、カメラや立ち位置を変えたときに位置自動調節を実行してください。")
        self.lbl_calib_status.pack(fill=tk.X, pady=(8, 0))

    def _build_camera_controls(self):
        frame = self._section("Webカメラ")

        self.lbl_camera_status = ttk.Label(
            frame, text="カメラ状態を確認中...", font=("Yu Gothic UI", 10, "bold"), wraplength=600)
        self.lbl_camera_status.pack(fill=tk.X, pady=(0, 8))

        settings = ttk.Frame(frame)
        settings.pack(fill=tk.X)
        settings.columnconfigure(3, weight=1)

        ttk.Label(settings, text="優先カメラ番号").grid(row=0, column=0, sticky="w")
        self.camera_index_var = tk.IntVar(value=CAMERA_INDEX)
        self.camera_index_spin = tk.Spinbox(
            settings, from_=0, to=9, width=5, textvariable=self.camera_index_var)
        self.camera_index_spin.grid(row=0, column=1, sticky="w", padx=(8, 18))

        ttk.Label(settings, text="接続方式").grid(row=0, column=2, sticky="w")
        self.camera_backend_var = tk.StringVar(value=CAMERA_BACKEND_MODE)
        self.camera_backend_combo = ttk.Combobox(
            settings,
            textvariable=self.camera_backend_var,
            values=["自動 (推奨)", "OpenCV Auto", "DirectShow", "Media Foundation"],
            state="readonly", width=20)
        self.camera_backend_combo.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        self.camera_auto_var = tk.BooleanVar(value=CAMERA_AUTO_SEARCH)
        ttk.Checkbutton(
            frame,
            text="指定番号で見つからない場合、カメラ0～9を自動で探す",
            variable=self.camera_auto_var).pack(anchor="w", pady=(8, 8))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)
        tk.Button(
            buttons, text="自動検出 / 再接続", bg="#3b82f6", fg="white",
            font=("Yu Gothic UI", 10, "bold"), command=self.reconnect_camera
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=4)
        ttk.Button(
            buttons, text="Windows カメラ権限", command=self.open_camera_privacy_settings
        ).pack(side=tk.LEFT, padx=(5, 0), ipady=4)
        ttk.Button(
            buttons, text="診断情報をコピー", command=self.copy_camera_diagnostics
        ).pack(side=tk.LEFT, padx=(5, 0), ipady=4)

        ttk.Label(
            frame,
            text="OBS / Discord / ブラウザ等がカメラを使用中だと開けない場合があります。",
            foreground="#666666", wraplength=600).pack(fill=tk.X, pady=(8, 0))

    def _build_support_controls(self):
        frame = self._section("トラブル解決 / GPTサポート")
        ttk.Label(
            frame,
            text=(
                "エラーが起きたら診断ファイルを作成し、support/AI の GPT_SUPPORT_SETUP.txt と一緒に"
                "利用中のGPTへ渡してください。"
            ),
            wraplength=600).pack(fill=tk.X, pady=(0, 8))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)
        tk.Button(
            buttons, text="GPTサポート用ファイルを作成", bg="#7c3aed", fg="white",
            font=("Yu Gothic UI", 10, "bold"), command=self.create_gpt_support_file
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=4)
        ttk.Button(
            buttons, text="GPT向け説明TXTを開く", command=self.open_gpt_support_setup
        ).pack(side=tk.LEFT, padx=(5, 0), ipady=4)

        ttk.Label(
            frame,
            text="アプリ自体が起動しない場合は、supportフォルダの GPT_SUPPORT.bat を実行してください。",
            foreground="#666666", wraplength=600).pack(fill=tk.X, pady=(8, 0))

    def _build_tracker_controls(self):
        frame = self._section("送信するトラッカー")

        toolrow = ttk.Frame(frame)
        toolrow.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolrow, text="すべてON", command=lambda: self.set_all_trackers(True)).pack(side=tk.LEFT)
        ttk.Button(toolrow, text="すべてOFF", command=lambda: self.set_all_trackers(False)).pack(side=tk.LEFT, padx=6)

        self.tracker_vars = {}
        grid = ttk.Frame(frame)
        grid.pack(fill=tk.X)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        for idx, (key, info) in enumerate(pose_virtual_transforms.items()):
            var = tk.BooleanVar(value=info["enable"])
            self.tracker_vars[key] = var
            cb = ttk.Checkbutton(
                grid, text=info["label"], variable=var,
                command=lambda k=key: self.update_tracker_enable(k))
            cb.grid(row=idx // 2, column=idx % 2, sticky="w", padx=8, pady=3)

    def _build_global_adjustments(self):
        frame = self._section("全体調整")

        reset_row = ttk.Frame(frame)
        reset_row.pack(fill=tk.X)
        ttk.Label(reset_row, text="体全体の位置と動きの滑らかさ").pack(side=tk.LEFT)
        ttk.Button(reset_row, text="初期値に戻す", command=self.reset_global_adjustments).pack(side=tk.RIGHT)

        self.scale_smooth = tk.Scale(
            frame, from_=0.0, to=0.95, resolution=0.01,
            orient=tk.HORIZONTAL, label="動きの滑らかさ", command=self.update_smoothing)
        self.scale_smooth.set(SMOOTHING_FACTOR)
        self.scale_smooth.pack(fill=tk.X, pady=(4, 6))

        self.scale_x = tk.Scale(
            frame, from_=-2.0, to=2.0, resolution=0.01,
            orient=tk.HORIZONTAL, label="左右 (X)", command=self.update_offsets)
        self.scale_x.set(MANUAL_X_OFFSET)
        self.scale_x.pack(fill=tk.X)

        self.scale_h = tk.Scale(
            frame, from_=-2.0, to=2.0, resolution=0.01,
            orient=tk.HORIZONTAL, label="上下 (Y)", command=self.update_offsets)
        self.scale_h.set(MANUAL_HEIGHT_OFFSET)
        self.scale_h.pack(fill=tk.X)

        self.scale_z = tk.Scale(
            frame, from_=-2.0, to=2.0, resolution=0.01,
            orient=tk.HORIZONTAL, label="前後 (Z)", command=self.update_offsets)
        self.scale_z.set(MANUAL_Z_OFFSET)
        self.scale_z.pack(fill=tk.X)

    def _build_detail_adjustments(self):
        frame = self._section("部位ごとの微調整")

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 5))
        self.target_tracker_key = tk.StringVar()
        tracker_labels = [pose_virtual_transforms[k]["label"] for k in pose_virtual_transforms]
        self.label_to_key = {v["label"]: k for k, v in pose_virtual_transforms.items()}

        self.cb_selector = ttk.Combobox(
            top, textvariable=self.target_tracker_key,
            values=tracker_labels, state="readonly")
        if tracker_labels:
            self.cb_selector.current(0)
        self.cb_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cb_selector.bind("<<ComboboxSelected>>", self.on_tracker_selected)
        ttk.Button(top, text="この部位をリセット", command=self.reset_detail_adjustment).pack(side=tk.LEFT, padx=(8, 0))

        self.detail_scale_x = tk.Scale(
            frame, from_=-0.5, to=0.5, resolution=0.01,
            orient=tk.HORIZONTAL, label="左右調整", command=self.on_detail_slide)
        self.detail_scale_x.pack(fill=tk.X)
        self.detail_scale_y = tk.Scale(
            frame, from_=-0.5, to=0.5, resolution=0.01,
            orient=tk.HORIZONTAL, label="上下調整", command=self.on_detail_slide)
        self.detail_scale_y.pack(fill=tk.X)
        self.detail_scale_z = tk.Scale(
            frame, from_=-0.5, to=0.5, resolution=0.01,
            orient=tk.HORIZONTAL, label="前後調整", command=self.on_detail_slide)
        self.detail_scale_z.pack(fill=tk.X)

        if tracker_labels:
            self.on_tracker_selected()

        footer = ttk.Frame(self.main_frame, padding=(14, 8, 14, 18))
        footer.pack(fill=tk.X)
        tk.Button(
            footer, text="WebTora-βを終了", bg="#c0392b", fg="white",
            font=("Yu Gothic UI", 10, "bold"), command=self.on_closing
        ).pack(fill=tk.X, ipady=4)

    # --- イベントハンドラ ---
    def create_gpt_support_file(self):
        try:
            out_dir = _support_dir()
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, GPT_DIAGNOSTICS_FILENAME)
            with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
                f.write(build_gpt_diagnostics_text())

            # GPTへ貼る短い依頼文もクリップボードへ。
            prompt = (
                "WebTora-βが正常に動きません。添付した GPT_SUPPORT_SETUP.txt と "
                "WEBTORA_GPT_DIAGNOSTICS.txt を読み、診断ログから最有力原因を特定して、"
                "安全な修復手順を一つずつ教えてください。"
            )
            self.root.clipboard_clear()
            self.root.clipboard_append(prompt)
            self.root.update_idletasks()

            try:
                if sys.platform.startswith("win"):
                    subprocess.Popen(["explorer", "/select,", os.path.normpath(out_path)])
            except Exception:
                pass

            messagebox.showinfo(
                "GPTサポート",
                "診断ファイルを作成しました。\n\n"
                f"{out_path}\n\n"
                "support\\AI\\GPT_SUPPORT_SETUP.txt と一緒にGPTへアップロードしてください。\n"
                "GPTへ送る依頼文はクリップボードにもコピーしました。")
        except Exception as e:
            messagebox.showerror(
                "GPTサポート",
                f"診断ファイルを作成できませんでした。\n{type(e).__name__}: {e}")

    def open_gpt_support_setup(self):
        candidates = [
            os.path.join(_ai_support_dir(), GPT_SUPPORT_SETUP_FILENAME),
        ]
        path = next((x for x in candidates if os.path.exists(x)), None)
        if not path:
            messagebox.showerror("GPTサポート", "GPT_SUPPORT_SETUP.txt が見つかりません。")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                webbrowser.open("file://" + os.path.abspath(path))
        except Exception as e:
            messagebox.showerror("GPTサポート", f"説明TXTを開けませんでした。\n{e}")

    def reconnect_camera(self):
        global CAMERA_INDEX, CAMERA_BACKEND_MODE, CAMERA_AUTO_SEARCH
        try:
            CAMERA_INDEX = int(self.camera_index_var.get())
        except (TypeError, ValueError, tk.TclError):
            CAMERA_INDEX = 0
            self.camera_index_var.set(0)

        CAMERA_BACKEND_MODE = self.camera_backend_var.get() or "自動 (推奨)"
        CAMERA_AUTO_SEARCH = bool(self.camera_auto_var.get())
        self.lbl_camera_status.config(text="カメラを再検出しています...", foreground="#b36b00")
        CAMERA_RECONNECT_REQUEST.set()

    def open_camera_privacy_settings(self):
        if not sys.platform.startswith("win"):
            messagebox.showinfo("カメラ権限", "このボタンはWindows向けです。")
            return
        try:
            os.startfile("ms-settings:privacy-webcam")
        except Exception:
            try:
                subprocess.Popen(["cmd", "/c", "start", "", "ms-settings:privacy-webcam"], shell=False)
            except Exception as e:
                messagebox.showerror("エラー", f"Windows設定を開けませんでした。\n{e}")

    def copy_camera_diagnostics(self):
        with camera_status_lock:
            status = camera_status
            connected = camera_connected
            active_index = camera_active_index
            backend = camera_active_backend

        info = camera_debug_info or "詳細な診断情報はまだありません。"
        device_info = ""
        if sys.platform.startswith("win"):
            try:
                ps = (
                    "Get-PnpDevice | Where-Object { "
                    "$_.Class -in @('Camera','Image') -or $_.FriendlyName -match 'camera|webcam' "
                    "} | Select-Object -ExpandProperty FriendlyName"
                )
                completed = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps],
                    capture_output=True, text=True, timeout=8,
                    encoding="utf-8", errors="replace")
                names = [x.strip() for x in completed.stdout.splitlines() if x.strip()]
                if names:
                    device_info = "\nWindows camera devices:\n- " + "\n- ".join(names)
            except Exception as e:
                device_info = f"\nWindows device scan failed: {type(e).__name__}: {e}"

        text = (
            "WebTora-β camera diagnostics\n"
            f"Status: {status}\n"
            f"Connected flag: {connected}\n"
            f"Active index: {active_index}\n"
            f"Active backend: {backend}\n"
            f"{info}{device_info}"
        )
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        messagebox.showinfo("診断情報", "カメラ診断情報をクリップボードへコピーしました。")

    def update_camera_status(self):
        with camera_status_lock:
            text = camera_status
            connected = camera_connected
            active_index = camera_active_index

        self.lbl_camera_status.config(
            text=text,
            foreground=("#16803c" if connected else "#b42318"))

        # 自動探索で別番号が見つかった場合、GUIにも反映。
        if connected and active_index is not None:
            try:
                if int(self.camera_index_var.get()) != active_index:
                    self.camera_index_var.set(active_index)
            except Exception:
                pass

        if self.root.winfo_exists():
            self.root.after(500, self.update_camera_status)

    def set_all_trackers(self, enabled):
        for key, var in self.tracker_vars.items():
            var.set(enabled)
            pose_virtual_transforms[key]["enable"] = enabled

    def reset_global_adjustments(self):
        self.scale_smooth.set(0.7)
        self.scale_x.set(0.0)
        self.scale_h.set(0.0)
        self.scale_z.set(0.0)
        self.update_smoothing()
        self.update_offsets()

    def reset_detail_adjustment(self):
        label = self.cb_selector.get()
        if not label:
            return
        key = self.label_to_key[label]
        tracker_offsets[key] = np.zeros(3, dtype=np.float32)
        self.detail_scale_x.set(0.0)
        self.detail_scale_y.set(0.0)
        self.detail_scale_z.set(0.0)

    def on_closing(self):
        if messagebox.askyesno("確認", "WebTora-βを終了しますか？"):
            CAMERA_STOP_REQUEST.set()
            try:
                self.canvas.unbind_all("<MouseWheel>")
                self.canvas.unbind_all("<Button-4>")
                self.canvas.unbind_all("<Button-5>")
            except Exception:
                pass
            self.root.destroy()

    def on_tracker_selected(self, event=None):
        label = self.cb_selector.get()
        if not label:
            return
        key = self.label_to_key[label]
        offset = tracker_offsets[key]
        self.detail_scale_x.set(float(offset[0]))
        self.detail_scale_y.set(float(offset[1]))
        self.detail_scale_z.set(float(offset[2]))

    def on_detail_slide(self, _=None):
        label = self.cb_selector.get()
        if not label:
            return
        key = self.label_to_key[label]
        tracker_offsets[key] = np.array([
            float(self.detail_scale_x.get()),
            float(self.detail_scale_y.get()),
            float(self.detail_scale_z.get())
        ], dtype=np.float32)

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
            self.btn_osc.config(text="OSC通信中 - クリックで停止", bg="#2e9d50", fg="white")
            webbrowser.open("http://127.0.0.1:5000/connect")
        else:
            self.btn_osc.config(text="OSC通信を開始", bg="#dddddd", fg="black")

    def open_auto_position_dialog(self):
        with camera_status_lock:
            connected = camera_connected
        if not connected:
            messagebox.showwarning("位置自動調節", "Webカメラが接続されていません。先にカメラ接続を確認してください。")
            return

        if getattr(self, "auto_position_dialog", None) is not None:
            try:
                if self.auto_position_dialog.winfo_exists():
                    self.auto_position_dialog.lift()
                    return
            except Exception:
                pass

        dlg = tk.Toplevel(self.root)
        self.auto_position_dialog = dlg
        dlg.title("位置自動調節")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        body = ttk.Frame(dlg, padding=22)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            body, text="両手を広げてTポーズになってください",
            font=("Yu Gothic UI", 15, "bold")
        ).pack(pady=(0, 10))
        ttk.Label(
            body,
            text=(
                "頭から足先までカメラに映る位置に立ち、\n"
                "両手を肩の高さまで横にまっすぐ広げてください。\n\n"
                "STARTを押すと3秒後に高さと左右位置を取得して自動調節します。"
            ),
            justify=tk.CENTER, wraplength=440
        ).pack(pady=(0, 14))

        self.auto_position_count_label = ttk.Label(
            body, text="準備ができたらSTARTを押してください。",
            font=("Yu Gothic UI", 11, "bold"), anchor="center")
        self.auto_position_count_label.pack(fill=tk.X, pady=(4, 14))

        buttons = ttk.Frame(body)
        buttons.pack(fill=tk.X)
        self.auto_position_start_button = tk.Button(
            buttons, text="START", bg="#2b8a9b", fg="white",
            font=("Yu Gothic UI", 11, "bold"), command=self.start_auto_position_countdown)
        self.auto_position_start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=5)
        self.auto_position_cancel_button = ttk.Button(buttons, text="キャンセル", command=dlg.destroy)
        self.auto_position_cancel_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), ipady=5)

        dlg.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dlg.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dlg.winfo_height()) // 2)
        dlg.geometry(f"+{x}+{y}")

    def start_auto_position_countdown(self):
        self.auto_position_start_button.config(state=tk.DISABLED)
        self.auto_position_cancel_button.config(state=tk.DISABLED)
        self.auto_position_count = 3
        self._update_auto_position_countdown()

    def _update_auto_position_countdown(self):
        dlg = getattr(self, "auto_position_dialog", None)
        if dlg is None or not dlg.winfo_exists():
            return

        if self.auto_position_count > 0:
            self.auto_position_count_label.config(
                text=f"そのまま動かないでください…  {self.auto_position_count}",
                foreground="")
            self.auto_position_count -= 1
            self.root.after(1000, self._update_auto_position_countdown)
            return

        self.auto_position_count_label.config(text="位置を取得しています…")
        self.root.update_idletasks()
        success, message, offsets = auto_adjust_position_from_tpose()

        if success and offsets is not None:
            x, y = offsets
            self.scale_x.set(x)
            self.scale_h.set(y)
            self.update_offsets()
            self.lbl_calib_status.config(
                text=f"自動調節完了  高さ {y:+.2f} m / 左右追従 ON",
                foreground="#16803c")
            self.auto_position_count_label.config(text="調節完了", foreground="#16803c")
            self.root.after(700, dlg.destroy)
        else:
            self.auto_position_count_label.config(text=message, foreground="#b42318", wraplength=440)
            self.auto_position_start_button.config(state=tk.NORMAL, text="もう一度START")
            self.auto_position_cancel_button.config(state=tk.NORMAL)

    def start_calibration(self):
        self.calib_count = 3
        self.update_calib_countdown()

    def update_calib_countdown(self):
        if self.calib_count > 0:
            self.lbl_calib_status.config(
                text=f"直立してください。計測まで {self.calib_count} 秒",
                foreground="#b36b00")
            self.calib_count -= 1
            self.root.after(1000, self.update_calib_countdown)
        else:
            self.lbl_calib_status.config(text="キャリブレーション実行中...", foreground="#b36b00")
            update_calibration_parameter()
            self.lbl_calib_status.config(text="キャリブレーション完了", foreground="#16803c")
            self.root.after(2500, lambda: self.lbl_calib_status.config(text=""))


if __name__ == "__main__":
    # 先にGUIを表示してからカメラを開く。
    # 一部のWindows環境でVideoCapture初期化がUI起動を邪魔するのを防ぐ。
    root = tk.Tk()
    app_gui = AppGUI(root)

    t_flask = threading.Thread(target=run_flask, daemon=True)
    t_flask.start()

    def start_camera_thread():
        try:
            t_pose = threading.Thread(target=run_analyze_pose, name="WebToraCamera", daemon=True)
            t_pose.start()
        except Exception as e:
            global camera_debug_info
            camera_debug_info = f"Camera thread start FAILED: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            _set_camera_status("カメラスレッドを開始できませんでした。診断情報をコピーしてください。", False)

    # GUI構築完了直後に開始。Tkのafter待ちで起動処理が消えるケースを避ける。
    start_camera_thread()
    root.mainloop()





