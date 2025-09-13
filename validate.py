import cv2, numpy as np, pytesseract, re
from PIL import Image
import difflib

KEYWORDS = ['GOVERNMENT', 'INDIA', 'INCOME', 'TAX', 'DEPARTMENT',
            'ACCOUNT', 'PERMANENT', 'CARD', 'PASSPORT', 'DRIVING',
            'LICENCE', 'VOTER', 'IDENTITY']

PAN_RE = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')

def variance_of_laplacian(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def ocr_with_tsv(image):
    pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    data = pytesseract.image_to_data(pil, output_type=pytesseract.Output.DICT)
    results = []
    for i in range(len(data['text'])):
        txt = data['text'][i].strip()
        if txt:
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 50
            results.append({'text': txt, 'conf': conf})
    return results

def fuzzy_keywords(words, keywords=KEYWORDS, cutoff=0.65):
    found = []
    texts = [w['text'].upper() for w in words]
    for t in texts:
        for k in keywords:
            if difflib.SequenceMatcher(None, t, k).ratio() > cutoff:
                found.append(k)
    return list(set(found))

def loose_pan_match(words):
    for w in words:
        t = re.sub(r'[^A-Z0-9]', '', w['text'].upper())
        if PAN_RE.match(t):
            return True, t
        if re.search(r'[A-Z]{3,}', t) and re.search(r'[0-9]{3,}', t):
            return True, t
    return False, None

def validate_document(image_path):
    img = cv2.imread(image_path)
    h,w = img.shape[:2]
    score = 0
    penalties, signals = [], []

    if max(h,w) < 800:
        scale = 1000 / max(h,w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        penalties.append("low_res")
        score -= 5

    sharpness = variance_of_laplacian(img)
    if sharpness < 40:
        penalties.append("blurry")
        score -= 10
    else:
        score += 15
        signals.append("sharp")

    words = ocr_with_tsv(img)
    texts = [w['text'].upper() for w in words]

    keywords = fuzzy_keywords(words)
    if keywords:
        score += min(40, 8*len(keywords))
        signals.append("keywords")

    pan_found, pan_val = loose_pan_match(words)
    if pan_found:
        score += 25
        signals.append("pan_pattern")

    upper_ratio = sum(t.isupper() for t in texts) / max(1,len(texts))
    if upper_ratio > 0.5:
        score += 10
        signals.append("mostly_upper")

    if len(words) > 20:
        score += 15
        signals.append("text_dense")

    score = max(0, min(100, score))

    if score >= 43:
        decision = 'accept'
    elif score >= 35:
        decision = 'review'
    else:
        decision = 'reject'

    return {
        'decision': decision,
        'score': score,
        'sharpness': sharpness,
        'keywords': keywords,
        'pan_found': pan_found,
        'pan_value': pan_val,
        'signals': signals,
        'penalties': penalties,
        'ocr_word_count': len(words),
        'upper_ratio': upper_ratio
    }
