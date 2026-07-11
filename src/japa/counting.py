"""Pure chant-counting logic — no microphone or models, so it is unit-testable.

The one non-obvious piece: a chanter often repeats a short mantra several
times in a single breath, which VoiceRecorder captures as one utterance.
detect_repetitions() therefore scores the captured IPA against k
concatenated copies of the reference for k = 1..max_reps and keeps the
best-scoring k, so one utterance can legitimately count for several beads.
"""

from dataclasses import dataclass, field


def detect_repetitions(
    utterance_ipa: str,
    references: str | list[str],
    matcher,
    threshold: float,
    max_reps: int = 8,
) -> tuple[int, float]:
    """Return (repetitions, best_score) for one captured utterance.

    `references` may be one reference IPA string or several (e.g. the
    built-in reference plus trained renditions of the chanter's own
    voice); the utterance is scored against all of them and the best
    match wins. repetitions is 0 when nothing scored at or above
    `threshold`; best_score is still returned so the caller can show
    how close it was.
    """
    if isinstance(references, str):
        references = [references]
    best_k, best_score = 0, -1.0
    for reference_ipa in references:
        for k in range(1, max_reps + 1):
            candidate = " ".join([reference_ipa] * k)
            s = matcher.score(utterance_ipa, candidate)
            if s > best_score:
                best_k, best_score = k, s
    if best_score >= threshold:
        return best_k, best_score
    return 0, best_score


@dataclass
class MantraProgress:
    """Running tally for one mantra within a session."""

    title: str
    target: int
    count: int = 0
    attempts: int = 0
    scores: list[float] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return self.count >= self.target

    @property
    def average_score(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else 0.0

    def register(self, repetitions: int, score: float) -> None:
        self.attempts += 1
        if repetitions > 0:
            # Never overshoot the target: a multi-repetition breath near the
            # end only counts up to the beads that remain.
            self.count = min(self.count + repetitions, self.target)
            self.scores.append(score)


def render_beads(count: int, target: int, width: int = 27) -> str:
    """Render progress as a compact mala strand, e.g. ●●●●○○○ 34/108."""
    filled = round(width * count / target) if target else width
    filled = min(filled, width)
    return "●" * filled + "○" * (width - filled) + f"  {count}/{target}"
