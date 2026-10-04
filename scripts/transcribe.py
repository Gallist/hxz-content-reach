"""Windows 视频转写：faster-whisper，CUDA 优先，失败回退 CPU。

用法: <venv python> transcribe.py <audio> <out.txt> [prompt]

本脚本禁用联网下载：两处 WhisperModel 构造都显式传 local_files_only=True，
缺本地模型时直接报错退出，绝不隐式下载权重（CUDA 与 CPU 回退都一样）。

模型与缓存位置可覆盖：
  XHS_WHISPER_MODEL  模型名/路径，默认 large-v3-turbo
  XHS_HF_HOME        HuggingFace 缓存目录；优先级高于既有的 HF_HOME
"""
import os
import sys
import glob
import time
from pathlib import Path

# Keep diagnostics readable and prevent console encoding from aborting fallback.
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, 'reconfigure', None)
    if _reconfigure is not None:
        _reconfigure(encoding='utf-8')

# XHS_HF_HOME 必须覆盖既有 HF_HOME（显式赋值，不用 setdefault）；
# 两者都没设时才落到用户缓存目录。
_xhs_hf_home = os.environ.get('XHS_HF_HOME')
if _xhs_hf_home:
    os.environ['HF_HOME'] = _xhs_hf_home
else:
    os.environ.setdefault('HF_HOME', str(Path.home() / '.cache' / 'hxz-content-reach' / 'hf'))
venv = os.path.dirname(os.path.abspath(sys.executable))
for d in glob.glob(os.path.join(venv, '..', 'Lib', 'site-packages', 'nvidia', '*', 'bin')):
    os.add_dll_directory(os.path.abspath(d))
    os.environ['PATH'] = os.path.abspath(d) + os.pathsep + os.environ['PATH']
from faster_whisper import WhisperModel

MODEL = os.environ.get('XHS_WHISPER_MODEL', 'large-v3-turbo')
audio, out = sys.argv[1], sys.argv[2]
prompt = sys.argv[3] if len(sys.argv) > 3 else "以下是普通话的句子，使用简体中文和全角标点。"
t0 = time.time()


def _missing_local_model(exc):
    return (
        f"无法加载本地 Whisper 模型 {MODEL!r}：{exc}\n"
        f"本脚本不会联网下载（local_files_only=True）；请先把模型放进 HF_HOME 缓存"
        f"（当前 HF_HOME={os.environ.get('HF_HOME')}），或用 XHS_WHISPER_MODEL 指向本地模型目录。")


try:
    model = WhisperModel(MODEL, device="cuda", compute_type="int8_float16", local_files_only=True)
    dev = "cuda"
except Exception as e:
    print("CUDA 失败，回退 CPU:", e)
    try:
        model = WhisperModel(MODEL, device="cpu", compute_type="int8", local_files_only=True)
        dev = "cpu"
    except Exception as e2:
        raise SystemExit(_missing_local_model(e2))
import subprocess
import numpy as np
# 用 ffmpeg 解码成 16k 单声道，避开 PyAV 版本不兼容
pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
audio_np = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
segs, info = model.transcribe(audio_np, language="zh", beam_size=5, vad_filter=True,
                              initial_prompt=prompt, condition_on_previous_text=False)
with open(out, "w", encoding="utf-8", newline="\n") as f:
    for s in segs:
        f.write(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text.strip()}\n")
print(f"done device={dev} dur={info.duration:.0f}s elapsed={time.time()-t0:.0f}s")
