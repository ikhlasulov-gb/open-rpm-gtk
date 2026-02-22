import os
import gettext
from gi.repository import GLib
from logger import get_logger

log = get_logger('locales')

_translation = None

_EN = {
    "app.title": "Raven's Test", "app.subtitle": "Raven's Progressive Matrices (RPM)",
    "app.site_title": "Open RPM",
    "app.description": "A modern implementation of Raven's Progressive Matrices (RPM)",
    "about.comments": "A modern IQ testing application based on Raven's Progressive Matrices.",
    "menu.shortcuts": "Keyboard Shortcuts", "menu.about": "About Open RPM", "menu.quit": "Quit",
    "shortcuts.title": "Shortcuts", "shortcuts.quit": "Quit",
    "intro.instruction_title": "Instruction:",
    "intro.instruction_text": "You will be offered 60 tasks (5 series). Find the pattern and select the missing piece.",
    "intro.time": "Time: 20 minutes.", "intro.age": "Age:", "intro.start_button": "Start",
    "age.14_30": "14 - 30 years", "age.31_35": "31 - 35 years", "age.36_40": "36 - 40 years",
    "age.41_45": "41 - 45 years", "age.46_50": "46 - 50 years", "age.51_55": "51 - 55 years",
    "age.56_plus": "56+ years", "test.question": "Question",
    "test.progress_template": "Question {q} of 60 (Series {s})",
    "test.prev": "Back", "test.next": "Next", "test.finish": "Finish", "test.end": "End",
    "test.series": "Series", "confirm.title": "End?", "confirm.message": "End early? Only completed questions count.",
    "confirm.cancel": "Cancel", "confirm.end": "Yes", "result.results_title": "Results",
    "result.label": "Result", "result.age": "Age", "result.total_score": "Score",
    "result.time_taken": "Time", "result.series": "Series", "result.correct": "Correct",
    "result.deviation": "Deviation", "result.return": "Return",
    "result.interpretation": "Interpretation", "result.analysis": "Analysis &amp; Advice",
    "result.stats": "Statistics", "result.series_title": "Series Results",
    "result.series_template": "Series {s}", "result.diagnosis": "Diagnosis",
    "result.reliability": "Reliability", "result.degree": "Degree", "result.status": "Status",
    "result.recommendation": "Recommendations", "diag.exceptional": "Exceptional Intelligence",
    "diag.high": "High Intelligence Level", "diag.above_avg": "Above Average Intelligence",
    "diag.avg": "Average Intelligence Level", "diag.below_avg": "Below Average Intelligence",
    "diag.low": "Low Intelligence Level", "diag.mild": "Mild Mental Deficiency",
    "diag.moderate": "Moderate Mental Deficiency", "diag.severe": "Severe Mental Deficiency",
    "reliability.good": "Reliable result.",
    "reliability.unreliable": "Significant deviations. Results may be unreliable.",
    "reliability.defect": "Significant deviation in Series A. Possible attention deficit.",
    "reliability.low_reliability": "Low score. Low indicators are less reliable.",
    "degree.1": "95%+ (Degree 1): Exceptionally Highly Developed Intelligence",
    "degree.2": "75% - 95% (Degree 2): Exceptional Intelligence",
    "degree.3": "25% - 74% (Degree 3): Average Intelligence",
    "degree.4": "5% - 24% (Degree 4): Below Average Intelligence",
    "degree.5": "5% or less (Degree 5): Defective Intellectual Capacity",
    "rec.120": "Exceptional potential. Engage in strategy, math, or architecture.",
    "rec.110": "Above average abilities. Try learning languages, coding, or chess.",
    "rec.90": "Average intelligence. Regular practice keeps the mind sharp.",
    "rec.80": "Slightly below average. Brain exercises can help improve speed.",
    "rec.low": "Difficulty with patterns. Focus on hands-on tasks.",
    "error.prefix": "Error: ", "error.py.missing": "Python 3 is not installed.",
    "error.gi.missing": "PyGObject library (gi) not found.",
    "error.window.missing": "File scripts/window.py not found.",
    "error.locale.missing": "Locale file not found: ",
    "error.locale.fallback.missing": "Fallback locale file not found: ",
    "error.locale.key.missing": "Localization key not found: ",
    "log.monitor.resolution": "Monitor: {screen_width}px, scale: {scale_factor:.2f}, window: {window_width}x{window_height}",
    "log.selected_age": "Selected age: {selected_age}", "log.test_start": "Starting test...",
}

AGE_RANGES = ["14-30", "31-35", "36-40", "41-45", "46-50", "51-55", "56+"]
AGE_PERCENTS = {0: 100, 1: 97, 2: 93, 3: 88, 4: 82, 5: 76, 6: 70}


def _init_gettext():
    global _translation
    if _translation is not None:
        return

    localedir = None
    for d in GLib.get_system_data_dirs() or []:
        p = os.path.join(d, 'locale')
        if os.path.exists(p):
            localedir = p
            break
    localedir = localedir or '/usr/share/locale'
    _translation = gettext.translation('openrpm', localedir=localedir, fallback=True)
    _translation.install()


def get_text(key):
    if _translation is None:
        _init_gettext()
    text = _translation.gettext(key)
    return _EN.get(key, text) if text == key else text


def get_localized_age_ranges():
    keys = ['age.14_30', 'age.31_35', 'age.36_40', 'age.41_45', 'age.46_50', 'age.51_55', 'age.56_plus']
    return [get_text(k) for k in keys]


def init_combo_models(builder):
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        from gi.repository import Gtk
    except ImportError:
        return

    combo = builder.get_object('age_combo')
    if combo:
        combo.set_model(Gtk.StringList.new(get_localized_age_ranges()))


def _apply_labels(builder, mapping):
    for obj_name, key in mapping.items():
        obj = builder.get_object(obj_name)
        if obj:
            if hasattr(obj, 'set_label'):
                obj.set_label(get_text(key))
            elif hasattr(obj, 'set_title'):
                obj.set_title(get_text(key))


def apply_localization(builder):
    window = builder.get_object('main_window')
    if window:
        window.set_title(get_text('app.title'))

    _apply_labels(builder, {
        'header_label': 'app.site_title', 'title_label': 'app.title',
        'subtitle_label': 'app.subtitle', 'time_row': 'intro.time',
        'age_combo': 'intro.age', 'start_button': 'intro.start_button',
    })

    instruction_row = builder.get_object('instruction_row')
    if instruction_row:
        instruction_row.set_title(get_text('intro.instruction_title'))
        instruction_row.set_subtitle(get_text('intro.instruction_text'))


def apply_test_localization(builder):
    _apply_labels(builder, {
        'prev_button': 'test.prev', 'next_button': 'test.next', 'end_button': 'test.end',
    })


def create_localized_menu():
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        from gi.repository import Gio
    except ImportError:
        return None

    menu = Gio.Menu.new()
    section = Gio.Menu.new()

    shortcuts_item = Gio.MenuItem.new(get_text('menu.shortcuts'), 'app.shortcuts')
    section.append_item(shortcuts_item)

    about_item = Gio.MenuItem.new(get_text('menu.about'), 'app.about')
    section.append_item(about_item)

    quit_item = Gio.MenuItem.new(get_text('menu.quit'), 'app.quit')
    section.append_item(quit_item)

    menu.append_section(None, section)
    return menu


_init_gettext()
