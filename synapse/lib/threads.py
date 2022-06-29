import logging
import threading

logger = logging.getLogger(__name__)

def current():
    return threading.current_thread()

def iden():
    return current().ident
