"""Small helpers shared by the recorder, transcriber and CLI."""
import os
import re

RATE = 16000  # sample rate Whisper expects

# Audio chunk names: <who>_<index>_<start seconds>.wav  (e.g. remote_0012_1349.5.wav)
CHUNK_PATTERN = re.compile(r"^(?P<who>[a-z]+)_(?P<idx>\d+)_(?P<start>\d+(?:\.\d+)?)\.wav$")


def chunk_info(path):
    """Return (who, start seconds) parsed from a chunk file name, or None if it doesn't match."""
    m = CHUNK_PATTERN.match(os.path.basename(path))
    if not m:
        return None
    return m.group("who"), float(m.group("start"))


def hms(t):
    t = int(t)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def read_glossary(path):
    """Turn a glossary file (one term per line, # for comments) into a one-line Whisper prompt."""
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        terms = [s.strip() for s in f if s.strip() and not s.lstrip().startswith("#")]
    return ", ".join(terms) + "." if terms else None


def recording_finished(folder):
    return os.path.exists(os.path.join(folder, "FINISHED"))
