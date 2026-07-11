"""Unit tests for the chant-counting logic — no mic or models needed."""

import tempfile
import unittest
from pathlib import Path

from japa.counting import MantraProgress, detect_repetitions, render_beads
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
