"""Pruebas de lógica pura: no requieren Ollama, GPU ni conexión."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from frames import periodic_times, merge_times
from reel import normalize_url, render_note


class TestFrames(unittest.TestCase):
    def test_interval_covers_full_duration(self):
        self.assertEqual(len(periodic_times(15, 1)), 15)
        self.assertEqual(len(periodic_times(1800, 2)), 900)

    def test_scene_adds_extra_timestamp(self):
        times = merge_times(periodic_times(6, 2), [1.0, 4.0], 6)
        self.assertGreater(len(times), 3)

    def test_subsecond_interval(self):
        self.assertEqual(len(periodic_times(2, .5)), 4)

    def test_scene_has_priority_over_close_periodic_frame(self):
        times = merge_times([0.25], [0.30], 1, min_gap=0.18)
        self.assertAlmostEqual(times[0], 0.42, places=2)


class TestMetadata(unittest.TestCase):
    def test_youtube_watch_param_survives(self):
        self.assertEqual(normalize_url("https://www.youtube.com/watch?v=abc123&si=test"),
                         "https://www.youtube.com/watch?v=abc123")

    def test_note_source_unchanged(self):
        url = "https://instagram.com/p/SYNTHETIC_FIXTURE"
        payload = {"title":"NetCut", "category":"Ciberseguridad", "note_kind":"herramienta",
                   "resources_expected":1,"resources":[{"name":"NetCut","kind":"tool","url_visible":""}]}
        note = render_note(url, payload, [{"name":"NetCut","url":"https://www.arcai.com/netCut/s/"}],
                           {"author":"autor"}, "gallery-dl", "en/cuda")
        self.assertIn("- Vídeo original: " + url, note)
        self.assertIn("Enlaces encontrados: 1 de 1", note)


if __name__ == "__main__":
    unittest.main()
