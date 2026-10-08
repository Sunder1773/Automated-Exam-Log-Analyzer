import csv
import random
from datetime import datetime, timedelta


def generate_mock_examity_csv(output_path='mock_examity_export.csv', num_sessions=50):

    random.seed(42)

    exam_date = datetime(2024, 5, 10)
    exam_start_hour = 14
    proctor_modes = ['Live', 'Automated-Institution Review', 'Automated-Exam Review']
    os_types = ['Windows 10', 'Windows 11', 'macOS 13', 'macOS 14', 'Ubuntu 22.04']
    browsers = ['Chrome', 'Firefox', 'Edge', 'Safari']
    locations = ['New York, US', 'London, UK', 'Toronto, CA', 'Mumbai, IN',
                 'Berlin, DE', 'Sydney, AU', 'Singapore, SG', 'Tokyo, JP']

    student_profiles = {
        'normal':              {'tab-switch': 1, 'audio-noise': 1},
        'slightly_suspicious': {'tab-switch': 3, 'audio-noise': 2, 'no-face-detected': 1},
        'moderate_risk':       {'tab-switch': 5, 'audio-noise': 3, 'no-face-detected': 2, 'phone-detected': 1},
        'high_risk':           {'tab-switch': 8, 'no-face-detected': 4, 'audio-noise': 3, 'phone-detected': 2},
        'critical':            {'tab-switch': 12, 'no-face-detected': 6, 'audio-noise': 4,
                                'phone-detected': 3, 'multiple-people': 2, 'screen-share': 1}
    }

    profile_distribution = {
        'normal': 20,
        'slightly_suspicious': 12,
        'moderate_risk': 10,
        'high_risk': 6,
        'critical': 2
    }

    profile_pool = []
    for profile, count in profile_distribution.items():
        profile_pool.extend([profile] * count)
    random.shuffle(profile_pool)

    rows = []

    for i in range(num_sessions):
        session_id = f'SES{2024050100 + i}'
        candidate_id = f'STU{1000 + i}'
        exam_id = 'MATH201-FINAL-SPRING2024'

        student_profile = profile_pool[i % len(profile_pool)]
        violations_config = student_profiles[student_profile].copy()

        start_offset_minutes = random.randint(0, 60)
        exam_start = exam_date.replace(hour=exam_start_hour, minute=start_offset_minutes)

        if student_profile in ['critical', 'high_risk']:
            actual_duration_min = random.randint(20, 50)
        elif student_profile == 'moderate_risk':
            actual_duration_min = random.randint(60, 75)
        else:
            actual_duration_min = random.randint(80, 110)

        exam_end = exam_start + timedelta(minutes=actual_duration_min)
        duration_sec = int((exam_end - exam_start).total_seconds())

        proctor_mode = random.choice(proctor_modes)

        if student_profile in ['critical', 'high_risk'] and random.random() < 0.4:
            auth_status = 'FAILED'
        elif student_profile == 'moderate_risk' and random.random() < 0.15:
            auth_status = 'WARNING - MANUAL REVIEW REQUIRED'
        else:
            auth_status = 'PASSED'

        os_type = random.choice(os_types)
        browser = random.choice(browsers)
        ip_address = f'{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}'
        location = random.choice(locations)
        video_url = f'https://portal.examity.com/video/{session_id}?token=abc123xyz'

        violation_rows = []
        total_violations = sum(violations_config.values())

        if student_profile in ['critical', 'high_risk']:
            burst_time = exam_start + timedelta(
                minutes=random.randint(10, max(11, actual_duration_min - 20))
            )
            for j in range(3):
                violation_rows.append({
                    'time': (burst_time + timedelta(seconds=j * 25)).isoformat(),
                    'type': random.choice(['no-face-detected', 'tab-switch', 'audio-noise']),
                    'comment': 'Possible rapid-fire suspicious activity detected'
                })

        for v_type, v_count in violations_config.items():
            for k in range(v_count):
                if (v_type in ['no-face-detected', 'tab-switch', 'audio-noise']
                        and student_profile in ['critical', 'high_risk']
                        and k < 1):
                    continue

                offset_min = random.uniform(5, min(actual_duration_min - 5, 80))
                v_time = exam_start + timedelta(minutes=offset_min)

                comment = ''
                if v_type == 'no-face-detected':
                    comment = 'Face lost from camera view for extended period'
                elif v_type == 'tab-switch':
                    comment = 'Browser tab changed away from exam window'
                elif v_type == 'audio-noise':
                    comment = 'Unusual audio detected in environment'
                elif v_type == 'multiple-people':
                    comment = 'Additional persons detected in camera frame'
                elif v_type == 'screen-share':
                    comment = 'Screen sharing application activated'
                elif v_type == 'phone-detected':
                    comment = 'Mobile phone detected in testing area'

                violation_rows.append({
                    'time': v_time.isoformat(),
                    'type': v_type,
                    'comment': comment
                })

        violation_rows.sort(key=lambda x: x['time'])

        row = {
            'SessionID': session_id,
            'CandidateID': candidate_id,
            'ExamID': exam_id,
            'StartTime': exam_start.isoformat(),
            'EndTime': exam_end.isoformat(),
            'DurationSec': duration_sec,
            'ProctorMode': proctor_mode,
            'AuthStatus': auth_status,
            'OS': os_type,
            'Browser': browser,
            'IP': ip_address,
            'Location': location,
            'VideoURL': video_url,
            'ViolationCount': total_violations
        }

        max_violation_slots = min(len(violation_rows), 50)
        for j in range(max_violation_slots):
            row[f'Violation{j + 1}_Time'] = violation_rows[j]['time']
            row[f'Violation{j + 1}_Type'] = violation_rows[j]['type']
            row[f'Violation{j + 1}_Comment'] = violation_rows[j]['comment']

        for j in range(max_violation_slots + 1, 51):
            row[f'Violation{j}_Time'] = ''
            row[f'Violation{j}_Type'] = ''
            row[f'Violation{j}_Comment'] = ''

        rows.append(row)

    fieldnames = [
        'SessionID', 'CandidateID', 'ExamID', 'StartTime', 'EndTime',
        'DurationSec', 'ProctorMode', 'AuthStatus', 'OS', 'Browser',
        'IP', 'Location', 'VideoURL', 'ViolationCount'
    ]
    for j in range(1, 51):
        fieldnames.append(f'Violation{j}_Time')
        fieldnames.append(f'Violation{j}_Type')
        fieldnames.append(f'Violation{j}_Comment')

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[GENERATED] Created {output_path}")
    print(f"  - {num_sessions} exam sessions")
    print(f"  - Fields: {len(fieldnames)} columns")

    profile_counts = {}
    for i in range(num_sessions):
        profile = profile_pool[i % len(profile_pool)]
        profile_counts[profile] = profile_counts.get(profile, 0) + 1

    print("\nStudent Profile Distribution:")
    for profile, count in sorted(profile_counts.items()):
        pct = count / num_sessions * 100
        print(f"  {profile:<20} {count:>3} ({pct:>5.1f}%)")


if __name__ == '__main__':
    generate_mock_examity_csv('mock_examity_export.csv', num_sessions=50)