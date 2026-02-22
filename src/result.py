from gi.repository import Gtk, Adw, GLib

import calculations
import locales
from logger import get_logger

log = get_logger('result')

SERIES_NAMES = 'ABCDE'


class ResultsScreen:
    def __init__(self, builder, test_results, on_reset_callback=None):
        self.builder = builder
        self.test_results = test_results
        self.on_reset_callback = on_reset_callback
        self.results = None

        self._cache_widgets()
        self._wire_signals()
        self._localize()
        self._render()

    def _cache_widgets(self):
        b = self.builder
        self.final_iq_label = b.get_object('final_iq_label')
        self.diagnosis_row = b.get_object('diagnosis_row')
        self.total_score_value = b.get_object('total_score_value')
        self.time_taken_value = b.get_object('time_taken_value')
        self.age_value = b.get_object('age_value')
        self.reliability_row = b.get_object('reliability_row')
        self.interpretation_row = b.get_object('interpretation_row')
        self.analysis_row = b.get_object('analysis_row')
        self.return_button = b.get_object('return_button')

        self.series_widgets = {}
        for s in SERIES_NAMES:
            self.series_widgets[s] = {
                'score': b.get_object(f'series_{s.lower()}_score'),
                'deviation': b.get_object(f'series_{s.lower()}_deviation'),
                'row': b.get_object(f'series_{s.lower()}_row')
            }

        self._groups = {name: b.get_object(f'{name}_group') for name in
                        ['result_header', 'stats', 'series', 'interpretation', 'analysis', 'reliability']}

        self._headers = {
            'series_header_row': b.get_object('series_header_row'),
            'series_header_correct': b.get_object('series_header_correct'),
            'series_header_deviation': b.get_object('series_header_deviation'),
        }

    def _wire_signals(self):
        if self.return_button:
            self.return_button.connect('clicked', self._return)

    def _localize(self):
        titles = {
            'result_header': 'result.label', 'stats': 'result.stats',
            'series': 'result.series_title', 'interpretation': 'result.interpretation',
            'analysis': 'result.analysis', 'reliability': 'result.reliability',
        }
        for name, key in titles.items():
            g = self._groups.get(name)
            if g:
                g.set_title(locales.get_text(key))

        if self._headers.get('series_header_row'):
            self._headers['series_header_row'].set_title(locales.get_text('result.series'))
        if self._headers.get('series_header_correct'):
            self._headers['series_header_correct'].set_label(locales.get_text('result.correct'))
        if self._headers.get('series_header_deviation'):
            self._headers['series_header_deviation'].set_label(locales.get_text('result.deviation'))

        for row in ['total_score_row', 'time_taken_row', 'age_row']:
            obj = self.builder.get_object(row)
            if obj:
                obj.set_title(locales.get_text(f'result.{row.replace("_row", "")}'))

        tmpl = locales.get_text('result.series_template')
        for s, w in self.series_widgets.items():
            if w.get('row'):
                title = tmpl.replace('{s}', s) if '{s}' in tmpl else f"{locales.get_text('result.series')} {s}"
                w['row'].set_title(title)

        if self.return_button:
            self.return_button.set_label(locales.get_text('result.return'))

    def _render(self):
        self.results = calculations.calculate_raven_results(
            user_answers=self.test_results.get('user_answers', {}),
            answer_key=self.test_results.get('answer_key', {}),
            age_percent=self.test_results.get('age_percent', 100)
        )

        if self.final_iq_label:
            self.final_iq_label.set_label(str(self.results['iq']))

        if self.diagnosis_row:
            self.diagnosis_row.set_title(locales.get_text('result.diagnosis'))
            self.diagnosis_row.set_subtitle(locales.get_text(f"diag.{self.results['diagnosis_key']}"))

        self._render_stats()
        self._render_series()
        self._render_interpretation()
        self._render_analysis()

    def _render_stats(self):
        if self.total_score_value:
            self.total_score_value.set_label(
                f"{self.results['raw_score']} / {self.results['max_score']}")

        if self.time_taken_value:
            t = self.test_results.get('time_taken', 0)
            self.time_taken_value.set_label(f"{t // 60}:{t % 60:02d}")

        if self.age_value:
            idx = self.test_results.get('selected_age_index', 0)
            if idx in locales.AGE_PERCENTS:
                r = locales.AGE_RANGES[idx]
                key = f"age.{r.replace('-', '_').replace('+', '_plus')}"
                txt = locales.get_text(key)
                self.age_value.set_label(txt if txt != key else r)

    def _render_series(self):
        for d in self.results.get('series_details', []):
            s = d['series']
            if s not in self.series_widgets:
                continue
            w = self.series_widgets[s]

            if w.get('score'):
                w['score'].set_label(str(d['score']))

            if w.get('deviation'):
                dev = d['deviation']
                w['deviation'].set_label(f"+{dev}" if dev > 0 else str(dev))
                for cls in ('error', 'warning', 'success'):
                    w['deviation'].remove_css_class(cls)
                if abs(dev) > 2:
                    w['deviation'].add_css_class('error')
                elif abs(dev) > 1:
                    w['deviation'].add_css_class('warning')
                else:
                    w['deviation'].add_css_class('success')

        if self.reliability_row:
            rel_key = self.results.get('reliability_status') or 'good'
            self.reliability_row.set_title(locales.get_text('result.status'))
            self.reliability_row.set_subtitle(
                GLib.markup_escape_text(locales.get_text(f"reliability.{rel_key}"), -1))
            for cls in ('error', 'warning', 'success'):
                self.reliability_row.remove_css_class(cls)

    def _render_interpretation(self):
        if not self.interpretation_row:
            return
        iq = self.results['iq']
        self.interpretation_row.set_title(locales.get_text('result.degree'))
        self.interpretation_row.set_subtitle(
            locales.get_text(f"degree.{calculations.get_degree_key(iq)}"))

    def _render_analysis(self):
        if not self.analysis_row:
            return
        rec_key = f"rec.{self.results.get('recommendation_key', '90')}"
        self.analysis_row.set_title(locales.get_text('result.recommendation'))
        self.analysis_row.set_subtitle(locales.get_text(rec_key))

    def _return(self, button):
        content_bin = self.builder.get_object('content_bin')
        intro_page = self.builder.get_object('intro_page')
        if content_bin and intro_page:
            content_bin.set_child(intro_page)
        if self.on_reset_callback:
            self.on_reset_callback()


def show_results(builder, test_results, on_reset_callback=None):
    content_bin = builder.get_object('content_bin')
    result_page = builder.get_object('result_page')
    if content_bin and result_page:
        content_bin.set_child(result_page)
        return ResultsScreen(builder, test_results, on_reset_callback)
    return None
