import os
import sys
import re
from datetime import timedelta
import win32service
import win32serviceutil
import win32event
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import argparse
import winreg
import servicemanager
import time
from main import main

exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
config_path = os.path.join(exe_dir, "DataFlowsConfig.xml")

def setup_service_logger():
    """
    Sets up a dedicated logger for service_runner.py.
    """
    log_file = os.path.join(exe_dir, "service.log")

    logger = logging.getLogger("service_logger")  # Use a named logger
    logger.setLevel(logging.DEBUG)

    # File handler for service.log
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Add the handler if not already added
    if not logger.handlers:
        logger.addHandler(file_handler)

    # Disable propagation to the root logger
    logger.propagate = False

    logger.info("Service logger initialized.")
    return logger

# Initialize the service logger
logger = setup_service_logger()

def manage_service(action):
    if action in ["install", "remove", "start", "stop", "restart"]:
        logger.info(f"Service action: {action}")
        win32serviceutil.HandleCommandLine(PythonWindowsService)
    else:
        print("Invalid service action. Use install, remove, start, stop, or restart.")

def increase_service_timeout(timeout=60000):  # Increase timeout to 60 seconds
    try:
        registry_path = r"SYSTEM\\CurrentControlSet\\Control"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ServicesPipeTimeout", 0, winreg.REG_DWORD, timeout)
        logger.info(f"Service timeout increased to {timeout} ms.")
    except PermissionError:
        logger.error("Failed to update service timeout: Access denied (PermissionError).")
    except Exception as e:
        logger.error(f"Failed to update service timeout: {e}")

@staticmethod
def get_main_script_path():
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Resolved base path for main.py: {base_path}")
    return os.path.join(base_path, "main.py")

def execute_main_script(provide_credentials=False):
    """Execute the main function from main.py."""
    try:
        start_time = datetime.now()
        main(provide_credentials)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Execution completed successfully.")
        logger.info(f"Time taken: {duration:.2f} seconds.")
    except Exception as e:
        logger.error(f"Error executing main function: {e}")
        
class PythonWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BigFixDataFlowAdapter"
    _svc_display_name_ = "BigFix DataFlow Adapter"
    _svc_description_ = "Runs the BigFix-SX Adapter application as a service."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.schedule = None
        self.next_run_time = None

    def load_schedule_from_config(self):
        try:
            tree = ET.parse(config_path)
            root = tree.getroot()
            schedule = root.find(".//setting[@key='SCHEDULE']").get("value")
            logger.info(f"Loaded schedule from config: {schedule}")
            return schedule
        except Exception as e:
            logger.error(f"Error loading schedule from config: {e}")
            return None

    def parse_iso8601_duration(self):
        """
        Parses an ISO 8601 duration string (e.g., 'PT15M', 'P1D', 'PT1H30M') and returns a timedelta object.
        
        Args:
            duration_str (str): ISO 8601 duration string.

        Returns:
            timedelta: Parsed duration as a timedelta object.
        """
        # Define regex pattern for ISO 8601 duration
        pattern = (
            r"P"                      # Duration starts with 'P'
            r"(?:(\d+)D)?"            # Days
            r"(?:T"                   # Time part starts with 'T'
            r"(?:(\d+)H)?"            # Hours
            r"(?:(\d+)M)?"            # Minutes
            r"(?:(\d+)S)?"            # Seconds
            r")?"                     # Time part is optional
        )
        
        match = re.fullmatch(pattern, self.schedule)
        if not match:
            raise ValueError(f"Invalid ISO 8601 duration format: {self.schedule}")
        
        # Extract duration components from regex groups
        days = int(match.group(1)) if match.group(1) else 0
        hours = int(match.group(2)) if match.group(2) else 0
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = int(match.group(4)) if match.group(4) else 0
        
        # Convert to timedelta
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def calculate_next_run_time(self):
        """Calculate the next scheduled run time based on the ISO 8601 schedule."""
        try:
            if self.schedule.lower() == "now":
                return datetime.now()
            else:
                duration = self.parse_iso8601_duration()
                return datetime.now() + duration
        except Exception as e:
            logger.error(f"Invalid schedule format: {self.schedule}. Error: {e}")
            return None

    def SvcDoRun(self):
        logger.info("Service is starting.")
        self.schedule = self.load_schedule_from_config()

        if not self.schedule:
            logger.error("No valid schedule found. Exiting.")
            return
        try:
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            logger.info("Reported SERVICE_START_PENDING.")
            # Simulate long initialization with periodic updates
            for i in range(10):  # Simulating a 10-second initialization with periodic updates
                logger.info(f"Initialization step {i + 1}/10 in progress...")
                time.sleep(1)  # Simulate work
                self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            logger.info("Service is now running.")
            self.next_run_time = self.calculate_next_run_time()
            execute_main_script()  # Execute the script on service start
            self.next_run_time = self.calculate_next_run_time()
            logger.info(f"Next scheduled run: {self.next_run_time}")

            while True:
                result = win32event.WaitForSingleObject(self.hWaitStop, 1000)
                if result == win32event.WAIT_OBJECT_0:
                    logger.info("Service stop signal received.")
                    break

                if datetime.now() >= self.next_run_time:
                    logger.info("Scheduled run time reached. Executing main.py.")
                    execute_main_script()
                    self.next_run_time = self.calculate_next_run_time()
                    logger.info(f"Next scheduled run: {self.next_run_time}")
        except Exception as e:
            logger.error(f"Error in SvcDoRun: {e}")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcStop(self):
        logger.info("Service is stopping.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="BigFix Adapter Service Manager")
        parser.add_argument("--providecredentials", action="store_true", help="Provide API Credentials")
        parser.add_argument("--init", action="store_true", help="Initialize Schema")
        parser.add_argument("--run", action="store_true", help="Run main.py directly")
        parser.add_argument("--provideproxycredentials", action="store_true", help="Provide Proxy Credentials"),
        parser.add_argument("--reset", action="store_true", help="Reset the CMDB hash in the XML config"),
        parser.add_argument("action", nargs="?", choices=["install", "remove", "start", "stop", "restart"],
                        help="Service control actions (install, remove, start, stop, restart)", default=None)
        args = parser.parse_args()

        try:
            if args.providecredentials:
                logger.info("API credentials management initiated.")
                main(provide_credentials=True)
                logger.info("API credentials provided successfully. Initiating authentication process.")
            elif args.provideproxycredentials:
                logger.info("Proxy credentials management initiated.")
                main(provide_proxy_credentials=True)
                logger.info("Proxy credentials provided successfully. Initiating authentication process.")
            elif args.reset:
                logger.info("Dataflow reset initiated.")
                main(reset=True)
                logger.info("Dataflow reset successfully.")
            elif args.init:
                logger.info("Schema initialization initiated.")
                main(init=True)
                logger.info("Schema initialization completed.")
            elif args.run:
                logger.info("Dataflow job triggered on demand. Pipeline execution initiated.")
                execute_main_script()
            elif args.action:
                logger.info(f"Service action initiated: {args.action}")
                try:
                    win32serviceutil.HandleCommandLine(PythonWindowsService)
                    logger.info(f"Service action '{args.action}' completed successfully.")
                except Exception as e:
                    logger.error(f"Error while performing service action '{args.action}': {e}")
            else:
                print("No valid arguments provided. Use --help for options.")
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}")
    else:
        # Called by Windows Service, initialize and start the service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PythonWindowsService)
        servicemanager.StartServiceCtrlDispatcher()