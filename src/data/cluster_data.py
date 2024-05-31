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
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
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

    def _plot_clusters(self, X: NDArray, n_clusters: int, is_dbscan: bool) -> None:
        """
        Plots clusters in a scatter plot.

        Args:
            X (NDArray): Data to plot.
            n_clusters (int): Number of clusters.
        """
        unique_labels = set(self.labels)
        if is_dbscan:
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
            if is_dbscan:
                xy = X[class_member_mask & ~core_samples_mask]
                plt.plot(
                    xy[:, 0], xy[:, 1],
                    marker='o',
                    markerfacecolor=tuple(color),
                    markeredgecolor='k',
                    markersize=6
                )

        algo_name = 'DBSCAN' if is_dbscan else 'KMeans++'
        plt.title(f'{algo_name} estimated number of clusters: {n_clusters}')
        plt.legend()
        plt.show()

    def cluster_DBSCAN(self, n_pca_comp: Optional[int], plot_results: bool = True) -> None:
        """
        Clusters the data using DBSCAN and optionally applies PCA for dimensionality reduction.

        Args:
            use_PCA (bool): Whether to use PCA for dimensionality reduction.
            plot_results (bool): Whether to plot the clustering results.
        """
        norm_data: NDArray = self._normalize_data()
        use_pca: bool = isinstance(n_pca_comp, int) and n_pca_comp > 0
        if use_pca:
            pca = PCA(n_components=n_pca_comp)
            norm_data = pca.fit_transform(norm_data)
        self.labels = self.dbscan.fit_predict(norm_data)

        n_clusters = len(set(self.labels)) - (1 if -1 in self.labels else 0)
        n_noise = list(self.labels).count(-1)
        print('\nDBSCAN:')
        print(f'PCA components: {pca.components_.shape[0] if use_pca else "N/A"}')
        print(f'Estimated number of clusters: {n_clusters}')
        print(f'Estimated number of noise points: {n_noise}\n')

        if plot_results:
            self._plot_clusters(norm_data, n_clusters, is_dbscan=True)

    def cluster_kmeans(self, n_pca_comp: Optional[int], plot_results: bool = True) -> None:
        """
        Clusters the data with KMeans++ after finding the optimal number of clusters
        via silhouette analysis. Optionally applies PCA for dimensionality reduction.

        Args:
            use_PCA (bool): Whether to use PCA for dimensionality reduction.
            plot_results (bool): Whether to plot the clustering results.
        """
        norm_data: NDArray = self._normalize_data()
        use_pca: bool = isinstance(n_pca_comp, int) and n_pca_comp > 0
        if use_pca:
            pca = PCA(n_components=n_pca_comp)
            norm_data = pca.fit_transform(norm_data)

        range_n_clusters = list(range(2, 10))
        silhouette_avg = []
        labels = []
        print('\nKMeans++:')
        # Perform K-means clustering for each number of clusters in the range
        for n_clusters in range_n_clusters:
            print(f'performing KMeans++ with {n_clusters} clusters...', end='\t', flush=True)
            kmeans = KMeans(n_clusters=n_clusters, init='k-means++')
            cluster_labels = kmeans.fit_predict(norm_data)
            labels.append(cluster_labels)

            # Calculate silhouette score (silhouette analysis)
            cluster_score = silhouette_score(norm_data, cluster_labels)
            silhouette_avg.append(cluster_score)
            print(f'silhouette score = {cluster_score}')

        # Determine the optimal number of clusters based on silhouette score
        optimal_clusters = range_n_clusters[np.argmax(silhouette_avg)]
        self.labels = labels[np.argmax(silhouette_avg)]
        print(f'PCA components: {pca.components_.shape[0] if use_pca else "N/A"}')
        print(f'Optimal number of clusters (Silhouette Analysis): {optimal_clusters}')
        # KMeans++ does not differentiate noise! Importatnt distinction from DBSCAN
        print('Estimated number of noise points: N/A\n')

        if plot_results:
            self._plot_clusters(norm_data, optimal_clusters, is_dbscan=False)

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
    elif args.algorithm == 'kmeans++':
        clu.cluster_kmeans(args.pca, args.plot_clustering)
    clu.summarize_clustering()


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
        type=int,
        metavar='N_COMPONENTS',
        help='# of components for PCA, ignore to skip PCA'
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
        help='Logs directory to take data from (default: %(default)s)'
    )
    args = parser.parse_args()
    main()
