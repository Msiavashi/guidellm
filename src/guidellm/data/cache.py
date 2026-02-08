"""Dataset filtering cache for avoiding redundant preprocessing."""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

from guidellm.logger import logger

__all__ = ["DatasetFilterCache"]


class DatasetFilterCache:
    """
    Cache for filtered datasets to avoid redundant preprocessing.
    
    Stores filtered datasets on disk with cache keys based on filter parameters,
    allowing quick reuse when the same filters are applied multiple times.
    """
    
    def __init__(self, cache_dir: Path | str | None = None):
        """
        Initialize the dataset filter cache.
        
        :param cache_dir: Directory to store cache files. 
                         Defaults to ~/.cache/guidellm/filtered_datasets
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "guidellm" / "filtered_datasets"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _compute_cache_key(
        self,
        data_sources: list[Any],
        filter_params: dict[str, Any],
        data_args: list[dict[str, Any]] | None = None,
        processor_name: str | None = None,
    ) -> str:
        """
        Compute a cache key based on data sources and filter parameters.
        
        :param data_sources: List of data source identifiers
        :param filter_params: Dictionary of filter parameters
        :param data_args: Optional per-dataset arguments
        :param processor_name: Optional tokenizer/processor name
        :return: Hash string to use as cache key
        """
        # Create a deterministic representation of inputs
        cache_dict = {
            "data_sources": [str(src) for src in data_sources],
            "filter_params": filter_params,
            "data_args": data_args or [],
            "processor": processor_name,
        }
        
        # Convert to JSON and hash
        cache_str = json.dumps(cache_dict, sort_keys=True)
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()
        
        return cache_hash
    
    def get(
        self,
        data_sources: list[Any],
        filter_params: dict[str, Any],
        data_args: list[dict[str, Any]] | None = None,
        processor_name: str | None = None,
    ) -> list[list[dict[str, Any]]] | None:
        """
        Retrieve cached filtered data if available.
        
        :param data_sources: List of data source identifiers
        :param filter_params: Dictionary of filter parameters
        :param data_args: Optional per-dataset arguments
        :param processor_name: Optional tokenizer/processor name
        :return: Cached filtered data or None if not found
        """
        cache_key = self._compute_cache_key(
            data_sources, filter_params, data_args, processor_name
        )
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            logger.debug(f"Cache miss for key {cache_key[:16]}...")
            return None
        
        try:
            with open(cache_file, "rb") as f:
                cached_data = pickle.load(f)
            logger.info(f"Loaded filtered dataset from cache ({cache_file.name})")
            return cached_data
        except Exception as e:
            logger.warning(f"Failed to load cache file {cache_file}: {e}")
            return None
    
    def set(
        self,
        data_sources: list[Any],
        filter_params: dict[str, Any],
        filtered_data: list[list[dict[str, Any]]],
        data_args: list[dict[str, Any]] | None = None,
        processor_name: str | None = None,
    ) -> None:
        """
        Store filtered data in the cache.
        
        :param data_sources: List of data source identifiers
        :param filter_params: Dictionary of filter parameters
        :param filtered_data: The filtered dataset to cache
        :param data_args: Optional per-dataset arguments
        :param processor_name: Optional tokenizer/processor name
        """
        cache_key = self._compute_cache_key(
            data_sources, filter_params, data_args, processor_name
        )
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(filtered_data, f)
            logger.info(f"Saved filtered dataset to cache ({cache_file.name})")
        except Exception as e:
            logger.warning(f"Failed to save cache file {cache_file}: {e}")
    
    def clear(self) -> None:
        """Clear all cached datasets."""
        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info(f"Cleared dataset cache at {self.cache_dir}")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
    
    def get_cache_size(self) -> int:
        """
        Get the total size of the cache in bytes.
        
        :return: Total size of all cache files in bytes
        """
        total_size = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            total_size += cache_file.stat().st_size
        return total_size
    
    def get_cache_count(self) -> int:
        """
        Get the number of cached datasets.
        
        :return: Number of cache files
        """
        return len(list(self.cache_dir.glob("*.pkl")))
