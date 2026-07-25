"""Pure chant-counting logic — no microphone or models, so it is unit-testable.

The one non-obvious piece: a chanter often repeats a short mantra several
times in a single breath, which VoiceRecorder captures as one utterance.
detect_repetitions() therefore scores the captured IPA against k
concatenated copies of the reference for k = 1..max_reps and keeps the
best-scoring k, so one utterance can legitimately count for several beads.

Flow mode (--flow) goes further: one utterance may span *different*
consecutive parts — e.g. the next several names of a namavali.
consume_sequence() slices the utterance greedily, part by part, each part
matched by best_prefix_match() against any of its acceptable references
(built-in IPA plus trained renditions), and stops at the first part that
falls below the threshold — so a mistake on name 2 blocks name 3 even if
name 3 itself was said correctly.
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


def best_prefix_match(utterance: str, reference: str) -> tuple[float, int]:
    """Score the best-matching *prefix* of `utterance` against `reference`.

    Returns (score, chars_consumed). One semi-global Levenshtein pass
    yields the edit distance from `reference` to every prefix of
    `utterance`; each is normalized exactly like voicekit's MatchingAlgo
    ((1 - distance / max(len)) * 100), so scores stay comparable with
    whole-utterance matching and share the same --threshold. Ties prefer
    the prefix closest in length to the reference, so an exact repetition
    ("durga durga...") consumes exactly one copy.
    """
    u = utterance.lower()
    r = reference.lower().strip()
    m, n = len(r), len(u)
    if m == 0:
        return 0.0, 0
    prev = list(range(n + 1))  # distance("", u[:j]) = j
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        rc = r[i - 1]
        for j in range(1, n + 1):
            cur[j] = min(
                prev[j] + 1,  # skip a reference char
                cur[j - 1] + 1,  # skip an utterance char
                prev[j - 1] + (rc != u[j - 1]),
            )
        prev = cur
    best_score, best_j = -1.0, 0
    for j, dist in enumerate(prev):
        score = (1.0 - dist / max(m, j)) * 100.0
        if score > best_score or (score == best_score and abs(j - m) < abs(best_j - m)):
            best_score, best_j = score, j
    return best_score, best_j


@dataclass
class FlowMatch:
    """How one utterance divided across a sequence of chant slots."""

    scores: list[float] = field(default_factory=list)  # one per matched slot
    consumed: int = 0  # utterance chars claimed by the matched slots
    stop_score: float | None = None  # score of the first failed slot, if any


def consume_sequence(
    utterance_ipa: str,
    reference_sets: list[list[str]],
    threshold: float,
) -> FlowMatch:
    """Slice one utterance across consecutive chant slots (flow mode).

    Each slot is the list of acceptable reference IPA strings for one
    expected part (a name, or one repetition of a mantra). Slots consume
    the utterance greedily from the start; matching stops when a slot
    scores below `threshold` (reported as stop_score) or when the
    utterance runs out — saying fewer parts than remain is not a mistake,
    so stop_score stays None in that case.
    """
    pos, n = 0, len(utterance_ipa)
    result = FlowMatch()
    for references in reference_sets:
        while pos < n and utterance_ipa[pos].isspace():
            pos += 1
        if pos >= n:
            break
        remaining = utterance_ipa[pos:]
        best_score, best_consumed = -1.0, 0
        for reference in references:
            if not reference:
                continue
            score, consumed = best_prefix_match(remaining, reference)
            if score > best_score:
                best_score, best_consumed = score, consumed
        if best_score < threshold or best_consumed == 0:
            result.stop_score = max(best_score, 0.0)
            break
        result.scores.append(best_score)
        pos += best_consumed
        result.consumed = pos
    return result


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
