import base64
import json
from gi.repository import Gtk, Gdk, GLib, Gio, Adw

import locales
import calculations
from logger import get_logger

log = get_logger('test')

TOTAL_TIME = 20 * 60
TOTAL_QUESTIONS = 60
IMG_EXT = '.svg'

_texture_cache = {}

ANSWERS_B64 = "eyIxIjo0LCIyIjo1LCIzIjoxLCI0IjoyLCI1Ijo2LCI2IjozLCI3Ijo2LCI4IjoyLCI5IjoxLCIxMCI6MywiMTEiOjQsIjEyIjo1LCIxMyI6MiwiMTQiOjYsIjE1IjoxLCIxNiI6MiwiMTciOjEsIjE4IjozLCIxOSI6NSwiMjAiOjYsIjIxIjo0LCIyMiI6MywiMjMiOjQsIjI0Ijo1LCIyNSI6OCwiMjYiOjIsIjI3IjozLCIyOCI6OCwiMjkiOjcsIjMwIjo0LCIzMSI6NSwiMzIiOjEsIjMzIjo3LCIzNCI6NiwiMzUiOjEsIjM2IjoyLCIzNyI6MywiMzgiOjQsIjM5IjozLCI0MCI6NywiNDEiOjgsIjQyIjo2LCI0MyI6NSwiNDQiOjQsIjQ1IjoxLCI0NiI6MiwiNDciOjUsIjQ4Ijo2LCI0OSI6NywiNTAiOjYsIjUxIjo4LCI1MiI6MiwiNTMiOjEsIjU0Ijo1LCI1NSI6MSwiNTYiOjYsIjU3IjozLCI1OCI6MiwiNTkiOjQsIjYwIjo1fQ=="


def decode_answers():
    try:
        return json.loads(base64.b64decode(ANSWERS_B64).decode('utf-8'))
    except Exception as e:
        log.error(f"Failed to decode answers: {e}")
        return {}


def get_options_count(series):
    return 6 if series in ('A', 'B') else 8


def is_dark_mode():
    try:
        return Adw.StyleManager.get_default().get_dark()
    except Exception:
        return True


def get_theme_dir():
    return 'dark' if is_dark_mode() else 'light'


def load_texture(q, theme=None):
    if theme is None:
        theme = get_theme_dir()
    path = f'/site/ikhlasulov/openrpm/images/{theme}/{q}{IMG_EXT}'
    try:
        data = Gio.resources_lookup_data(path, Gio.ResourceLookupFlags.NONE)
        if data:
            return Gdk.Texture.new_from_bytes(data)
    except GLib.Error as e:
        log.warning(f"Could not load image {q} for {theme}: {e.message}")
    return None


def get_texture(q, theme=None):
    if theme is None:
        theme = get_theme_dir()
    key = (q, theme)
    if key not in _texture_cache:
        _texture_cache[key] = load_texture(q, theme)
    return _texture_cache.get(key)


