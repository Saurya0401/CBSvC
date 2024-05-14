import pandas as pd

# Load the CSV file
df = pd.read_csv('input.csv')

# Columns to consider while removing duplicates
consider_columns = ['time_seconds', 'time', 'speed', 'throttle']

# Remove duplicate columns except the ones specified in ignore_columns
df_no_duplicates = df.drop_duplicates(subset=['time_seconds', 'time', 'speed', 'throttle'], keep='first', inplace=False, ignore_index=False)

# Save the data frame without duplicates (and with ignored columns) to a new CSV file
df_no_duplicates.to_csv('output_no_duplicates.csv', index=False)
