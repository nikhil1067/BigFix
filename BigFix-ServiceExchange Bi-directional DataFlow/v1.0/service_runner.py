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
from threading import Thread
from main import main

base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "DataFlowsConfig.xml")

def setup_service_logger():
    log_file = os.path.join(base_dir, "service.log")
    logger = logging.getLogger("service_logger")
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
    logger.propagate = False
    logger.info("Service logger initialized.")
    return logger

logger = setup_service_logger()

def manage_service(action):
    if action in ["install", "remove", "start", "stop", "restart"]:
        logger.info(f"Service action: {action}")
        win32serviceutil.HandleCommandLine(PythonWindowsService)
    else:
        print("Invalid service action. Use install, remove, start, stop, or restart.")

def increase_service_timeout(timeout=60000):
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

def execute_main_script(dataflow_filter=None):
    try:
        start_time = datetime.now()
        main(dataflow_filter=dataflow_filter)
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
        self.running_threads = []

    def run_dataflow_in_thread(self, dataflow_name):
        def task():
            try:
                logger.info(f"Started dataflow in thread: {dataflow_name}")
                execute_main_script(dataflow_filter=dataflow_name)
            except Exception as e:
                logger.error(f"Dataflow '{dataflow_name}' failed: {e}")
        thread = Thread(target=task, name=f"Dataflow-{dataflow_name}", daemon=True)
        thread.start()
        self.running_threads.append(thread)

    def load_schedules_from_config(self):
        try:
            tree = ET.parse(config_path)
            root = tree.getroot()
            dataflows = root.findall(".//dataflows/dataflow")
            schedules = {df.get("displayname"): df.get("schedule") for df in dataflows}
            logger.info(f"Loaded per-dataflow schedules: {schedules}")
            return schedules
        except Exception as e:
            logger.error(f"Error loading dataflow schedules: {e}")
            return {}

    def parse_iso8601_duration(self, duration_str):
        pattern = (
            r"P"
            r"(?:(\d+)D)?"
            r"(?:T"
            r"(?:(\d+)H)?"
            r"(?:(\d+)M)?"
            r"(?:(\d+)S)?"
            r")?"
        )
        match = re.fullmatch(pattern, duration_str)
        if not match:
            raise ValueError(f"Invalid ISO 8601 duration format: {self.schedule}")
        days = int(match.group(1)) if match.group(1) else 0
        hours = int(match.group(2)) if match.group(2) else 0
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = int(match.group(4)) if match.group(4) else 0
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def calculate_next_run_time(self, schedule):
        try:
            if schedule.lower() == "now":
                return datetime.now()
            else:
                duration = self.parse_iso8601_duration(schedule)
                return datetime.now() + duration
        except Exception as e:
            logger.error(f"Invalid schedule format: {schedule}. Error: {e}")
            return None

    def SvcDoRun(self):
        try:
            logger.info(">>> Entered SvcDoRun <<<")
            self.dataflow_schedules = self.load_schedules_from_config()
            if not self.dataflow_schedules:
                logger.error("No valid dataflow schedules found. Exiting.")
                return

            self.schedule = next(iter(self.dataflow_schedules.values()))
            logger.info(f"Default schedule set: {self.schedule}")

            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            logger.info("Reported SERVICE_START_PENDING.")

            for i in range(3):
                logger.info(f"Initialization step {i+1}/3...")
                time.sleep(1)
                self.ReportServiceStatus(win32service.SERVICE_START_PENDING)

            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            logger.info("Service is now running.")

            self.next_run_times = {
                name: self.calculate_next_run_time(schedule)
                for name, schedule in self.dataflow_schedules.items()
            }

            formatted_times = {
                name: dt.strftime("%Y-%m-%d %H:%M:%S") for name, dt in self.next_run_times.items()
            }
            logger.info(f"Scheduled times: {formatted_times}")
            execute_main_script()

            while True:
                result = win32event.WaitForSingleObject(self.hWaitStop, 1000)
                if result == win32event.WAIT_OBJECT_0:
                    logger.info("Stop signal received.")
                    break

                now = datetime.now()
                for dataflow_name, next_run in self.next_run_times.items():
                    if now >= next_run:
                        logger.info(f"Starting dataflow thread: {dataflow_name}")
                        self.run_dataflow_in_thread(dataflow_name)
                        next_time = self.calculate_next_run_time(self.dataflow_schedules[dataflow_name])
                        self.next_run_times[dataflow_name] = next_time
                        logger.info(f"Next scheduled time for '{dataflow_name}': {next_time.strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            logger.error(f"Fatal error in SvcDoRun: {e}")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcStop(self):
        logger.info("Service is stopping.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        logger.info("Waiting for running threads to complete...")
        for thread in self.running_threads:
            if thread.is_alive():
                thread.join()
        logger.info("All threads completed.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="BigFix Adapter Service Manager")
        parser.add_argument("--providecredentials", action="store_true", help="Provide API Credentials")
        parser.add_argument("--init", action="store_true", help="Initialize Schema")
        parser.add_argument("--run", action="store_true", help="Run main.py directly")
        parser.add_argument("--provideproxycredentials", action="store_true", help="Provide Proxy Credentials")
        parser.add_argument("--reset", action="store_true", help="Reset the CMDB hash in the XML config")
        parser.add_argument("--dataflow", type=str, help="Run a specific dataflow by display name")
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
                execute_main_script(dataflow_filter=args.dataflow)
            elif args.action:
                logger.info(f"Service action initiated: {args.action}")
                win32serviceutil.HandleCommandLine(PythonWindowsService)
            else:
                print("No valid arguments provided. Use --help for options.")
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}")
    else:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PythonWindowsService)
        servicemanager.StartServiceCtrlDispatcher()