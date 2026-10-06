#verify_build.py

import pandas as pd


class RepresentationError(RuntimeError):
    """Raised when one or more build-input UIDs are absent from the outputs."""

    def __init__(self, missing_uids):
        self.missing_uids = frozenset(missing_uids)
        preview = ", ".join(sorted(self.missing_uids)[:10])
        suffix = (
            f" (first UIDs: {preview})"
            if preview
            else ""
        )
        super().__init__(
            f"{len(self.missing_uids):,} input organisation UID(s) are missing "
            f"from the spine and matches outputs{suffix}"
        )


def _nonblank_uids(values):
    """Return trimmed, non-null UID strings from a pandas Series."""

    return {
        value
        for value in values.dropna().astype(str).str.strip()
        if value
    }


def verify_representation(infiles,ofile_basename):

    ofile_basename = str(ofile_basename)
    infile_uids = set()
    for csvfile in infiles:
        # find all uids in infiles, excepting CIS and CQC
        df = pd.read_csv(csvfile, usecols=['uid','source'])
        # handlers emit lowercase source labels ('careinspectoratescot', 'carequalitycommission'),
        # so normalise case before filtering
        df = df[~df['source'].astype(str).str.lower().isin(['careinspectoratescot','carequalitycommission'])]
        uids = _nonblank_uids(df['uid'])
        infile_uids.update(uids)
        print(f'\tinfile {csvfile} has {len(uids)} (ignoring any CIS and CQC)')
        
    print(f'\n\nTotal unique uids in all infiles = {len(infile_uids)} \n\n')

    spine_uids = set()
    for csv,fields in [(ofile_basename+'.spine.csv',['uid']),
                        (ofile_basename+'.matches.csv',['orgA_uid','orgB_uid'])]:
        # find all uids in spine
        df = pd.read_csv(csv,usecols=fields)
        for f in fields:
            spine_uids.update(_nonblank_uids(df[f]))

    print(f'\n\nUnique uids in spine and matches files = {len(spine_uids)}\n\n')

    # use set comprehension to find any expected from infiles which aren't in ofiles.
    print('All infile uids are expected in ofiles. Any missing?')
    diff = infile_uids.difference(spine_uids)
    print(f'Difference between infile and spine uid sets = {len(diff)}')
    print(sorted(diff))
    if diff:
        raise RepresentationError(diff)
    return diff
