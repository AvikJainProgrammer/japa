"""Optional audio feedback for chanting sessions (--audio).

All cues are short sine tones synthesized with numpy and played through
sounddevice — no sound files. The wave-building functions are pure and
unit-testable; AudioFeedback wraps them behind an enabled flag and plays
best-effort, so a missing/busy output device can never break a session.

Cues:
  ready    — one soft tone: the recorder is about to listen, chant now
  wrong    — two gentle descending low tones: that chant wasn't counted
  mantra_complete  — short ascending chime: one mantra's target reached
  session_complete — fuller happy arpeggio: the whole japa is done
"""

import time

import numpy as np

# Must match VoiceRecorder's rate: if playback and recording use different
# sample rates, macOS reconfigures the audio device on every play->listen
# switch, which cuts off any tone still draining to the speaker.
SAMPLE_RATE = 16000
VOLUME = 0.25


def _tone(freq: float, duration: float, volume: float = VOLUME) -> np.ndarray:
    """One warm sine note with a soft attack and exponential decay."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    wave = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t)
    attack = np.minimum(t / 0.015, 1.0)  # 15 ms fade-in avoids clicks
    decay = np.exp(-3.5 * t / duration)
    return (wave * attack * decay * volume).astype(np.float32)


def _chime(freqs: list[float], durations: list[float], gap: float = 0.0) -> np.ndarray:
    """Consecutive notes; `gap` seconds of silence between them keeps notes
    perceptually distinct (without it, adjacent low tones blur into one)."""
    silence = np.zeros(int(SAMPLE_RATE * gap), dtype=np.float32)
    parts: list[np.ndarray] = []
    for i, (f, d) in enumerate(zip(freqs, durations)):
        if i and gap:
            parts.append(silence)
        parts.append(_tone(f, d))
    return np.concatenate(parts)


def ready_wave() -> np.ndarray:
    """A single soothing tone (528 Hz)."""
    return _tone(528.0, 0.35)


def wrong_wave() -> np.ndarray:
    """Three clearly distinct descending notes — corrective, not harsh.
    Kept very distinct (stepwise fall, audible gaps) so truncation bugs —
    a cue partly swallowed around mic transitions — are immediately
    noticeable by ear."""
    return _chime([523.25, 392.0, 261.63], [0.2, 0.2, 0.3], gap=0.12)


def mantra_complete_wave() -> np.ndarray:
    """Short ascending major chime (C5 E5 G5)."""
    return _chime([523.25, 659.25, 783.99], [0.18, 0.18, 0.34])


def session_complete_wave() -> np.ndarray:
    """Fuller happy arpeggio up to C6 with a lingering final note."""
    return _chime(
        [523.25, 659.25, 783.99, 1046.5, 783.99, 1046.5],
        [0.18, 0.18, 0.18, 0.36, 0.18, 0.7],
    )


class AudioFeedback:
    """Plays the cues above when enabled; every method no-ops when not.

    Uses ONE persistent output stream for the whole session instead of
    sounddevice's per-play streams: opening a fresh output stream right
    after the mic stream closes makes macOS ramp/reconfigure the device,
    which audibly swallows the start (and sometimes end) of short cues.
    A stream that stays open has no such transitions.
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._out = None

    def _stream(self):
        if self._out is None:
            import sounddevice as sd
            self._out = sd.OutputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32"
            )
            self._out.start()
            # Prime with silence so the device's power-up ramp swallows
            # nothing audible from the first real cue.
            self._out.write(np.zeros((int(SAMPLE_RATE * 0.25), 1), dtype=np.float32))
        return self._out

    def _play(self, wave: np.ndarray) -> None:
        if not self.enabled:
            return
        try:
            # Trailing silence: write() returns when the buffer is handed
            # to the device, slightly before the tail physically plays, so
            # pad with silence and add a small guard delay to guarantee the
            # cue has fully sounded before the caller opens the mic.
            padded = np.concatenate(
                [wave, np.zeros(int(SAMPLE_RATE * 0.15), dtype=np.float32)]
            )
            self._stream().write(padded.reshape(-1, 1))
            time.sleep(0.1)
        except Exception:
            self._out = None  # retry with a fresh stream on the next cue
            # audio out is best-effort; never break the chant loop

    def close(self) -> None:
        if self._out is not None:
            try:
                self._out.stop()
                self._out.close()
            except Exception:
                pass
            self._out = None

    def ready(self) -> None:
        self._play(ready_wave())

    def wrong(self) -> None:
        self._play(wrong_wave())

    def mantra_complete(self) -> None:
        self._play(mantra_complete_wave())

    def session_complete(self) -> None:
        self._play(session_complete_wave())
