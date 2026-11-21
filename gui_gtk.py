"""GTK 4 front-end for GAV (Linux / BSD; also works on Windows via MSYS2).

Requirements: PyGObject + GTK 4 (e.g. `apt install python3-gi gir1.2-gtk-4.0`).
Run: python3 gui_gtk.py [--lang tr] [folder]
"""
import locale
import os
import sys
import time

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk, Pango  # noqa: E402

import gav_core  # noqa: E402
from lang_loader import LangLoader  # noqa: E402

APP_ID = "io.github.gubir34.GAV"
PROGRESS_INTERVAL = 0.05


def detect_language(argv):
    if "--lang" in argv:
        i = argv.index("--lang")
        if i + 1 < len(argv):
            code = argv[i + 1]
            del argv[i:i + 2]
            return code
    code = (locale.getlocale()[0] or os.environ.get("LANG") or "en")[:2].lower()
    return code


class ResultList(Gtk.ScrolledWindow):
    def __init__(self, placeholder):
        super().__init__(vexpand=True, hexpand=True)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_placeholder(Gtk.Label(label=placeholder, margin_top=24, margin_bottom=24))
        self.set_child(self.listbox)
        self.count = 0

    def clear(self):
        self.listbox.remove_all()
        self.count = 0

    def add(self, title, subtitle, icon):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      margin_top=6, margin_bottom=6, margin_start=10, margin_end=10)
        row.append(Gtk.Image.new_from_icon_name(icon))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        name = Gtk.Label(label=title, xalign=0, selectable=True, ellipsize=Pango.EllipsizeMode.MIDDLE)
        name.set_tooltip_text(title)
        detail = Gtk.Label(label=subtitle, xalign=0, selectable=True, ellipsize=Pango.EllipsizeMode.END)
        detail.add_css_class("dim-label")
        detail.add_css_class("monospace")
        text.append(name)
        text.append(detail)
        row.append(text)
        self.listbox.append(row)
        self.count += 1


