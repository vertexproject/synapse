import logging
import threading

logger = logging.getLogger(__name__)

def current():
    return threading.currentThread()

def iden():
    return threading.currentThread().ident
