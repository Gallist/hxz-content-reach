"""小红书 → 飞书多维表格 一键流程（Windows，单篇视频默认链路）。

  python xhs_pipeline.py doctor                    离线诊断配置，不联网、不采集、不写表
  python xhs_pipeline.py fetch <链接或分享口令>     采集+下载+转写+查重，打印摘要（含工作目录）
  python xhs_pipeline.py repair <工作目录> <起秒> <止秒> [提示词]   局部重转一小段
  python xhs_pipeline.py push <工作目录>            读 reviewed.txt / title.txt / remark.txt，写入或更新飞书

配置见 docs/CONFIGURATION.md。base_token / table_id 缺失或仍是示例占位时，fetch、push 会在任何飞书写入前明确拒绝。
脚本默认从 PATH 找 lark-cli / Chrome，但绝不自动登录、下载模型或安装依赖。doctor 只做配置与文件存在性检查，缺核心工具路径时非零退出，不等于 GPU / 授权 / 模型已就绪。
"""
import datetime, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

import xhs_config
from product_rules import (counts_from_page, douyin_note, make_remark, platform_of, profile_debug_port,
                           save_write_state, verify_record)

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))

_CFG = xhs_config.load()
PORT = _CFG["cdp_port"]
CHROME = _CFG.get("chrome_path", "")
PROFILE = _CFG.get("chrome_profile", "")
SCRATCH = _CFG["scratch_dir"]
WHISPER_PY = _CFG.get("whisper_python", "")
WHISPER_SCRIPT = _CFG["transcribe_script"]
PUNCT_MODEL = _CFG.get("punct_model", "")
LARK = _CFG.get("lark_cli", "")
BASE = _CFG.get("base_token", "")
TABLE = _CFG.get("table_id", "")
WHISPER_MODEL = _CFG.get("whisper_model", "")
HF_HOME = _CFG.get("hf_home", "")
HDR = {"Referer": "https://www.xiaohongshu.com/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/154"}
TZ = datetime.timezone(datetime.timedelta(hours=8))

USAGE = """\
用法: python xhs_pipeline.py <命令> [参数]

命令:
  doctor                     离线检查配置（缺必需项或核心工具路径时非零退出），不联网、不采集、不写表
  fetch <链接或分享口令>      采集页面 → 下载 → 本地转写 + 标点 → 飞书查重，打印 JSON 摘要
                            可加 --note-json <页面JSON绝对路径> 走浏览器备用路径
                            可加 --force 命中既有记录时强制重跑
  repair <工作目录> <起秒> <止秒> [提示词]   对 audio.wav 局部重转一小段
  push <fetch返回的workdir>   读取 reviewed.txt / title.txt / remark.txt，写入或更新飞书并精确回读核验

配置: 环境变量(XHS_*) > config.local.json / $XHS_CONFIG_FILE > PATH 默认。见 docs/CONFIGURATION.md。
"""


def log(*a):
    print("·", *a, file=sys.stderr, flush=True)


def require_base_table():
    try:
        xhs_config.require({"base_token": BASE, "table_id": TABLE})
    except xhs_config.ConfigError as e:
        raise SystemExit(str(e))


def chrome_ready(port):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
        return True
    except Exception:
        return False


def live_port():
    # 固定端口优先；同一份配置已被 Hermes 浏览器工具以随机端口打开时，复用它写下的真实端口。
    ports = [PORT]
    if PROFILE:
        ports.append(profile_debug_port(PROFILE))
    for port in ports:
        if port and chrome_ready(port):
            return port
    return None


def ensure_chrome():
    port = live_port()
    if port:
        return port
    if not CHROME or not PROFILE:
        raise SystemExit('未配置 Chrome：请设置 XHS_CHROME_PATH 与 XHS_CHROME_PROFILE（见 docs/CONFIGURATION.md）。')
    log("启动专用 Chrome（最小化后台窗口）")
    subprocess.Popen([CHROME, f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}",
                      "--no-first-run", "--no-default-browser-check", "--disable-sync", "--start-minimized",
                      "--window-position=-32000,-32000", "--hide-crash-restore-bubble", "about:blank"])
    for _ in range(30):
        time.sleep(0.5)
        port = live_port()
        if port:
            return port
    raise SystemExit("Chrome 启动失败：专用配置可能被一个未开调试端口的 Chrome 占用")


def headers_for(platform):
    return {**HDR, "Referer": "https://www.douyin.com/"} if platform == "抖音" else HDR


def download(url, path, platform="小红书"):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers_for(platform)), timeout=300) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)


