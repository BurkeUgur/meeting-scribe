"""The `scribe` command: starts recording and transcription in the background, stops them,
and shows progress."""
import argparse
import datetime
import glob
import os
import subprocess
import sys
import time

from .common import chunk_info


def _folder(a):
    f = a.dir or os.path.join("recordings", datetime.date.today().isoformat())
    return os.path.abspath(f)


def _spawn(folder, name, module, *args):
    """Start a module as a separate, windowless process; its output goes to <name>_log.txt."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    log = open(os.path.join(folder, f"{name}_log.txt"), "a", encoding="utf-8")
    p = subprocess.Popen([sys.executable, "-u", "-m", f"meeting_scribe.{module}", folder, *args],
                         stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=flags,
                         start_new_session=(os.name != "nt"))
    with open(os.path.join(folder, f"{name}.pid"), "w") as f:
        f.write(str(p.pid))
    print(f"  {name}: started (pid {p.pid})")


def start(a):
    folder = _folder(a)
    os.makedirs(folder, exist_ok=True)
    for leftover in ("STOP", "FINISHED"):  # from a previous stop
        path = os.path.join(folder, leftover)
        if os.path.exists(path):
            os.remove(path)
    print(f"Recording folder: {folder}")
    rec_args = ["--device", a.device] + (["--mic"] if a.mic else [])
    _spawn(folder, "recorder", "recorder", *rec_args)
    main_args = ["--mode", "main", "--lang", a.lang] + (["--model", a.model] if a.model else [])
    if a.glossary:
        main_args += ["--glossary", os.path.abspath(a.glossary)]
    _spawn(folder, "transcriber", "transcriber", *main_args)
    if a.extra_langs:
        _spawn(folder, "transcriber_other", "transcriber", "--mode", "other", "--langs", a.extra_langs)
    print("To stop: scribe stop" + (f' --dir "{a.dir}"' if a.dir else ""))


def stop(a):
    folder = _folder(a)
    open(os.path.join(folder, "STOP"), "w").close()
    print("Stopping recording...")
    for _ in range(30):
        if os.path.exists(os.path.join(folder, "FINISHED")):
            print("Recording stopped. Transcription will exit once the remaining chunks are done.")
            return
        time.sleep(1)
    print("The recorder did not respond within 30 s; check with 'scribe status'.")


def status(a):
    folder = _folder(a)
    if not os.path.isdir(folder):
        print(f"No such folder: {folder}")
        return
    chunks = [p for p in glob.glob(os.path.join(folder, "*.wav")) if chunk_info(p)]
    done = 0
    path = os.path.join(folder, "processed.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            done = len(f.read().split())
    finished = os.path.exists(os.path.join(folder, "FINISHED"))
    print(f"Folder: {folder}")
    print(f"Recording: {'finished' if finished else 'running'}")
    for s in sorted(glob.glob(os.path.join(folder, "status_*.txt"))):
        with open(s, encoding="utf-8") as f:
            t, state, device = f.read().split("|", 2)
        print(f"  last check {time.strftime('%H:%M:%S', time.localtime(float(t)))}: {state} ({device})")
    print(f"Audio chunks: {len(chunks)}, transcribed: {done}")
    tr = os.path.join(folder, "transcript.txt")
    if os.path.exists(tr):
        with open(tr, encoding="utf-8") as f:
            lines = f.read().strip().splitlines()[-a.tail:]
        print("--- end of transcript ---")
        print("\n".join(lines))


def devices(a):
    """List audio outputs and listen briefly to show which one is playing sound."""
    import numpy as np
    import soundcard as sc
    default = sc.default_speaker().name
    print(f"Listening for {a.seconds} s...")
    for s in sc.all_speakers():
        m = sc.get_microphone(id=str(s.name), include_loopback=True)
        with m.recorder(samplerate=16000, channels=1) as r:
            d = r.record(numframes=16000 * a.seconds)
        peak = float(np.abs(d).max())
        mark = " (default)" if s.name == default else ""
        print(f"  {'AUDIO' if peak >= 0.003 else 'silent':6} peak={peak:.4f}  {s.name}{mark}")


def main():
    p = argparse.ArgumentParser(prog="scribe", description="Record and transcribe a meeting.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("start", help="Start recording and transcription in the background")
    s.add_argument("--dir", help="Recording folder (default: recordings/<today>)")
    s.add_argument("--device", default="all", help="'all' (default), 'default', or part of an output's name")
    s.add_argument("--mic", action="store_true", help="Also record your own microphone")
    s.add_argument("--lang", default="en", help="Main spoken language (default: en)")
    s.add_argument("--model", help="Whisper model for the main language (default: small.en)")
    s.add_argument("--glossary", help="File of names/acronyms to spell correctly")
    s.add_argument("--extra-langs", default="ar,fr",
                   help="Also transcribe these languages with a multilingual model (default: ar,fr; '' to disable)")
    s.set_defaults(f=start)

    t = sub.add_parser("stop", help="Stop recording")
    t.add_argument("--dir")
    t.set_defaults(f=stop)

    u = sub.add_parser("status", help="Show recording and transcription progress")
    u.add_argument("--dir")
    u.add_argument("--tail", type=int, default=10, help="Number of transcript lines to show")
    u.set_defaults(f=status)

    d = sub.add_parser("devices", help="List audio outputs and check which one has sound")
    d.add_argument("--seconds", type=int, default=3)
    d.set_defaults(f=devices)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
