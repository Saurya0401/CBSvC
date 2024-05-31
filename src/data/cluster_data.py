"""
Data clustering tool for various scenarios using DBSCAN or KMeans++ algorithms.

This module provides functionalities to cluster, and visualize data patterns
from log files for different scenarios.
"""

import argparse
from pathlib import Path
from typing import Optional

from numpy.typing import NDArray
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from src.scenarios.scenario import Scenario


class DataClusterer:

    DATA_COLS: list[str] = ['speed', 'heart_rate', 'breathing_rate']

    def __init__(self, scenario_name: str, logs_dir: str, data_cols: Optional[list[str]] = None) -> None:
        """
        Clusters data from log files using the DBSCAN or KMeans++ algorithm.

        Attributes:
            scenario_name (str): The name of the scenario.
            logs_dir (str): Directory containing log files.
            data_cols (list[str]): Columns to include in clustering.
        """

        self.scenario_name: str = scenario_name
        self.logs_dir: str = logs_dir
        self.data_cols: list[str] = data_cols or DataClusterer.DATA_COLS
        self.data: pd.DataFrame = self._load_data().reset_index(drop=True)
        self.data[self.data_cols] = self.data[self.data_cols] \
            .apply(pd.to_numeric, errors='coerce')
        self.data = self.data.dropna(subset=self.data_cols)

        # modify DBSCAN hyperparameters here
        self.dbscan: DBSCAN = DBSCAN(eps=0.5, min_samples=5)

        self.labels: Optional[NDArray] = None

    def _read_csv(self, file: Path) -> pd.DataFrame:
        """
        Reads a CSV file and returns a DataFrame.

        Args:
            file (Path): Path to the CSV file.

        Returns:
            pd.DataFrame: DataFrame containing the data from the CSV file.
        """
        print(f'Reading "{file.name}"')
        return pd.read_csv(file, usecols=['time_seconds', *self.data_cols])

    def _load_data(self) -> pd.DataFrame:
        """
        Loads data from all CSV files matching the scenario name in the logs directory.

        Returns:
            pd.DataFrame: Concatenated DataFrame containing data from all matched files.
        """
        data: pd.DataFrame = pd.concat([
            self._read_csv(f) for f in Path(self.logs_dir).glob(f'*{self.scenario_name}*')
        ], ignore_index=True)
        print(f'Read {len(data)} samples.')
        return data

    def _normalize_data(self) -> NDArray:
        """
        Normalizes the data using StandardScaler.

        Returns:
            NDArray: Normalized data.
        """
        scaler: StandardScaler = StandardScaler()
        return scaler.fit_transform(self.data[self.data_cols])

    def _plot_clusters(self, X: NDArray, n_clusters: int) -> None:
        """
        Plots clusters in a scatter plot.

        Args:
            X (NDArray): Data to plot.
            n_clusters (int): Number of clusters.
        """
        unique_labels = set(self.labels)
        core_samples_mask = np.zeros_like(self.labels, dtype=bool)
        core_samples_mask[self.dbscan.core_sample_indices_] = True
        colors = [plt.cm.Spectral(each) for each in np.linspace(0, 1, len(unique_labels))]

        for k, color in zip(unique_labels, colors):
            if k == -1:
                # Black used for noise.
                color = [0, 0, 0, 1]
                label = 'Noise'
            else:
                label = f'Cluster {k}'

            class_member_mask = self.labels == k
            xy = X[class_member_mask]
            plt.plot(
                xy[:, 0], xy[:, 1],
                marker='o',
                markerfacecolor=tuple(color),
                markeredgecolor='k',
                markersize=14,
                label=label
            )
            xy = X[class_member_mask & ~core_samples_mask]
            plt.plot(
                xy[:, 0], xy[:, 1],
                marker='o',
                markerfacecolor=tuple(color),
                markeredgecolor='k',
                markersize=6
            )

        plt.title(f'DBSCAN estimated number of clusters: {n_clusters}')
        plt.legend()
        plt.show()

    def cluster_DBSCAN(self, use_PCA: bool, plot_results: bool = True) -> None:
        """
        Clusters the data using DBSCAN and optionally applies PCA for dimensionality reduction.

        Args:
            use_PCA (bool): Whether to use PCA for dimensionality reduction.
            plot_results (bool): Whether to plot the clustering results.
        """
        norm_data: NDArray = self._normalize_data()
        if use_PCA:
            pca = PCA(n_components=2)
            norm_data = pca.fit_transform(norm_data)
        self.labels = self.dbscan.fit_predict(norm_data)

        n_clusters = len(set(self.labels)) - (1 if -1 in self.labels else 0)
        n_noise = list(self.labels).count(-1)
        print('\nDBSCAN:')
        print(f'PCA components: {pca.components_.shape[0] if use_PCA else "N/A"}')
        print(f'Estimated number of clusters: {n_clusters}')
        print(f'Estimated number of noise points: {n_noise}\n')

        if plot_results:
            self._plot_clusters(norm_data, n_clusters)

    def summarize_clustering(self) -> None:
        """
        Summarizes the clustering results with a cluster summary and box plots.
        """
        self.data['cluster'] = self.labels

        # drop noisy data
        self.data.loc[self.data['cluster'] == -1, 'cluster'] = np.nan
        self.data = self.data.dropna(subset=['cluster'])
        self.data['cluster'] = self.data['cluster'].astype(np.int64)

        cluster_summary = self.data.groupby('cluster')[self.data_cols].agg(['mean', 'var'])

        print('\nCluster Summary:')
        print(cluster_summary, end='\n\n')

        n_data_cols: int = len(self.data_cols)
        fig, axes = plt.subplots(1, n_data_cols, figsize=(n_data_cols * 4, 6))

        for i, column in enumerate(self.data_cols):
            ax = axes[i]
            self.data.boxplot(
                column=column, by='cluster',
                ax=axes[i],
                vert=True,
                grid=False,
                patch_artist=True,
                boxprops={'facecolor': 'lightblue'}
            )

            ax.set_title(f'Box plot of {column} by cluster')
            ax.set_xlabel('Cluster')
            ax.set_ylabel(column)
            ax.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.7)

        fig.suptitle(f'Clustering for scenario "{self.scenario_name}"')
        fig.tight_layout()
        plt.show()


def main():
    clu = DataClusterer(args.scenario, args.logs_dir, args.data_cols)
    if args.algorithm == 'dbscan':
        clu.cluster_DBSCAN(args.pca, args.plot_clustering)
        clu.summarize_clustering()
    elif args.algorithm == 'kmeans++':
        raise NotImplementedError('kmeans++ unavailable')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        'scenario',
        type=str,
        choices=[s.name for s in Scenario],
        help='Scenario name'
    )
    parser.add_argument(
        'algorithm',
        type=str,
        choices=['dbscan', 'kmeans++'],
        help='Clustering algorithm to use'
    )
    parser.add_argument(
        '--pca',
        action='store_true',
        help='Do PCA filtering before clustering'
    )
    parser.add_argument(
        '--plot_clustering',
        action='store_true',
        help='Display data clusters in a scatter plot'
    )
    parser.add_argument(
        '-d', '--data_cols',
        type=str,
        choices=['speed', 'throttle', 'brake', 'steer', 'heart_rate', 'breathing_rate'],
        nargs='*',
        help='Data to include in clustering (default: speed heart_rate breathing_rate)'
    )
    parser.add_argument(
        '--logs_dir',
        metavar='DIR',
        type=str,
        default='src/logs/filtered',
        help='Filter all logs from this directory (default: %(default)s)'
    )
    args = parser.parse_args()
    main()
