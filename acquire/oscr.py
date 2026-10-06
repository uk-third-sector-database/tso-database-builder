"""OSCR: Scottish Charity Register - daily register downloads.

Source page : https://www.oscr.org.uk/about-charities/search-the-register/download-the-scottish-charity-register/
Products    : current register  -> https://www.oscr.org.uk/download/charity-register
              former (removed)  -> https://www.oscr.org.uk/download/charity-former-register
Output      : <raw_root>/oscr/CharityExport-DD-Mon-YYYY.csv
              <raw_root>/oscr/CharityExport-Removed-DD-Mon-YYYY.csv

Both downloads arrive as a zip containing a single CSV whose name
already follows OSCR's own convention (which is exactly what the
preprocess step parses the snapshot date from), so the native filename
inside the zip is kept unchanged.

OSCR licence note: use of the download implies acceptance of the Open
Government Licence v3 terms shown on the download page (no direct
marketing; do not present the list as the Scottish Charity Register).
"""

import argparse
import io
import zipfile

from .common import DEFAULT_RAW_ROOT, http_get, resolve_outdir

REGISTER_URL = 'https://www.oscr.org.uk/download/charity-register'
REMOVED_URL = 'https://www.oscr.org.uk/download/charity-former-register'


def _download_zip_member(url, folder):
    """Download one OSCR zip and extract its single CSV member, keeping
    the member's own (dated) filename. Returns the path written."""
    print(f'Downloading {url}')
    resp = http_get(url)
    print(f'  got {len(resp.content):,} bytes')
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        members = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(members) != 1:
            raise RuntimeError(
                f'Expected exactly one CSV inside the zip, found: '
                f'{z.namelist()}')
        name = members[0]
        out = folder / name
        with z.open(name) as src, open(out, 'wb') as dst:
            dst.write(src.read())
    print(f'  wrote {out}')
    return out


def download_register(outdir=None, which='both'):
    """Download the OSCR register CSV(s).

    which: 'current', 'removed' or 'both' (default).
    Returns the list of paths written."""
    folder = resolve_outdir(outdir, 'oscr')
    paths = []
    if which in ('current', 'both'):
        paths.append(_download_zip_member(REGISTER_URL, folder))
    if which in ('removed', 'both'):
        paths.append(_download_zip_member(REMOVED_URL, folder))
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the OSCR charity register (current and/or '
                    'former charities) keeping OSCR\'s dated filenames')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    parser.add_argument('--which', choices=['current', 'removed', 'both'],
                        default='both')
    args = parser.parse_args()
    download_register(outdir=args.outdir, which=args.which)
