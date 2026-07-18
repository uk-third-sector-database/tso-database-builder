"""Shared helpers for the acquire package (raw register downloads).

Every downloader in this package writes into a "raw data root" folder,
one subfolder per source, using the exact filename patterns the
preprocess step expects (see RUNBOOK.md section 3.2). The default root
is `../raw_data` relative to the repo root, i.e. the sibling folder the
rest of the pipeline already uses. Pass `outdir=` (or `--outdir` on the
command line) to write somewhere else, e.g. for a test run.

Only plain functions and the `requests` library - no framework.
"""

import os
import re
import time
from pathlib import Path

import requests

# repo root = parent of this package's folder
REPO_ROOT = Path(__file__).resolve().parents[1]
# default raw-data root: sibling of the repo, as used by the whole pipeline
DEFAULT_RAW_ROOT = REPO_ROOT.parent / 'raw_data'

# polite, identifiable user agent
USER_AGENT = ('tso-database-builder data acquisition '
              '(academic research; Mozilla/5.0 compatible)')

DEFAULT_TIMEOUT = 300          # seconds per request
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 5.0          # seconds; doubled after each failed attempt


def resolve_outdir(outdir, source_subfolder):
    """Return (and create) the output folder for one source.

    `outdir` is the raw-data root (None -> DEFAULT_RAW_ROOT);
    `source_subfolder` is that source's folder name, e.g. 'ccew'.
    """
    root = Path(outdir) if outdir else DEFAULT_RAW_ROOT
    folder = root / source_subfolder
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def http_get(url, *, params=None, headers=None, stream=False,
             timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES,
             backoff=DEFAULT_BACKOFF, session=None):
    """GET a URL with a few retries on connection errors / 5xx responses.

    Returns the requests.Response (status checked: raises for a final
    non-2xx). Retries do NOT hammer: they wait `backoff` seconds,
    doubling each time.
    """
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)
    getter = session.get if session is not None else requests.get

    last_error = None
    wait = backoff
    for attempt in range(1, retries + 1):
        try:
            resp = getter(url, params=params, headers=hdrs,
                          stream=stream, timeout=timeout)
            if resp.status_code >= 500 or resp.status_code == 429:
                last_error = RuntimeError(
                    f'HTTP {resp.status_code} from {url}')
            else:
                resp.raise_for_status()
                return resp
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
        if attempt < retries:
            print(f'  attempt {attempt} failed ({last_error}); '
                  f'retrying in {wait:.0f}s')
            time.sleep(wait)
            wait *= 2
    raise RuntimeError(f'Download failed after {retries} attempts: {url}') \
        from last_error


def download_file(url, dest_path, *, params=None, headers=None,
                  timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES,
                  session=None, chunk_size=1024 * 1024):
    """Stream a URL to `dest_path` (Path), writing via a .part temp file
    so an interrupted download never leaves a half-written file with the
    final name. Returns the Path written."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_path.with_suffix(dest_path.suffix + '.part')

    resp = http_get(url, params=params, headers=headers, stream=True,
                    timeout=timeout, retries=retries, session=session)
    written = 0
    with open(tmp, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                written += len(chunk)
    os.replace(tmp, dest_path)
    print(f'  saved {written:,} bytes -> {dest_path}')
    return dest_path


def filename_from_response(resp):
    """Filename given in a response's Content-Disposition header, or None."""
    cd = resp.headers.get('Content-Disposition', '')
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
    return m.group(1).strip() if m else None


def strip_utf8_bom(data: bytes) -> bytes:
    """Remove a UTF-8 byte-order mark, if present, from raw file bytes.

    Several preprocess readers open files with plain 'UTF8' or 'Latin-1'
    encodings; a BOM would corrupt the first column name and silently
    empty that column downstream."""
    if data.startswith(b'\xef\xbb\xbf'):
        return data[3:]
    return data
