import logging
import os
from datetime import datetime, timedelta
from utils.config_loader import load_config

class LogConfigManager:
    def __init__(self, retention_days=10, log_level="INFO", log_folder="logs"):
        self.retention_days = retention_days
        self.log_level = log_level.upper()
        self.log_folder = log_folder  # Allow specifying a custom log folder
        self.logger_name = "main_logger"  # Use a named logger
        self._ensure_log_folder()
        self._apply_retention_policy()
        self._configure_logging()

    def _ensure_log_folder(self):
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

    def _apply_retention_policy(self):
        retention_cutoff = datetime.now() - timedelta(days=self.retention_days)
        for log_file in os.listdir(self.log_folder):
            log_path = os.path.join(self.log_folder, log_file)
            if os.path.isfile(log_path):
                file_creation_time = datetime.fromtimestamp(os.path.getctime(log_path))
                if file_creation_time < retention_cutoff:
                    os.remove(log_path)
                    print(f"Deleted old log file: {log_path}")

    def _configure_logging(self):
        log_file = os.path.join(self.log_folder, f"{datetime.now().strftime('%Y%m%d')}.log")
        self.logger = logging.getLogger(self.logger_name)  # Use a specific logger name
        self.logger.setLevel(getattr(logging, self.log_level))

        # Configure the file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, self.log_level))
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        # Add the handler to the logger
        if not self.logger.handlers:  # Avoid adding multiple handlers if logger is re-initialized
            self.logger.addHandler(file_handler)

        # Disable propagation to the root logger
        self.logger.propagate = False

        self.logger.info("Logging initialized")

    def get_logger(self):
        return self.logger


# Initialize the logger at the module level
config_path = r"C:\BigFix-SX Adapter\config.xml"
config = load_config(config_path)
SETTINGS = config["dataflowconfig"]["settings"]["setting"]
if isinstance(SETTINGS, dict):
    settings = [SETTINGS]
else:
    settings = SETTINGS

# Retrieve settings for logging
retention_days = int(next(item["value"] for item in settings if item["key"] == "LOG_RETENTION"))
log_level = next(item["value"] for item in settings if item["key"] == "LOG_LEVEL")
log_folder = r"C:\BigFix-SX Adapter\logs"  # Explicit log folder for main.py logs

# Initialize the LogConfigManager
log_manager = LogConfigManager(retention_days, log_level, log_folder)
logger = log_manager.get_logger()