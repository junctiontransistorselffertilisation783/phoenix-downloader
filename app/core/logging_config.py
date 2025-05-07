import logging

from app.config import Get_log_file_path


def setup_logging():
    root_logger = logging.getLogger()
    if len(root_logger.handlers) > 0:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=Get_log_file_path(),
        filemode="a",
        encoding="utf-8",
    )
