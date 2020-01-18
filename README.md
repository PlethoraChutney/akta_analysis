# FPLC_processing

This is a simple script that takes the exported traces from AKTA
instruments and converts them to a long format. This format is suitable
for further analysis in R, or whichever program you prefer.

Right now, the script only pulls mAU, mS/cm, and %B data, as well as
fraction split points. More can be added but it's all hard-coded because
of the format the AKTA exports in. Additionally, this script skips the first
line of a file because usually it's mostly empty (with only a few 'Chrom 1'
cells in it). If your exports don't have this empty line, use the
`--skiprows` flag to change the value. If you get an empty output csv, or
one with just headers, or one with just fractions, this is probably your issue.

If you have exported several files from the AKTA and want them all in their own
directories, use the `--mass-export` option. This will take all .csv files in the
specified directory and copy them to their own directory, make a long table, and
make the default R plots.
