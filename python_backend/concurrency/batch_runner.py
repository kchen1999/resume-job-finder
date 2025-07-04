import asyncio

import sentry_sdk
from concurrency.job_runner import process_job_with_semaphore
from utils.constants import SKIPPED, SUCCESS, TERMINATE
from utils.context import ScrapeContext
from utils.utils import backoff_if_high_cpu, pause_briefly


def aggregate_job_results(job_results: list) -> tuple:
    final_jobs = []
    early_termination = False
    n_skipped = 0
    n_terminated = 0

    for job_result in job_results:
        status = job_result["status"]
        if status == TERMINATE:
            early_termination = True
            n_terminated += 1
        elif status == SUCCESS:
            final_jobs.append(job_result["job"])
        elif status == SKIPPED:
            n_skipped += 1

    return final_jobs, early_termination, n_skipped, n_terminated

async def process_jobs_concurrently(job_urls: list, ctx: ScrapeContext, page_num: int) -> tuple:
    tasks = []

    for idx, job_url in enumerate(job_urls):
        await backoff_if_high_cpu()
        task = asyncio.create_task(
            process_job_with_semaphore(job_url, idx, ctx)
        )
        tasks.append(task)
        await pause_briefly(0.05, 0.25)

    job_results = await asyncio.gather(*tasks)

    final_jobs, early_termination, n_skipped, n_terminated = aggregate_job_results(job_results)
    n_success = len(final_jobs)

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "process_jobs_concurrently")
        scope.set_tag("page_num", page_num)
        scope.set_extra("total_jobs_attempted", len(job_results))
        scope.set_extra("jobs_successful", n_success)
        scope.set_extra("jobs_skipped", n_skipped)
        scope.set_extra("jobs_terminated_early", n_terminated)
        scope.set_extra("early_termination", early_termination)
        sentry_sdk.capture_message("Scraping job batch completed", level="info")

    return final_jobs, early_termination
