"""Unit tests for the chant-counting logic — no mic or models needed."""

import tempfile
import unittest
from pathlib import Path

from japa.counting import (
    MantraProgress,
    best_prefix_match,
    consume_sequence,
    detect_repetitions,
    render_beads,
)
from japa.mantras import MANTRAS, get_mantra
from japa.namavalis import NAMAVALIS, get_namavali
from japa.profiles import append_to_profile, load_profile, slugify
from japa.sounds import (
    AudioFeedback,
    mantra_complete_wave,
    ready_wave,
    session_complete_wave,
    wrong_wave,
)
from voicekit import MatchingAlgo

REF = "oːm nəməɦə ʃɪʋaːjə"  # Om Namah Shivaya


class TestDetectRepetitions(unittest.TestCase):
    def setUp(self):
        self.matcher = MatchingAlgo(algorithm="levenshtein")

    def test_exact_single_repetition(self):
        reps, score = detect_repetitions(REF, REF, self.matcher, threshold=50)
        self.assertEqual(reps, 1)
        self.assertEqual(score, 100.0)

    def test_near_miss_still_counts(self):
        heard = "oːm nəməɦ ʃɪʋaːja"  # two characters off
        reps, score = detect_repetitions(heard, REF, self.matcher, threshold=50)
        self.assertEqual(reps, 1)
        self.assertGreater(score, 80)

    def test_unrelated_speech_rejected(self):
        heard = "ɡuːt̪ən t̪aːk viː ɡeːt̪ əs iːnən"
        reps, _ = detect_repetitions(heard, REF, self.matcher, threshold=50)
        self.assertEqual(reps, 0)

    def test_two_repetitions_in_one_breath(self):
        heard = f"{REF} {REF}"
        reps, score = detect_repetitions(heard, REF, self.matcher, threshold=50)
        self.assertEqual(reps, 2)
        self.assertEqual(score, 100.0)

    def test_three_imperfect_repetitions(self):
        one = "oːm nəməɦ ʃɪʋaːjə"
        heard = " ".join([one] * 3)
        reps, _ = detect_repetitions(heard, REF, self.matcher, threshold=50)
        self.assertEqual(reps, 3)

    def test_multiple_references_takes_best(self):
        # A real trained rendition (no spaces, different vowels) that scores
        # well below threshold against the textbook reference alone.
        trained = "oːmnamahʃivaːʌ"
        reps, score = detect_repetitions(trained, REF, self.matcher, threshold=50)
        self.assertEqual(reps, 0)
        reps, score = detect_repetitions(
            trained, [REF, "oːmnamahʃivaːjʌ"], self.matcher, threshold=50
        )
        self.assertEqual(reps, 1)
        self.assertGreater(score, 80)


DURGA = "dʊrɡaː"
SHAMANI = "dʊrɡaːt̪ɪrʃəməniː"
NIVARINI = "dʊrɡaːpəd̪ʋɪnɪʋaːrɪniː"


class TestBestPrefixMatch(unittest.TestCase):
    def test_exact_match_consumes_reference_length(self):
        self.assertEqual(best_prefix_match(DURGA, DURGA), (100.0, len(DURGA)))

    def test_prefix_of_longer_utterance(self):
        score, consumed = best_prefix_match(f"{DURGA} {SHAMANI}", DURGA)
        self.assertEqual(score, 100.0)
        self.assertEqual(consumed, len(DURGA))

    def test_scores_like_matching_algo(self):
        # One substitution against a 6-char reference: (1 - 1/6) * 100.
        score, _ = best_prefix_match("dʊrɡaː", "dʊrɡoː")
        self.assertAlmostEqual(score, MatchingAlgo().score("dʊrɡaː", "dʊrɡoː"))

    def test_repetition_consumes_exactly_one_copy(self):
        score, consumed = best_prefix_match(DURGA * 3, DURGA)
        self.assertEqual(score, 100.0)
        self.assertEqual(consumed, len(DURGA))

    def test_empty_reference(self):
        self.assertEqual(best_prefix_match(DURGA, ""), (0.0, 0))


class TestConsumeSequence(unittest.TestCase):
    def test_three_names_in_one_breath(self):
        heard = f"{DURGA} {SHAMANI} {NIVARINI}"
        match = consume_sequence(heard, [[DURGA], [SHAMANI], [NIVARINI]], threshold=50)
        self.assertEqual(len(match.scores), 3)
        self.assertIsNone(match.stop_score)
        self.assertEqual(match.consumed, len(heard))

    def test_stops_at_wrong_second_name_even_if_third_is_right(self):
        heard = f"{DURGA} blahblahblah {NIVARINI}"
        match = consume_sequence(heard, [[DURGA], [SHAMANI], [NIVARINI]], threshold=50)
        self.assertEqual(len(match.scores), 1)
        self.assertIsNotNone(match.stop_score)
        self.assertLess(match.stop_score, 50)

    def test_fewer_parts_spoken_is_not_a_mistake(self):
        heard = f"{DURGA} {SHAMANI}"
        match = consume_sequence(heard, [[DURGA], [SHAMANI], [NIVARINI]], threshold=50)
        self.assertEqual(len(match.scores), 2)
        self.assertIsNone(match.stop_score)

    def test_repeated_mantra_counts_each_repetition(self):
        heard = " ".join([REF] * 5)
        match = consume_sequence(heard, [[REF]] * 5, threshold=50)
        self.assertEqual(len(match.scores), 5)
        self.assertTrue(all(s == 100.0 for s in match.scores))

    def test_trained_rendition_matches_where_textbook_fails(self):
        # A real trained rendition scores under threshold against the
        # textbook IPA alone but must still count via the voiceprint.
        trained = "oːmnamahʃivaːʌ"
        heard = f"{trained} {trained}"
        match = consume_sequence(heard, [[REF]] * 2, threshold=50)
        self.assertEqual(len(match.scores), 0)
        match = consume_sequence(heard, [[REF, "oːmnamahʃivaːjʌ"]] * 2, threshold=50)
        self.assertEqual(len(match.scores), 2)

    def test_nothing_matched(self):
        match = consume_sequence("ɡuːt̪ən t̪aːk", [[DURGA], [SHAMANI]], threshold=50)
        self.assertEqual(match.scores, [])
        self.assertEqual(match.consumed, 0)
        self.assertIsNotNone(match.stop_score)

    def test_empty_utterance(self):
        match = consume_sequence("", [[DURGA]], threshold=50)
        self.assertEqual(match.scores, [])
        self.assertIsNone(match.stop_score)


