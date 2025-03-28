import logging
import os
from datetime import datetime, timedelta
import sys
import xml.etree.ElementTree as ET

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
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle (PyInstaller)
    base_dir = os.path.dirname(sys.executable)
else:
    # If run as a script
    base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "DataFlowsConfig.xml")
tree = ET.parse(config_path)
root = tree.getroot()
SETTINGS = {setting.get('key'): setting.get('value') for setting in root.findall(".//settings/setting")}

# Retrieve settings for logging
retention_days = int(SETTINGS["log_retention"])
log_level = SETTINGS["log_level"]
log_folder = os.path.join(base_dir, "logs")  # Explicit log folder for main.py logs

# Initialize the LogConfigManager
log_manager = LogConfigManager(retention_days, log_level, log_folder)
logger = log_manager.get_logger()