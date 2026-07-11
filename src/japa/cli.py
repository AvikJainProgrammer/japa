"""Interactive japa CLI: pick mantras or namavalis, chant into the mic, count beads.

Flow per mantra: VoiceRecorder captures one utterance at a time,
PhoneticTranslator turns it into IPA, and detect_repetitions() matches it
against the mantra's references — counting multiple repetitions chanted
in a single breath. A chant only advances the counter when its phonetic
score clears the threshold, so this doubles as a pronunciation trainer.

References come from two places: the built-in textbook IPA, and — far
more effective — the chanter's own confirmed renditions saved by
training mode (--train) into voiceprints/<mantra-key>.txt.

A namavali (e.g. durga-32) expands into its sequence of names, each an
independent mantra with its own voiceprint file, chanted once each by
default instead of a full mala.
"""

import argparse
import sys
import time
from pathlib import Path

from .counting import MantraProgress, detect_repetitions, render_beads
from .journal import format_history, load_journal, save_session
from .mantras import MANTRAS, Mantra, get_mantra
from .namavalis import NAMAVALIS, get_namavali
from .profiles import (
    DEFAULT_VOICEPRINTS_DIR,
    append_to_profile,
    load_profile,
    profile_path,
    slugify,
)
from .sounds import AudioFeedback

DEFAULT_TARGET = 108  # one full mala
DEFAULT_NAMAVALI_TARGET = 1  # each name once, in sequence
DEFAULT_THRESHOLD = 50.0  # same bar the voicekit Durga trainer settled on

RULE = "─" * 70

# One unit of a session: a mantra (or name) and how many times to chant it.
Item = tuple[Mantra, int]


def expand_token(token: str, count_arg: int | None) -> list[Item] | None:
    """Resolve one selection token into session items, or None if unknown."""
    namavali = get_namavali(token)
    if namavali is not None:
        target = count_arg or DEFAULT_NAMAVALI_TARGET
        return [(name, target) for name in namavali.names]
    mantra = get_mantra(token)
    if mantra is not None:
        return [(mantra, count_arg or DEFAULT_TARGET)]
    return None


def choose_items(count_arg: int | None) -> list[Item]:
    print("\nChoose — numbers separated by commas, or 0 for a custom mantra:\n")
    print("Mantras:")
    for i, m in enumerate(MANTRAS, 1):
        print(f"  {i}. {m.title:<34} {m.devanagari}")
    print("Namavalis (name sequences):")
    for j, nv in enumerate(NAMAVALIS, len(MANTRAS) + 1):
        print(f"  {j}. {nv.title:<34} ({len(nv.names)} names)")
    print("  0. Custom mantra (matched against your own voice)")

    while True:
        raw = input("\nYour choice: ").strip()
        chosen: list[Item] = []
        valid = True
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            if token == "0":
                text = input("Type the mantra text (transliteration is fine): ").strip()
                if text:
                    custom = Mantra(
                        key=slugify(text),
                        title=text,
                        text=text,
                        devanagari="",
                        meaning="Your own mantra",
                        ipa="",  # no textbook reference — train or calibrate
                    )
                    chosen.append((custom, count_arg or DEFAULT_TARGET))
                continue
            items = expand_token(token, count_arg)
            if items is None:
                print(f"'{token}' is not on the list — try again.")
                valid = False
                break
            chosen.extend(items)
        if valid and chosen:
            return chosen
        if valid:
            print("Pick at least one option.")


def calibrate(mantra: Mantra, recorder, phonetics, sounds: AudioFeedback) -> str:
    """Record the chanter's own rendition once and use its IPA as reference."""
    print(f"\nCalibration — chant \"{mantra.text}\" once, slowly and clearly.")
    while True:
        print(">>> Listening...")
        sounds.ready()
        audio = recorder.record()
        if audio.size == 0:
            print("(nothing heard — try again)")
            continue
        ipa = phonetics.convert(audio)
        if not ipa:
            print("(could not extract phonetics — try again)")
            continue
        print(f"Reference captured: {ipa}")
        return ipa


def build_references(mantra: Mantra, args, recorder, phonetics, sounds: AudioFeedback) -> list[str]:
    """Collect everything a chant may be scored against, best sources first."""
    references = load_profile(args.voiceprints, mantra.key)
    if references:
        print(f"(using {len(references)} trained rendition(s) from "
              f"{profile_path(args.voiceprints, mantra.key)})")
    if mantra.ipa:
        references.append(mantra.ipa)
    if args.calibrate or not references:
        references.insert(0, calibrate(mantra, recorder, phonetics, sounds))
    return references


