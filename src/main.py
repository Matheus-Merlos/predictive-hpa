import logging as logger
from datetime import datetime

def shadow_mode_controller():
    logger.info('Initializing Predictive-HPA Shadow Mode Controller...')
    while True:
        now = datetime.now()


if __name__ == '__main__':
    shadow_mode_controller()