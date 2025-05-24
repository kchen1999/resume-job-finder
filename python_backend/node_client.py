import logging
import httpx
import os

NODE_BACKEND_URL = os.getenv("NODE_BACKEND_URL", "http://localhost:3000")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def send_page_jobs_to_node(jobs):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(
                f"{NODE_BACKEND_URL}/api/jobs/page-batch",
                json={"jobs": jobs}
            )
            response.raise_for_status()
            logging.info("Successfully sent jobs to Node backend")
    except httpx.HTTPStatusError as exc:
        error_msg = f"Failed to insert jobs: {exc.response.status_code} - {exc.response.text}"
        logging.error(error_msg)
        raise RuntimeError(error_msg) from exc
