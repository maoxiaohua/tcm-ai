"""Central logging setup for staged architecture migration."""

import logging
import sys
from pathlib import Path
from typing import Optional, Union

from app.core.settings import get_path


LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_app_logging(
    logger_name: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure logging with file + stdout handlers.

    Behavior is intentionally compatible with the existing project setup:
    if file handler fails, stdout logging still works.
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    log_path: Path
    if log_file is None:
        log_path = get_path("logs_dir") / "tcm_api.log"
    else:
        log_path = Path(log_file)

    try:
        handlers.insert(0, logging.FileHandler(str(log_path), encoding="utf-8"))
    except OSError as file_error:
        print(f"Log file handler init failed: {file_error}. Using stdout handler only.")

    logging.basicConfig(level=level, format=LOG_FORMAT, handlers=handlers)
    return logging.getLogger(logger_name) if logger_name else logging.getLogger(__name__)

