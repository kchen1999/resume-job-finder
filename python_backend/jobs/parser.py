import logging
import json
import sentry_sdk

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from json_repair import repair_json
from llm.parser import parse_job_posting
from utils.utils import clean_string

def clean_repair_parse_json(json_block):
    try:
        if isinstance(json_block, str):
            json_block = clean_string(json_block)

        logging.debug("Attempting to repair JSON...")
        repaired_json_string = repair_json(json_block)
        job_data = json.loads(repaired_json_string)

        logging.debug("Repaired JSON: %s", job_data)
        return job_data
    
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "clean_repair_parse_json")
            scope.set_extra("input_json", json_block)
            scope.set_extra("error_stage", "repair or json.loads")
            sentry_sdk.capture_exception(e)
        raise 

def parse_json_block_from_text(response):
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        extracted = response[start:end]
        return json.loads(extracted)
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "parse_json_block_from_text")
            scope.set_extra("raw_response", response)
            sentry_sdk.capture_exception(e)
        return response

async def parse_job_data_from_markdown(job_markdown, count):
    try:
        raw_llm_output  = await parse_job_posting(job_markdown, count)
        json_block = parse_json_block_from_text(raw_llm_output)

        if isinstance(json_block, dict):
            return json_block
    
        job_data = clean_repair_parse_json(json_block)
        if not job_data:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "parse_job_data_from_markdown")
                scope.set_extra("input_markdown", job_markdown[:1000])
                scope.capture_message("Parsed job data is empty after JSON repair", level="warning")
            return None

        return job_data
        
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "parse_job_data_from_markdown")
            scope.set_extra("input_markdown", job_markdown[:1000]) 
            sentry_sdk.capture_exception(e)
        return None


