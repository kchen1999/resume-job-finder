import logging
import httpx
import os
from dotenv import load_dotenv

if os.environ.get("FLY_REGION") is None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_node_backend_url():
    return os.getenv("NODE_BACKEND_URL", "http://localhost:3000/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def send_page_jobs_to_node(jobs):
    url = get_node_backend_url()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(
                f"{url}/jobs/page-batch",
                json={"jobs": jobs}
            )
            response.raise_for_status()
            logging.info("Successfully sent jobs to Node backend")
    except httpx.HTTPStatusError as exc:
        error_msg = f"Failed to insert jobs: {exc.response.status_code} - {exc.response.text}"
        logging.error(error_msg)
        raise RuntimeError(error_msg) from exc
    
async def send_scrape_summary_to_node(summary: dict):
    url = get_node_backend_url()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(
                f"{url}/jobs/scrape-summary",
                json=summary
            )
            response.raise_for_status()
            logging.info("Successfully sent scrape summary to Node backend")
    except httpx.HTTPStatusError as exc:
        error_msg = f"Failed to send scrape summary: {exc.response.status_code} - {exc.response.text}"
        logging.error(error_msg)
    except Exception as exc:
        logging.error(f"Unexpected error while sending scrape summary: {exc}")
