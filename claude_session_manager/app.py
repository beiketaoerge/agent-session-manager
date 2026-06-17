"""Application entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from .prefs import apply_color_scheme
from .state import AppState
from .store import SessionStore
from .window import MainWindow

# Bundled icons (e.g. tab-close-symbolic); found by name when installed.
_BUNDLED_ICONS = Path(__file__).resolve().parent.parent / "data" / "icons"

_CSS = b"""
.status-dot {
  min-width: 8px;
  min-height: 8px;
  border-radius: 100%;
  background-color: alpha(currentColor, 0.25);
}
.status-dot.open { background-color: #2ec27e; }
.status-dot.attention { background-color: #3584e4; }

.group-header { padding: 10px 10px 4px 10px; }

/* session-row state badges */
.waiting-badge { color: #e5a50a; }
.interrupted-badge { color: #e01b24; }

/* make the active tab clearly stand out from inactive ones */
notebook tab:active {
  background-color: shade(#D97757, 1.6);
  border-bottom: 3px solid #D97757;
}
notebook tab:active label { font-weight: bold; }
notebook tab label { opacity: 0.6; }
notebook tab:active label { opacity: 1.0; }

.count-badge {
  background-color: alpha(currentColor, 0.1);
  border-radius: 10px;
  padding: 1px 8px;
  font-size: 0.8em;
}

/* children connect to their group via a left guide line, on a faint card */
row.session-child {
  margin-left: 20px;
  margin-right: 16px;
  background-color: alpha(currentColor, 0.06);
  border-left: 2px solid alpha(currentColor, 0.15);
  border-radius: 0 8px 8px 0;
}
row.session-child:hover {
  background-color: alpha(currentColor, 0.1);
  border-left-color: alpha(currentColor, 0.3);
}

.heading { font-weight: bold; }
.caption { font-size: 0.85em; }
"""


APP_ID = "io.github.r4nd3l.AgentSessionManager"


class App(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=os.environ.get("CSM_APP_ID") or APP_ID)

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_data(_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        if _BUNDLED_ICONS.is_dir():
            Gtk.IconTheme.get_default().append_search_path(str(_BUNDLED_ICONS))

        self.state = AppState()
        apply_color_scheme(self.state.get_setting("color_scheme"))
        self.store = SessionStore(self.state)
        self.store.start()

        focus = Gio.SimpleAction.new("focus-session", GLib.VariantType("s"))
        focus.connect("activate", self._on_focus_session)
        self.add_action(focus)

        new_window = Gio.SimpleAction.new("new-window", None)
        new_window.connect("activate", lambda *_: self._new_window())
        self.add_action(new_window)
        self.set_accels_for_action("app.new-window", ["<Control><Shift>n"])

    def _new_window(self) -> MainWindow:
        window = MainWindow(application=self, state=self.state, store=self.store)
        window.show_all()
        return window

    def _on_focus_session(self, _action, param: GLib.Variant) -> None:
        window = self.get_active_window()
        if window is None:
            return
        window.present()
        session_id = param.get_string()
        if session_id and hasattr(window, "focus_session"):
            window.focus_session(session_id)

    def do_activate(self) -> None:
        window = self.get_active_window()
        if window is None:
            window = self._new_window()
        window.present()


def main() -> int:
    from . import i18n
    from .state import AppState

    i18n.init(AppState().get_setting("language"))
    app = App()
    return app.run(sys.argv)
