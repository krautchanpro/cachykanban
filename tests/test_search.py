import unittest

from cachykanban.models import Card, Column
from cachykanban.search import card_matches, priority_rank, visible_cards


class CardMatchesTests(unittest.TestCase):
    def _card(self, **kw):
        defaults = dict(id="c", title="Fix nav bug", notes="repro in Blackmarsh",
                        label_ids=["l1"], priority="high")
        defaults.update(kw)
        return Card(**defaults)

    def test_empty_query_matches(self):
        self.assertTrue(card_matches(self._card()))

    def test_text_matches_title_case_insensitive(self):
        self.assertTrue(card_matches(self._card(), text="NAV"))

    def test_text_matches_notes(self):
        self.assertTrue(card_matches(self._card(), text="blackmarsh"))

    def test_text_no_match(self):
        self.assertFalse(card_matches(self._card(), text="zzz"))

    def test_label_filter(self):
        self.assertTrue(card_matches(self._card(), label_id="l1"))
        self.assertFalse(card_matches(self._card(), label_id="l2"))

    def test_priority_filter(self):
        self.assertTrue(card_matches(self._card(), priority="high"))
        self.assertFalse(card_matches(self._card(), priority="low"))


class PriorityRankTests(unittest.TestCase):
    def test_rank_order(self):
        self.assertEqual(priority_rank("high"), 3)
        self.assertEqual(priority_rank("none"), 0)
        self.assertGreater(priority_rank("med"), priority_rank("low"))


class VisibleCardsTests(unittest.TestCase):
    def test_excludes_archived_by_default(self):
        col = Column(id="c", name="x", cards=[
            Card(id="1", title="keep"),
            Card(id="2", title="gone", archived=True),
        ])
        ids = [c.id for c in visible_cards(col)]
        self.assertEqual(ids, ["1"])

    def test_include_archived_when_requested(self):
        col = Column(id="c", name="x", cards=[
            Card(id="1", title="keep"),
            Card(id="2", title="gone", archived=True),
        ])
        self.assertEqual(len(visible_cards(col, include_archived=True)), 2)

    def test_applies_text_filter_preserving_order(self):
        col = Column(id="c", name="x", cards=[
            Card(id="1", title="alpha"),
            Card(id="2", title="beta"),
            Card(id="3", title="alphabet"),
        ])
        self.assertEqual([c.id for c in visible_cards(col, text="alpha")], ["1", "3"])


if __name__ == "__main__":
    unittest.main()
