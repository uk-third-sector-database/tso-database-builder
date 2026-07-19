import csv

import pytest

from spine.suppress_echo_matches import partition_echo_rows, suppress_echo_matches

HEADER = ['uid', 'orgA_id_in_source', 'orgA_source', 'orgA_uid',
          'orgB_id_in_source', 'orgB_source', 'orgB_uid', 'match_type']


def row(a_uid, b_uid, match_type):
    return [a_uid, a_uid.split('-')[-1], 'ccew', a_uid,
            b_uid.split('-')[-1], 'CH', b_uid, match_type]


def test_partition_suppresses_echo_and_keeps_everything_else():
    built = [
        # echo: new companyid row on a pair v1.0 linked via ftc, ftc row present
        row('GB-CHC-1', 'GB-COH-100', 'companyid - id_in_source'),
        row('GB-CHC-1', 'GB-COH-100', 'ftc'),
        # continuity: v1.0 published this same companyid row itself
        row('GB-CHC-2', 'GB-COH-200', 'companyid - id_in_source'),
        # sole evidence: pair known to v1.0 but no other built row - kept
        row('GB-CHC-3', 'GB-COH-300', 'companyid - id_in_source'),
        # genuinely new link: pair unknown to v1.0 - kept
        row('GB-CHC-4', 'GB-COH-400', 'companyid - id_in_source'),
        # echo pair recorded in the opposite orientation in v1.0 - suppressed
        row('GB-CHC-5', 'GB-COH-500', 'companyid - id_in_source'),
        row('GB-CHC-5', 'GB-COH-500', 'ftc'),
    ]
    prior = [
        row('GB-CHC-1', 'GB-COH-100', 'ftc'),
        row('GB-CHC-2', 'GB-COH-200', 'companyid - id_in_source'),
        row('GB-CHC-3', 'GB-COH-300', 'ftc'),
        row('GB-COH-500', 'GB-CHC-5', 'ftc'),
    ]

    kept, suppressed, counts = partition_echo_rows(HEADER, built, HEADER, prior)

    assert counts == {'built': 7, 'prior': 4,
                      'suppressed': 2, 'kept_sole_evidence': 1}
    assert suppressed == [built[0], built[5]]
    assert kept == [built[1], built[2], built[3], built[4], built[6]]


def test_partition_refuses_missing_columns():
    with pytest.raises(ValueError):
        partition_echo_rows(HEADER[:-1], [], HEADER, [])


def test_suppress_echo_matches_writes_all_files_and_refuses_second_run(tmp_path):
    def write(name, rows):
        p = tmp_path / name
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)
        return str(p)

    built = write('built.matches.csv',
                  [row('GB-CHC-1', 'GB-COH-100', 'companyid - id_in_source'),
                   row('GB-CHC-1', 'GB-COH-100', 'ftc')])
    prior = write('prior.matches.csv',
                  [row('GB-CHC-1', 'GB-COH-100', 'ftc')])

    counts = suppress_echo_matches(built, prior)
    assert counts['suppressed'] == 1

    with open(built, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    assert rows == [HEADER, row('GB-CHC-1', 'GB-COH-100', 'ftc')]
    with open(tmp_path / 'built.matches.suppressed-echo.csv', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    assert rows == [HEADER, row('GB-CHC-1', 'GB-COH-100', 'companyid - id_in_source')]
    assert (tmp_path / 'built.matches.preecho.csv').exists()

    with pytest.raises(RuntimeError):
        suppress_echo_matches(built, prior)
