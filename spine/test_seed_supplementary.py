import csv

import pytest

from spine.seed_supplementary import merge_supplementary_rows, seed_supplementary

HEADER = ['uid', 'organisationname', 'normalisedname', 'fulladdress', 'city',
          'postcode', 'registerdate', 'removeddate', 'source_register', 'id_in_source']


def row(uid, name, address):
    return [uid, name, name, address, '', '', '', '', 'Test Register', '']


def test_merge_seeds_missing_rows_and_keeps_uid_blocks_contiguous():
    base = [row('GB-CHC-1', 'OLD NAME A', 'ADDR A1'),
            row('GB-CHC-2', 'NAME B', 'ADDR B1')]
    prior = [row('GB-CHC-1', 'OLD NAME A', 'ADDR A1'),      # duplicate: skipped
             row('GB-CHC-1', 'OLDER NAME A', 'ADDR A0'),    # new variant: seeded
             row('GB-CHC-3', 'NAME C', 'ADDR C1'),          # uid has no base block: appended
             row('GB-COH-4', 'ABSORBED CO', 'ADDR D1'),     # absorbed org uid, known via matches: seeded
             row('GB-CHC-9', 'GONE ORG', 'ADDR X')]         # org not in release: dropped
    release_uids = {'GB-CHC-1', 'GB-CHC-2', 'GB-CHC-3', 'GB-COH-4'}

    merged, counts = merge_supplementary_rows(HEADER, base, HEADER, prior, release_uids)

    assert counts == {'base': 2, 'prior': 5, 'seeded': 3,
                      'duplicate': 1, 'org_not_in_release': 1}
    # seeded variant sits directly after GB-CHC-1's existing block,
    # the no-block uids come last in uid order
    assert [r[0] for r in merged] == ['GB-CHC-1', 'GB-CHC-1', 'GB-CHC-2',
                                      'GB-CHC-3', 'GB-COH-4']
    assert merged[1][1] == 'OLDER NAME A'


def test_merge_refuses_mismatched_columns():
    other_header = HEADER[:-1]
    with pytest.raises(ValueError):
        merge_supplementary_rows(HEADER, [], other_header, [], set())


def test_seed_supplementary_is_atomic_and_refuses_second_run(tmp_path):
    def write(name, header, rows):
        p = tmp_path / name
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        return str(p)

    built = write('built.supplementary.csv', HEADER,
                  [row('GB-CHC-1', 'NAME A', 'ADDR A1')])
    spine = write('built.spine.csv', ['uid'], [['GB-CHC-1']])
    matches = write('built.matches.csv',
                    ['uid', 'orgA_id_in_source', 'orgA_source', 'orgA_uid',
                     'orgB_id_in_source', 'orgB_source', 'orgB_uid', 'match_type'],
                    [['GB-CHC-1', '1', 'ccew', 'GB-CHC-1',
                      '100', 'CH', 'GB-COH-100', 'companyid - id_in_source']])
    prior = write('prior.supplementary.csv', HEADER,
                  [row('GB-CHC-1', 'OLDER NAME A', 'ADDR A0'),
                   row('GB-COH-100', 'ABSORBED CO NAME', 'ADDR CO')])

    counts = seed_supplementary(built, spine, matches, prior)
    assert counts['seeded'] == 2  # incl. the absorbed org known only via matches

    with open(built, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    assert len(rows) == 4  # header + base + two seeded
    assert (tmp_path / 'built.supplementary.preseed.csv').exists()

    with pytest.raises(RuntimeError):
        seed_supplementary(built, spine, matches, prior)