def lark(args, cwd):
    if not LARK:
        raise SystemExit("未配置 lark_cli：请设置 XHS_LARK_CLI，或确保 lark-cli 在 PATH 中（见 docs/CONFIGURATION.md）。")
    argv = [LARK, *args, "--as", "user"]
    command = subprocess.list2cmdline(argv) if os.name == "nt" else argv
    r = subprocess.run(command, shell=(os.name == "nt"), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"ok": False, "raw": (r.stdout + r.stderr)[-1500:]}


def find_existing(note_id, cwd):
    flt = json.dumps({"logic": "and", "conditions": [["笔记链接", "intersects", note_id]]}, ensure_ascii=False)
    out = os.path.join(cwd, "dup.ndjson")
    Path(out).unlink(missing_ok=True)
    r = lark(["base", "+record-list", "--base-token", BASE, "--table-id", TABLE, "--filter-json", flt,
              "--field-id", "标题", "--format", "ndjson", "--output", "dup.ndjson", "--overwrite"], cwd)
    if r.get("ok") is False or r.get("has_more") or not os.path.exists(out):
        raise SystemExit(f"飞书查重失败（不敢瞎写，先停下）: {r}")
    ids = []
    for line in Path(out).read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            ids.append(d.get("record_id") or d.get("_record_id"))
    for f in ("dup.ndjson", "dup.manifest.json"):
        if os.path.exists(os.path.join(cwd, f)):
            os.remove(os.path.join(cwd, f))
    return [i for i in ids if i]


