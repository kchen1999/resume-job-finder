import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if os.environ.get("ENV") is None:
    file_path = Path(__file__).parent.parent / ".env"
    load_dotenv(file_path)

def setup_logging() -> None:
    env = os.getenv("ENV")
    log_level = logging.DEBUG if env == "development" else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger().info("Logging initialized at %s level", logging.getLevelName(log_level))