def position_label(index: int, total: int) -> str:
    return f" {index}/{total}" if total > 1 else ""


def train_mantra(
    mantra: Mantra, args, recorder, phonetics, matcher, sounds: AudioFeedback,
    index: int = 1, total: int = 1,
) -> None:
    """Record renditions, let the chanter confirm them, save confirmed ones."""
    existing = load_profile(args.voiceprints, mantra.key)
    references = existing + ([mantra.ipa] if mantra.ipa else [])

    print(f"\n{RULE}")
    print(f"TRAINING{position_label(index, total)}: {mantra.title}   "
          f"({len(existing)} rendition(s) already saved)")
    print(f"Meaning: {mantra.meaning}")
    if mantra.ipa:
        print(f"Target IPA: {mantra.ipa}")
    print(f"Chant \"{mantra.text}\" once, then confirm whether it was correct.")
    print("Answer y to save, n to discard, q to finish training this one.")
    print(RULE)

    saved = 0
    while True:
        print("\n>>> Listening...")
        sounds.ready()
        audio = recorder.record()
        if audio.size == 0:
            print("(nothing heard — try again)")
            continue
        ipa = phonetics.convert(audio)
        if not ipa:
            print("(could not extract phonetics — try again)")
            continue

        closest = max((matcher.score(ipa, r) for r in references), default=None)
        vs = f"   (closest saved/built-in match: {closest:.1f}%)" if closest is not None else ""
        print(f"heard: {ipa}{vs}")

        answer = input("Save this as a correct rendition? [y/n/q] ").strip().lower()
        if answer == "y":
            path = append_to_profile(args.voiceprints, mantra.key, ipa)
            references.append(ipa)
            saved += 1
            print(f"Saved ({len(existing) + saved} total) -> {path}")
        elif answer == "q":
            break

    print(f"\nTraining done: {saved} new rendition(s) saved for {mantra.title}.")


def chant_mantra(
    mantra: Mantra, references: list[str], target: int, threshold: float,
    max_reps: int, recorder, phonetics, matcher, sounds: AudioFeedback,
    index: int = 1, total: int = 1,
) -> MantraProgress:
    print(f"\n{RULE}")
    print(f"MANTRA{position_label(index, total)}: {mantra.title}")
    if mantra.devanagari:
        print(f"        {mantra.devanagari}")
    print(f"Meaning: {mantra.meaning}")
    print(f"Target:  {target} repetition(s)")
    print(RULE)

    progress = MantraProgress(title=mantra.title, target=target)
    print("\nBegin chanting. Pause briefly between repetitions. Ctrl+C to finish early.\n")

    while not progress.done:
        sounds.ready()
        audio = recorder.record()
        if audio.size == 0:
            continue
        ipa = phonetics.convert(audio)
        if not ipa:
            continue

        reps, score = detect_repetitions(ipa, references, matcher, threshold, max_reps)
        progress.register(reps, score)

        if reps > 0:
            extra = f" (x{reps} in one breath)" if reps > 1 else ""
            print(f"  ✓ {score:5.1f}%{extra}   {render_beads(progress.count, target)}")
        else:
            sounds.wrong()
            print(f"  ✗ {score:5.1f}%  heard: {ipa}")
            print(f"    not counted — chant clearly.   {render_beads(progress.count, target)}")

    sounds.mantra_complete()
    print(f"\n🙏 {mantra.title} complete — {target} repetition(s), "
          f"average accuracy {progress.average_score:.1f}%.")
    return progress


def run_session(items: list[Item], args) -> None:
    print("\nLoading models (the first run downloads them)...")
    from voicekit import MatchingAlgo, PhoneticTranslator, VoiceRecorder

    recorder = VoiceRecorder(silence_timeout=args.silence)
    phonetics = PhoneticTranslator()
    matcher = MatchingAlgo(algorithm="levenshtein")
    sounds = AudioFeedback(enabled=args.audio)

    total = len(items)

    if args.train:
        try:
            for i, (mantra, _) in enumerate(items, 1):
                train_mantra(mantra, args, recorder, phonetics, matcher, sounds, i, total)
        except KeyboardInterrupt:
            print("\nTraining interrupted — confirmed renditions are already saved.")
        return

    started_at = time.time()
    results: list[MantraProgress] = []
    finished = False

    try:
        for i, (mantra, target) in enumerate(items, 1):
            references = build_references(mantra, args, recorder, phonetics, sounds)
            results.append(
                chant_mantra(
                    mantra, references, target, args.threshold, args.max_reps,
                    recorder, phonetics, matcher, sounds, i, total,
                )
            )
        finished = True
    except KeyboardInterrupt:
        print("\n\nSession ended early.")

    if results:
        save_session(
            [
                {
                    "title": p.title,
                    "count": p.count,
                    "target": p.target,
                    "average_score": round(p.average_score, 1),
                }
                for p in results
            ],
            started_at,
        )
        print(f"\n{RULE}")
        print("SESSION SUMMARY")
        for p in results:
            print(f"  {p.title:<40} {p.count}/{p.target}  "
                  f"(avg accuracy {p.average_score:.1f}%)")
        print(f"{RULE}")
        print("Saved to your japa journal. Pranam! 🙏")
        if finished:
            sounds.session_complete()


