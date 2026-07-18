"""acquire: programmatic download of the raw register files (RUNBOOK step 0).

One module per source; each saves files with the exact names the
preprocess step expects (RUNBOOK.md section 3.2). Run any module
directly, e.g.:

    python -m acquire.ccew --outdir ../raw_data

Modules deliberately do NOT get imported here, so that a problem with
one source (or a missing optional dependency) never blocks the others.
"""
