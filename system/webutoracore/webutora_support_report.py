import datetime
import importlib.metadata
import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path

VERSION = "WebTora-β 0.4.0-beta1 / booth-support-v8-auto-position"
EXPECTED = {
    "numpy": "1.26.4",
    "mediapipe": "0.10.18",
    "opencv-contrib-python": "4.11.0.86",
    "python-osc": "1.9.3",
    "Flask": "3.1.2",
    "matplotlib": "3.10.8",
}


def dist_version(name):
    try:
        return importlib.metadata.version(name)
    except Exception as exc:
        return f"not installed ({type(exc).__name__}: {exc})"


def safe_read(path, limit=30000):
    try:
        p = Path(path)
        if not p.exists():
            return f"[missing] {p}"
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > limit:
            text = text[-limit:]
            return "[truncated to last characters]\n" + text
        return text
    except Exception as exc:
        return f"[read failed] {type(exc).__name__}: {exc}"




def mediapipe_info():
    lines = []
    try:
        spec = importlib.util.find_spec("mediapipe")
        lines.append(f"mediapipe spec: {spec}")
        if spec and spec.origin:
            mp_root = Path(spec.origin).resolve().parent
            pose_graph = mp_root / "modules" / "pose_landmark" / "pose_landmark_cpu.binarypb"
            lines.append(f"MediaPipe root: {mp_root}")
            lines.append(f"Pose graph: {pose_graph}")
            lines.append(f"Pose graph exists: {pose_graph.exists()}")
    except Exception as exc:
        lines.append(f"MediaPipe path check failed: {type(exc).__name__}: {exc}")

    try:
        import mediapipe as mp
        lines.append(f"mediapipe import: OK ({getattr(mp, '__version__', 'unknown')})")
        try:
            pose = mp.solutions.pose.Pose(model_complexity=0)
            pose.close()
            lines.append("MediaPipe Pose initialization: OK")
        except Exception as exc:
            lines.append(f"MediaPipe Pose initialization: FAILED: {type(exc).__name__}: {exc}")
    except Exception as exc:
        lines.append(f"mediapipe import: FAILED: {type(exc).__name__}: {exc}")
    return lines



def main():
    out_arg = sys.argv[1] if len(sys.argv) > 1 else "WEBTORA_GPT_DIAGNOSTICS.txt"
    out = Path(out_arg).resolve()
    cwd = Path.cwd()

    lines = [
        "WebTora-β GPT diagnostics",
        "=======================",
        f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"Product version: {VERSION}",
        "",
        "[Runtime]",
        f"Platform: {platform.platform()}",
        f"sys.platform: {sys.platform}",
        f"Python: {sys.version.replace(chr(10), ' ')}",
        f"Python executable: {sys.executable}",
        f"Python architecture: {platform.architecture()[0]}",
        f"sys.prefix: {sys.prefix}",
        f"Current working directory: {cwd}",
        f"Original WebTora directory: {os.environ.get('WEBTORA_ORIGINAL_DIR', 'not set')}",
        f"Package root: {os.environ.get('WEBTORA_PACKAGE_ROOT', 'not set')}",
        f"WEBTORA_SUBST_ACTIVE: {os.environ.get('WEBTORA_SUBST_ACTIVE', 'not set')}",
        f"WEBTORA_SUBST_DRIVE: {os.environ.get('WEBTORA_SUBST_DRIVE', 'not set')}",
        "",
        "[Installed package versions]",
    ]

    for name, expected in EXPECTED.items():
        actual = dist_version(name)
        lines.append(f"{name}: {actual} (expected {expected})")
    lines.append(f"opencv-python: {dist_version('opencv-python')} (expected not installed)")
    lines.append(f"opencv-python-headless: {dist_version('opencv-python-headless')} (expected not installed)")
    lines.append(f"opencv-contrib-python-headless: {dist_version('opencv-contrib-python-headless')} (expected not installed)")

    lines.extend(["", "[MediaPipe check]"])
    lines.extend(mediapipe_info())

    lines.extend([
        "",
        "[Camera check]",
        "Active camera probing is intentionally not run by GPT_SUPPORT.bat.",
        "If the issue is camera-related, run CAMERA_TEST.bat and include its result or use the GUI GPT support export.",
    ])

    package_root = Path(os.environ.get("WEBTORA_PACKAGE_ROOT", cwd.parent)).resolve()
    support_dir = Path(os.environ.get("WEBTORA_SUPPORT_DIR", package_root / "support")).resolve()
    ai_dir = Path(os.environ.get("WEBTORA_AI_DIR", support_dir / "AI")).resolve()

    lines.extend([
        "",
        "[Files / setup markers]",
        f"requirements.txt exists: {(cwd / 'requirements.txt').exists()}",
        f".venv exists: {(cwd / '.venv').exists()}",
        f"v8 setup marker exists: {(cwd / '.webtora_setup_v8_complete').exists()}",
        f"GPT_SUPPORT_SETUP.txt exists: {(ai_dir / 'GPT_SUPPORT_SETUP.txt').exists()}",
    ])

    for logname in ["webtora_last_error.log", "webtora_setup_error.log"]:
        lines.extend(["", f"[{logname}]", safe_read(cwd / logname)])

    lines.extend([
        "",
        "[Instructions for GPT]",
        "Read support/AI/GPT_SUPPORT_SETUP.txt together with this report.",
        "Use facts from this report first; do not blindly update packages.",
        "Prefer support/REPAIR_WEBTORA.bat and support/CAMERA_TEST.bat before source edits.",
    ])

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"[WebTora-β] GPT diagnostics created: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
