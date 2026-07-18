"""acquire/cqc_api.py -- fetch the full CQC provider register via the public CQC
syndication API and write ONE pipeline-ready CSV per run into
../raw_data/CareQualityCommission/.

Why: the "care directory" download previously used for CQC carries no company or
charity numbers, so CQC providers could only be linked to the spine by name
(weak evidence, demonstrably over-merged). The API's per-provider record carries
companiesHouseNumber and charityNumber, which allow identifier-based matching.
This module ports the fetch approach from the owner's social-care-cics project
(syntax/data-collection/fetch_cqc_providers.py and _fetch_locations_concurrent.py).

Authentication
--------------
Every request needs a CQC API subscription key (free: register at
https://api-portal.service.cqc.org.uk/ and subscribe to the syndication API),
sent as the `Ocp-Apim-Subscription-Key` header. Keys are read from, in order:
  1. environment variables CQC_PRIMARY_KEY / CQC_SECONDARY_KEY
  2. a `.env` file (KEY=value lines) in the repo root, or the path given
     with --env
A `partnerCode` header (an informative organisation string per CQC docs) is
also sent, which grants the 2000 requests/minute tier.

Output file layout (deliberate, please do not "clean up")
---------------------------------------------------------
The CSV is written so that BOTH existing consumers can read it without any
change to handler/preprocess.py:
  line 1     : header row        -> read by handler/base.iter_csv_rows
                                    (handler/careQC.py path)
  lines 2-4  : blank             -> csv.DictReader skips truly blank rows
  line 5     : header row again  -> handler/preprocess.fix_CQC_files skips the
                                    first 4 lines (care-directory preamble
                                    convention) and reads THIS as the header
  line 6+    : data rows
The repeated header appears to the handler as one data row whose values equal
the column names; handler/careQC.CQCDataHandler.all_filters drops it.
The filename follows the DD_MonthName_YYYY_ prefix convention that
fix_CQC_files parses for the iteration date.

Usage
-----
  python acquire/cqc_api.py                  # full register (~64k providers)
  python acquire/cqc_api.py --limit 200      # smoke test
  python acquire/cqc_api.py --out DIR --env PATH
Environment overrides: CQC_FETCH_RATE (req/sec, default 10),
CQC_FETCH_WORKERS (threads, default 8).

The run is resumable within a calendar month: each provider's JSON is appended
to a cache file (.cqc_api_cache/providers-YYYYMM.jsonl next to the output CSV);
re-running skips providers already cached and rewrites the CSV from the cache.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT.parent / "raw_data" / "CareQualityCommission"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"

BASE_URL = "https://api.service.cqc.org.uk/public/v1"
PARTNER_CODE = "Braw Data Ltd"  # informative org string per CQC docs -> 2000 req/min tier
USER_AGENT = "tso-database-builder/0.1"
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)
LIST_PER_PAGE = 500

RATE_PER_SEC = float(os.environ.get("CQC_FETCH_RATE", "10"))
WORKERS = int(os.environ.get("CQC_FETCH_WORKERS", "8"))

# Column order of the output CSV. The subset shared with the old care-directory
# download keeps the directory's exact column names so handler/careQC.py and
# handler/preprocess.fix_CQC_files work on both old and new files.
CSV_FIELDS = [
    "CQC Provider ID (for office use only)",
    "Provider name",
    "Also known as",
    "Brand ID",
    "Brand Name",
    "Ownership Type",
    "Companies House Number",
    "Charity Number",
    "Address",
    "City",
    "Postcode",
    "Local authority",
    "Region",
    "Registration Status",
    "Registration Date",
    "Deregistration Date",
    "Iteration",
]


def load_keys(env_file: Path) -> tuple[str, str]:
    """Subscription keys from environment variables, else a .env file."""
    primary = os.environ.get("CQC_PRIMARY_KEY", "")
    secondary = os.environ.get("CQC_SECONDARY_KEY", "")
    if not primary and env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "CQC_PRIMARY_KEY":
                    primary = v
                elif k == "CQC_SECONDARY_KEY":
                    secondary = v
    return primary, secondary


class RateLimiter:
    """Caps request starts to RATE_PER_SEC across all worker threads."""

    def __init__(self, rps: float):
        self.iv = 1.0 / rps
        self.lock = threading.Lock()
        self.next = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            wait = self.next - now
            if wait < 0:
                wait = 0.0
                self.next = now + self.iv
            else:
                self.next += self.iv
        if wait > 0:
            time.sleep(wait)


def fetch_once(url: str, key: str) -> tuple[int, str | None, str | None]:
    req = Request(url, headers={
        "Ocp-Apim-Subscription-Key": key,
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        "partnerCode": PARTNER_CODE,
    })
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, resp.read().decode("utf-8"), None
    except HTTPError as e:
        retry_after = e.headers.get("Retry-After", "") if e.headers else ""
        return e.code, None, f"HTTP {e.code}: {e.reason} | retry-after={retry_after}"
    except (URLError, socket.timeout, ConnectionError, TimeoutError) as e:
        return 0, None, f"{type(e).__name__}: {e}"


def _retry_after_seconds(error_msg: str) -> float | None:
    if "retry-after=" not in (error_msg or ""):
        return None
    try:
        token = error_msg.split("retry-after=", 1)[1].split(" ")[0]
        return float(token) if token else None
    except (ValueError, IndexError):
        return None


def fetch_with_retry(url: str, primary: str, secondary: str,
                     sleep=time.sleep) -> tuple[str, str | None, str]:
    """Returns (outcome, body, error). Outcomes: ok / not_found / auth_failed /
    gave_up. Swaps to the secondary key on 401/403, honours Retry-After."""
    key, swapped, last_error = primary, False, ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        status, body, error = fetch_once(url, key)
        last_error = error or ""
        if status == 200 and body is not None:
            return "ok", body, ""
        if status == 404:
            return "not_found", None, ""
        if status in (401, 403):
            if not swapped and secondary:
                key, swapped = secondary, True
                continue
            return "auth_failed", None, last_error
        if attempt < MAX_ATTEMPTS:
            sleep(_retry_after_seconds(last_error) or BACKOFF_SECONDS[attempt - 1])
    return "gave_up", None, last_error


def list_all_provider_ids(primary: str, secondary: str) -> list[str]:
    """Page through GET /providers (id + name only) to enumerate the register."""
    ids: list[str] = []
    page, total_pages = 1, 1
    while page <= total_pages:
        url = f"{BASE_URL}/providers?page={page}&perPage={LIST_PER_PAGE}"
        outcome, body, error = fetch_with_retry(url, primary, secondary)
        if outcome != "ok" or body is None:
            raise RuntimeError(f"provider list page {page} failed: {outcome} {error}")
        data = json.loads(body)
        total_pages = int(data.get("totalPages", 1))
        ids.extend(p["providerId"] for p in data.get("providers", []))
        if page == 1:
            print(f"register lists {data.get('total')} providers over {total_pages} pages")
        if page % 20 == 0 or page == total_pages:
            print(f"  listed page {page}/{total_pages} ({len(ids)} ids)", flush=True)
        page += 1
    return ids


def provider_to_row(d: dict, iteration: str) -> dict:
    """Flatten one provider-detail JSON object into an output CSV row."""

    def g(key: str) -> str:
        v = d.get(key)
        return str(v).strip() if v is not None else ""

    address = ", ".join(x for x in (g("postalAddressLine1"), g("postalAddressLine2"),
                                    g("postalAddressCounty")) if x)
    return {
        "CQC Provider ID (for office use only)": g("providerId"),
        "Provider name": g("name"),
        "Also known as": g("alsoKnownAs"),
        "Brand ID": g("brandId"),
        "Brand Name": g("brandName"),
        "Ownership Type": g("ownershipType"),
        "Companies House Number": g("companiesHouseNumber"),
        "Charity Number": g("charityNumber"),
        "Address": address,
        "City": g("postalAddressTownCity"),
        "Postcode": g("postalCode"),
        "Local authority": g("localAuthority"),
        "Region": g("region"),
        "Registration Status": g("registrationStatus"),
        "Registration Date": g("registrationDate"),
        "Deregistration Date": g("deregistrationDate"),
        "Iteration": iteration,
    }


def read_cache(cache_file: Path) -> dict[str, dict]:
    """Load already-fetched provider JSON objects (keyed by providerId)."""
    cached: dict[str, dict] = {}
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue  # torn tail line from an interrupted run
                pid = obj.get("providerId")
                if pid:
                    cached[pid] = obj
    return cached


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write the dual-reader CSV (see module docstring for the layout)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()          # line 1: header (for handler/careQC.py)
        f.write("\r\n" * 3)           # lines 2-4: truly blank (csv.DictReader skips them)
        writer.writerow({k: k for k in CSV_FIELDS})  # line 5: header again (for preprocess)
        for row in rows:
            writer.writerow(row)
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=None,
                    help="fetch only the first N providers (smoke test)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR,
                    help=f"output directory (default {DEFAULT_OUT_DIR})")
    ap.add_argument("--env", type=Path, default=DEFAULT_ENV_FILE,
                    help=f".env file with CQC_PRIMARY_KEY (default {DEFAULT_ENV_FILE})")
    args = ap.parse_args(argv)

    primary, secondary = load_keys(args.env)
    if not primary:
        print("ERROR: no CQC subscription key. Set CQC_PRIMARY_KEY as an environment "
              f"variable or in {args.env} (register free at "
              "https://api-portal.service.cqc.org.uk/).", file=sys.stderr)
        return 1

    now = dt.datetime.now()
    iteration = now.strftime("%m/%Y")
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"{now.strftime('%d_%B_%Y')}_cqc_api_providers.csv"
    cache_file = out_dir / ".cqc_api_cache" / f"providers-{now.strftime('%Y%m')}.jsonl"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"CQC API provider fetch at {now.isoformat(timespec='seconds')}")
    ids = list_all_provider_ids(primary, secondary)
    if args.limit:
        ids = ids[: args.limit]

    cached = read_cache(cache_file)
    to_fetch = [i for i in ids if i not in cached]
    print(f"providers: {len(ids)} wanted | {len(cached)} already cached this month "
          f"| {len(to_fetch)} to fetch | workers={WORKERS} rate={RATE_PER_SEC}/s")

    rate = RateLimiter(RATE_PER_SEC)
    io_lock = threading.Lock()
    abort = threading.Event()
    counts = {"ok": 0, "not_found": 0, "gave_up": 0, "auth_failed": 0}
    done_n = [0]

    cache_f = open(cache_file, "a", encoding="utf-8")

    def work(pid: str) -> None:
        if abort.is_set():
            return
        rate.wait()
        url = f"{BASE_URL}/providers/{quote(pid)}"
        outcome, body, error = fetch_with_retry(url, primary, secondary)
        with io_lock:
            counts[outcome] = counts.get(outcome, 0) + 1
            done_n[0] += 1
            n = done_n[0]
            if outcome == "ok" and body is not None:
                try:
                    obj = json.loads(body)
                except json.JSONDecodeError:
                    counts["ok"] -= 1
                    counts["gave_up"] += 1
                else:
                    cached[pid] = obj
                    cache_f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            elif outcome != "not_found":
                print(f"  WARN {pid}: {outcome} {error}", flush=True)
        if n % 500 == 0:
            print(f"  [{n}/{len(to_fetch)}] {counts}", flush=True)
        if outcome == "auth_failed":
            abort.set()

    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(work, to_fetch))
    finally:
        cache_f.close()

    if abort.is_set():
        print("ABORT: authentication failed with both keys; CSV not written.",
              file=sys.stderr)
        return 2

    rows = [provider_to_row(cached[i], iteration) for i in ids if i in cached]
    rows.sort(key=lambda r: r["CQC Provider ID (for office use only)"])
    write_csv(out_csv, rows)

    n = len(rows)
    n_co = sum(1 for r in rows if r["Companies House Number"])
    n_ch = sum(1 for r in rows if r["Charity Number"])
    print(f"fetch outcomes: {counts}")
    print(f"wrote {out_csv}: {n} providers "
          f"| {n_co} ({100 * n_co / n:.1f}%) with Companies House number "
          f"| {n_ch} ({100 * n_ch / n:.1f}%) with charity number" if n else
          f"wrote {out_csv}: 0 providers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
