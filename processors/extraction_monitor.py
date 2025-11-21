#!/usr/bin/env python3
"""
Continuous transcript extraction monitor and auto-restarter
"""

import subprocess
import time
import logging
import os
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/extraction_monitor.log'),
        logging.StreamHandler()
    ]
)

class ExtractionMonitor:
    def __init__(self):
        self.processes = {
            'focused_mass_extraction': {
                'script': 'focused_mass_extraction.py',
                'process': None,
                'restart_count': 0,
                'last_restart': None
            },
            'mass_rss_extractor': {
                'script': 'mass_rss_transcript_extractor.py',
                'process': None,
                'restart_count': 0,
                'last_restart': None
            }
        }

        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)

    def start_process(self, process_name):
        """Start a specific extraction process"""
        config = self.processes[process_name]

        try:
            # Log output to dedicated file
            log_file = f'logs/{process_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

            with open(log_file, 'w') as f:
                config['process'] = subprocess.Popen(
                    ['python3', config['script']],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd='/home/ubuntu/dev/atlas'
                )

            config['last_restart'] = datetime.now()
            config['restart_count'] += 1

            logging.info(f"Started {process_name} (PID: {config['process'].pid}, Restart #{config['restart_count']})")
            return True

        except Exception as e:
            logging.error(f"Failed to start {process_name}: {e}")
            return False

    def check_processes(self):
        """Check if processes are still running, restart if needed"""
        for process_name, config in self.processes.items():
            if config['process'] is None:
                logging.info(f"Starting {process_name} for the first time")
                self.start_process(process_name)
                continue

            # Check if process is still running
            return_code = config['process'].poll()

            if return_code is not None:
                logging.info(f"{process_name} exited with code {return_code}")

                # Check if it exited successfully (0) or with an error
                if return_code == 0:
                    logging.info(f"{process_name} completed successfully, restarting...")
                else:
                    logging.warning(f"{process_name} failed with code {return_code}, restarting...")

                # Restart the process
                self.start_process(process_name)

                # Add delay between restarts to prevent rapid cycling
                time.sleep(30)

    def run(self):
        """Main monitoring loop"""
        logging.info("Starting extraction monitor...")

        try:
            while True:
                self.check_processes()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logging.info("Shutting down monitor...")

            # Terminate all processes
            for process_name, config in self.processes.items():
                if config['process'] and config['process'].poll() is None:
                    logging.info(f"Terminating {process_name}...")
                    config['process'].terminate()

        except Exception as e:
            logging.error(f"Monitor error: {e}")
            raise

if __name__ == "__main__":
    monitor = ExtractionMonitor()
    monitor.run()