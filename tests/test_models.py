import unittest

from cachykanban.models import ChecklistItem, Label, new_id, PRIORITIES


class HelperTests(unittest.TestCase):
    def test_new_id_is_unique_hex(self):
        a, b = new_id(), new_id()
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 8)
        int(a, 16)  # raises if not hex

    def test_priorities_constant(self):
        self.assertEqual(PRIORITIES, ("none", "low", "med", "high"))


class ChecklistItemTests(unittest.TestCase):
    def test_round_trip(self):
        item = ChecklistItem(text="write tests", done=True)
        self.assertEqual(ChecklistItem.from_dict(item.to_dict()), item)

    def test_from_dict_defaults(self):
        item = ChecklistItem.from_dict({})
        self.assertEqual(item.text, "")
        self.assertFalse(item.done)


class LabelTests(unittest.TestCase):
    def test_round_trip(self):
        label = Label(id="lbl12345", name="bug", color="#fc8181")
        self.assertEqual(Label.from_dict(label.to_dict()), label)

    def test_from_dict_generates_id_when_missing(self):
        label = Label.from_dict({"name": "idea", "color": "#6ea8fe"})
        self.assertTrue(label.id)
        self.assertEqual(label.name, "idea")


if __name__ == "__main__":
    unittest.main()
