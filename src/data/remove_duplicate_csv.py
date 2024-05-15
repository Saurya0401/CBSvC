import pandas as pd
import os

data_dir = ''

for folder in os.listdir(data_dir):
    path = data_dir+folder
    # Load the CSV file
    df = pd.read_csv(path)

    # Columns to consider while removing duplicates
    consider_columns = ['time_seconds', 'time', 'speed', 'throttle']

    # Remove duplicate columns except the ones specified in ignore_columns
    df_no_duplicates = df.drop_duplicates(subset=['time_seconds', 'time', 'speed', 'throttle'], keep='first', inplace=False, ignore_index=False)

    # Save the data frame without duplicates (and with ignored columns) to a new CSV file
    df_no_duplicates.to_csv(f'{folder[:-4]}_preprocessed.csv', index=False)