def transcribe(audio, out, prompt=None):
    env = dict(os.environ, HF_ENDPOINT=os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"), PYTHONIOENCODING="utf-8")
    if WHISPER_MODEL:
        env["XHS_WHISPER_MODEL"] = WHISPER_MODEL
    if HF_HOME:
        env["XHS_HF_HOME"] = HF_HOME
    args = [WHISPER_PY, WHISPER_SCRIPT, audio, out] + ([prompt] if prompt else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    done = [l for l in r.stdout.splitlines() if l.startswith("done")]
    if r.returncode or not done:
        raise SystemExit("转写失败:\n" + (r.stdout + r.stderr)[-1500:])
    return done[-1]


def cmd_fetch(arg, *_):
    if platform_of(arg) == "视频号":
        from wechat_channels import fetch as fetch_channels
        m = re.search(r"https?://\S+", arg)
        link = m.group(0).rstrip("，。,.") if m else arg
        result = fetch_channels(link)
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    require_base_table()
    t0 = time.time()
    m = re.search(r"https?://\S+", arg)
    url = m.group(0).rstrip("，。,") if m else arg
    if "--note-json" in sys.argv:
        # Browser-tool fallback: consume page data, never read profile secrets.
        source = sys.argv[sys.argv.index("--note-json") + 1]
        note = json.loads(Path(source).read_text(encoding="utf-8"))
    elif platform_of(arg) == "抖音":
        port = ensure_chrome()
        r = subprocess.run(["node", os.path.join(HERE, "douyin_collect.mjs"), str(port), url],
                           capture_output=True, text=True, encoding="utf-8")
        detail = json.loads(r.stdout.strip() or "null") or {"error": "empty"}
        note = detail if detail.get("error") else douyin_note(detail)
    else:
        port = ensure_chrome()
        r = subprocess.run(["node", os.path.join(HERE, "xhs_collect.mjs"), str(port), url],
                           capture_output=True, text=True, encoding="utf-8")
        note = json.loads(r.stdout.strip() or "null") or {"error": "empty"}
    if note.get("error"):
        raise SystemExit(f"采集失败: {note}")
    platform = note.setdefault("platform", "小红书")
    nid = note["note_id"]
    wd = os.path.join(SCRATCH, nid)
    os.makedirs(wd, exist_ok=True)
    clean = note["href"].split("&")[0] if "xsec_token" in note["href"] else note["href"]
    tok = re.search(r"xsec_token=([^&]+)", note["href"])
    note["clean_url"] = note["href"] if platform == "抖音" else (
        f"https://www.xiaohongshu.com/explore/{nid}" + (f"?xsec_token={tok.group(1)}&xsec_source=app_share" if tok else ""))
    note["kind"] = "视频" if note["type"] == "video" else "图文"
    note["published"] = datetime.datetime.fromtimestamp(note["time"] / 1000, TZ).strftime("%Y-%m-%d %H:%M") if note.get("time") else ""
    note["collected_at"] = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    ia = note["interact"]
    note["counts"] = counts_from_page(ia)
    note["missing_counts"] = [k for k in ("点赞", "收藏", "评论", "分享") if k not in note["counts"]]
    Path(wd, "note.json").write_text(json.dumps(note, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"采集完成 {note['kind']}：{note['title'] or '(无标题)'}")
    dup = find_existing(nid, wd)
    summary = {"workdir": wd, "platform": platform, "note_id": nid, "kind": note["kind"], "title": note["title"], "desc": note["desc"],
               "author": note["author"], "published": note["published"], "tags": note["tags"], "counts": note["counts"],
               "existing_record": dup}
    if dup and "--force" not in sys.argv:
        summary.update(media="表里已有这篇，跳过下载和转写；直接 push 只更新互动数据", seconds=round(time.time() - t0))
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return

    if note["images"]:
        download(note["images"][0], os.path.join(wd, "cover.webp"), platform)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "cover.webp", "cover.jpg"], cwd=wd, check=True)
    if note["kind"] == "图文":
        for i, u in enumerate(note["images"], 1):
            p = os.path.join(wd, f"img{i:02d}.webp")
            download(u, p)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", p, p[:-5] + ".jpg"], check=True)
            os.remove(p)
        info = f"{len(note['images'])} 张图已下载 (img01.jpg…)"
    else:
        last = "页面里没有带声音的视频地址"
        vp = os.path.join(wd, "video.mp4")
        hdr = "".join(f"{k}: {v}\r\n" for k, v in headers_for(platform).items())
        for s in note["streams"]:
            probe = subprocess.run(["ffprobe", "-v", "error", "-headers", hdr, "-select_streams", "a",
                                    "-show_entries", "stream=index", "-of", "csv=p=0", s["url"]],
                                   capture_output=True, text=True, timeout=60)
            if probe.returncode == 0 and not probe.stdout.strip():
                continue  # 远程确认没声音，跳过
            for u in [s["url"], *s["backup"]]:
                try:
                    log("下载视频", s["codec"], f"{(s['size'] or 0) / 1e6:.0f}MB")
                    download(u, vp, platform)
                    break
                except Exception as e:
                    last = e
            else:
                continue
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                    "-of", "csv=p=0", vp], capture_output=True, text=True)
            if probe.stdout.strip():
                last = None
                break
            log(s["codec"], "没有声音，换下一个")
            last = "所有视频格式都没有声音"
        if last is not None:
            raise SystemExit(f"视频下载失败: {last}")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "video.mp4", "-vn", "-ac", "1", "-ar", "16000", "audio.wav"],
                       cwd=wd, check=True)
        log("转写中…")
        prompt = "以下是普通话的句子，使用简体中文和全角标点。" + (note["title"] or "") + " " + " ".join(note["tags"])
        info = transcribe(os.path.join(wd, "audio.wav"), os.path.join(wd, "raw.txt"), prompt)
        # Default: local punctuation, no AI rewriting; raw timestamps retained for optional repair.
        punct_env = dict(os.environ)
        if PUNCT_MODEL:
            punct_env["XHS_PUNCT_MODEL"] = PUNCT_MODEL
        punct_result = subprocess.run(
            [WHISPER_PY, os.path.join(HERE, 'punctuate.py'),
             os.path.join(wd, 'raw.txt'), os.path.join(wd, 'reviewed.txt')],
            capture_output=True, text=True, encoding='utf-8', errors='replace', env=punct_env,
        )
        if punct_result.returncode:
            raise SystemExit('标点处理失败：' + punct_result.stderr[-1500:])
        log(punct_result.stdout.strip())
        os.remove(os.path.join(wd, "video.mp4"))
    summary.update(media=info, seconds=round(time.time() - t0))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def cmd_repair(wd, a, b, prompt=None):
    clip = os.path.join(wd, f"clip_{a}_{b}.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", a, "-to", b, "-i", "audio.wav", clip], cwd=wd, check=True)
    out = clip[:-4] + ".txt"
    transcribe(clip, out, prompt)
    print(open(out, encoding="utf-8").read())


def read_opt(wd, name):
    p = os.path.join(wd, name)
    return Path(p).read_text(encoding="utf-8").strip() if os.path.exists(p) else ""


def read_remote_record(wd, rid, fields, filename="verify.ndjson"):
    target = Path(wd, filename)
    target.unlink(missing_ok=True)
    args = ["base", "+record-get", "--base-token", BASE, "--table-id", TABLE, "--record-id", rid]
    for field in dict.fromkeys(fields):
        args += ["--field-id", field]
    result = lark(args + ["--format", "ndjson", "--output", filename, "--overwrite"], wd)
    if result.get("ok") is False or not target.exists():
        raise SystemExit("记录回读失败；保留工作目录")
    rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 1:
        raise SystemExit("记录回读数量不一致；保留工作目录")
    return rows[0]


