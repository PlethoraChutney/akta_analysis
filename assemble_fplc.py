import numpy as np
import pandas as pd
import sys
import os
import argparse
import subprocess

skip_rows = 1

def get_file_list(directory, quiet):
    file_list = []
    for file in os.listdir(directory):
        if file.endswith(".csv"):
            file_list.append(os.path.join(directory, file))

    if not quiet:
        print(f'Found {len(file_list)} files')

    return file_list

def append_chroms(file_list, quiet):
    if not quiet:
        print('Generating compiled trace csv...')
    chroms = pd.DataFrame(columns = ['mL', 'Channel', 'Signal', 'frac_mL', 'Fraction', 'Sample', 'inst_frac'])
    for file in file_list:
        fplc_trace = pd.read_csv(file, skiprows = skip_rows, header = [1], encoding = 'utf-16-le', delimiter = '\t', engine = 'python', )
        fplc_trace = fplc_trace.filter(regex = '(ml|mAU$|mS/cm$|\%$|Fraction)')
        columns = fplc_trace.columns
        renaming = {}
        if 'mAU' in columns:
            au_column = columns.get_loc('mAU')
            renaming[columns[au_column-1]] = 'mL_mAU'
        if 'mS/cm' in columns:
            ms_column = columns.get_loc('mS/cm')
            renaming[columns[ms_column-1]] = 'mL_mScm'
        if '%' in columns:
            percent_column = columns.get_loc('%')
            renaming[columns[percent_column-1]] = 'mL_percentB'
        if 'Fraction' in columns:
            frac_column = columns.get_loc('Fraction')
            renaming[columns[frac_column-1]] = 'frac_mL'
        fplc_trace = fplc_trace.rename(columns = renaming)

        long_trace = pd.DataFrame(columns = ['mL', 'Channel', 'Signal'])
        if 'mAU' in columns:
            mau = pd.melt(fplc_trace, id_vars = ['mL_mAU'], value_vars = ['mAU'], var_name = 'Channel', value_name = 'Signal')
            mau = mau.rename(columns = {'mL_mAU':'mL'}).dropna()
            long_trace = long_trace.append(mau)
        if 'mS/cm' in columns:
            mscm = pd.melt(fplc_trace, id_vars = ['mL_mScm'], value_vars = 'mS/cm', var_name = 'Channel', value_name = 'Signal')
            mscm = mscm.rename(columns = {'mL_mScm':'mL'}).dropna()
            long_trace = long_trace.append(mscm)
        if '%' in columns:
            perc = pd.melt(fplc_trace, id_vars = 'mL_percentB', value_vars = '%', var_name = 'Channel', value_name = 'Signal')
            perc = perc.rename(columns = {'mL_percentB':'mL'}).dropna()
            long_trace = long_trace.append(perc)
        if "Fraction" in columns:
            frac = fplc_trace.filter(regex = 'rac').dropna()
            long_trace = pd.concat([long_trace.reset_index(drop=True), frac], axis = 1)

        long_trace['Sample'] = os.path.basename(file)

        long_trace['inst_frac'] = 1
        frac_mL = long_trace['frac_mL'].dropna()
        for i in range(len(frac_mL)):
            long_trace.loc[long_trace['mL'] > frac_mL[i], 'inst_frac'] = i + 2

        chroms = chroms.append(long_trace, ignore_index = True)

    if not quiet:
        print('Done with csv...')
    return chroms

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'A script to collect FPLC traces from GE AKTA FPLCs')
    parser.add_argument('-d', '--directory', default = os.getcwd(), help = 'Which directory to pull all .csv files from. Default is the current directory')
    parser.add_argument('-o', '--output', default = os.path.join(os.getcwd(), 'fplcs.csv'), help = 'Where to write the compiled traces. Default is fplcs.csv in the current directory')
    parser.add_argument('-s', '--skiprows', default = 1, help = 'Number of rows to skip reading. Default 1', action = 'store', dest = 'skip_rows', type = int)
    parser.add_argument('-m', '--minfrac', default = 1, help = 'The lowest fraction to highlight in the plot. Default is 1', dest = 'min_frac', type = int)
    parser.add_argument('-a', '--maxfrac', default = 50, help = 'The highest fraction to hightlight in the plot. Default is 50', dest = 'max_frac', type = int)
    parser.add_argument('-q', '--quiet', help = 'Don\'t print messages about progress', action = 'store_true')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)
    args = parser.parse_args()

    dir = os.path.normpath(args.directory)
    outfile = os.path.normpath(args.output)
    outdir = os.path.dirname(outfile)
    skip_rows = args.skip_rows
    min_frac = str(args.min_frac)
    max_frac = str(args.max_frac)
    quiet = args.quiet

    if os.path.isfile(outfile):
        print('I don\'t want to overwrite a file. Please move or delete it first.')
        sys.exit()

    file_list = get_file_list(dir, quiet)
    compiled = append_chroms(file_list, quiet)
    compiled.to_csv(outfile, index = False)
    if not quiet:
        print('Generating plots...')
    subprocess.run(['Rscript', '--quiet', 'plot_traces.R', outfile, min_frac, max_frac])
    if os.path.isfile(os.path.join(outdir, 'Rplots.pdf')) :
        os.remove(os.path.join(outdir, 'Rplots.pdf'))
    if not quiet:
        print('Done.')
