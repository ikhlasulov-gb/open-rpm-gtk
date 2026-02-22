import logging
import sys

LOG_FMT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
DATE_FMT = '%Y-%m-%d %H:%M:%S'

_root_logger = None


def get_logger(name: str = 'openrpm') -> logging.Logger:
    global _root_logger
    if _root_logger is None:
        _root_logger = logging.getLogger('openrpm')
        _root_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(LOG_FMT, DATE_FMT))
        _root_logger.addHandler(handler)

    return _root_logger.getChild(name.split('.')[-1]) if '.' in name else _root_logger


log = get_logger()
