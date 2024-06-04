"""
Filters our redundant data from log files
"""


from pathlib import Path
import argparse

import pandas as pd
import numpy as np

def remove_duplicates(log_file):
    """Remove duplicates from single log file"""

    f = Path(log_file)
    df = pd.read_csv(f)
    df_new = df.drop_duplicates(keep='first')
    df_new.to_csv(f'{f.parent}/{f.stem}_filtered.csv', index=False)

def interpolate(df, col_name):
    """
    Interpolates the specified column in the DataFrame.
    
    Parameters:
    df (pd.DataFrame): The DataFrame containing the data.
    col_name (str): The name of the column to be interpolated.
    """

    df.loc[df[col_name] < 60, col_name] = np.nan
    df[col_name] = df[col_name].interpolate()
    df[col_name] = df[col_name].fillna(0)

def remove_duplicates_multi(logs_dir):
    """Remove duplicates from all log files in a directory"""

    output_dir = Path(f'{logs_dir}/filtered')
    output_dir.mkdir(parents=True, exist_ok=True)

    for f in Path(logs_dir).glob('*.csv'):
        df = pd.read_csv(f)
        df_new = df.drop_duplicates(keep='first')
        if args.interpolate:
            try:
                interpolate(df_new, 'heart_rate')
                interpolate(df_new, 'breathing_rate')
            except KeyError as e:
                print(f'Error for log "{f}": {e.args[0]}')
        df_new.to_csv(f'{output_dir}/{f.stem}_filtered.csv', index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-d', '--logs_dir',
        metavar='DIR',
        type=str,
        help='Filter all logs from this directory'
    )
    group.add_argument(
        '-f', '--log_file',
        metavar='FILE',
        type=str,
        help='Log file to filter'
    )
    group.add_argument(
        '-i', '--interpolate',
        action='store_true',
        default=False,
        help='Interpolate invalid data (WARNING: USE ONLY IF NECESSARY)'
    )
    args = parser.parse_args()

    if args.logs_dir:
        remove_duplicates_multi(args.logs_dir)
    elif args.log_file:
        remove_duplicates(args.log_file)
    else:
        remove_duplicates_multi('src/logs')