class GavWindow(Gtk.ApplicationWindow):
    def __init__(self, app, lang, initial_path=None):
        super().__init__(application=app, title=lang.t("gui_title"), default_width=820, default_height=560)
        self.lang = lang
        self.worker = None
        self.last_progress = 0.0

        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                       margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        self.set_child(root)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.path_entry = Gtk.Entry(hexpand=True, placeholder_text=lang.t("gui_path_placeholder"))
        self.path_entry.connect("activate", lambda *_: self.on_scan_clicked(None))
        if initial_path:
            self.path_entry.set_text(initial_path)
        choose = Gtk.Button(label=lang.t("gui_choose"))
        choose.connect("clicked", self.on_choose_clicked)
        self.scan_button = Gtk.Button(label=lang.t("gui_scan"))
        self.scan_button.add_css_class("suggested-action")
        self.scan_button.connect("clicked", self.on_scan_clicked)
        bar.append(self.path_entry)
        bar.append(choose)
        bar.append(self.scan_button)
        root.append(bar)

        self.progress = Gtk.ProgressBar(show_text=True)
        self.progress.set_text(lang.t("gui_ready"))
        root.append(self.progress)

        self.status = Gtk.Label(label=lang.t("gui_ready"), xalign=0, wrap=True)
        root.append(self.status)

        self.threats = ResultList(lang.t("gui_no_threats"))
        self.errors = ResultList("—")
        self.stack = Gtk.Stack(vexpand=True)
        self.stack.add_titled(self.threats, "threats", lang.t("gui_threats"))
        self.stack.add_titled(self.errors, "errors", lang.t("gui_errors"))
        switcher = Gtk.StackSwitcher(stack=self.stack, halign=Gtk.Align.CENTER)
        root.append(switcher)
        root.append(self.stack)

    # ---- folder picker -------------------------------------------------
    def on_choose_clicked(self, _button):
        if hasattr(Gtk, "FileDialog"):  # GTK >= 4.10
            dialog = Gtk.FileDialog(title=self.lang.t("gui_choose"), modal=True)
            dialog.select_folder(self, None, self._on_folder_dialog_done)
        else:
            chooser = Gtk.FileChooserNative(title=self.lang.t("gui_choose"), transient_for=self,
                                            action=Gtk.FileChooserAction.SELECT_FOLDER)
            chooser.connect("response", self._on_native_chooser_done)
            chooser.show()
            self._chooser = chooser

    def _on_folder_dialog_done(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return  # dismissed
        if folder and folder.get_path():
            self.path_entry.set_text(folder.get_path())

    def _on_native_chooser_done(self, chooser, response):
        if response == Gtk.ResponseType.ACCEPT and chooser.get_file():
            self.path_entry.set_text(chooser.get_file().get_path())
        self._chooser = None

    # ---- scanning --------------------------------------------------------
    def set_status(self, text, error=False):
        self.status.set_text(text)
        if error:
            self.status.add_css_class("error")
        else:
            self.status.remove_css_class("error")

    def on_scan_clicked(self, _button):
        if self.worker and self.worker.is_alive():
            self.worker.cancel()
            self.scan_button.set_sensitive(False)
            return
        path = self.path_entry.get_text().strip()
        if not path or not os.path.exists(path):
            self.set_status(self.lang.t("gui_invalid_path", path=gav_core.safe_display(path)), error=True)
            return

        self.threats.clear()
        self.errors.clear()
        self.update_tab_titles()
        self.progress.set_fraction(0)
        self.progress.set_text(self.lang.t("gui_collecting"))
        self.set_status(self.lang.t("gui_collecting"))
        self.scan_button.set_label(self.lang.t("gui_cancel"))
        self.scan_button.remove_css_class("suggested-action")
        self.scan_button.add_css_class("destructive-action")
        self.path_entry.set_sensitive(False)

        idle = GLib.idle_add
        self.worker = gav_core.ScanWorker(
            path,
            on_start=lambda total: idle(self.on_start, total),
            on_progress=self._progress_from_worker,
            on_threat=lambda t: idle(self.on_threat, t),
            on_error=lambda e: idle(self.on_error, e),
            on_done=lambda s, exc: idle(self.on_done, s, exc),
        )
        self.worker.start()

    def _progress_from_worker(self, done, total):
        now = time.monotonic()
        if done == total or now - self.last_progress >= PROGRESS_INTERVAL:
            self.last_progress = now
            GLib.idle_add(self.on_progress, done, total)

    def on_start(self, total):
        self.progress.set_text(self.lang.t("gui_progress", done=0, total=total))
        return False

    def on_progress(self, done, total):
        self.progress.set_fraction(done / total if total else 1)
        self.progress.set_text(self.lang.t("gui_progress", done=done, total=total))
        return False

    def on_threat(self, threat):
        self.threats.add(gav_core.safe_display(threat.path), f"{threat.algo}  {threat.hash}", "dialog-warning-symbolic")
        self.update_tab_titles()
        self.stack.set_visible_child_name("threats")
        return False

    def on_error(self, err):
        self.errors.add(gav_core.safe_display(err.path), err.reason, "dialog-question-symbolic")
        self.update_tab_titles()
        return False

    def update_tab_titles(self):
        self.stack.get_page(self.threats).set_title(f"{self.lang.t('gui_threats')} ({self.threats.count})")
        self.stack.get_page(self.errors).set_title(f"{self.lang.t('gui_errors')} ({self.errors.count})")

    def on_done(self, summary, exc):
        self.scan_button.set_sensitive(True)
        self.scan_button.set_label(self.lang.t("gui_scan"))
        self.scan_button.remove_css_class("destructive-action")
        self.scan_button.add_css_class("suggested-action")
        self.path_entry.set_sensitive(True)

        if isinstance(exc, gav_core.NoSignaturesError):
            self.progress.set_text(self.lang.t("gui_ready"))
            self.set_status(self.lang.t("gui_no_signatures"), error=True)
        elif exc is not None:
            self.progress.set_text(self.lang.t("gui_ready"))
            self.set_status(f"{type(exc).__name__}: {exc}", error=True)
        else:
            text = self.lang.t("gui_summary", scanned=summary.scanned, total=summary.total,
                               threats=len(summary.threats), errors=len(summary.errors),
                               elapsed=f"{summary.elapsed:.1f}")
            if summary.cancelled:
                text = f"{self.lang.t('gui_cancelled')} — {text}"
            else:
                self.progress.set_fraction(1)
            self.progress.set_text(self.lang.t("scan_done").strip("-"))
            self.set_status(text, error=bool(summary.threats))
        return False


class GavApp(Gtk.Application):
    def __init__(self, lang, initial_path):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.lang = lang
        self.initial_path = initial_path

    def do_activate(self):
        from gi.repository import Gdk
        css = Gtk.CssProvider()
        rules = ".monospace { font-family: monospace; font-size: 0.9em; }"
        if hasattr(css, "load_from_string"):  # GTK >= 4.12
            css.load_from_string(rules)
        else:
            css.load_from_data(rules.encode(), -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        GavWindow(self, self.lang, self.initial_path).present()


def main(argv):
    argv = list(argv)
    lang = LangLoader("lng.ltf", default=detect_language(argv))
    initial = argv[1] if len(argv) > 1 else None
    return GavApp(lang, initial).run([argv[0]])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
