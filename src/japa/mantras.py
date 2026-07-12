"""Built-in mantra library.

Each mantra carries a transliteration (for display), Devanagari where it
applies, a short meaning, and a reference IPA string matched against the
output of voicekit's PhoneticTranslator (wav2vec2 espeak-style IPA). The
IPA references are approximate on purpose — MatchingAlgo scores fuzzily,
and any mantra can be re-calibrated against the chanter's own voice.
"""

from dataclasses import dataclass


@dataclass
class Mantra:
    key: str
    title: str
    text: str  # transliteration shown to (and chanted by) the user
    devanagari: str
    meaning: str
    ipa: str  # reference IPA; empty means calibration is required


MANTRAS: list[Mantra] = [
    Mantra(
        key="om",
        title="Oṁ",
        text="Om",
        devanagari="ॐ",
        meaning="The primordial sound",
        ipa="oːm",
    ),
    Mantra(
        key="om-namah-shivaya",
        title="Oṁ Namaḥ Śivāya",
        text="Om Namah Shivaya",
        devanagari="ॐ नमः शिवाय",
        meaning="I bow to Shiva",
        ipa="oːm nəməɦə ʃɪʋaːjə",
    ),
    Mantra(
        key="om-mani-padme-hum",
        title="Oṁ Maṇi Padme Hūṁ",
        text="Om Mani Padme Hum",
        devanagari="ॐ मणि पद्मे हूँ",
        meaning="The jewel in the lotus",
        ipa="oːm məɳɪ pəd̪meː ɦuːm",
    ),
    Mantra(
        key="om-namo-bhagavate",
        title="Oṁ Namo Bhagavate Vāsudevāya",
        text="Om Namo Bhagavate Vasudevaya",
        devanagari="ॐ नमो भगवते वासुदेवाय",
        meaning="Salutations to Lord Vasudeva",
        ipa="oːm nəmoː bʱəɡəʋət̪eː ʋaːsʊd̪eːʋaːjə",
    ),
    Mantra(
        key="om-gam-ganapataye",
        title="Oṁ Gaṁ Gaṇapataye Namaḥ",
        text="Om Gam Ganapataye Namaha",
        devanagari="ॐ गं गणपतये नमः",
        meaning="Salutations to Ganesha, remover of obstacles",
        ipa="oːm ɡəm ɡəɳəpət̪əjeː nəməɦə",
    ),
    Mantra(
        key="gayatri",
        title="Gāyatrī Mantra",
        text=(
            "Om Bhur Bhuvah Svaha, Tat Savitur Varenyam, "
            "Bhargo Devasya Dhimahi, Dhiyo Yo Nah Prachodayat"
        ),
        devanagari=(
            "ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं "
            "भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात्"
        ),
        meaning="Meditation on the divine light of the sun",
        ipa=(
            "oːm bʱuːr bʱʊʋəɦ sʋəɦə t̪ət̪ səʋɪt̪ʊr ʋəreːɳjəm "
            "bʱərɡoː d̪eːʋəsjə dʱiːməɦiː dʱɪjoː joː nəɦə prətʃoːd̪əjaːt̪"
        ),
    ),
    Mantra(
        key="mahamrityunjaya",
        title="Mahāmṛtyuñjaya Mantra",
        text=(
            "Om Tryambakam Yajamahe Sugandhim Pushtivardhanam, "
            "Urvarukamiva Bandhanan Mrityor Mukshiya Mamritat"
        ),
        devanagari=(
            "ॐ त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् "
            "उर्वारुकमिव बन्धनान्मृत्योर्मुक्षीय मामृतात्"
        ),
        meaning="Prayer to Shiva for liberation from death",
        ipa=(
            "oːm t̪rjəmbəkəm jədʒaːməɦeː sʊɡənd̪ʱɪm pʊʃʈɪʋərd̪ʱənəm "
            "ʊrʋaːrʊkəmɪʋə bənd̪ʱənaːn mrɪt̪joːr mʊkʃiːjə maːmrɪt̪aːt̪"
        ),
    ),
    Mantra(
        key="hare-krishna",
        title="Hare Kṛṣṇa Mahāmantra",
        text=(
            "Hare Krishna Hare Krishna Krishna Krishna Hare Hare, "
            "Hare Rama Hare Rama Rama Rama Hare Hare"
        ),
        devanagari=(
            "हरे कृष्ण हरे कृष्ण कृष्ण कृष्ण हरे हरे "
            "हरे राम हरे राम राम राम हरे हरे"
        ),
        meaning="Invocation of Krishna and Rama",
        ipa=(
            "ɦəreː krɪʃɳə ɦəreː krɪʃɳə krɪʃɳə krɪʃɳə ɦəreː ɦəreː "
            "ɦəreː raːmə ɦəreː raːmə raːmə raːmə ɦəreː ɦəreː"
        ),
    ),
    Mantra(
        key="om-shanti",
        title="Oṁ Śāntiḥ",
        text="Om Shantih Shantih Shantih",
        devanagari="ॐ शान्तिः शान्तिः शान्तिः",
        meaning="Invocation of peace",
        ipa="oːm ʃaːnt̪ɪɦ ʃaːnt̪ɪɦ ʃaːnt̪ɪɦ",
    ),
    Mantra(
        key="namokar",
        title="Ṇamōkāra Mantra (Navkar Mantra)",
        text=(
            "Namo Arihantanam, Namo Siddhanam, Namo Ayariyanam, "
            "Namo Uvajjhayanam, Namo Loe Savva Sahunam"
        ),
        devanagari=(
            "णमो अरिहंताणं णमो सिद्धाणं णमो आयरियाणं "
            "णमो उवज्झायाणं णमो लोए सव्वसाहूणं"
        ),
        meaning="Jain salutation to the five supreme beings (Pañca Parameṣṭhi)",
        ipa=(
            "ɳəmoː ərɪɦənt̪aːɳəm ɳəmoː sɪd̪ʱaːɳəm ɳəmoː aːjərɪjaːɳəm "
            "ɳəmoː ʊʋədʒdʒʱaːjaːɳəm ɳəmoː loːeː səʋʋəsaːɦuːɳəm"
        ),
    ),
    Mantra(
        key="bhairav",
        title="Bhairava Nāma Mantra",
        text="Om Bhairavaya Namaha",
        devanagari="ॐ भैरवाय नमः",
        meaning="Salutation to Bhairava, the fierce form of Shiva",
        ipa="oːm bʱɛːrəʋaːjə nəməɦə",
    ),
]


def get_mantra(key_or_index: str) -> Mantra | None:
    """Look a mantra up by menu number or by key."""
    if key_or_index.isdigit():
        i = int(key_or_index) - 1
        return MANTRAS[i] if 0 <= i < len(MANTRAS) else None
    key = key_or_index.strip().lower()
    for m in MANTRAS:
        if m.key == key:
            return m
    return None
