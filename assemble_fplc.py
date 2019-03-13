import numpy as np
import pandas as pd
import sys
import os
import argparse

skip_rows = 1

def get_file_list(directory):
    file_list = []
    for file in os.listdir(directory):
        if file.endswith(".csv"):
            file_list.append(os.path.join(directory, file))

    return file_list

def append_chroms(file_list):
    chroms = pd.DataFrame(columns = ['mL', 'Channel', 'Signal', 'frac_mL', 'Fraction', 'Sample'])
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

        chroms = chroms.append(long_trace, ignore_index = True)

    return chroms

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'A script to collect FPLC traces from GE AKTA FPLCs')
    parser.add_argument('-d', '--directory', default = os.getcwd(), help = 'Which directory to pull all .csv files from. Default is the current directory')
    parser.add_argument('-o', '--output', default = os.path.join(os.getcwd(), 'fplcs.csv'), help = 'Where to write the compiled traces. Default is fplcs.csv in the current directory')

    if len(sys.argv) == 1:
		parser.print_help(sys.stderr)
		sys.exit(0)
    args = parser.parse_args()

    dir = os.path.normpath(args.directory)
    outfile = os.path.normpath(args.output)
    file_list = get_file_list(dir)
    compiled = append_chroms(file_list)
    compiled.to_csv(outfile, index = False)