def verify_remote_record(wd, rid, counts, expected_text, require_cover):
    fields = ["标题", "作者", "逐字稿", "封面", "采集时间", "发布日期", "笔记链接", "备注", *counts]
    for attempt in range(5):
        try:
            row = read_remote_record(wd, rid, fields)
            verify_record(row, rid, counts, expected_text, require_cover)
            return row
        except (ValueError, SystemExit):
            if attempt == 4:
                raise
            time.sleep(2)


def recover_pending(wd, note, title, body, counts):
    state = json.loads(Path(wd, 'write-state.json').read_text(encoding='utf-8'))
    if state.get('status') != 'written_unverified':
        raise SystemExit('未知写入状态，保留现场')
    rid = state['record_id']
    if rid not in find_existing(note['note_id'], wd):
        raise SystemExit('未验收记录与原笔记ID不匹配，不写入')
    if not body:
        raise SystemExit('恢复缺少 reviewed.txt，不写入')
    rec = {'平台': [note.get('platform', '小红书')], '标题': title, '类型': [note['kind']], **counts,
           '逐字稿': body, '作者': note['author'],
           '发布日期': note['published'], '笔记链接': note['clean_url'],
           '采集时间': note['collected_at'],
           '备注': make_remark(counts) + read_opt(wd, 'remark.txt')}
    Path(wd, 'recover.json').write_text(json.dumps({'update_records': {rid: rec}}, ensure_ascii=False), encoding='utf-8')
    result = lark(['base', '+record-batch-update', '--base-token', BASE,
                   '--table-id', TABLE, '--json', '@recover.json'], wd)
    if not result.get('ok'):
        raise SystemExit('恢复补写失败，保留现场：' + json.dumps(result, ensure_ascii=False))

    def read_row():
        return read_remote_record(wd, rid, ['标题', '作者', '逐字稿', '封面', *counts], 'recover-verify.ndjson')

    row = read_row()
    require_cover = os.path.exists(os.path.join(wd, 'cover.jpg'))
    if require_cover and not row.get('封面'):
        result = lark(['base', '+record-upload-attachment', '--base-token', BASE,
                       '--table-id', TABLE, '--record-id', rid,
                       '--field-id', '封面', '--file', './cover.jpg'], wd)
        if not result.get('ok'):
            raise SystemExit('恢复封面失败，保留现场：' + json.dumps(result, ensure_ascii=False))
        row = read_row()
    verify_remote_record(wd, rid, counts,
                         {'标题': title, '作者': note['author'], '逐字稿': body}, require_cover)
    for _ in range(5):
        shutil.rmtree(wd, ignore_errors=True)
        if not os.path.exists(wd):
            break
        time.sleep(1)
    print(json.dumps({'action': '恢复并验收入库', 'record_id': rid, 'title': title,
                      'cleaned': not os.path.exists(wd),
                      'url': f'https://feishu.cn/base/{BASE}'}, ensure_ascii=False))


