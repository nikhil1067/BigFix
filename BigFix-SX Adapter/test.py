import logging
import os
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

class LogConfigManager:
    def __init__(self, retention_days=10, log_level="INFO", config_file_path=r"C:\\BigFix-SX Adapter\\config.xml"):
        self.retention_days = retention_days
        self.log_level = log_level.upper()
        self.config_file_path = config_file_path
        self.config = self._load_xml_config()
        self.log_folder = "logs"
        self._ensure_log_folder()
        self._apply_retention_policy()
        self._configure_logging()

    def _load_xml_config(self):
        try:
            tree = ET.parse(self.config_file_path)
            root = tree.getroot()
            config = {}

            # Extract logging level and file
            logging_element = root.find("logging")
            if logging_element is not None:
                config["logging_level"] = logging_element.find("level").text if logging_element.find("level") is not None else "INFO"

            # Extract settings
            settings_element = root.find("settings")
            if settings_element is not None:
                for setting in settings_element.findall("setting"):
                    key = setting.get("key")
                    value = setting.get("value")
                    if key and value:
                        config[key] = value

            return config
        except Exception as e:
            print(f"Error loading XML configuration: {e}")
            return {}

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
        logging.basicConfig(
            filename=log_file,
            level=getattr(logging, self.config.get("logging_level", self.log_level)),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger()
        self.logger.info("Logging initialized")

    def get_logger(self):
        return self.logger

# Example usage
if __name__ == "__main__":
    log_manager = LogConfigManager(retention_days=7, log_level="DEBUG")
    logger = log_manager.get_logger()
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
