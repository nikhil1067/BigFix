import pickle
import os
from logger import logger

class CacheManager:
    def __init__(self, filename):
        """
        Initialize the CacheManager with a single cache file name.
        """
        self.filename = filename
        self.cache_data = self._load_cache_file()

    def _load_cache_file(self):
        """
        Load the entire cache file into memory, or return an empty dictionary if the file doesn't exist.
        """
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "rb") as file:
                    logger.info(f"Loading cache from file: {self.filename}")
                    data = pickle.load(file)
                    if isinstance(data, dict):
                        logger.info("Cache file loaded successfully.")
                        return data
                    else:
                        logger.error(f"Unexpected data type in cache file: {type(data)}. Expected a dictionary.")
                        return {}
            except Exception as e:
                logger.error(f"Error loading cache file: {e}")
        else:
            logger.info(f"No cache file found at {self.filename}. Starting fresh.")
        return {}

    def _save_cache_file(self):
        """
        Save the entire cache dictionary to the file.
        """
        try:
            with open(self.filename, "wb") as file:
                pickle.dump(self.cache_data, file)
                logger.info("Cache file saved successfully.")
        except Exception as e:
            logger.error(f"Error saving cache file: {e}")

    def save_to_cache(self, key, data):
        """
        Save data to the cache under the specified key.
        """
        self.cache_data[key] = data
        self._save_cache_file()
        logger.info(f"Data cached successfully under key '{key}'.")

    def load_from_cache(self, key):
        """
        Load data from the cache for the specified key.
        """
        if key in self.cache_data:
            logger.info(f"Data loaded successfully for key '{key}'.")
            return self.cache_data[key]
        else:
            logger.warning(f"Key '{key}' not found in cache.")
            return None

    def clear_cache(self, key=None):
        """
        Clear specific data from the cache or the entire cache.
        """
        if key:
            if key in self.cache_data:
                del self.cache_data[key]
                self._save_cache_file()
                logger.info(f"Cache for key '{key}' cleared successfully.")
            else:
                logger.warning(f"Key '{key}' not found in cache.")
        else:
            self.cache_data.clear()
            self._save_cache_file()
            logger.info("All cache cleared successfully.")