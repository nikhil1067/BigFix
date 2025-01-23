import os
import sys
import logging
import subprocess
import win32service
import win32serviceutil
import win32event
import servicemanager
import argparse
from datetime import datetime
import time
import shutil
import winreg
 
# Define base directory for extracted files
BASE_DIR = "C:\BigFix-SX Adapter"
 
# Ensure the base directory exists
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)
 
def setup_logging():
    """
    Sets up logging to write to 'service.log' in the base directory and optionally to the console.
    """
    log_file = os.path.join(BASE_DIR, "service.log")
 
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
 
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logging.getLogger().addHandler(console_handler)
 
    logging.info("Logging initialized.")
 
setup_logging()
 
def get_file_path(file_name):
    """
    Returns the correct path for a file, handling both standalone and bundled modes.
    """
    if hasattr(sys, '_MEIPASS'):
        # Running as a bundled executable
        return os.path.join(sys._MEIPASS, file_name)
    else:
        # Running as a script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)
 
def copy_required_files():
    """
    Copies required files to the base directory if they are not already present.
    """
    required_files = ['main.py', 'config.xml', 'utils', 'credentials_manager',
                      'bigfix_data_operations', 'sx_data_operations', 'mailbox_records', 'data_correlation']
    for file_name in required_files:
        src_path = get_file_path(file_name)
        dest_path = os.path.join(BASE_DIR, file_name)
 
        try:
            if os.path.isdir(src_path):
                if not os.path.exists(dest_path):
                    shutil.copytree(src_path, dest_path)
            else:
                if not os.path.exists(dest_path):
                    shutil.copy2(src_path, dest_path)
            logging.info(f"Copied: {file_name} to {dest_path}")
        except Exception as e:
            logging.error(f"Error copying {file_name}: {e}")
 
def increase_service_timeout(timeout=300000):  # Increase timeout to 300 seconds
    try:
        registry_path = r"SYSTEM\\CurrentControlSet\\Control"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ServicesPipeTimeout", 0, winreg.REG_DWORD, timeout)
        logging.info(f"Service timeout increased to {timeout} ms.")
    except PermissionError:
        logging.error("Failed to update service timeout: Access denied (PermissionError).")
    except Exception as e:
        logging.error(f"Failed to update service timeout: {e}")
 
class PythonWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BigFixDataFlowAdapter"
    _svc_display_name_ = "BigFix DataFlow Adapter"
    _svc_description_ = "Runs the BigFix-SX Adapter application as a service."
 
    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.main_script = os.path.join(BASE_DIR, "main.py")
 
    def SvcDoRun(self):
        os.chdir(BASE_DIR)
        logging.info(f"Working directory set to: {BASE_DIR}")
 
        logging.info("Service is starting.")
        try:
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            logging.info("Reported SERVICE_START_PENDING.")
 
            # Simulate long initialization with periodic updates
            for i in range(10):  # Simulating a 10-second initialization with periodic updates
                logging.info(f"Initialization step {i + 1}/10 in progress...")
                time.sleep(1)  # Simulate work
                self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
 
            # Validate and log required files
            main_script = self.main_script
            if not os.path.exists(main_script):
                logging.error(f"Main script not found: {main_script}")
                raise FileNotFoundError(f"Main script not found: {main_script}")
            logging.info(f"Main script located: {main_script}")
 
            copy_required_files()
            logging.info("Required files copied.")
 
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            logging.info("Service is now running.")
 
            while True:
                result = win32event.WaitForSingleObject(self.hWaitStop, 1000)
                if result == win32event.WAIT_OBJECT_0:
                    logging.info("Stop signal received.")
                    break
        except Exception as e:
            logging.error(f"Error in SvcDoRun: {e}")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
 
    def SvcStop(self):
        logging.info("Service is stopping.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
 
def debug_mode():
    """
    Runs the service logic directly in debug mode without interacting with the Service Control Manager.
    """
    logging.info("Running in debug mode.")
    copy_required_files()
    main_script = os.path.join(BASE_DIR, "main.py")
 
    if not os.path.exists(main_script):
        logging.error(f"Main script not found: {main_script}")
        return
 
    try:
        if hasattr(sys, 'frozen'):
            python_executable = "python"
        else:
            python_executable = sys.executable
 
        logging.info(f"Python executable: {python_executable}")
        logging.info(f"Executing: {python_executable} {main_script} --debug")
 
        result = subprocess.run(
            [python_executable, main_script, "--debug"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
 
        logging.info(f"Main script stdout:\n{result.stdout}")
        if result.stderr:
            logging.error(f"Main script stderr:\n{result.stderr}")
    except Exception as e:
        logging.error(f"Failed to execute main script: {e}")
 
def main():
    # Check if the script is called by the Windows Service or from the shell
    if len(sys.argv) > 1:
        # Called from the command line, handle command-line arguments
        parser = argparse.ArgumentParser(description="BigFix Adapter Service Manager")
        parser.add_argument("--debug", action="store_true", help="Run the service in debug mode")
        parser.add_argument(
            "action",
            nargs="?",
            choices=["install", "remove", "start", "stop", "restart"],
            help="Service control actions (install, remove, start, stop, restart)",
            default=None,
        )
        args = parser.parse_args()
 
        try:
            if args.debug:
                # Run the service in debug mode
                debug_mode()
            elif args.action:
                # Handle service management actions (install, remove, etc.)
                increase_service_timeout()  # Ensure timeout is extended before starting
                win32serviceutil.HandleCommandLine(PythonWindowsService)
            else:
                print("No valid arguments provided. Use --help for options.")
        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
    else:
        # Called by Windows Service, initialize and start the service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PythonWindowsService)
        servicemanager.StartServiceCtrlDispatcher()

if __name__ == "__main__":
    main()