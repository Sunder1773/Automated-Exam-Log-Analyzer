VIOLATION_WEIGHTS = {
    'no-face-detected': 15,
    'multiple-people': 20,
    'screen-share': 18,
    'phone-detected': 18,
    'tab-switch': 8,
    'audio-noise': 6,
}

BURST_PENALTY = 25
AUTH_FAILURE_PENALTY = 30
SHORT_EXAM_PENALTY = 20
MAX_SCORE = 100

RISK_CATEGORIES = [
    {'min': 0, 'max': 19, 'label': 'Low Risk', 'color': '#2ecc71', 'action': 'No review needed'},
    {'min': 20, 'max': 39, 'label': 'Moderate Risk', 'color': '#f39c12', 'action': 'Automated review'},
    {'min': 40, 'max': 69, 'label': 'High Risk', 'color': '#e67e22', 'action': 'Human review recommended'},
    {'min': 70, 'max': 100, 'label': 'Critical', 'color': '#e74c3c', 'action': 'Immediate review + hold'},
]

DEFAULT_RULES = {
    'max_violation_count': 3,
    'violation_type_thresholds': {
        'no-face-detected': 2, 'multiple-people': 1, 'tab-switch': 3,
        'audio-noise': 2, 'screen-share': 1, 'phone-detected': 1
    },
    'min_exam_duration_sec': 300,
    'auth_failure_flag': True
}