import json
import re
from pathlib import Path

COUNT_FIELDS = {
    '点赞': 'likedCount', '收藏': 'collectedCount',
    '评论': 'commentCount', '分享': 'shareCount',
}


def counts_from_page(interact):
    result = {}
    for label, key in COUNT_FIELDS.items():
        value = interact.get(key)
        if value is None or str(value).strip() == '':
            if label == '评论':
                result[label] = 0
            continue
        match = re.fullmatch(r'([\d]+(?:\.[\d]+)?)\s*([万wWkK千]?)',
                             str(value).replace(',', '').strip())
        if not match:
            continue
        scale = {'万': 10000, 'w': 10000, 'W': 10000, 'k': 1000, 'K': 1000, '千': 1000}.get(match[2], 1)
        result[label] = int(round(float(match[1]) * scale))
    return result


def make_remark(counts, title_source='原作者标题'):
    missing = [name for name in COUNT_FIELDS if name not in counts]
    parts = ['本地转写 + 标点模型，未做AI全文校对', '标题来源：' + title_source]
    if missing:
        parts.append('、'.join(missing) + '未显示，字段留空')
    return '；'.join(parts) + '。'


def verify_record(row, record_id, counts, expected_text, require_cover):
    if row.get('record_id') != record_id:
        raise ValueError('回读 record_id 不一致')
    for field, expected in {**counts, **expected_text}.items():
        if row.get(field) != expected:
            raise ValueError('回读字段不一致：' + field)
    if require_cover and not row.get('封面'):
        raise ValueError('封面未写入')


def save_write_state(workdir, record_id):
    path = Path(workdir) / 'write-state.json'
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'record_id': record_id, 'status': 'written_unverified'}), encoding='utf-8')
    tmp.replace(path)


def platform_of(text):
    return '抖音' if 'douyin.com' in text else '小红书'


def profile_debug_port(profile_dir):
    """Chrome writes the real debugging port here when started with --remote-debugging-port=0."""
    try:
        first = Path(profile_dir, 'DevToolsActivePort').read_text(encoding='utf-8').splitlines()[0]
        return int(first.strip())
    except (OSError, ValueError, IndexError):
        return None


def douyin_note(detail):
    """Map Douyin aweme_detail to the same note shape the Xiaohongshu flow uses."""
    aid = str(detail['aweme_id'])
    desc = (detail.get('desc') or '').strip()
    title = (detail.get('preview_title') or '').strip() or re.sub(r'#\S+', '', desc).strip()
    s = detail.get('statistics') or {}
    v = detail.get('video') or {}
    mp4 = sorted((b for b in v.get('bit_rate') or [] if b.get('format') == 'mp4'),
                 key=lambda b: b.get('bit_rate') or 0)
    streams = []
    for b in mp4:
        urls = (b.get('play_addr') or {}).get('url_list') or []
        if urls:
            streams.append({'codec': f"mp4-{b.get('bit_rate')}", 'url': urls[0], 'backup': urls[1:],
                            'size': (b.get('play_addr') or {}).get('data_size') or 0})
    default = (v.get('play_addr') or {}).get('url_list') or []
    if default:
        streams.append({'codec': 'default', 'url': default[0], 'backup': default[1:], 'size': 0})
    cover = ((v.get('origin_cover') or v.get('cover') or {}).get('url_list') or [])[:1]
    return {
        'platform': '抖音', 'note_id': aid, 'href': f'https://www.douyin.com/video/{aid}',
        'title': title, 'desc': desc, 'type': 'video',
        'author': (detail.get('author') or {}).get('nickname') or '',
        'time': (detail.get('create_time') or 0) * 1000 or None, 'ip': detail.get('ip_attribution') or '',
        'interact': {'likedCount': s.get('digg_count'), 'collectedCount': s.get('collect_count'),
                     'commentCount': s.get('comment_count'), 'shareCount': s.get('share_count')},
        'tags': [t['hashtag_name'] for t in detail.get('text_extra') or [] if t.get('hashtag_name')],
        'images': cover, 'streams': streams,
    }
