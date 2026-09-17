from __future__ import annotations

import argparse
import html
import secrets
import threading
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from .controller import Controller
from .models import Board, Card, ChecklistItem, Column, PRIORITIES
from .store import Store, StoreError

HOST = "127.0.0.1"
PORT = 8766
MAX_BODY = 1_000_000
_CSRF_TOKEN = secrets.token_urlsafe(32)
_LOCK = threading.RLock()


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _page(title: str, body: str, *, status: str = "") -> str:
    notice = f'<p class="notice">{_escape(status)}</p>' if status else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="dark light">
  <title>{_escape(title)} · CachyKanban</title>
  <style>
    :root {{ color-scheme: dark; --bg:#11151c; --panel:#1a202b; --raised:#232b38;
      --text:#eef2f7; --muted:#9aa6b6; --line:#344052; --accent:#6ea8fe;
      --danger:#ff7b83; --shadow:0 8px 26px #0005; }}
    * {{ box-sizing:border-box }}
    body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.45 system-ui,sans-serif }}
    header {{ position:sticky; top:0; z-index:5; padding:12px max(14px,env(safe-area-inset-left));
      background:#11151cf2; border-bottom:1px solid var(--line); backdrop-filter:blur(12px) }}
    h1 {{ margin:0 0 9px; font-size:21px }} h2,h3 {{ margin:.2rem 0 .7rem }}
    .selectors {{ display:flex; gap:8px; flex-wrap:wrap }}
    select,input,textarea,button {{ font:inherit; color:var(--text); background:var(--raised);
      border:1px solid var(--line); border-radius:9px; padding:9px 11px }}
    select {{ min-width:145px }} button {{ cursor:pointer; font-weight:650 }}
    a.button {{ display:inline-block; color:var(--text); background:var(--raised); border:1px solid var(--line);
      border-radius:9px; padding:8px 11px; text-decoration:none; font-weight:650 }}
    a.button.active {{ background:var(--accent); border-color:var(--accent); color:#09111d }}
    button.primary {{ background:var(--accent); border-color:var(--accent); color:#09111d }}
    button.danger {{ color:var(--danger) }} textarea {{ width:100%; min-height:120px; resize:vertical }}
    main {{ padding:16px max(14px,env(safe-area-inset-left)) 30px }}
    .board-heading {{ display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap }}
    .filters {{ display:flex; gap:7px; flex-wrap:wrap; margin:10px 0 15px }}
    .board {{ display:grid; grid-auto-flow:column; grid-auto-columns:minmax(285px,340px); gap:14px;
      overflow-x:auto; align-items:start; padding-bottom:16px; scroll-snap-type:x proximity }}
    .overview {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(285px,1fr)); gap:14px; align-items:start }}
    .overview .column:only-child {{ max-width:720px }}
    .column {{ background:var(--panel); border:1px solid var(--line); border-top:4px solid var(--column);
      border-radius:13px; padding:11px; scroll-snap-align:start; min-height:120px }}
    .column-head {{ display:flex; justify-content:space-between; align-items:center; gap:8px }}
    .count {{ color:var(--muted); font-size:13px }}
    .card {{ margin:9px 0; background:var(--raised); border:1px solid var(--line); border-radius:10px;
      padding:11px; box-shadow:var(--shadow) }}
    .card-title {{ display:flex; justify-content:space-between; gap:8px; font-weight:700 }}
    .priority {{ color:#ffc46b; font-size:12px; text-transform:uppercase }}
    .board-badge {{ display:inline-block; color:var(--muted); background:#ffffff0c; border-radius:5px;
      padding:2px 6px; margin-top:7px; font-size:12px }}
    .labels {{ display:flex; gap:5px; flex-wrap:wrap; margin-top:7px }}
    .label {{ border-left:4px solid var(--label); background:#ffffff0c; border-radius:5px; padding:2px 6px; font-size:12px }}
    .notes {{ color:#c9d1dc; white-space:pre-wrap; margin:.65rem 0 0 }}
    .progress {{ color:var(--muted); font-size:13px; margin-top:7px }}
    details {{ margin-top:9px }} summary {{ cursor:pointer; color:var(--accent); font-weight:650 }}
    form {{ margin:0 }} .editor {{ display:grid; gap:9px; margin-top:10px }}
    .row {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center }}
    .row > input[type=text] {{ flex:1; min-width:150px }}
    .checks {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:5px }}
    .checks label {{ display:flex; gap:6px; align-items:center }}
    .actions {{ display:flex; gap:7px; flex-wrap:wrap }}
    .add {{ margin-top:10px }} .empty {{ color:var(--muted); text-align:center; padding:25px 8px }}
    .notice {{ max-width:700px; margin:0 auto 12px; padding:9px 12px; background:#244c38; border-radius:8px }}
    footer {{ color:var(--muted); text-align:center; padding:10px 15px 25px; font-size:12px }}
    @media (max-width:640px) {{ .board {{ grid-auto-columns:calc(100vw - 28px) }} main {{ padding-top:12px }} }}
  </style>
</head>
<body>{notice}{body}<footer>Private tailnet access · data stays on this computer</footer></body></html>"""


class CachyKanbanHandler(BaseHTTPRequestHandler):
    server_version = "CachyKanbanWeb/1"

    @property
    def store(self) -> Store:
        return self.server.store  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def _send(self, content: str, status: HTTPStatus = HTTPStatus.OK, *, content_type: str = "text/html; charset=utf-8") -> None:
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Set-Cookie", f"cachykanban_csrf={_CSRF_TOKEN}; Path=/; Secure; HttpOnly; SameSite=Strict")
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _form(self) -> dict[str, list[str]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 1 or length > MAX_BODY:
            raise ValueError("Invalid request size")
        return parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)

    def _validate_csrf(self, form: dict[str, list[str]]) -> None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        cookie_token = cookie.get("cachykanban_csrf")
        form_token = form.get("csrf", [""])[0]
        if cookie_token is None or not secrets.compare_digest(cookie_token.value, _CSRF_TOKEN) or not secrets.compare_digest(form_token, _CSRF_TOKEN):
            raise PermissionError("The form expired. Reload the page and try again.")

    def _controller(self, project_id: str = "", board_id: str = "") -> Controller:
        controller = Controller(self.store)
        controller.load()
        if project_id:
            controller.open_project(project_id, board_id or None)
        elif board_id:
            controller.open_board(board_id)
        return controller

    @staticmethod
    def _value(form: dict[str, list[str]], name: str) -> str:
        return form.get(name, [""])[0].strip()

    @staticmethod
    def _url(
        project_id: str,
        board_id: str,
        status: str = "",
        view: str = "",
        column_id: str = "",
    ) -> str:
        query = {"project": project_id, "board": board_id}
        if status:
            query["status"] = status
        if view:
            query["view"] = view
        if column_id:
            query["column"] = column_id
        return "/?" + urlencode(query)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send("ok\n", content_type="text/plain; charset=utf-8")
            return
        if parsed.path != "/":
            self._send(_page("Not found", "<main><h1>Not found</h1></main>"), HTTPStatus.NOT_FOUND)
            return
        query = parse_qs(parsed.query)
        try:
            with _LOCK:
                controller = self._controller(
                    query.get("project", [""])[0], query.get("board", [""])[0]
                )
                content = self._render_board(
                    controller,
                    query.get("status", [""])[0],
                    query.get("view", [""])[0],
                    query.get("column", [""])[0],
                )
            self._send(content)
        except (StoreError, KeyError, RuntimeError) as exc:
            self._send(_page("Error", f"<main><h1>Unable to load board</h1><p>{_escape(exc)}</p></main>"), HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            form = self._form()
            self._validate_csrf(form)
            project_id = self._value(form, "project_id")
            board_id = self._value(form, "board_id")
            return_view = self._value(form, "return_view")
            return_column = self._value(form, "return_column")
            with _LOCK:
                controller = self._controller(project_id, board_id)
                status = self._mutate(parsed.path, controller, form)
            self._redirect(
                self._url(project_id, board_id, status, return_view, return_column)
            )
        except PermissionError as exc:
            self._send(_page("Expired", f"<main><h1>Request rejected</h1><p>{_escape(exc)}</p></main>"), HTTPStatus.FORBIDDEN)
        except (ValueError, KeyError, StoreError, RuntimeError) as exc:
            self._send(_page("Error", f"<main><h1>Could not save</h1><p>{_escape(exc)}</p></main>"), HTTPStatus.BAD_REQUEST)

    def _mutate(self, path: str, controller: Controller, form: dict[str, list[str]]) -> str:
        if path == "/card/add":
            title = self._value(form, "title")
            if not title:
                raise ValueError("Card title is required")
            controller.add_card(self._value(form, "column_id"), title[:300])
            return "Card added"
        if path == "/card/update":
            card_id = self._value(form, "card_id")
            title = self._value(form, "title")
            if not title:
                raise ValueError("Card title is required")
            priority = self._value(form, "priority")
            if priority not in PRIORITIES:
                raise ValueError("Invalid priority")
            checklist_lines = [line.strip() for line in self._value(form, "checklist").splitlines() if line.strip()]
            done = {int(value) for value in form.get("done", []) if value.isdigit()}
            valid_labels = {label.id for label in controller.board.labels}  # type: ignore[union-attr]
            labels = [value for value in form.get("label", []) if value in valid_labels]
            controller.update_card(
                card_id,
                title=title[:300],
                notes=self._value(form, "notes")[:50_000],
                priority=priority,
                label_ids=labels,
                checklist=[ChecklistItem(text=line[:500], done=index in done) for index, line in enumerate(checklist_lines)],
            )
            return "Card saved"
        if path == "/card/move":
            controller.move_card(self._value(form, "card_id"), self._value(form, "column_id"), 10_000)
            return "Card moved"
        if path == "/card/archive":
            controller.set_card_archived(self._value(form, "card_id"), self._value(form, "archived") == "1")
            return "Card updated"
        if path == "/card/delete":
            controller.delete_card(self._value(form, "card_id"))
            return "Card deleted"
        raise ValueError("Unknown action")

    def _hidden(
        self,
        project_id: str,
        board_id: str,
        return_view: str = "",
        return_column: str = "",
    ) -> str:
        fields = (
            f'<input type="hidden" name="csrf" value="{_CSRF_TOKEN}">'
            f'<input type="hidden" name="project_id" value="{_escape(project_id)}">'
            f'<input type="hidden" name="board_id" value="{_escape(board_id)}">'
        )
        if return_view:
            fields += f'<input type="hidden" name="return_view" value="{_escape(return_view)}">'
        if return_column:
            fields += f'<input type="hidden" name="return_column" value="{_escape(return_column)}">'
        return fields

    def _render_board(
        self,
        controller: Controller,
        status: str,
        view: str = "",
        column_filter: str = "",
    ) -> str:
        project = controller.project
        board = controller.board
        if project is None or board is None:
            raise RuntimeError("No board is available")
        project_options = "".join(
            f'<option value="{_escape(item["id"])}" {"selected" if item["id"] == project.id else ""}>{_escape(item["name"])}</option>'
            for item in controller.summaries
        )
        board_options = "".join(
            f'<option value="{_escape(item.id)}" {"selected" if item.id == board.id else ""}>{_escape(item.name)}</option>'
            for item in project.boards
        )
        header = f"""<header><h1>CachyKanban</h1><form class="selectors" method="get" action="/">
          <select name="project" aria-label="Project">{project_options}</select>
          <select name="board" aria-label="Board">{board_options}</select>
          <button type="submit">Open</button></form></header>"""
        if view == "overview":
            content = self._render_project_overview(controller, column_filter)
            board_url = self._url(project.id, board.id)
            heading_action = f'<a class="button" href="{_escape(board_url)}">Board view</a>'
            heading = f"{project.name} overview"
        else:
            columns = "".join(self._render_column(controller, column) for column in board.columns)
            if not columns:
                columns = '<p class="empty">This board has no columns. Add one in the desktop app.</p>'
            content = f'<section class="board">{columns}</section>'
            overview_url = self._url(project.id, board.id, view="overview")
            heading_action = f'<a class="button" href="{_escape(overview_url)}">Project overview</a>'
            heading = board.name
        body = (
            f'{header}<main><div class="board-heading"><h2>{_escape(heading)}</h2>'
            f'{heading_action}</div>{content}</main>'
        )
        return _page(board.name, body, status=status)

    @staticmethod
    def _column_key(name: str) -> str:
        return " ".join(name.casefold().split())

    def _render_project_overview(
        self, controller: Controller, column_filter: str
    ) -> str:
        board = controller.board
        project = controller.project
        assert board is not None and project is not None

        groups: dict[str, dict[str, object]] = {}
        for source_board in project.boards:
            for source_column in source_board.columns:
                key = self._column_key(source_column.name)
                group = groups.setdefault(
                    key,
                    {
                        "name": source_column.name,
                        "color": source_column.color,
                        "cards": [],
                        "archived": [],
                    },
                )
                for card in source_column.cards:
                    target = "archived" if card.archived else "cards"
                    group[target].append((source_board, source_column, card))

        selected = self._column_key(column_filter)
        if selected not in groups:
            selected = ""
        all_url = self._url(project.id, board.id, view="overview")
        filters = [
            f'<a class="button {"active" if not selected else ""}" href="{_escape(all_url)}">All</a>'
        ]
        for key, group in groups.items():
            url = self._url(
                project.id, board.id, view="overview", column_id=key
            )
            count = len(group["cards"])
            filters.append(
                f'<a class="button {"active" if selected == key else ""}" '
                f'href="{_escape(url)}">{_escape(group["name"])} ({count})</a>'
            )
        visible = [
            (key, group)
            for key, group in groups.items()
            if not selected or key == selected
        ]
        columns = "".join(
            self._render_project_group(controller, key, group, selected)
            for key, group in visible
        )
        if not columns:
            columns = '<p class="empty">This project has no board columns.</p>'
        return (
            '<nav class="filters" aria-label="Filter cards">'
            + "".join(filters)
            + f'</nav><section class="overview">{columns}</section>'
        )

    def _render_project_group(
        self,
        controller: Controller,
        key: str,
        group: dict[str, object],
        selected: str,
    ) -> str:
        cards = group["cards"]
        archived_cards = group["archived"]
        rendered = "".join(
            self._render_card(
                controller,
                column,
                card,
                return_view="overview",
                return_column=selected,
                source_board=source_board,
                show_board=True,
            )
            for source_board, column, card in cards
        )
        if not rendered:
            rendered = '<p class="empty">No cards yet</p>'
        archived = ""
        if archived_cards:
            archived = (
                f'<details><summary>Archived ({len(archived_cards)})</summary>'
                + "".join(
                    self._render_card(
                        controller,
                        column,
                        card,
                        return_view="overview",
                        return_column=selected,
                        source_board=source_board,
                        show_board=True,
                    )
                    for source_board, column, card in archived_cards
                )
                + "</details>"
            )
        return (
            f'<article class="column" data-column="{_escape(key)}" '
            f'style="--column:{_escape(group["color"])}">'
            f'<div class="column-head"><h3>{_escape(group["name"])}</h3>'
            f'<span class="count">{len(cards)}</span></div>{rendered}{archived}</article>'
        )

    def _render_column(
        self,
        controller: Controller,
        column: Column,
        return_view: str = "",
        return_column: str = "",
    ) -> str:
        board = controller.board
        project = controller.project
        assert board is not None and project is not None
        active_cards = [card for card in column.cards if not card.archived]
        archived_cards = [card for card in column.cards if card.archived]
        cards = "".join(
            self._render_card(
                controller, column, card, return_view, return_column
            )
            for card in active_cards
        )
        if not cards:
            cards = '<p class="empty">No cards yet</p>'
        archived = ""
        if archived_cards:
            archived = (
                f'<details><summary>Archived ({len(archived_cards)})</summary>'
                + "".join(
                    self._render_card(
                        controller, column, card, return_view, return_column
                    )
                    for card in archived_cards
                )
                + "</details>"
            )
        hidden = self._hidden(
            project.id, board.id, return_view, return_column
        )
        return f"""<article class="column" style="--column:{_escape(column.color)}">
          <div class="column-head"><h3>{_escape(column.name)}</h3><span class="count">{len(active_cards)}</span></div>
          {cards}{archived}
          <form class="add row" method="post" action="/card/add">{hidden}
            <input type="hidden" name="column_id" value="{_escape(column.id)}">
            <input type="text" name="title" maxlength="300" placeholder="New card" required>
            <button class="primary" type="submit">Add</button>
          </form></article>"""

    def _render_card(
        self,
        controller: Controller,
        column: Column,
        card: Card,
        return_view: str = "",
        return_column: str = "",
        source_board: Board | None = None,
        show_board: bool = False,
    ) -> str:
        board = source_board or controller.board
        project = controller.project
        assert board is not None and project is not None
        hidden = self._hidden(
            project.id, board.id, return_view, return_column
        )
        board_badge = (
            f'<span class="board-badge">{_escape(board.name)}</span>'
            if show_board else ""
        )
        labels_by_id = {label.id: label for label in board.labels}
        labels = "".join(
            f'<span class="label" style="--label:{_escape(labels_by_id[label_id].color)}">{_escape(labels_by_id[label_id].name)}</span>'
            for label_id in card.label_ids if label_id in labels_by_id
        )
        done, total = card.progress()
        progress = f'<p class="progress">Checklist {done}/{total}</p>' if total else ""
        priority = f'<span class="priority">{_escape(card.priority)}</span>' if card.priority != "none" else ""
        notes = f'<p class="notes">{_escape(card.notes)}</p>' if card.notes else ""
        priority_options = "".join(
            f'<option value="{item}" {"selected" if item == card.priority else ""}>{item.title()}</option>'
            for item in PRIORITIES
        )
        label_checks = "".join(
            f'<label><input type="checkbox" name="label" value="{_escape(label.id)}" {"checked" if label.id in card.label_ids else ""}>{_escape(label.name)}</label>'
            for label in board.labels
        )
        checklist_text = "\n".join(item.text for item in card.checklist)
        done_checks = "".join(
            f'<label><input type="checkbox" name="done" value="{index}" {"checked" if item.done else ""}>{_escape(item.text)}</label>'
            for index, item in enumerate(card.checklist)
        )
        column_options = "".join(
            f'<option value="{_escape(item.id)}" {"selected" if item.id == column.id else ""}>{_escape(item.name)}</option>'
            for item in board.columns
        )
        return f"""<article class="card">
          <div class="card-title"><span>{_escape(card.title)}</span>{priority}</div>{board_badge}{labels}{notes}{progress}
          <details><summary>Edit</summary>
            <form class="editor" method="post" action="/card/update">{hidden}
              <input type="hidden" name="card_id" value="{_escape(card.id)}">
              <label>Title <input type="text" name="title" maxlength="300" value="{_escape(card.title)}" required></label>
              <label>Notes <textarea name="notes" maxlength="50000">{_escape(card.notes)}</textarea></label>
              <label>Priority <select name="priority">{priority_options}</select></label>
              <div class="checks">{label_checks or '<span class="count">No labels</span>'}</div>
              <label>Checklist (one item per line)<textarea name="checklist">{_escape(checklist_text)}</textarea></label>
              <div class="checks">{done_checks}</div>
              <button class="primary" type="submit">Save card</button>
            </form>
            <form class="editor" method="post" action="/card/move">{hidden}
              <input type="hidden" name="card_id" value="{_escape(card.id)}">
              <div class="row"><select name="column_id">{column_options}</select><button type="submit">Move</button></div>
            </form>
            <div class="actions">
              <form method="post" action="/card/archive">{hidden}<input type="hidden" name="card_id" value="{_escape(card.id)}"><input type="hidden" name="archived" value="{0 if card.archived else 1}"><button type="submit">{'Restore' if card.archived else 'Archive'}</button></form>
              <form method="post" action="/card/delete">{hidden}<input type="hidden" name="card_id" value="{_escape(card.id)}"><button class="danger" type="submit">Delete</button></form>
            </div>
          </details></article>"""


class CachyKanbanServer(HTTPServer):
    def __init__(self, address: tuple[str, int], store: Store | None = None) -> None:
        self.store = store or Store()
        super().__init__(address, CachyKanbanHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Private web UI for CachyKanban")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    server = CachyKanbanServer((args.host, args.port))
    print(f"CachyKanban web listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
