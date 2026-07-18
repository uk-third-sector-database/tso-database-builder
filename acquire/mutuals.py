"""Mutuals: FCA Mutuals Public Register - society list.

Source site : https://mutuals.fca.org.uk/
Product     : "SocietyList.csv" - the full society list the site links
              from its front page ("Download the register" link to
              https://fcastoragemprprod.blob.core.windows.net/societylist/SocietyList.csv)
Output      : <raw_root>/mutuals/SocietyList-YYYY-MM.csv

No session or search interaction is needed: the register export is a
single static CSV (~32,000 societies, verified July 2026). The output
name carries the download month, which is what the preprocess step
parses (last two -separated parts of the name).

The pipeline relies on the register's own header typo
"Full Registation Number" (see RUNBOOK 3.2); this module checks that
column is still present and stops with a clear error if the FCA has
fixed the typo (in which case handler/preprocess.py needs updating).
"""

import argparse
import re
from datetime import date

from .common import (DEFAULT_RAW_ROOT, http_get, resolve_outdir,
                     strip_utf8_bom)

SITE = 'https://mutuals.fca.org.uk/'
# direct link as published on the site front page (July 2026)
FALLBACK_CSV_URL = ('https://fcastoragemprprod.blob.core.windows.net'
                    '/societylist/SocietyList.csv')


def find_society_list_url():
    """Find the SocietyList.csv link on the register front page, falling
    back to the last known blob URL."""
    try:
        resp = http_get(SITE, timeout=60)
        m = re.search(r'href="(//[^"]*SocietyList\.csv|https?://[^"]*'
                      r'SocietyList\.csv)"', resp.text)
        if m:
            url = m.group(1)
            return 'https:' + url if url.startswith('//') else url
        print('WARNING: SocietyList.csv link not found on the site; '
              'using the last known URL')
    except Exception as e:
        print(f'WARNING: could not read {SITE} ({e}); using the last '
              f'known URL')
    return FALLBACK_CSV_URL


def download_society_list(outdir=None):
    """Download the FCA mutuals society list. Returns the path written."""
    folder = resolve_outdir(outdir, 'mutuals')
    url = find_society_list_url()
    print(f'Downloading {url}')
    resp = http_get(url)
    data = strip_utf8_bom(resp.content)

    header = data.split(b'\n', 1)[0].decode('latin-1')
    if 'Full Registation Number' not in header:
        raise RuntimeError(
            'The register no longer has the "Full Registation Number" '
            'column (typo included) that handler/preprocess.py relies '
            'on. Inspect the new header and update the pipeline before '
            'saving this download. Header was: ' + header[:300])

    out = folder / f'SocietyList-{date.today():%Y-%m}.csv'
    out.write_bytes(data)
    n_rows = data.count(b'\n') - 1
    print(f'  saved {len(data):,} bytes (~{n_rows:,} societies) -> {out}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the FCA Mutuals Public Register society list')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    args = parser.parse_args()
    download_society_list(outdir=args.outdir)
