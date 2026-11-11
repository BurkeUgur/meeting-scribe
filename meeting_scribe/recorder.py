"""Records the computer's audio output (the remote side) and, optionally, the microphone (you)
in 2-minute WAV chunks.

To stop, drop a file named STOP into the recording folder (or run `scribe stop`).
"""
import argparse
import glob
import os
import threading
import time
import wave

import numpy as np
import soundcard as sc

from .common import RATE

BLOCK = RATE // 2   # read 0.5 s at a time
SILENCE = 0.003     # chunks whose peak stays below this are treated as silence and not saved


class Recorder:
    def __init__(self, folder, chunk_seconds=120):
        self.folder = folder
        self.chunk_seconds = chunk_seconds
        self.stop_file = os.path.join(folder, "STOP")
        os.makedirs(folder, exist_ok=True)
        start_file = os.path.join(folder, "start_time.txt")
        if os.path.exists(start_file):  # resuming in the same folder keeps the timeline
            with open(start_file) as f:
                self.t0 = float(f.read())
        else:
            self.t0 = time.time()
            with open(start_file, "w") as f:
                f.write(str(self.t0))
        # Several devices may record at once, so the chunk index is shared and locked
        self._lock = threading.Lock()
        self._index = {}

    def _next_index(self, who):
        with self._lock:
            if who not in self._index:
                self._index[who] = len(glob.glob(os.path.join(self.folder, f"{who}_*.wav")))
            n = self._index[who]
            self._index[who] += 1
            return n

    def _write(self, who, start, data):
        data = np.clip(data, -1, 1)
        pcm = (data * 32767).astype(np.int16)
        path = os.path.join(self.folder, f"{who}_{self._next_index(who):04d}_{start - self.t0:.1f}.wav")
        tmp = path + ".tmp"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        os.replace(tmp, path)  # so the transcriber never sees a half-written file

    def _heartbeat(self, who, state, device):
        with open(os.path.join(self.folder, f"status_{who}.txt"), "w", encoding="utf-8") as f:
            f.write(f"{time.time()}|{state}|{device}")
        print(f"[{who}] {time.strftime('%H:%M')} {state} ({device})", flush=True)

    def record(self, who, get_device):
        """get_device() -> (name, recording device). Switches over if the name changes
        (e.g. headphones plugged in)."""
        buf, chunk_start = [], time.time()
        while not os.path.exists(self.stop_file):
            try:
                name, device = get_device()
                print(f"[{who}] device: {name}", flush=True)
                last_check = time.time()
                with device.recorder(samplerate=RATE, channels=1, blocksize=1024) as rec:
                    while not os.path.exists(self.stop_file):
                        d = rec.record(numframes=BLOCK)
                        buf.append(d[:, 0] if d.ndim > 1 else d)
                        if time.time() - chunk_start >= self.chunk_seconds:
                            data = np.concatenate(buf)
                            silent = float(np.abs(data).max()) < SILENCE
                            if not silent:
                                self._write(who, chunk_start, data)
                            self._heartbeat(who, "silent" if silent else "audio", name)
                            buf, chunk_start = [], time.time()
                        if time.time() - last_check >= 3:
                            last_check = time.time()
                            if get_device()[0] != name:
                                print(f"[{who}] device changed", flush=True)
                                break
            except Exception as e:  # device unplugged etc.: wait a moment and retry
                print(f"[{who}] error: {e!r}, retrying", flush=True)
                time.sleep(1)
        if buf:
            data = np.concatenate(buf)
            if float(np.abs(data).max()) >= SILENCE:
                self._write(who, chunk_start, data)
        print(f"[{who}] stopped", flush=True)


def _default_output():
    spk = sc.default_speaker()
    return spk.name, sc.get_microphone(id=str(spk.name), include_loopback=True)


def _fixed_output(name):
    return lambda: (name, sc.get_microphone(id=str(name), include_loopback=True))


def _output_matching(part):
    def get():
        spk = next((s for s in sc.all_speakers() if part.lower() in s.name.lower()), sc.default_speaker())
        return spk.name, sc.get_microphone(id=str(spk.name), include_loopback=True)
    return get


def _microphone():
    m = sc.default_microphone()
    return m.name, m


def run(folder, device="all", mic=False, chunk_seconds=120):
    """device: 'all' (every output), 'default', or part of an output's name."""
    r = Recorder(folder, chunk_seconds)
    if device == "all":
        # Rather than guess which output the meeting uses, listen to all of them;
        # silent ones produce no files.
        targets = [_fixed_output(s.name) for s in sc.all_speakers()]
    elif device == "default":
        targets = [_default_output]
    else:
        targets = [_output_matching(device)]
    threads = [threading.Thread(target=r.record, args=("remote", t)) for t in targets]
    if mic:
        threads.append(threading.Thread(target=r.record, args=("me", _microphone)))
    else:
        print("Microphone recording off", flush=True)
    for t in threads:
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        open(r.stop_file, "w").close()
        for t in threads:
            t.join()
    with open(os.path.join(folder, "FINISHED"), "w") as f:
        f.write("ok")
    print("Recording finished.", flush=True)


def main():
    p = argparse.ArgumentParser(description="Record audio output in chunks.")
    p.add_argument("folder")
    p.add_argument("--device", default="all", help="'all', 'default', or part of an output's name")
    p.add_argument("--mic", action="store_true", help="Also record the microphone separately")
    p.add_argument("--chunk-seconds", type=int, default=120)
    a = p.parse_args()
    run(a.folder, a.device, a.mic, a.chunk_seconds)


if __name__ == "__main__":
    main()
