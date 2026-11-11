"""Transcribes new audio chunks in a recording folder and keeps a time-ordered transcript.

Two modes:
- main (default): transcribes every chunk in one language (e.g. English) with a fast model
  -> transcript.txt
- other: detects each chunk's language and transcribes only the chosen ones (e.g. Arabic,
  French) in their original language with a large multilingual model -> transcript_other.txt
  Useful when the floor audio comes through instead of the interpretation channel.

Exits on its own once recording has finished and every chunk is processed.
"""
import argparse
import glob
import json
import os
import time
import wave

import numpy as np
from faster_whisper import WhisperModel

from .common import chunk_info, hms, read_glossary, recording_finished

LABEL = {"remote": "REMOTE", "me": "ME"}


class Transcript:
    """Segments plus the list of processed files; resumes where it left off after a restart."""

    def __init__(self, folder, suffix=""):
        self.folder = folder
        self.seg_path = os.path.join(folder, f"segments{suffix}.json")
        self.done_path = os.path.join(folder, f"processed{suffix}.txt")
        self.text_path = os.path.join(folder, f"transcript{suffix}.txt")
        self.segments = []
        if os.path.exists(self.seg_path):
            with open(self.seg_path, encoding="utf-8") as f:
                self.segments = json.load(f)
        self.done = set()
        if os.path.exists(self.done_path):
            with open(self.done_path, encoding="utf-8") as f:
                self.done = set(f.read().split())

    def new_chunks(self, not_before=0.0):
        chunks = []
        for path in glob.glob(os.path.join(self.folder, "*.wav")):
            info = chunk_info(path)
            if info and os.path.basename(path) not in self.done and info[1] >= not_before:
                chunks.append((info[1], path, info[0]))
        return [(path, who, start) for start, path, who in sorted(chunks)]

    def add(self, file, who, start, segments, lang=None):
        for s in segments:
            text = s.text.strip()
            if text:
                item = {"file": file, "who": who, "t": start + s.start, "text": text}
                if lang:
                    item["lang"] = lang
                self.segments.append(item)

    def mark_done(self, file):
        self.done.add(file)
        with open(self.done_path, "a", encoding="utf-8") as f:
            f.write(file + "\n")
        self.save()

    def save(self):
        with open(self.seg_path, "w", encoding="utf-8") as f:
            json.dump(self.segments, f, ensure_ascii=False)
        lines = []
        for s in sorted(self.segments, key=lambda s: s["t"]):
            lang = f" ({s['lang']})" if s.get("lang") else ""
            lines.append(f"[{hms(s['t'])}] {LABEL.get(s['who'], s['who'])}{lang}: {s['text']}")
        with open(self.text_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def read_audio(path):
    with wave.open(path, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def run_main(folder, model="small.en", lang="en", glossary=None, poll=10):
    m = WhisperModel(model, device="cpu", compute_type="int8")
    prompt = read_glossary(glossary)
    tr = Transcript(folder)
    while True:
        new = tr.new_chunks()
        for path, who, start in new:
            segments, _ = m.transcribe(read_audio(path), language=lang, vad_filter=True, beam_size=5,
                                       initial_prompt=prompt)
            tr.add(os.path.basename(path), who, start, segments)
            tr.mark_done(os.path.basename(path))
            print("processed:", os.path.basename(path), flush=True)
        if recording_finished(folder) and not new:
            tr.save()
            print("All chunks processed.", flush=True)
            return
        time.sleep(poll)


def run_other(folder, langs=("ar", "fr"), model="large-v3", not_before=0.0, poll=10):
    # The tiny model only detects the language. Accented English is sometimes detected as
    # another language, so only the requested languages go to the slow large model.
    detector = WhisperModel("tiny", device="cpu", compute_type="int8")
    big = WhisperModel(model, device="cpu", compute_type="int8")
    tr = Transcript(folder, "_other")
    while True:
        new = tr.new_chunks(not_before)
        for path, who, start in new:
            audio = read_audio(path)
            _, info = detector.transcribe(audio, vad_filter=True)
            if info.language in langs and info.language_probability > 0.5:
                segments, _ = big.transcribe(audio, language=info.language, vad_filter=True, beam_size=1)
                tr.add(os.path.basename(path), who, start, segments, lang=info.language)
            tr.mark_done(os.path.basename(path))
            print(f"processed (other): {os.path.basename(path)} lang={info.language}", flush=True)
        if recording_finished(folder) and not new:
            tr.save()
            print("All chunks processed (other).", flush=True)
            return
        time.sleep(poll)


def main():
    p = argparse.ArgumentParser(description="Transcribe recorded chunks.")
    p.add_argument("folder")
    p.add_argument("--mode", choices=["main", "other"], default="main")
    p.add_argument("--model", help="Whisper model (main: small.en, other: large-v3)")
    p.add_argument("--lang", default="en", help="Spoken language for main mode")
    p.add_argument("--langs", default="ar,fr", help="Comma-separated languages for other mode")
    p.add_argument("--glossary", help="Names/acronyms to spell correctly (one term per line)")
    p.add_argument("--not-before", type=float, default=0.0, help="other mode: skip chunks before this second")
    a = p.parse_args()
    if a.mode == "main":
        run_main(a.folder, a.model or "small.en", a.lang, a.glossary)
    else:
        run_other(a.folder, tuple(a.langs.split(",")), a.model or "large-v3", a.not_before)


if __name__ == "__main__":
    main()
