"""Keeps the modelling guide in step with the code: every hook of Behavior must be explained in sim/MODELLING_GUIDE.md,
and the files that should point newcomers to the guide must do so."""
import inspect
import unittest
from pathlib import Path

from sim import behaviors as B

DB = Path(__file__).resolve().parents[2]
GUIDE = DB / 'sim' / 'MODELLING_GUIDE.md'


class GuideInSync(unittest.TestCase):
    def test_every_hook_is_documented(self):
        text = GUIDE.read_text(encoding='utf-8')
        hooks = [n for n, f in inspect.getmembers(B.Behavior, inspect.isfunction) if not n.startswith('_')]
        self.assertGreater(len(hooks), 30)
        missing = [h for h in hooks if f'`{h}(' not in text]
        self.assertEqual(missing, [], f'hooks missing from sim/MODELLING_GUIDE.md (add them to the hook table): {missing}')

    def test_registries_and_helpers_named_in_the_guide_exist(self):
        text = GUIDE.read_text(encoding='utf-8')
        for name in ('once_turn', 'once', 'fetch_from_deck', 'find_in', 'synthetic', '_x', 'mp', 'mastery', 'passive'):
            self.assertIn(name, text)
        for name in ('once_turn', 'once', 'fetch_from_deck', 'find_in', '_x', 'mp', 'mastery', 'passive'):
            self.assertTrue(hasattr(B, name), name)

    def test_entry_points_link_to_the_guide(self):
        for rel in ('sim/README.md', 'DECKBUILDING_NOTES.md', 'WORKFLOW_LESSONS.md', '../CLAUDE.md'):
            self.assertIn('MODELLING_GUIDE.md', (DB / rel).read_text(encoding='utf-8'), f'{rel} must link to sim/MODELLING_GUIDE.md')


if __name__ == '__main__':
    unittest.main()
