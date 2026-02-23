import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gdk, Gio, GLib

import locales
import result
import test
from logger import get_logger

log = get_logger('window')

BASE_WIDTH = 1920
WINDOW_WIDTH_PCT = 0.5
WINDOW_ASPECT = 0.75

UI_FILES = ['window.ui', 'intro.ui', 'test.ui', 'result.ui', 'shortcuts.ui']
RESOURCE_BASE = '/site/ikhlasulov/openrpm/'

INTRO_SIZES = [
    ('intro_page', 'spacing', 24), ('intro_page', 'margin-top', 48),
    ('intro_page', 'margin-bottom', 48), ('intro_page', 'margin-start', 24),
    ('intro_page', 'margin-end', 24), ('prefs_group_info', 'width-request', 400),
    ('prefs_group_settings', 'width-request', 400), ('start_button', 'width-request', 140),
]

TEST_FIXED_SIZES = [
    ('timer_progress', 'width-request', 418),
    ('question_image', 'pixel-size', 400),
    ('options_grid', 'width-request', 418),
    ('navigation_container', 'width-request', 418),
]

TEST_SCALED_SIZES = [
    ('test_page', 'spacing', 12), ('test_page', 'margin-start', 24),
    ('test_page', 'margin-end', 24), ('test_page', 'margin-top', 12),
    ('test_page', 'margin-bottom', 12), ('progress_container', 'spacing', 8),
    ('content_box', 'spacing', 8),
    ('options_grid', 'column-spacing', 8), ('options_grid', 'row-spacing', 8),
    ('navigation_container', 'spacing', 8),
]

RESULT_SIZES = [
    ('result_page', 'margin-top', 32), ('result_page', 'margin-bottom', 32),
    ('result_page', 'margin-start', 24), ('result_page', 'margin-end', 24),
    ('result_page', 'spacing', 24), ('result_content_box', 'spacing', 24),
    ('return_button', 'width-request', 140),
]

MIN_TEST_WIDTH = 468
MIN_TEST_HEIGHT = 700
MIN_RESULT_WIDTH = 1000
MIN_RESULT_HEIGHT = 650


def load_ui(builder):
    for ui_file in UI_FILES:
        try:
            builder.add_from_resource(f'{RESOURCE_BASE}ui/{ui_file}')
        except GLib.Error as e:
            log.warning(f"Could not load {ui_file}: {e.message}")


def load_css():
    try:
        css_bytes = Gio.resources_lookup_data(
            f'{RESOURCE_BASE}styles/style.css', Gio.ResourceLookupFlags.NONE)
        provider = Gtk.CssProvider()
        provider.load_from_data(css_bytes.get_data())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    except GLib.Error as e:
        log.warning(f"Could not load CSS: {e.message}")


def apply_sizes(builder, configs, scale=1.0):
    for name, prop, base in configs:
        widget = builder.get_object(name)
        if widget:
            widget.set_property(prop, int(base * scale))


def set_clamp(builder, scale, wide=False):
    clamp = builder.get_object('content_clamp')
    if not clamp:
        return
    max_size = 1200 if wide else 600
    threshold = 800 if wide else 400
    clamp.set_property('maximum-size', int(max_size * scale))
    clamp.set_property('tightening-threshold', int(threshold * scale))


