"""Local punctuation only; refuses non-whitespace character changes.

Model path comes from ``XHS_PUNCT_MODEL`` (no default model is bundled; the
operator points it at their pre-placed CT-Transformer ONNX file). Run with the
ASR venv interpreter:

    <whisper-python> punctuate.py raw.txt reviewed.txt
"""
import os
import re
import sys
import time
from pathlib import Path
import sherpa_onnx

PUNCT = '，。？！、,.?!：:；;'


def words(text):
    return ''.join(c for c in text if not c.isspace() and c not in PUNCT)


def model_path():
    path = os.environ.get('XHS_PUNCT_MODEL', '').strip()
    if not path:
        raise SystemExit('未配置标点模型：请设置 XHS_PUNCT_MODEL 指向 CT-Transformer ONNX 文件'
                         '（或写入 config.local.json 的 punct_model；见 docs/CONFIGURATION.md）。')
    return path


def main(src, dst):
    raw = Path(src).read_text(encoding='utf-8')
    segments = re.findall(r'^\[\s*[\d.]+-\s*[\d.]+\]\s*(.*)$', raw, re.M)
    if not segments:
        raise ValueError('No timestamped transcription segments found')
    original = ' '.join(segments)
    text = ''.join(c for c in original if c not in PUNCT)
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s+|\s+(?=[\u4e00-\u9fff])', '', text)
    t0 = time.perf_counter()
    config = sherpa_onnx.OfflinePunctuationConfig(model=sherpa_onnx.OfflinePunctuationModelConfig(
        ct_transformer=model_path(), num_threads=4))
    punct = sherpa_onnx.OfflinePunctuation(config)
    result = punct.add_punctuation(text).replace(',', '，').replace('?', '？').replace('!', '！')
    sentences = re.findall(r'[^。？！]*[。？！]|[^。？！]+$', result)
    paras, cur = [], ''
    for sentence in sentences:
        cur += sentence
        if len(cur) >= 180:
            paras.append(cur.strip())
            cur = ''
    if cur.strip():
        paras.append(cur.strip())
    result = '\n\n'.join(paras)
    if words(original) != words(result):
        raise ValueError('Punctuation changed source characters; output refused')
    Path(dst).write_text(result + '\n', encoding='utf-8')
    print(f'punctuation verified: {time.perf_counter()-t0:.2f}s; {len(paras)} paragraphs')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
