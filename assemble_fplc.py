import numpy as np
import pandas as pd
import sys
import os
import argparse
import subprocess
import shutil

skip_rows = 1
script_path = dir_path = os.path.dirname(os.path.realpath(__file__))

def get_file_list(directory, quiet):
    file_list = []

    if os.path.isdir(directory):
        for file in os.listdir(directory):
            if file.endswith(".csv"):
                file_list.append(os.path.normpath(os.path.join(directory, file)))
    elif os.path.isfile(directory):
        if directory.endswith('.csv'):
            file_list.append(os.path.normpath(directory))

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

        # The AKTA exports data with several different ml columns, each with their
        # own name (like ml.2, ml.3, etc.). These are mL axes for each channel.
        # Unfortunately, they are different for each channel! So we need to keep
        # each and know which channel it goes with. Additionally, since users
        # don't have to export every channel every time, we can't hard code positions
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
            perc['Channel'] = '%_B'
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
    parser.add_argument('directory', default = os.getcwd(), help = 'Which directory to pull all .csv files from, or a particular .csv file. Default is all files in the current directory')
    parser.add_argument('-o', '--output', default = os.path.join(os.getcwd(), 'fplcs.csv'), help = 'Where to write the compiled traces. Default is fplcs.csv in the current directory')
    parser.add_argument('-s', '--skiprows', default = 1, help = 'Number of rows to skip reading. Default 1', action = 'store', dest = 'skip_rows', type = int)
    parser.add_argument('-f', '--fractions', nargs = 2, default = ['0', '0'], help = 'Inclusive range of fractions to fill in. Default is not to fill any.')
    parser.add_argument('-m', '--ml', nargs = 2, default = ['5', '20'], help = 'Inclusive range for x-axis, in mL. Default is 5 to 20')
    parser.add_argument('-q', '--quiet', help = 'Don\'t print messages about progress', action = 'store_true')
    parser.add_argument('--copy-manual', help = 'Copy the manual plotting Rscript for further tweaking', action = 'store_true')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)
    args = parser.parse_args()

    dir = os.path.normpath(args.directory)
    outfile = os.path.abspath(args.output)
    outdir = os.path.dirname(outfile)
    if outfile[-4:] != '.csv':
        print('Please include the name of the file in outfile, i.e., \'path/to/[name].csv\'')
        sys.exit(1)

    skip_rows = args.skip_rows
    min_frac = str(args.fractions[0])
    max_frac = str(args.fractions[1])
    low_ml = str(args.ml[0])
    high_ml = str(args.ml[1])
    quiet = args.quiet
    copy_manual = args.copy_manual

    if os.path.isfile(outfile):
        if input(f'Are you sure you want to overwrite the file {os.path.abspath(outfile)}?\n[Y]es / [N]o\n').upper() != 'Y':
            sys.exit(0)

    file_list = get_file_list(dir, quiet)
    compiled = append_chroms(file_list, quiet)
    compiled.to_csv(outfile, index = False)
    if not quiet:
        print(f'Generating plots ({low_ml} to {high_ml}mL, fractions {min_frac} to {max_frac})...')
    subprocess.run(['Rscript', '--quiet', os.path.join(script_path, 'plot_traces.R'), outfile, min_frac, max_frac, low_ml, high_ml])
    if os.path.isfile(os.path.join(outdir, 'Rplots.pdf')) :
        os.remove(os.path.join(outdir, 'Rplots.pdf'))

    if copy_manual:
        if not quiet:
            print('Copying manual RScript...')
        shutil.copyfile(os.path.join(script_path, 'manual_plot_traces.R'), os.path.join(outdir, 'manual_plot_traces.R'))
    if not quiet:
        print('Done.')