def cmd_push(wd):
    require_base_table()
    note = json.loads(Path(wd, "note.json").read_text(encoding="utf-8"))
    body = read_opt(wd, "reviewed.txt")
    dup = find_existing(note["note_id"], wd)
    if not body and note["kind"] == "视频" and not dup:
        raise SystemExit("缺 reviewed.txt")
    title = read_opt(wd, "title.txt") or note["title"]
    counts = note["counts"]
    if os.path.exists(os.path.join(wd, 'write-state.json')):
        return recover_pending(wd, note, title, body, counts)
    # 标签：先补齐选项
    if note["tags"]:
        f = lark(["base", "+field-get", "--base-token", BASE, "--table-id", TABLE, "--field-id", "标签"], wd)
        fld = f.get("data", {}).get("field", f.get("data", {}))
        opts = [o["name"] for o in fld.get("options", [])]
        new = [t for t in note["tags"] if t not in opts]
        if new:
            spec = {"name": "标签", "type": "select", "multiple": True,
                    "options": [{"name": o} for o in opts + new]}
            Path(wd, "tagfield.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            r = lark(["base", "+field-update", "--base-token", BASE, "--table-id", TABLE, "--field-id", "标签",
                      "--json", "@tagfield.json", "--yes"], wd)
            if not r.get("ok"):
                raise SystemExit(f"加标签选项失败: {r}")
    stats = {**counts, "采集时间": note["collected_at"]}
    if dup:
        rid = dup[0]
        payload = {"update_records": {rid: stats}}
        Path(wd, "rec.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        r = lark(["base", "+record-batch-update", "--base-token", BASE, "--table-id", TABLE, "--json", "@rec.json"], wd)
        action = "已存在，只更新互动数据"
    else:
        rec = {"平台": [note.get("platform", "小红书")], "标题": title, "类型": [note["kind"]], **counts, "逐字稿": body, "作者": note["author"],
               "发布日期": note["published"], "笔记链接": note["clean_url"], "采集时间": note["collected_at"],
               "备注": make_remark(counts, '封面大字或正文首句' if read_opt(wd, 'title.txt') else '原作者标题')
                       + read_opt(wd, 'remark.txt')}
        if note["tags"]:
            rec["标签"] = note["tags"]
        Path(wd, "rec.json").write_text(json.dumps({"create_records": [rec]}, ensure_ascii=False), encoding="utf-8")
        for attempt in range(6):  # 新加的标签选项在飞书里生效有延迟，not_found 时等一下重试
            r = lark(["base", "+record-batch-create", "--base-token", BASE, "--table-id", TABLE, "--json", "@rec.json"], wd)
            if r.get("ok") or "800030005" not in json.dumps(r):
                break
            time.sleep(2 + attempt * 2)
        if not r.get("ok"):
            raise SystemExit(f"写入失败: {r}")
        rid = r["data"]["record_id_list"][0]
        save_write_state(wd, rid)  # persist before attachment upload so a crash can be resumed
        if os.path.exists(os.path.join(wd, "cover.jpg")):
            u = lark(["base", "+record-upload-attachment", "--base-token", BASE, "--table-id", TABLE, "--record-id", rid,
                      "--field-id", "封面", "--file", "./cover.jpg"], wd)
            if not u.get("ok"):
                raise SystemExit('记录已创建但封面上传失败，保留目录供续跑：' + json.dumps(u, ensure_ascii=False))
        action = "新增一行"
    if not r.get("ok"):
        raise SystemExit(f"写入失败: {r}")
    # Allow Feishu's asynchronous write visibility to settle before acceptance.
    expected_text = {} if dup else {"标题": title, "作者": note["author"], "逐字稿": body}
    require_cover = (not dup) and os.path.exists(os.path.join(wd, "cover.jpg"))
    try:
        verify_remote_record(wd, rid, counts, expected_text, require_cover)
    except ValueError as e:
        raise SystemExit(str(e) + "；保留工作目录")
    for _ in range(5):  # 入表成功后删掉整个临时文件夹；Windows 偶尔晚一点才释放文件，重试几次
        shutil.rmtree(wd, ignore_errors=True)
        if not os.path.exists(wd):
            break
        time.sleep(1)
    print(json.dumps({"action": action, "record_id": rid, "title": title, "cleaned": not os.path.exists(wd),
                      "url": f"https://feishu.cn/base/{BASE}"}, ensure_ascii=False))


def cmd_doctor(*_):
    """Offline configuration report. Never starts Chrome, calls lark or reads the network."""
    try:
        cfg = xhs_config.load()
    except xhs_config.ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2
    report = xhs_config.describe(cfg)
    print('小红书 → 飞书 配置诊断（离线，不联网、不采集、不写表）')
    print('说明：只检查配置项与本地文件/路径是否存在，不代表 GPU、飞书授权或模型权重完整可用。')
    print('config file:', report['config_file'], '' if report['config_file_exists'] else '(未找到)')
    for key, env_name in xhs_config.ENV_KEYS.items():
        value = report['values'].get(key)
        print(f"  {key:18} {value if value is not None else '(未设置)'}   [{env_name}]")
    if report['missing_required']:
        print('缺少必需项或仍为示例占位: ' + '、'.join(report['missing_required']) + '（fetch / push 会拒绝运行）')
    if report['missing_tools']:
        print('核心工具缺失（未配置或路径不存在，真实运行会失败）: ' + '、'.join(report['missing_tools']))
    for warning in report.get('warnings', []):
        print('提醒: ' + warning)
    print(json.dumps(report, ensure_ascii=False))
    not_ready = bool(report['missing_required'] or report['missing_tools'])
    return 1 if not_ready else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else ''
    if cmd in ('', '-h', '--help', 'help'):
        print(USAGE)
        return 0
    handlers = {'fetch': cmd_fetch, 'repair': cmd_repair, 'push': cmd_push, 'doctor': cmd_doctor}
    if cmd not in handlers:
        print(f'未知命令: {cmd}', file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    result = handlers[cmd](*argv[1:])
    return 0 if result is None else int(result)


if __name__ == "__main__":
    sys.exit(main())
