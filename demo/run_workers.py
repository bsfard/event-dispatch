import logging
import time

from demo.workers import Worker1, WorkerEvent, Worker2, Worker3
from eventdispatch import post_event

LOG_LEVEL = logging.INFO


def set_up_logger():
    formatter = logging.Formatter('[%(asctime)s - %(levelname)s - %(name)s] %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)
    logging.getLogger().setLevel(LOG_LEVEL)


set_up_logger()

Worker1()
Worker2()
Worker3()

# Generate initial event to kick things off.
post_event(WorkerEvent.APP_STARTED)

# Give demo workers time to finish.
time.sleep(6)