class TestController:
    def __init__(self, builder, age_percent, on_finish_callback=None, on_reset_callback=None):
        self.builder = builder
        self.age_percent = age_percent
        self.on_finish = on_finish_callback
        self.on_reset = on_reset_callback

        self.current = 1
        self.answers = {}
        self.time_left = TOTAL_TIME
        self.active = False
        self.timer_id = None
        self.answer_key = decode_answers()
        self.dialog = None
        self._handlers = {}
        self._theme_handler = None
        self._current_theme = None
        self._option_buttons = []
        self._current_options_count = 0
        self._current_cols = 0
        self._click_handlers = {}

        self._cache_widgets()
        self._create_option_buttons()
        self._wire()
        self._watch_theme()

    def _cache_widgets(self):
        b = self.builder
        self.timer_progress = b.get_object('timer_progress')
        self.progress_label = b.get_object('progress_label')
        self.question_image = b.get_object('question_image')
        self.options_grid = b.get_object('options_grid')
        self.prev_btn = b.get_object('prev_button')
        self.end_btn = b.get_object('end_button')
        self.next_btn = b.get_object('next_button')

    def _create_option_buttons(self):
        """Create 8 option buttons."""
        for i in range(1, 9):
            btn = Gtk.Button(label=str(i))
            btn.add_css_class('pill')
            btn.set_hexpand(True)
            btn.set_vexpand(True)
            btn.set_halign(Gtk.Align.FILL)
            btn.set_valign(Gtk.Align.FILL)
            btn.set_visible(False)
            self._option_buttons.append(btn)

    def _wire(self):
        self._unwire()
        for name, obj, cb in [('prev', self.prev_btn, self._prev),
                              ('end', self.end_btn, self._prompt_end),
                              ('next', self.next_btn, self._next)]:
            if obj:
                self._handlers[name] = (obj, obj.connect('clicked', cb))

    def _unwire(self):
        for obj, hid in self._handlers.values():
            try:
                obj.disconnect(hid)
            except Exception as e:
                log.debug(f"Handler already disconnected: {e}")
        self._handlers = {}

    def _watch_theme(self):
        self._current_theme = get_theme_dir()
        try:
            style_mgr = Adw.StyleManager.get_default()
            self._theme_handler = style_mgr.connect('notify::dark', self._on_theme_changed)
        except Exception as e:
            log.warning(f"Could not watch theme: {e}")

    def _on_theme_changed(self, style_mgr, param):
        new_theme = get_theme_dir()
        if new_theme != self._current_theme:
            self._current_theme = new_theme
            GLib.idle_add(self._preload_theme_images, new_theme, GLib.PRIORITY_LOW)
            if self.active and self.question_image:
                paintable = get_texture(self.current)
                if paintable:
                    self.question_image.set_from_paintable(paintable)

    def _preload_theme_images(self, theme, *args):
        for q in range(1, TOTAL_QUESTIONS + 1):
            if get_texture(q, theme) is None:
                return True
        return False

    def start(self):
        self.active = True
        self.current = 1
        self.answers = {}
        self.time_left = TOTAL_TIME
        self._current_theme = get_theme_dir()
        self._current_cols = 0
        self._current_options_count = 0

        # Reset all buttons - hide all, remove styles
        for btn in self._option_buttons:
            btn.set_visible(False)
            if btn.has_css_class('suggested-action'):
                btn.remove_css_class('suggested-action')

        if self.timer_progress:
            self.timer_progress.set_fraction(1.0)

        theme = self._current_theme
        for q in range(1, 6):
            get_texture(q, theme)

        self._run_timer()
        self._show()

    def _run_timer(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
        self.timer_id = GLib.timeout_add(1000, self._tick)

    def _stop_timer(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None

    def _tick(self):
        if not self.active:
            return False
        self.time_left -= 1
        if self.timer_progress:
            self.timer_progress.set_fraction(max(0, self.time_left / TOTAL_TIME))
        if self.time_left <= 0:
            self._complete()
            return False
        return True

    def _show(self):
        q = self.current
        series = calculations.get_series(q)

        if self.progress_label:
            tmpl = locales.get_text('test.progress_template')
            if '{q}' in tmpl and '{s}' in tmpl:
                self.progress_label.set_label(tmpl.replace('{q}', str(q)).replace('{s}', series))
            else:
                self.progress_label.set_label(f"{locales.get_text('test.question')} {q} | {series}")

        if self.question_image:
            paintable = get_texture(q)
            if paintable:
                self.question_image.set_from_paintable(paintable)

        self._update_options(series)
        self._update_nav()

    def _update_options(self, series):
        count = get_options_count(series)
        cols = 3 if count == 6 else 4

        need_rebuild = (cols != self._current_cols)
        self._current_cols = cols

        if self.options_grid:
            # ALWAYS clear grid completely first
            while child := self.options_grid.get_first_child():
                self.options_grid.remove(child)

            # Force grid to reset column geometry
            self.options_grid.set_column_homogeneous(False)
            self.options_grid.queue_resize()

            # Rebuild with new layout
            for i in range(1, count + 1):
                btn = self._option_buttons[i - 1]
                btn.set_label(str(i))
                btn.set_visible(True)

                is_selected = self.answers.get(self.current) == i
                has_suggested = btn.has_css_class('suggested-action')

                if is_selected and not has_suggested:
                    btn.add_css_class('suggested-action')
                elif not is_selected and has_suggested:
                    btn.remove_css_class('suggested-action')

                old_handler = self._click_handlers.get(btn)
                if old_handler:
                    try:
                        btn.disconnect(old_handler)
                    except Exception:
                        pass
                self._click_handlers[btn] = btn.connect('clicked', self._select, i)

                row, col = (i - 1) // cols, (i - 1) % cols
                self.options_grid.attach(btn, col, row, 1, 1)

            # Hide extra buttons (7, 8 for series A, B)
            for i in range(count + 1, 9):
                btn = self._option_buttons[i - 1]
                btn.set_visible(False)
                if btn.has_css_class('suggested-action'):
                    btn.remove_css_class('suggested-action')

            self.options_grid.set_column_homogeneous(True)
            self.options_grid.queue_resize()

        self._current_options_count = count

    def _select(self, btn, opt):
        self.answers[self.current] = opt
        for i, b in enumerate(self._option_buttons[:self._current_options_count], 1):
            is_selected = (i == opt)
            has_suggested = b.has_css_class('suggested-action')
            if is_selected and not has_suggested:
                b.add_css_class('suggested-action')
            elif not is_selected and has_suggested:
                b.remove_css_class('suggested-action')

    def _update_nav(self):
        if self.prev_btn:
            self.prev_btn.set_sensitive(self.current > 1)
        if self.next_btn:
            label = locales.get_text('test.finish' if self.current == TOTAL_QUESTIONS else 'test.next')
            self.next_btn.set_label(label)
        if self.end_btn:
            self.end_btn.set_label(locales.get_text('test.end'))

    def _prev(self, btn):
        if self.current > 1:
            self.current -= 1
            self._show()

    def _next(self, btn):
        if self.current < TOTAL_QUESTIONS:
            self.current += 1
            self._show()
        else:
            self._complete()

    def _prompt_end(self, btn):
        if self.dialog:
            self.dialog.close()
            self.dialog = None

        self.dialog = Adw.MessageDialog.new(
            self.builder.get_object('main_window'),
            locales.get_text('confirm.title'),
            locales.get_text('confirm.message')
        )
        self.dialog.add_response('cancel', locales.get_text('confirm.cancel'))
        self.dialog.add_response('end', locales.get_text('confirm.end'))
        self.dialog.set_response_appearance('end', Adw.ResponseAppearance.DESTRUCTIVE)
        self.dialog.connect('response', self._handle_confirm)
        self.dialog.present()

    def _handle_confirm(self, dlg, resp):
        dlg.close()
        self.dialog = None
        if resp == 'end':
            self._complete()

    def _complete(self):
        self.active = False
        self._stop_timer()
        self._unwire()

        if self._theme_handler:
            try:
                Adw.StyleManager.get_default().disconnect(self._theme_handler)
            except Exception as e:
                log.debug(f"Theme handler already disconnected: {e}")
            self._theme_handler = None

        elapsed = TOTAL_TIME - self.time_left
        if self.on_finish:
            self.on_finish({
                'user_answers': self.answers.copy(),
                'answer_key': self.answer_key,
                'age_percent': self.age_percent,
                'time_taken': elapsed
            })
