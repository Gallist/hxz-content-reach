"""Read-only WeChat Channels share-link capture and local transcription.

Only public share URLs that the user is authorized to archive. The resolver
is third-party: it receives the share URL; no WeChat cookies or credentials.
Public resolver availability is not guaranteed. Never treat a failed resolve
as an empty author feed or claim a historical-account crawl.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, shutil, subprocess, sys, urllib.request, wave
from pathlib import Path
from urllib.parse import urlparse

API = "https://v.mtotech.com/api/resolve"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
LINK_RE = re.compile(r"^https://weixin\.qq\.com/sph/([A-Za-z0-9_-]+)(?:[/?#].*)?$")
CHINA_TZ = dt.timezone(dt.timedelta(hours=8))


def validate_link(url: str) -> tuple[str, str]:
    url = url.strip()
    m = LINK_RE.fullmatch(url)
    if not m:
        raise ValueError("Expected an authorized https://weixin.qq.com/sph/<id> share URL")
    return "https://weixin.qq.com/sph/" + m.group(1), m.group(1)


def resolve(url: str) -> dict:
    clean, _ = validate_link(url)
    req = urllib.request.Request(API, data=json.dumps({"url": clean}).encode("utf-8"),
        headers={"Content-Type":"application/json", "User-Agent":USER_AGENT}, method="POST")
    with urllib.request.urlopen(req, timeout=65) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not data.get("ok") or not isinstance(data.get("data"), dict):
        raise RuntimeError("WeChat Channels resolver did not return usable metadata")
    result = data["data"]
    if not result.get("h264_url") and not result.get("h265_url"):
        raise RuntimeError("No media URL; video may be access-restricted or expired")
    return result


def parse_metadata(url: str, data: dict) -> dict:
    clean, vid = validate_link(url)
    stats = data.get("stats") or {}
    def integer(key):
        value = stats.get(key)
        if value is None or value == "":
            return None
        s = str(value).replace(",","").strip()
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([万wWkK]?)", s)
        if not m:
            return None
        mult = {"万": 10000, "w": 10000, "W": 10000, "k": 1000, "K": 1000}.get(m[2], 1)
        return int(round(float(m[1])*mult))
    created = data.get("created_at")
    published = dt.datetime.fromtimestamp(int(created),CHINA_TZ).isoformat() if created else None
    return {
        "platform": "视频号", "work_id": vid, "url": clean,
        "title": data.get("description") or "", "author": data.get("author") or "",
        "published_at": published,
        "likes": integer("likes"), "comments": integer("comments"),
        "forwards": integer("forwards"), "favorites": integer("favorites"),
        "collected_at": dt.datetime.now(CHINA_TZ).isoformat(),
        "transcription_status": "not_started",
        "note": "Counts are a point-in-time snapshot; unreturned counts stay null."
    }


def ffmpeg_binary(name: str) -> str:
    exe = shutil.which(name)
    if exe: return exe
    local = Path("F:/Apps/ffmpeg/bin")/(name+".exe")
    if local.exists(): return str(local)
    local = Path("F:/tools/ffmpeg/bin")/(name+".exe")
    if local.exists(): return str(local)
    raise FileNotFoundError(f"Required {name} not available")


def media_download(src: str, destination: Path) -> None:
    p=urlparse(src)
    if p.scheme!="https" or p.hostname!="finder.video.qq.com":
        raise ValueError("Unexpected video CDN host; refusing to download")
    req=urllib.request.Request(src,headers={"User-Agent":USER_AGENT,"Referer":"https://channels.weixin.qq.com/"})
    temp=destination.with_suffix(".part")
    try:
        with urllib.request.urlopen(req,timeout=160) as response, temp.open("wb") as fh:
            shutil.copyfileobj(response, fh, 1024*1024)
        if temp.stat().st_size < 100_000: raise RuntimeError("Downloaded video too small")
        temp.replace(destination)
    finally:
        temp.unlink(missing_ok=True)


def probe_video(path: Path) -> float:
    cp=subprocess.run([ffmpeg_binary("ffprobe"),"-v","error","-show_entries",
        "format=duration:stream=codec_type", "-of","json",str(path)],
        capture_output=True,text=True,check=True,timeout=30)
    meta=json.loads(cp.stdout)
    streams={x.get("codec_type") for x in meta.get("streams",[])}
    if not {"video","audio"}.issubset(streams):
        raise RuntimeError("Video does not contain both video and audio streams")
    duration=float(meta["format"]["duration"])
    if duration <= 0: raise RuntimeError("Invalid duration")
    return duration


def transcribe(video: Path, output_dir: Path, model_path: str|None=None) -> dict:
    import numpy as np
    from faster_whisper import WhisperModel
    if not model_path:
        model_path=os.getenv("HXZ_WHISPER_MODEL") or next((str(p) for p in (
            Path("F:/tools/models/faster-whisper-medium"),
            Path("F:/tools/models/faster-whisper-large-v3")) if p.exists()),None)
    if not model_path: raise RuntimeError("Set HXZ_WHISPER_MODEL to an installed faster-whisper model directory")
    audio_path=output_dir/"audio_16k.wav"
    subprocess.run([ffmpeg_binary("ffmpeg"),"-y","-v","error","-i",str(video),
        "-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(audio_path)],
        check=True,timeout=200)
    with wave.open(str(audio_path),"rb") as wav:
        if wav.getframerate()!=16000 or wav.getnchannels()!=1:
            raise RuntimeError("Audio conversion failed")
        audio=np.frombuffer(wav.readframes(wav.getnframes()),dtype=np.int16).astype(np.float32)/32768.0
    model=WhisperModel(model_path,device="cpu",compute_type="int8",cpu_threads=min(os.cpu_count() or 4,8))
    segments,info=model.transcribe(audio,language="zh",beam_size=5,
        vad_filter=True,vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False)
    rows=[{"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip()} for s in segments]
    if not rows or rows[-1]["end"] < float(info.duration)*.80:
        raise RuntimeError("Transcript missing or ends much earlier than source audio")
    def mark(v):
        ms=round(v*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);sec,ms=divmod(ms,1000)
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"
    (output_dir/"segments.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    (output_dir/"transcript.txt").write_text("\n".join(
        f"[{int(r['start']//60):02}:{r['start']%60:05.2f}] {r['text']}" for r in rows),encoding="utf-8")
    (output_dir/"subtitles.srt").write_text("\n\n".join(
        f"{i}\n{mark(r['start'])} --> {mark(r['end'])}\n{r['text']}"
        for i,r in enumerate(rows,1)),encoding="utf-8")
    return {"status":"transcribed_machine_unreviewed","segments":len(rows),
            "last_segment_end":rows[-1]["end"],"audio_duration":float(info.duration)}


def fetch(url: str, root: str|Path|None=None, metadata_only=False, no_transcribe=False) -> dict:
    clean,work_id=validate_link(url)
    folder=Path(root) if root else Path(os.getenv("HXZ_WX_OUTPUT_ROOT",str(Path.home()/"Downloads"/"hxz-content-reach-videohao")))
    dest=folder/work_id
    dest.mkdir(parents=True,exist_ok=True)
    data=resolve(clean)
    meta=parse_metadata(clean,data)
    if not metadata_only:
        video=dest/"video.mp4"
        if not video.exists():
            errors=[]
            for codec in ("h264_url","h265_url"):
                src=data.get(codec)
                if not src: continue
                try:
                    media_download(src,video)
                    probe_video(video)
                    break
                except Exception as exc:
                    errors.append(str(exc))
                    video.unlink(missing_ok=True)
            if not video.exists(): raise RuntimeError("All video download attempts failed: "+" | ".join(errors))
        meta["duration_seconds"]=round(probe_video(video),3)
        if not no_transcribe:
            # PyAV compatibility: feed decoded PCM arrays to Whisper, not an MP4 pathname.
            meta["transcription"]=transcribe(video,dest)
            meta["transcription_status"]="transcribed_machine_unreviewed"
    (dest/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"output_dir":str(dest),**meta}


def main(argv=None):
    ap=argparse.ArgumentParser(description="Archive authorized WeChat Channels share links")
    ap.add_argument("command",choices=["fetch"])
    ap.add_argument("url")
    ap.add_argument("--out",help="Output root (not a single-video directory)")
    ap.add_argument("--metadata-only",action="store_true")
    ap.add_argument("--no-transcribe",action="store_true")
    args=ap.parse_args(argv)
    result=fetch(args.url,args.out,args.metadata_only,args.no_transcribe)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
