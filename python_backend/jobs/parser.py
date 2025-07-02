import json
import logging
import re

import sentry_sdk
from json_repair import repair_json
from llm.parser import parse_job_posting
from utils.utils import clean_string, normalize_keys, try_fix_missing_closing_brace

logger = logging.getLogger(__name__)

def clean_repair_parse_json(json_block: str) -> dict | None:
    try:
        if isinstance(json_block, str):
            json_block = clean_string(json_block)

        logger.debug("Attempting to repair JSON...")
        repaired_json_string = repair_json(json_block)
        job_data = json.loads(repaired_json_string)

        logger.debug("Repaired JSON: %s", job_data)

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "clean_repair_parse_json")
            scope.set_extra("input_json", json_block)
            scope.set_extra("error_stage", "repair or json.loads")
            sentry_sdk.capture_exception(e)
        return None

    else:
        return job_data

def parse_json_block_from_text(response: str) -> dict | str:
    def extract_json_block(text: str) -> str | None:
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        return match.group(0) if match else None

    try:
        json_str = extract_json_block(response)
        if not json_str:
            fixed_response = try_fix_missing_closing_brace(response)
            json_str = extract_json_block(fixed_response)

        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return clean_repair_parse_json(json_str)

        logger.error("Full LLM response:\n%s", response)
        error_msg = "No JSON block found in response."
        raise ValueError(error_msg)  # noqa: TRY301

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "parse_json_block_from_text")
            scope.set_extra("raw_response", response)
            sentry_sdk.capture_exception(e)
    return response

async def parse_job_data_from_markdown(job_markdown: str, count: int) -> dict | None:
    try:
        raw_llm_output  = await parse_job_posting(job_markdown, count)
        job_data = parse_json_block_from_text(raw_llm_output)

        if not isinstance(job_data, dict):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "parse_job_data_from_markdown")
                scope.set_extra("input_markdown", job_markdown[:1000])
                scope.capture_message("Parsed job data is empty after JSON repair", level="warning")
            return None

        job_data = normalize_keys(job_data)

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "parse_job_data_from_markdown")
            scope.set_extra("input_markdown", job_markdown[:1000])
            sentry_sdk.capture_exception(e)
        return None

    else:
        return job_data


