import re
import pandas as pd
import easyocr

# Initialize once (English)
_reader = easyocr.Reader(["en"])  # this may take a few seconds the first time

# Matches: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY/MM/DD, also D/M/YY variants
_DATE_REGEX = re.compile(
    r"\b((?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(?:\d{4}[/-]\d{1,2}[/-]\d{1,2}))\b"
)

# common keywords near expiry text to prioritize
_PRIORITY_WORDS = {"exp", "expiry", "expires", "best", "before", "use", "bb", "mfg", "manufacture"}

def extract_expiry_date(image_path):
    """Return (date, raw_text) if found, else (None, full_text)."""
    results = _reader.readtext(image_path, detail=1)
    candidates = []
    full_text = []

    for bbox, text, conf in results:
        t = text.strip()
        if not t:
            continue
        full_text.append(t)
        m = _DATE_REGEX.search(t)
        if m:
            score = conf
            lower = t.lower()
            # boost if line contains expiry-related words
            if any(w in lower for w in _PRIORITY_WORDS):
                score += 0.1
            candidates.append((m.group(0), score))

    # Sort by confidence/priority
    candidates.sort(key=lambda x: x[1], reverse=True)

    for raw, _ in candidates:
        # Try parsing with dayfirst=True then False
        for dayfirst in (True, False):
            try:
                dt = pd.to_datetime(raw, dayfirst=dayfirst, errors="raise").date()
                from datetime import date, timedelta
                # sanity check: past dates far in the past are probably MFG; keep if >= today-7
                if dt < date.today() - timedelta(days=7):
                    continue
                return dt, "\n".join(full_text)
            except Exception:
                pass

    return None, "\n".join(full_text)
