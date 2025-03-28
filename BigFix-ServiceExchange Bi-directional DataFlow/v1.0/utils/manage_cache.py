import os
import json
import gzip
from logger import logger

class CacheManager:
    def __init__(self, filename):
        self.filename = filename
        self.cache_data = self._load_cache_file()

    def _load_cache_file(self):
        if os.path.exists(self.filename):
            try:
                with gzip.open(self.filename, "rt", encoding="utf-8") as file:
                    logger.info(f"Loading cache from file: {self.filename}")
                    data = json.load(file)
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
        try:
            with gzip.open(self.filename, "wt", encoding="utf-8") as file:
                json.dump(self.cache_data, file, ensure_ascii=False, indent=None, separators=(",", ":"))
                logger.info("Cache file saved successfully.")
        except Exception as e:
            logger.error(f"Error saving cache file: {e}")

    def save_to_cache(self, key, data):
        self.cache_data[key] = data
        self._save_cache_file()
        logger.info(f"Data cached successfully under key '{key}'.")

    def load_from_cache(self, key):
        if key in self.cache_data:
            logger.info(f"Data loaded successfully for key '{key}'.")
            return self.cache_data[key]
        else:
            logger.warning(f"Key '{key}' not found in cache.")
            return None

    def clear_cache(self, key=None):
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