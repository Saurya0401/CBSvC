"""
Module for plotting logged driving data from a CSV file.

This script allows the user to plot specific logged driving data, such as speed,
throttle, brake, steer, heart rate, and breathing rate, against time. The data can 
be plotted either in individual figures or combined into a single figure with 
shared axes.

Usage:
    python plot_logged_data.py <log_file_pattern> [options]

Options:
    -d, --data    Plot specific data(s) in multiple figures
    -c, --combi   Plot specific data(s) in a single figure
    --all         Plot all data in multiple figures
    --dir DIR     Folder where log files are (default: src/logs/filtered)
"""

from dataclasses import dataclass
from pathlib import Path
import argparse
import pandas as pd
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class LogData:
    """Utility class for formatting text in plots.

    Attributes:
        df_label (str): Label of the data in the DataFrame.
        unit (str, optional): Unit of the data. Defaults to an empty string.
    """
    df_label: str
    unit: str = ''

    def __repr__(self):
        return self.df_label

    @property
    def legend_text(self):
        """Returns the legend text for the plot, with underscores replaced by spaces."""
        return self.df_label.replace('_', ' ')

    @property
    def y_label(self):
        """Returns the y-axis label for the plot, including the unit if provided."""
        return self.legend_text + f' {f"({self.unit})" if self.unit else ""}'

    @property
    def title_text(self):
        """Returns the title text for the plot, formatted in title case."""
        return self.df_label.replace("_", " ").title()


class DataPlotter:
    """Class for plotting logged driving data.

    Attributes:
        df (pandas.DataFrame): DataFrame containing the logged data.
        figsize (tuple): Size of the figure for the plots.
        colors (dict): Dictionary mapping data labels to colors.
    """

    def __init__(self, log_file, figsize=(12, 6)):
        """Initializes the DataPlotter with the given DataFrame and figure size.

        Args:
            df (pandas.DataFrame): DataFrame containing the logged data.
            figsize (tuple, optional): Size of the figure for the plots. Defaults to (12, 6).
        """
        self.df = pd.read_csv(log_file)
        self.figsize = figsize
        self.file_name = ' '.join(log_file.stem.split('_')[2:4]).title()
        self.colors = {
            'speed': 'blue',
            'throttle': 'green',
            'brake': 'red',
            'steer': 'brown',
            'heart_rate': 'darkorange',
            'breathing_rate': 'purple'
        }

    def _set_plot(self, title, lines=None):
        """Sets the title and legend for the plot.

        Args:
            title (str): Title of the plot.
            lines (list, optional): List of Line2D objects for the legend. Defaults to None.
        """
        plt.title(title + f' ({self.file_name})')
        if lines:
            plt.legend(handles=lines)
        plt.tight_layout()

    def plot(self, log_data):
        """Plots specific data against time (in seconds).

        Args:
            log_data (LogData): LogData object containing the data label and unit.
        """
        data_label = str(log_data)
        plt.figure(figsize=self.figsize)
        plt.plot(
            self.df['time_seconds'], self.df[data_label],
            label=log_data.legend_text,
            color=self.colors[data_label]
        )
        plt.xlabel('time (s)')
        plt.ylabel(log_data.y_label, color=self.colors[data_label])
        plt.tick_params(axis='y', labelcolor=self.colors[data_label])

        self._set_plot(f'Time vs {log_data.title_text}')

    def plot_combination(self, log_data_list):
        """Plots multiple data against time (in seconds) on a shared axis.

        Args:
            log_data_list (list of LogData): List of LogData objects to plot.
        """
        ax1, line1 = self._plot_shared_axes(log_data_list[0])
        lines = [line1]
        for i, ld in enumerate(log_data_list[1:]):
            lines.append(self._plot_shared_axes(ld, ax=ax1, shift_y_mul=i)[1])
        self._set_plot(
            title='Time vs ' + ', '.join([ld.title_text for ld in log_data_list]),
            lines=lines
        )

    def _plot_shared_axes(self, log_data, shift_y_mul=0, ax=None):
        """Plots data on a shared axis.

        Args:
            log_data (LogData): LogData object containing the data label and unit.
            shift_y_mul (int, optional): Multiplier for shifting the y-axis position. Defaults to 0.
            ax (matplotlib.axes.Axes, optional): Existing axis to plot on. Defaults to None.

        Returns:
            tuple: Tuple containing the axis and the Line2D object.
        """
        if ax is None:
            _, ax = plt.subplots(figsize=self.figsize)
            ax.set_xlabel('time (s)')
        else:
            ax = ax.twinx()
        data_label = str(log_data)
        ax.spines['right'].set_position(('outward', shift_y_mul * 45))
        ax.set_ylabel(log_data.y_label, color=self.colors[data_label])
        line, = ax.plot(
            self.df['time_seconds'], self.df[data_label],
            label=log_data.legend_text,
            color=self.colors[data_label],
        )
        ax.tick_params(axis='y', labelcolor=self.colors[data_label])
        return ax, line


LOG_DATA_INFO = {
    'speed': LogData('speed', 'km/h'),
    'throttle': LogData('throttle'),
    'brake': LogData('brake'),
    'steer': LogData('steer'),
    'heart_rate': LogData('heart_rate', 'beats/min'),
    'breathing_rate': LogData('breathing_rate', 'breaths/min')
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        'log_file_pattern',
        type=str,
        help='Plot log file(s) with this pattern (src/logs/filtered/<pattern>.csv)'
    )
    parser.add_argument(
        '--dir',
        type=str,
        default='src/logs/filtered',
        help='Folder where log files are (default: %(default)s)'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-d', '--data',
        type=str,
        choices=LOG_DATA_INFO.keys(),
        nargs='+',
        help='Plot specific data(s) in multiple figures'
    )
    group.add_argument(
        '-c', '--combi',
        type=str,
        choices=LOG_DATA_INFO.keys(),
        nargs='+',
        help='Plot specific data(s) in a single figure'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='Plot all data in multiple figures'
    )
    args = parser.parse_args()


    for log_file in Path(args.dir).glob(f'*{args.log_file_pattern}*'):
        plotter = DataPlotter(log_file)
        if args.all:
            for log_data in LOG_DATA_INFO.values():
                plotter.plot(log_data)
        else:
            if args.data:
                for data in args.data:
                    plotter.plot(LOG_DATA_INFO[data])
            elif args.combi:
                plotter.plot_combination([LOG_DATA_INFO[data] for data in args.combi])
    plt.show()
