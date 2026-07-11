# pray — a japa (mantra chanting) app

Chant a mantra — or a set of mantras — a target number of times, hands-free.
The app listens on the microphone, checks each chant phonetically against the
mantra, and only advances the bead counter when the chant is close enough, so
it doubles as a pronunciation trainer. Built on
[voicekit](https://github.com/AvikJainProgrammer/voicekit)
(`VoiceRecorder` + `PhoneticTranslator` + `MatchingAlgo`).

## Install

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .
```

voicekit is pulled straight from GitHub as a dependency. The first session
downloads the wav2vec2 phonetic model (~1 GB) and the Silero VAD model.

## Use

```bash
python app.py                        # interactive: pick mantra(s), chant a mala of 108
python app.py om-namah-shivaya -n 21 # 21 repetitions of a specific mantra
python app.py 2 5 -n 11              # a set: mantras #2 and #5, 11 times each
python app.py --list                 # the built-in mantra library
python app.py --calibrate 6          # match against your own voice instead of the
                                     # built-in IPA reference (good for accents)
python app.py --history              # your japa journal (~/.japa/journal.json)
```

(Use the venv's python: `source .venv/bin/activate` first, or call
`.venv/bin/python app.py ...` directly. The installed `japa` command is
equivalent, but macOS keeps marking this venv's `.pth` files hidden —
which Python 3.12+ then ignores — so `app.py` is the reliable entry
point on this machine.)

While chanting, pause briefly between repetitions — that's how utterances are
segmented. Chanting the mantra several times in one breath is fine: the
matcher detects up to `--max-reps` repetitions per utterance and counts them
all. A chant below `--threshold` (default 50% phonetic similarity) is not
counted and the heard phonetics are shown so you can adjust. `Ctrl+C` ends the
session early; completed counts are still journaled.

## Train it on your voice (recommended)

The built-in references are textbook IPA; the phonetic model hears *your*
voice, which can consistently land just under the threshold. Fix that once
with training mode:

```bash
python app.py om-namah-shivaya --train
```

Chant, look at what was heard, and answer `y` (save as a correct rendition),
`n` (discard), or `q` (finish). Confirmed renditions are stored one-per-line
in `voiceprints/om-namah-shivaya.txt` — gitignored, since it's your personal
voice data. Save 3–5 good takes. Every future chanting session automatically
matches against your saved renditions **plus** the built-in reference and
keeps the best score, so no extra flags are needed afterwards. Once trained,
your correct chants score near 100%, and you can raise the bar (e.g. `-t 65`)
for stricter counting. `--voiceprints DIR` relocates the storage directory.

Custom mantras (option `0` in the picker) have no built-in reference: either
train them the same way, or chant once at session start to calibrate
(`--calibrate` does the same one-off calibration for any mantra without
saving anything).

## Namavalis — sequences of names

A namavali is a garland of divine names chanted in order, once each —
different from one mantra repeated 108 times. The 32 Names of Durga
(Dvātriṁśannāmamālā) are built in:

```bash
python app.py durga-32              # chant all 32 names in sequence, once each
python app.py durga-32 -n 3         # each name 3 times
python app.py durga-32 --train      # walk the sequence training each name
python app.py durga-32 --start 12   # resume from name 12
```

Every name is its own mantra with its own voiceprint file, nested under the
namavali's directory: `voiceprints/durga-32/01-durga.txt`,
`voiceprints/durga-32/02-durgatitsamani.txt`, … `--train` walks the names in
order (`q` finishes the current name and moves to the next), and `--start N`
lets you resume a long training or chanting run partway through.
`python app.py --list` shows all names with their meanings.

## Layout

- `src/japa/mantras.py` — built-in mantra library with IPA references
- `src/japa/counting.py` — pure counting/matching logic (unit-tested)
- `src/japa/journal.py` — session history
- `src/japa/cli.py` — the interactive app
- `tests/` — mic-free unit tests: `.venv/bin/python -m unittest discover tests`
