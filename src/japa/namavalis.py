"""Nāmāvalī (नामावली) — garlands of divine names chanted in sequence.

Unlike a mantra chanted many times over, a namavali is a fixed sequence of
names each chanted once (or a few times) in order. Every name is a Mantra
in its own right, with its own voiceprint file for training: the name's key
nests under the namavali's key, so trained renditions land in e.g.
voiceprints/durga-32/01-durga.txt.

The 32 Names of Durga data (transliteration, meaning, reference IPA) comes
from voicekit's durga_names_learner example.
"""

from dataclasses import dataclass

from .mantras import Mantra
from .profiles import slugify


@dataclass
class Namavali:
    key: str
    title: str
    meaning: str
    names: list[Mantra]


def _build(key: str, title: str, meaning: str, entries: list[tuple[str, str, str]]) -> Namavali:
    names = [
        Mantra(
            key=f"{key}/{i:02d}-{slugify(phrase)}",
            title=phrase,
            text=phrase,
            devanagari="",
            meaning=name_meaning,
            ipa=ipa,
        )
        for i, (phrase, name_meaning, ipa) in enumerate(entries, 1)
    ]
    return Namavali(key=key, title=title, meaning=meaning, names=names)


DURGA_32_ENTRIES = [
    ("Durgā", "The Reliever of Difficulties", "dʊrɡaː"),
    ("Durgatitśamanī", "The Dispeller of Evil Tendencies", "dʊrɡətɪʃəməniː"),
    ("Durgāpadvinivārinī", "The Preventer of Miseries", "dʊrɡaːpədvɪnɪvaːrɪniː"),
    ("Durgamacchedinī", "The Destroyer of Difficulties", "dʊrɡəmətʃʰeːdɪniː"),
    ("Durgasādhinī", "The Performer of Difficult Disciplines", "dʊrɡəsaːdʱɪniː"),
    ("Durganāśinī", "The Destroyer of Hurdles", "dʊrɡənaːʃɪniː"),
    ("Durgatoddhārinī", "The Savior from Distresses", "dʊrɡət̪oːdʱaːrɪniː"),
    ("Durganihantrī", "The Ruiner of Obstacles", "dʊrɡənɪɦəntriː"),
    ("Durgamāpahā", "The Stealer of Difficulties", "dʊrɡəmaːpəɦaː"),
    ("Durgamajñānadā", "The Giver of Difficult Knowledge", "dʊrɡəmədʒɲaːnədaː"),
    ("Durgadaityalokadavānalā", "The Destroyer of Demon Worlds", "dʊrɡəd̪eːt̪jəloːkəd̪əvaːnəlaː"),
    ("Durgamā", "The Unapproachable", "dʊrɡəmaː"),
    ("Durgamālokā", "The One Whose Sight is Hard to Attain", "dʊrɡəmaːloːkaː"),
    ("Durgamātmaswarūpinī", "The Soul of Unfathomable Reality", "dʊrɡəmaːt̪məsʋəruːpɪniː"),
    ("Durgamārgapradā", "The Guide Through Difficult Paths", "dʊrɡəmaːrɡəprədaː"),
    ("Durgamavidyā", "The Incomprehensible Knowledge", "dʊrɡəməvɪdjaː"),
    ("Durgamāśritā", "The Refuge from Extreme Distresses", "dʊrɡəmaːʃrɪt̪aː"),
    ("Durgamajñānasaṁsthānā", "The Abode of Profound Wisdom", "dʊrɡəmədʒɲaːnəsənstʰaːnaː"),
    ("Durgamadhyānabhāsinī", "The Light of Deep Meditation", "dʊrɡəmədʱjaːnəbʱaːsɪniː"),
    ("Durgamohā", "The Deluder of Obstacles", "dʊrɡəmoːɦaː"),
    ("Durgamagā", "The Piercer of Intricate Spaces", "dʊrɡəməɡaː"),
    ("Durgamārthaswarūpinī", "The Essence of Profound Meanings", "dʊrɡəmaːrtʰəsʋəruːpɪniː"),
    ("Durgamāsurahantrī", "The Slayer of Supreme Demons", "dʊrɡəmaːsʊrəɦəntriː"),
    ("Durgamāyudhadhārinī", "The Wielder of Formidable Weapons", "dʊrɡəmaːjʊdʱədʱaːrɪniː"),
    ("Durgamaṅgī", "The One with Sacred, Invincible Forms", "dʊrɡəməŋɡiː"),
    ("Durgamatā", "The Source of Infinite Perceptions", "dʊrɡəmət̪aː"),
    ("Durgamyā", "The One Who Carries Us Across Difficulties", "dʊrɡəmjaː"),
    ("Durgameśwarī", "The Supreme Goddess of Fortresses", "dʊrɡəmeːʃʋəriː"),
    ("Durgabhīmā", "The Terrifying Form of Protection", "dʊrɡəbʱiːmaː"),
    ("Durgabhāmā", "The Fiercely Radiant Goddess", "dʊrɡəbʱaːmaː"),
    ("Durgabhābā", "The Source of Brilliant Light", "dʊrɡəbʱaːbaː"),
    ("Durgadārinī", "The Annihilator of Ultimate Misery", "dʊrɡədaːrɪniː"),
]

NAMAVALIS: list[Namavali] = [
    _build(
        "durga-32",
        "32 Names of Durgā (Dvātriṁśannāmamālā)",
        "Chanted in sequence for protection and the removal of difficulties",
        DURGA_32_ENTRIES,
    ),
]


def get_namavali(key_or_index: str) -> Namavali | None:
    """Look a namavali up by key, or by its menu number continued after the mantras."""
    key = key_or_index.strip().lower()
    for nv in NAMAVALIS:
        if nv.key == key:
            return nv
    if key.isdigit():
        from .mantras import MANTRAS
        i = int(key) - len(MANTRAS) - 1
        if 0 <= i < len(NAMAVALIS):
            return NAMAVALIS[i]
    return None
