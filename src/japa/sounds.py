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
    """Two soft descending low tones — corrective, not harsh."""
    return _chime([311.1, 233.1], [0.18, 0.28], gap=0.07)


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
    """Plays the cues above when enabled; every method no-ops when not."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def _play(self, wave: np.ndarray) -> None:
        if not self.enabled:
            return
        try:
            import sounddevice as sd
            # Trailing silence matters: sd.wait() returns when the buffer is
            # handed to the device, and closing the stream then can swallow
            # the tail of a short tone before it physically plays. Padding
            # means anything clipped is silence.
            padded = np.concatenate(
                [wave, np.zeros(int(SAMPLE_RATE * 0.35), dtype=np.float32)]
            )
            sd.play(padded, SAMPLE_RATE)
            sd.wait()
            # Guard delay: let the hardware finish physically emitting the
            # tail before the caller opens the mic or plays the next cue —
            # sd.wait() alone returns slightly too early.
            time.sleep(0.15)
        except Exception:
            pass  # audio out is best-effort; never break the chant loop

    def ready(self) -> None:
        self._play(ready_wave())

    def wrong(self) -> None:
        self._play(wrong_wave())

    def mantra_complete(self) -> None:
        self._play(mantra_complete_wave())

    def session_complete(self) -> None:
        self._play(session_complete_wave())