class OpenRpmApp(Adw.Application):

    def __init__(self, **kwargs):
        super().__init__(application_id='site.ikhlasulov.openrpm', **kwargs)
        self.builder = None
        self.win = None
        self.current_monitor = None
        self.monitor_handler_id = None
        self.test_controller = None
        self.selected_age_index = 0
        self.scale_factor = 1.0
        self.settings = None
        self.original_window_width = None
        self.original_window_height = None
        self.is_resized_mode = False
        self.scrolled_window = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.settings = Gio.Settings.new('site.ikhlasulov.openrpm')
        self._register_actions()

    def _register_actions(self):
        about = Gio.SimpleAction.new('about', None)
        about.connect('activate', self._show_about)
        self.add_action(about)

        quit_act = Gio.SimpleAction.new('quit', None)
        quit_act.connect('activate', lambda a, p: self.quit())
        self.add_action(quit_act)

        shortcuts = Gio.SimpleAction.new('shortcuts', None)
        shortcuts.connect('activate', self._show_shortcuts)
        self.add_action(shortcuts)

        self.set_accels_for_action('app.quit', ['<Control>q', '<Control>w'])

    def _show_about(self, action, param):
        dialog = Adw.AboutDialog()
        dialog.set_application_name('Open RPM')
        dialog.set_application_icon('site.ikhlasulov.openrpm')
        dialog.set_version('1.0.1')
        dialog.set_comments(locales.get_text('about.comments'))
        dialog.set_developer_name('Ikhlasulov')
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.present(self.win)

    def _show_shortcuts(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_resource(f'{RESOURCE_BASE}ui/shortcuts.ui')
        shortcuts = builder.get_object('shortcuts_dialog')
        if shortcuts:
            shortcuts.present(self.win)

    def do_activate(self):
        self.builder = Gtk.Builder()
        load_ui(self.builder)
        load_css()

        self.win = self.builder.get_object('main_window')
        self.win.set_application(self)

        content_bin = self.builder.get_object('content_bin')
        intro_page = self.builder.get_object('intro_page')
        if content_bin and intro_page:
            content_bin.set_child(intro_page)

        self.scrolled_window = self.builder.get_object('content_clamp').get_first_child()

        menu_button = self.builder.get_object('buttonMenu')
        if menu_button:
            localized_menu = locales.create_localized_menu()
            if localized_menu:
                menu_button.set_menu_model(localized_menu)

        start_button = self.builder.get_object('start_button')
        if start_button:
            start_button.connect('clicked', self._on_start_clicked, self.builder)

        self.win.connect('notify::default-width', self._on_window_resize)
        self.win.connect('notify::is-active', self._on_window_active)

        self._setup_initial_size()

        locales.init_combo_models(self.builder)
        locales.apply_localization(self.builder)

        age_combo = self.builder.get_object('age_combo')
        if age_combo and self.settings:
            saved = self.settings.get_int('last-age-group')
            age_combo.set_selected(saved)
            self.selected_age_index = saved

        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            monitors.connect('items-changed', self._on_monitors_changed)

        self.win.present()
        GLib.idle_add(self._preload_images_idle, GLib.PRIORITY_LOW)

    def _preload_images_idle(self, *args):
        for theme in ['dark', 'light']:
            for q in range(1, 61):
                key = (q, theme)
                if key not in test._texture_cache:
                    test.get_texture(q, theme)
                    return True
        return False

    def _get_monitor(self):
        if not self.win:
            return None
        display = Gdk.Display.get_default()
        if not display:
            return None
        surface = self.win.get_surface()
        if surface:
            return display.get_monitor_at_surface(surface)
        monitors = display.get_monitors()
        return monitors.get_item(0) if monitors else None

    def _screen_width(self, monitor):
        if not monitor:
            return BASE_WIDTH
        return monitor.get_geometry().width

    def _setup_initial_size(self):
        monitor = self._get_monitor()
        if monitor:
            self._connect_monitor(monitor)

        w = int(self._screen_width(monitor) * WINDOW_WIDTH_PCT)
        h = int(w * WINDOW_ASPECT)
        self.scale_factor = self._screen_width(monitor) / BASE_WIDTH

        self.win.set_default_size(w, h)
        self.win.set_size_request(w, h)
        self._apply_all_sizes()

    def _connect_monitor(self, monitor):
        if self.current_monitor and self.monitor_handler_id:
            self.current_monitor.disconnect(self.monitor_handler_id)
        self.current_monitor = monitor
        self.monitor_handler_id = monitor.connect('invalidate', self._on_monitor_change)

    def _apply_all_sizes(self):
        apply_sizes(self.builder, INTRO_SIZES, self.scale_factor)
        apply_sizes(self.builder, TEST_FIXED_SIZES)
        apply_sizes(self.builder, TEST_SCALED_SIZES, self.scale_factor)
        apply_sizes(self.builder, RESULT_SIZES, self.scale_factor)
        set_clamp(self.builder, self.scale_factor)

    def _on_monitor_change(self, monitor):
        if not self.win or not self.builder:
            return
        w = int(self._screen_width(monitor) * WINDOW_WIDTH_PCT)
        h = int(w * WINDOW_ASPECT)
        self.scale_factor = self._screen_width(monitor) / BASE_WIDTH
        self.win.set_default_size(w, h)
        self.win.set_size_request(w, h)
        self._apply_all_sizes()
        log.debug(locales.get_text('log.monitor.resolution').format(
            screen_width=self._screen_width(monitor),
            scale_factor=self.scale_factor, window_width=w, window_height=h))

    def _on_monitors_changed(self, monitor_list, position, removed, added):
        current = self._get_monitor()
        if current and current != self.current_monitor:
            self._connect_monitor(current)
            self._on_monitor_change(current)

    def _on_window_resize(self, window, param):
        current = self._get_monitor()
        if current and current != self.current_monitor:
            self._connect_monitor(current)
            self._on_monitor_change(current)

    def _on_window_active(self, window, param):
        if not self.win.is_active():
            return
        current = self._get_monitor()
        if current and current != self.current_monitor:
            self._connect_monitor(current)
            self._on_monitor_change(current)

    def _save_original_window_size(self):
        if not self.is_resized_mode:
            self.original_window_width = self.win.get_width()
            self.original_window_height = self.win.get_height()

    def _restore_original_window_size(self):
        if self.original_window_width and self.original_window_height:
            self.win.set_default_size(
                self.original_window_width,
                self.original_window_height
            )

        if self.scrolled_window:
            self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.is_resized_mode = False

    def _set_window_size(self, min_width, min_height):
        self._save_original_window_size()

        current_width = self.win.get_width()
        current_height = self.win.get_height()

        new_width = max(current_width, min_width)
        new_height = max(current_height, min_height)

        if new_width != current_width or new_height != current_height:
            self.win.set_default_size(new_width, new_height)

        if self.scrolled_window:
            self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)

        self.is_resized_mode = True

    def _on_start_clicked(self, button, builder):
        age_combo = builder.get_object('age_combo')
        age_pct = 100
        if age_combo:
            self.selected_age_index = age_combo.get_selected()
            if self.settings:
                self.settings.set_int('last-age-group', self.selected_age_index)
            log.debug(locales.get_text('log.selected_age').format(
                selected_age=self.selected_age_index))
            age_pct = locales.AGE_PERCENTS.get(self.selected_age_index, 100)

        log.info(locales.get_text('log.test_start'))
        self._begin_test(age_pct)

    def _begin_test(self, age_pct):
        content_bin = self.builder.get_object('content_bin')
        test_page = self.builder.get_object('test_page')

        if content_bin and test_page:
            self._set_window_size(MIN_TEST_WIDTH, MIN_TEST_HEIGHT)

            content_bin.set_child(test_page)
            locales.apply_test_localization(self.builder)

            self.test_controller = test.TestController(
                builder=self.builder,
                age_percent=age_pct,
                on_finish_callback=self._on_test_complete,
                on_reset_callback=self._on_test_reset
            )
            self.test_controller.start()

    def _on_test_reset(self):
        log.info("Test reset by user")
        self._restore_original_window_size()
        self.test_controller = None

    def _on_test_complete(self, test_results):
        log.info(f"Test completed: {len(test_results['user_answers'])} answers, "
                 f"{test_results['time_taken']}s elapsed")
        test_results['selected_age_index'] = self.selected_age_index
        self._show_results(test_results)

    def _show_results(self, test_results):
        self._set_window_size(MIN_RESULT_WIDTH, MIN_RESULT_HEIGHT)

        set_clamp(self.builder, self.scale_factor, wide=True)
        result.show_results(
            builder=self.builder,
            test_results=test_results,
            on_reset_callback=self._on_results_reset
        )
        self.test_controller = None

    def _on_results_reset(self):
        log.debug("Returned to intro from results")
        self._restore_original_window_size()
        set_clamp(self.builder, self.scale_factor, wide=False)
        self.test_controller = None
