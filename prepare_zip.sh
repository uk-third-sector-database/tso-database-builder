#!/bin/bash

jupyter nbconvert --to pdf --execute visualise/stats_and_visuals.ipynb
pdflatex builder.tex
zip tso-spine-files.zip ../public_spine_data/public_spine.*csv builder.pdf release_info.pdf -j
git add tso-spine-files.zip
git commit -m 'updated zip file for downloads'
git push

