from logger import get_logger

log = get_logger('calculations')

NORMATIVE_DISTRIBUTION = {
    0: [0, 0, 0, 0, 0], 15: [8, 4, 2, 1, 0], 16: [8, 4, 2, 1, 0],
    17: [8, 5, 2, 1, 1], 18: [8, 5, 2, 2, 1], 19: [8, 6, 3, 2, 0],
    20: [8, 6, 4, 2, 0], 21: [8, 6, 4, 2, 1], 22: [9, 6, 4, 2, 1],
    23: [9, 7, 4, 3, 1], 24: [9, 7, 4, 3, 1], 25: [10, 7, 4, 3, 1],
    26: [10, 7, 5, 3, 1], 27: [10, 7, 5, 4, 1], 28: [10, 7, 6, 4, 1],
    29: [10, 7, 6, 4, 1], 30: [10, 7, 7, 5, 1], 31: [10, 8, 7, 5, 1],
    32: [10, 8, 7, 5, 2], 33: [11, 8, 7, 5, 2], 34: [11, 8, 7, 5, 2],
    35: [11, 8, 7, 6, 2], 36: [11, 8, 7, 6, 2], 37: [11, 9, 8, 7, 2],
    38: [11, 9, 8, 8, 2], 39: [11, 10, 8, 8, 2], 40: [11, 10, 8, 8, 3],
    41: [11, 10, 9, 8, 3], 42: [11, 10, 9, 8, 3], 43: [11, 10, 9, 9, 3],
    44: [12, 10, 9, 9, 4], 45: [12, 10, 9, 9, 5], 46: [12, 10, 9, 10, 5],
    47: [12, 10, 9, 10, 6], 48: [12, 11, 10, 10, 6], 49: [12, 11, 10, 10, 6],
    50: [12, 11, 11, 10, 7], 51: [12, 11, 11, 11, 7], 52: [12, 11, 11, 11, 7],
    53: [12, 12, 12, 9, 8], 54: [12, 12, 12, 10, 8], 55: [12, 12, 12, 11, 9],
    56: [12, 12, 12, 11, 9], 57: [12, 12, 12, 12, 10], 58: [12, 12, 12, 12, 10],
    59: [12, 12, 12, 12, 11], 60: [12, 12, 12, 12, 12],
}

SPLINE_POINTS = [
    (0, 0), (15, 62), (16, 65), (17, 65), (18, 66), (19, 67),
    (20, 69), (22, 71), (23, 72), (24, 73), (25, 75), (26, 76),
    (27, 77), (28, 79), (29, 80), (30, 82), (31, 83), (32, 84),
    (33, 86), (34, 87), (35, 88), (36, 90), (37, 91), (38, 92),
    (39, 94), (40, 95), (41, 96), (42, 98), (43, 99), (44, 100),
    (45, 102), (46, 104), (47, 105), (48, 106), (49, 108), (50, 110),
    (51, 112), (52, 114), (53, 116), (54, 118), (55, 122), (56, 124),
    (57, 126), (58, 128), (59, 130), (60, 140),
]

DIAGNOSIS_RANGES = [
    (140, 'exceptional'), (121, 'high'), (111, 'above_avg'),
    (91, 'avg'), (81, 'below_avg'), (71, 'low'),
    (51, 'mild'), (21, 'moderate'), (0, 'severe'),
]

DEGREE_RANGES = [
    (121, '1'), (111, '2'), (91, '3'), (81, '4'), (0, '5'),
]

RECOMMENDATION_RANGES = [
    (120, '120'), (110, '110'), (90, '90'), (80, '80'), (0, 'low'),
]


def _find_threshold(value, ranges):
    for threshold, key in ranges:
        if value >= threshold:
            return key
    return ranges[-1][1]


def get_diagnosis_key(iq):
    return _find_threshold(iq, DIAGNOSIS_RANGES)


def get_degree_key(iq):
    return _find_threshold(iq, DEGREE_RANGES)


def get_recommendation_key(iq):
    return _find_threshold(iq, RECOMMENDATION_RANGES)


class CatmullRomSpline:
    def __init__(self, points):
        self.points = sorted(points, key=lambda p: p[0])

    def interpolate(self, x):
        pts = self.points
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]

        for j in range(len(pts) - 1):
            if pts[j][0] <= x <= pts[j+1][0]:
                i = j
                break

        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[min(len(pts) - 1, i + 1)]
        p3 = pts[min(len(pts) - 1, i + 2)]

        dx = p2[0] - p1[0]
        t = 0 if dx == 0 else (x - p1[0]) / dx
        t2, t3 = t * t, t * t * t

        return 0.5 * (
            2 * p1[1] + (-p0[1] + p2[1]) * t +
            (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
            (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
        )


_iq_spline = CatmullRomSpline(SPLINE_POINTS)


def get_series(q):
    if q <= 12: return 'A'
    if q <= 24: return 'B'
    if q <= 36: return 'C'
    if q <= 48: return 'D'
    return 'E'


def get_base_iq(score):
    return _iq_spline.interpolate(round(score))


def get_closest_normative(score):
    if score < 15:
        r = score / 15
        return [round(8 * r), round(4 * r), round(2 * r), round(1 * r), 0]
    if score in NORMATIVE_DISTRIBUTION:
        return NORMATIVE_DISTRIBUTION[score]
    keys = sorted(NORMATIVE_DISTRIBUTION.keys())
    closest = min(keys, key=lambda k: abs(score - k))
    return NORMATIVE_DISTRIBUTION[closest]


def calculate_raven_results(user_answers, answer_key, age_percent):
    raw_score = 0
    series_scores = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}

    for q in range(1, 61):
        correct = answer_key.get(str(q)) or answer_key.get(q)
        user = user_answers.get(q)
        if correct is not None and user == correct:
            raw_score += 1
            series_scores[get_series(q)] += 1

    base_iq = get_base_iq(raw_score)
    final_iq = round((base_iq * 100) / age_percent) if age_percent > 0 else 0

    expected = get_closest_normative(raw_score)
    series_names = ['A', 'B', 'C', 'D', 'E']
    unreliable = 0
    deviation_a = 0
    details = []

    for idx, name in enumerate(series_names):
        actual = series_scores[name]
        exp = expected[idx]
        dev = actual - exp
        if name == 'A':
            deviation_a = dev
        if abs(dev) > 2:
            unreliable += 1
        details.append({"series": name, "score": actual, "expected": exp, "deviation": dev})

    if deviation_a <= -3:
        rel_key = 'defect'
    elif unreliable > 2:
        rel_key = 'unreliable'
    elif raw_score < 15:
        rel_key = 'low_reliability'
    else:
        rel_key = 'good'

    return {
        "raw_score": raw_score,
        "max_score": 60,
        "iq": final_iq,
        "diagnosis_key": get_diagnosis_key(final_iq),
        "reliability_status": rel_key,
        "recommendation_key": get_recommendation_key(final_iq),
        "series_details": details,
        "age_used": age_percent
    }