def print_list() -> None:
    print("Mantras:")
    for i, m in enumerate(MANTRAS, 1):
        print(f"{i:>2}. {m.key:<22} {m.title:<34} {m.devanagari}")
    print("\nNamavalis (name sequences — chanted once each, in order):")
    for j, nv in enumerate(NAMAVALIS, len(MANTRAS) + 1):
        print(f"{j:>2}. {nv.key:<22} {nv.title:<40} ({len(nv.names)} names)")
        for name in nv.names:
            print(f"      {name.key.split('/')[-1]:<28} {name.title:<26} {name.meaning}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="japa",
        description="Mantra chanting counter and pronunciation trainer.",
    )
    parser.add_argument(
        "selections", nargs="*", metavar="mantra-or-namavali",
        help="mantra/namavali keys or menu numbers (e.g. 'om-namah-shivaya', "
             "'durga-32', or '2'); omit for the interactive picker",
    )
    parser.add_argument("-n", "--count", type=int, default=None,
                        help=f"repetitions per mantra (default {DEFAULT_TARGET} for a "
                             f"mantra, {DEFAULT_NAMAVALI_TARGET} per name of a namavali)")
    parser.add_argument("-t", "--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"phonetic accuracy needed to count a chant "
                             f"(default {DEFAULT_THRESHOLD})")
    parser.add_argument("--train", action="store_true",
                        help="training mode: chant, confirm correct renditions, and "
                             "save them as voiceprints matched against in future "
                             "sessions")
    parser.add_argument("--voiceprints", type=Path, default=DEFAULT_VOICEPRINTS_DIR,
                        help="directory holding trained voiceprint files "
                             f"(default ./{DEFAULT_VOICEPRINTS_DIR}/)")
    parser.add_argument("--start", type=int, default=1, metavar="N",
                        help="start at item N of the session sequence (useful to "
                             "resume partway through a namavali)")
    parser.add_argument("--silence", type=float, default=1.0,
                        help="seconds of silence that end one utterance (default 1.0)")
    parser.add_argument("--max-reps", type=int, default=8,
                        help="max repetitions detected in a single breath (default 8)")
    parser.add_argument("--audio", action="store_true",
                        help="audio feedback: a soothing tone when it's your turn to "
                             "chant, a low tone when a chant isn't counted, and happy "
                             "tones when a mantra and the session complete")
    parser.add_argument("--audio-demo", action="store_true",
                        help="play each audio feedback cue once and exit")
    parser.add_argument("--calibrate", action="store_true",
                        help="record your own rendition once at session start and "
                             "match against it too (one-off, not saved; use --train "
                             "to save permanently)")
    parser.add_argument("--list", action="store_true",
                        help="list built-in mantras and namavalis")
    parser.add_argument("--history", action="store_true",
                        help="show your recent japa sessions")
    args = parser.parse_args()

    if args.list:
        print_list()
        return

    if args.audio_demo:
        sounds = AudioFeedback(enabled=True)
        for label, cue in [
            ("ready to chant", sounds.ready),
            ("chant not counted", sounds.wrong),
            ("mantra complete", sounds.mantra_complete),
            ("session complete", sounds.session_complete),
        ]:
            print(f"♪ {label}")
            cue()
            time.sleep(0.5)
        return

    if args.history:
        print(format_history(load_journal()))
        return

    if args.selections:
        items: list[Item] = []
        for token in args.selections:
            expanded = expand_token(token, args.count)
            if expanded is None:
                sys.exit(f"Unknown mantra or namavali '{token}' — see "
                         f"`python app.py --list`.")
            items.extend(expanded)
    else:
        items = choose_items(args.count)

    if args.start > 1:
        if args.start > len(items):
            sys.exit(f"--start {args.start} is beyond the sequence "
                     f"({len(items)} item(s)).")
        items = items[args.start - 1:]

    run_session(items, args)


if __name__ == "__main__":
    main()
