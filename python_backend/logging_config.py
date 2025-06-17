import logging
import os
import sys

from dotenv import load_dotenv

if os.environ.get("ENV") is None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

def setup_logging():
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