class TestMantraProgress(unittest.TestCase):
    def test_counts_and_average(self):
        p = MantraProgress(title="Om", target=5)
        p.register(1, 90.0)
        p.register(0, 30.0)  # rejected attempt: no count, score not averaged in
        p.register(2, 70.0)
        self.assertEqual(p.count, 3)
        self.assertEqual(p.attempts, 3)
        self.assertAlmostEqual(p.average_score, 80.0)
        self.assertFalse(p.done)

    def test_never_overshoots_target(self):
        p = MantraProgress(title="Om", target=3)
        p.register(5, 88.0)
        self.assertEqual(p.count, 3)
        self.assertTrue(p.done)


class TestMantraLibrary(unittest.TestCase):
    def test_lookup_by_key_and_number(self):
        self.assertEqual(get_mantra("om-namah-shivaya").key, "om-namah-shivaya")
        self.assertEqual(get_mantra("1").key, MANTRAS[0].key)
        self.assertIsNone(get_mantra("99"))
        self.assertIsNone(get_mantra("not-a-mantra"))

    def test_all_builtins_have_reference_ipa(self):
        for m in MANTRAS:
            self.assertTrue(m.ipa, f"{m.key} is missing reference IPA")


class TestProfiles(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            dir = Path(d) / "voiceprints"
            self.assertEqual(load_profile(dir, "om"), [])
            append_to_profile(dir, "om", "oːm")
            append_to_profile(dir, "om", "uːm ")
            self.assertEqual(load_profile(dir, "om"), ["oːm", "uːm"])
            self.assertEqual(load_profile(dir, "other"), [])

    def test_slugify(self):
        self.assertEqual(slugify("Om Namah Shivaya!"), "om-namah-shivaya")
        self.assertEqual(slugify("   "), "custom")

    def test_slugify_folds_diacritics(self):
        self.assertEqual(slugify("Durgā"), "durga")
        self.assertEqual(slugify("Durgatitśamanī"), "durgatitsamani")
        self.assertEqual(slugify("Durgamaṅgī"), "durgamangi")


class TestNamavalis(unittest.TestCase):
    def test_durga_32_data(self):
        nv = get_namavali("durga-32")
        self.assertIsNotNone(nv)
        self.assertEqual(len(nv.names), 32)
        keys = [n.key for n in nv.names]
        self.assertEqual(len(set(keys)), 32, "name keys must be unique")
        for name in nv.names:
            self.assertTrue(name.key.startswith("durga-32/"))
            self.assertTrue(name.ipa, f"{name.title} is missing reference IPA")
            self.assertTrue(name.meaning)
        # per-name voiceprint files nest under the namavali directory
        self.assertEqual(nv.names[0].key, "durga-32/01-durga")

    def test_lookup(self):
        self.assertIsNone(get_namavali("not-a-namavali"))
        # menu numbering continues after the mantras
        self.assertEqual(get_namavali(str(len(MANTRAS) + 1)).key, NAMAVALIS[0].key)
        self.assertIsNone(get_namavali(str(len(MANTRAS) + len(NAMAVALIS) + 1)))


class TestSounds(unittest.TestCase):
    def test_waves_are_playable(self):
        import numpy as np
        for wave_fn in (ready_wave, wrong_wave, mantra_complete_wave,
                        session_complete_wave):
            wave = wave_fn()
            self.assertGreater(wave.size, 0)
            self.assertEqual(wave.dtype, np.float32)
            self.assertTrue(np.all(np.isfinite(wave)))
            self.assertLessEqual(np.abs(wave).max(), 1.0, "would clip")

    def test_disabled_feedback_is_silent_noop(self):
        # Must not touch the audio device at all when disabled.
        sounds = AudioFeedback(enabled=False)
        sounds.ready()
        sounds.wrong()
        sounds.mantra_complete()
        sounds.session_complete()


class TestRenderBeads(unittest.TestCase):
    def test_bounds(self):
        self.assertTrue(render_beads(0, 108).startswith("○"))
        self.assertIn("108/108", render_beads(108, 108))
        self.assertNotIn("○", render_beads(108, 108).split()[0])


if __name__ == "__main__":
    unittest.main()
