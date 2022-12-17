import logging
import time

from demo.workers import Worker1, Worker2, WorkerEvent
from eventdispatch import post_event

logging.basicConfig(level=logging.INFO)

Worker1()
Worker2()

# Generate initial event to kick things off.
post_event(WorkerEvent.APP_STARTED)

time.sleep(6)
