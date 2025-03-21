import time
from datetime import datetime, timedelta
import logging
import re

class Scheduler:
    def __init__(self, schedule):
        """
        Initialize the scheduler with the schedule value.
        :param schedule: The schedule value (e.g., 'now', 'P30M', 'P1D').
        """
        self.schedule = schedule

    def parse_schedule(self):
        """
        Parse the schedule value.
        - If 'now', return 'now'.
        - If ISO 8601 format (e.g., P2H, P30M), return interval in seconds.
        """
        logging.info(f"Parsing schedule: {self.schedule}")
        if self.schedule.lower() == "now":
            logging.info("Schedule type is 'now'. Task will run immediately and exit.")
            return "now"

        # Parse ISO 8601 duration (e.g., P30M, P2H, P1D)
        pattern = r"P(?:(\d+)D)?(?:T)?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, self.schedule)
        if not match:
            logging.error(f"Invalid schedule format: {self.schedule}")
            raise ValueError(f"Invalid schedule format: {self.schedule}")

        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)
        seconds = int(match.group(4) or 0)
        logging.info(f"Parsed schedule - Days: {days}, Hours: {hours}, Minutes: {minutes}, Seconds: {seconds}")

        total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
        logging.info(f"Total interval in seconds: {total_seconds}")
        return total_seconds

    def run(self, task_function):
        """
        Run the task based on the parsed schedule.
        :param task_function: The function to execute.
        """
        try:
            schedule_value = self.parse_schedule()

            if schedule_value == "now":
                logging.info("Executing task as per 'now' schedule.")
                try:
                    task_function()
                    logging.info("Task marked as completed after execution.")
                except SystemExit:
                    logging.info("Task exited using exit(). Marked as completed.")
                except Exception as e:
                    logging.error(f"Task encountered an error: {e}")
            else:
                logging.info(f"Task will execute every {schedule_value} seconds.")

                # Schedule subsequent executions
                while True:
                    # Execute the task
                    start_time = time.time()  # Record the task start time
                    logging.info("Starting task execution.")
                    try:
                        task_function()
                        logging.info("Task execution completed.")
                    except SystemExit:
                        logging.info("Task exited using exit(). Marked as completed.")
                    except Exception as e:
                        logging.error(f"Task encountered an error: {e}")

                    # Calculate the next execution time
                    end_time = time.time()  # Record the task end time
                    elapsed_time = end_time - start_time
                    logging.info(f"DataFlow execution completed in {elapsed_time:.2f} seconds.")
                    logging.info(f"Sleeping for {schedule_value:.2f} seconds before next execution.")
                    current_time = datetime.now()
                    next_execution_time = current_time + timedelta(seconds=schedule_value)
                    logging.info(f"Next execution time: {next_execution_time}.")
                    time.sleep(schedule_value)
        except Exception as e:
            logging.error(f"Scheduler encountered an error: {e}")
            raise