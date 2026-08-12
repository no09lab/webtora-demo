import os
import sys
import time
import subprocess

if sys.platform.startswith('win'):
    os.environ.setdefault('OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS', '0')

import cv2


def windows_devices():
    if not sys.platform.startswith('win'):
        return []
    try:
        ps = (
            "Get-PnpDevice | Where-Object { "
            "$_.Class -in @('Camera','Image') -or $_.FriendlyName -match 'camera|webcam' "
            "} | Select-Object -ExpandProperty FriendlyName"
        )
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps],
            capture_output=True, text=True, timeout=5,
            encoding='utf-8', errors='replace')
        return [x.strip() for x in r.stdout.splitlines() if x.strip()]
    except Exception as e:
        return [f'(device scan error: {type(e).__name__}: {e})']


def try_read(cap, seconds=1.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        ok, frame = cap.read()
        if ok and frame is not None and frame.size:
            return frame
        time.sleep(0.05)
    return None


def main():
    print('=== WebTora-β Camera Only Test ===')
    print('Python :', sys.version.split()[0])
    print('OpenCV :', cv2.__version__)
    print('Platform:', sys.platform)
    print('\nWindows camera devices:')
    names = windows_devices()
    if names:
        for n in names:
            print(' -', n)
    else:
        print(' - (not detected by PnP scan)')

    backends = [(None, 'OpenCV Auto')]
    if sys.platform.startswith('win'):
        if hasattr(cv2, 'CAP_DSHOW'):
            backends.append((cv2.CAP_DSHOW, 'DirectShow'))
        if hasattr(cv2, 'CAP_MSMF'):
            backends.append((cv2.CAP_MSMF, 'Media Foundation'))

    found = None
    print('\nScanning camera indexes 0-9...')
    for index in range(10):
        for backend, name in backends:
            cap = None
            try:
                cap = cv2.VideoCapture(index) if backend is None else cv2.VideoCapture(index, backend)
                if cap is None or not cap.isOpened():
                    print(f' #{index} {name}: open failed')
                    if cap is not None:
                        cap.release()
                    continue

                frame = try_read(cap, 0.8)
                profile = 'default'
                if frame is None:
                    try:
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                    except Exception:
                        pass
                    frame = try_read(cap, 1.2)
                    profile = '640x480 MJPG 30fps'

                if frame is None:
                    print(f' #{index} {name}: opened, but frame read failed')
                    cap.release()
                    continue

                h, w = frame.shape[:2]
                print(f' #{index} {name}: OK ({w}x{h}, {profile})')
                found = (index, name, profile, cap, frame)
                break
            except Exception as e:
                print(f' #{index} {name}: {type(e).__name__}: {e}')
                if cap is not None:
                    try: cap.release()
                    except Exception: pass
        if found:
            break

    if not found:
        print('\nRESULT: OpenCV could not get a frame from any camera.')
        print('Close apps that may be using the webcam and check Windows camera privacy settings.')
        return 2

    index, name, profile, cap, frame = found
    print(f'\nRESULT: Camera works in OpenCV. index={index}, backend={name}, profile={profile}')
    print('A preview window will open. Press Q or ESC to close it.')
    try:
        while True:
            ok, current = cap.read()
            if ok and current is not None:
                cv2.putText(current, f'WebTora-β camera test #{index} / {name}', (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2, cv2.LINE_AA)
                cv2.imshow('WebTora-β Camera Test', current)
            key = cv2.waitKey(20) & 0xFF
            if key in (ord('q'), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
