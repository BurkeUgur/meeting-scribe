# meeting-scribe

[Türkçe](README.tr.md)

Records whatever your computer plays during an online meeting (Interactio, Zoom, Teams, Webex, ...) and transcribes it locally with Whisper. It doesn't join the meeting or add a bot: it captures the audio going to your speakers. Everything runs on your machine; no audio leaves it.

- Audio is saved in 2-minute chunks. Silent stretches (breaks) are not saved.
- Transcription runs alongside the recording, and the transcript is updated after every chunk.
- All audio outputs are captured at once, so switching to headphones or an external speaker mid-meeting doesn't break the recording.
- If the floor audio comes through instead of the interpretation channel and the speaker uses Arabic or French, those parts are also transcribed in their original language with a multilingual model.

> Tested on Windows only. Capturing audio output relies on the loopback support of the `SoundCard` library, which macOS doesn't provide.

## Install

Requires Python 3.9 or newer.

```
pip install git+https://github.com/BurkeUgur/meeting-scribe.git
```

Models download automatically on first use: `small.en` for the main language (~500 MB) and `large-v3` for Arabic/French (~3 GB).

## Usage

```
scribe devices     # list audio outputs and show which one is playing sound
scribe start       # start recording and transcription in the background
scribe status      # show progress and the last lines of the transcript
scribe stop        # stop recording; transcription finishes the remaining chunks and exits
```

Run `scribe start` before the meeting begins. Silent stretches aren't saved, so starting early costs nothing. Recordings go to `recordings/<date>/` by default.

Common options for `scribe start`:

| Option | Description |
|---|---|
| `--dir D:\meetings\day1` | Recording folder |
| `--glossary glossary.txt` | Names and acronyms to spell correctly, one per line (see `glossary_example.txt`) |
| `--lang de --model small` | If the main language isn't English. `small.en` is English-only; for other languages use `small`, `medium` or `large-v3` |
| `--extra-langs ""` | Turns off the Arabic/French pass. That pass is slow: a 2-minute chunk takes about 3-4 minutes on CPU |
| `--mic` | Also records your own microphone; it appears as `ME` in the transcript |
| `--device Speakers` | Only capture the output whose name contains this text |

## Output files

| File | Contents |
|---|---|
| `transcript.txt` | `[hh:mm:ss] REMOTE: text`. Times count from the start of the recording; the start time is stored in `start_time.txt` |
| `transcript_other.txt` | Arabic/French parts, in the original language |
| `remote_XXXX_<sec>.wav` | Audio chunks |
| `*_log.txt` | Output of each background process; the first place to look if something goes wrong |

If the processes are interrupted, run `scribe start --dir ...` again with the same folder. The timeline and already processed chunks are kept.

## Taking notes with Claude Code

The transcript is raw text. To turn it into readable notes during the meeting, open [Claude Code](https://claude.com/claude-code) and ask something like:

> Follow `recordings/2026-11-10/transcript.txt`. As new lines arrive, write notes to `notes.md` with headings per session and speaker. Arabic parts are in `transcript_other.txt`.

If there is an agenda PDF, share it too. Speaker names and session titles come out more accurate that way.

## Known limitations

- There's no speaker separation: all remote audio is labelled `REMOTE`, and speakers have to be inferred from context.
- Accented English is sometimes detected as another language. That's why the second pass only handles the languages listed in `--extra-langs`.
- Nothing is recorded if the system volume is muted or the meeting tab is muted. Check with `scribe devices`.
- You are responsible for getting consent from the participants and the organiser before recording a meeting.

## License

MIT. See [LICENSE](LICENSE).
