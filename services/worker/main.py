import time
import math
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def cpu_spike():
    # Simulate CPU intensive task
    for _ in range(10**7):
        math.sqrt(_)

if __name__ == "__main__":
    logging.info("Starting AIGitOps Worker...")
    while True:
        logging.info("Worker is doing background tasks...")
        # Periodically spike CPU to simulate workload
        cpu_spike()
        time.sleep(10)
