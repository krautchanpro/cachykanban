import http.client
import re
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from cachykanban.controller import Controller
from cachykanban.store import Store
from cachykanban.web import CachyKanbanServer, HOST, PORT


class WebServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tempdir.name))
        self.server = CachyKanbanServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tempdir.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read().decode("utf-8")
        result = response.status, dict(response.getheaders()), payload
        connection.close()
        return result

    def test_defaults_are_localhost_only_and_do_not_overlap_seedswiki(self):
        self.assertEqual(HOST, "127.0.0.1")
        self.assertEqual(PORT, 8766)

    def test_home_creates_and_renders_default_board(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("CachyKanban", body)
        self.assertIn("Backlog", body)
        self.assertIn("Secure", headers["Set-Cookie"])
        self.assertEqual(headers["X-Frame-Options"], "DENY")

    def test_card_can_be_added_with_csrf_protection(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        token = re.search(r'name="csrf" value="([^"]+)"', body).group(1)
        project_id = re.search(r'name="project_id" value="([^"]+)"', body).group(1)
        board_id = re.search(r'name="board_id" value="([^"]+)"', body).group(1)
        column_id = re.search(r'name="column_id" value="([^"]+)"', body).group(1)
        payload = urlencode({
            "csrf": token,
            "project_id": project_id,
            "board_id": board_id,
            "column_id": column_id,
            "title": "Remote card",
        })
        status, response_headers, _ = self.request(
            "POST", "/card/add", payload,
            {"Content-Type": "application/x-www-form-urlencoded", "Cookie": f"cachykanban_csrf={token}"},
        )
        self.assertEqual(status, 303)
        self.assertIn("status=Card+added", response_headers["Location"])
        status, _, body = self.request("GET", response_headers["Location"])
        self.assertEqual(status, 200)
        self.assertIn("Remote card", body)

    def test_project_overview_aggregates_all_boards_and_filters_status(self):
        controller = Controller(self.store)
        controller.load()
        project_id = controller.project.id
        board_id = controller.board.id
        backlog, in_progress, done = controller.board.columns
        controller.add_card(backlog.id, "First board backlog card")
        controller.add_card(in_progress.id, "Progress overview card")
        controller.add_card(done.id, "Done overview card")
        second_board = controller.add_board("Second Board")
        second_backlog, second_progress, second_done = second_board.columns
        controller.add_card(second_backlog.id, "Second board backlog card")
        controller.add_card(second_progress.id, "Second board progress card")
        controller.add_card(second_done.id, "Second board done card")

        query = urlencode({
            "project": project_id,
            "board": board_id,
            "view": "overview",
        })
        status, _, body = self.request("GET", f"/?{query}")
        self.assertEqual(status, 200)
        self.assertIn('class="overview"', body)
        self.assertIn("First board backlog card", body)
        self.assertIn("Second board backlog card", body)
        self.assertIn("Second Board", body)
        self.assertIn("Progress overview card", body)
        self.assertIn("Second board progress card", body)
        self.assertIn("Done overview card", body)
        self.assertIn("Second board done card", body)
        self.assertIn("Backlog (2)", body)
        self.assertIn("In Progress (2)", body)
        self.assertIn("Done (2)", body)
        self.assertIn('name="return_view" value="overview"', body)

        query = urlencode({
            "project": project_id,
            "board": board_id,
            "view": "overview",
            "column": "backlog",
        })
        status, _, body = self.request("GET", f"/?{query}")
        self.assertEqual(status, 200)
        self.assertIn("First board backlog card", body)
        self.assertIn("Second board backlog card", body)
        self.assertNotIn("Progress overview card", body)
        self.assertNotIn("Second board progress card", body)
        self.assertNotIn("Done overview card", body)
        self.assertNotIn("Second board done card", body)

    def test_board_view_has_overview_button(self):
        status, _, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Project overview", body)
        self.assertIn("view=overview", body)

    def test_post_without_csrf_is_rejected(self):
        payload = urlencode({"project_id": "x", "board_id": "x", "title": "Nope"})
        status, _, body = self.request(
            "POST", "/card/add", payload,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 403)
        self.assertIn("Request rejected", body)


if __name__ == "__main__":
    unittest.main()
