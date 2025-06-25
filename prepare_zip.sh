#!/bin/bash

# prepare zipped spine files:

jupyter nbconvert --to pdf --execute visualise/stats_and_visuals.ipynb
pdflatex builder.tex
zip tso-spine-files.zip ../public_spine_data/public_spine.*csv builder.pdf  -j
git add tso-spine-files.zip
git commit -m 'updated spine zip file for downloads'
git push origin new-build-spine


# prepare zipped financial history files:

zip finhist_files.zip ../processed_data/payload_data/public_spine.finhist.csv -j
git add finhist_files.zip
git commit -m 'updated finhist zip for downloads'
git push origin new-build-spine