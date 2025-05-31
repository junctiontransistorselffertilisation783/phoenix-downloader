import logging

from app.config import Get_log_file_path


def setup_logging():
    root_logger = logging.getLogger()
    log_file_path = Get_log_file_path()
    for handler in root_logger.handlers:
        if getattr(handler, "baseFilename", "") == log_file_path:
            return

    root_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root_logger.addHandler(file_handler)
