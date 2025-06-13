import pytest
import json
from unittest.mock import patch, AsyncMock

from jobs.parser import clean_repair_parse_json, parse_json_block_from_text, parse_job_data_from_markdown
from tests.data.sample_job_json_strings import VALID_JSON_STRING, MALFORMED_JSON_STRING

repaired = """{
    "description": "This innovative tech business is expanding its engineering function and seeking a Site Reliability Engineer to help ensure their world-class platform continues to run like clockwork.", 
    "responsibilities": [
        "Maintain the reliability, availability and performance of the company's software applications", 
        "Resolve incidents swiftly to minimise downtime and ensure a seamless user experience", 
        "Continuously improve system stability and scalability through automation and robust infrastructure tooling", 
        "Dive deep into root cause analysis and propose long-term solutions", 
        "Collaborate with engineers and cross-functional teams to embed DevOps best practices"
    ], 
    "requirements": [
        "Excellent problem-solving skills and a passion for fixing issues at the structural level", 
        "Experience working with cloud-based infrastructure (AWS), Linux, and scripting (Python)", 
        "Familiarity with tooling like Prometheus, Ansible, PostgreSQL, Elasticsearch and Node.js", 
        "Strong communication skills, especially under pressure", 
        "A First or 2:1 degree (Bachelor’s or Master’s) — ideally in a technical field", 
        "Curiosity, collaboration and a desire to make things better!"
    ], 
    "experience_level": "mid_or_senior", 
    "work_model": "Hybrid", 
    "other": [
        "Competitive Salary | $120,000 - $140,000 + Super", 
        "Join a market leader at the forefront of AI in the legal sector", 
        "Be part of a small, high-calibre SRE team with real ownership", 
        "Solve critical problems in complex systems daily", 
        "Fast-paced scale-up environment with rapid learning & growth", 
        "Inclusive, collaborative, and innovation-focused culture", 
        "Flexible working and attractive package on offer"
    ]
}"""

@patch("jobs.parser.clean_string")
@patch("jobs.parser.repair_json")
def test_clean_repair_parse_json_valid_input(mock_repair_json, mock_clean_string):
    mock_clean_string.return_value = VALID_JSON_STRING
    mock_repair_json.return_value = VALID_JSON_STRING

    result = clean_repair_parse_json(VALID_JSON_STRING)
    parsed = json.loads(VALID_JSON_STRING)

    assert isinstance(result, dict)
    assert result["experience_level"] == parsed["experience_level"]
    assert result["work_model"] == parsed["work_model"]
    assert "description" in result

@patch("jobs.parser.clean_string")
@patch("jobs.parser.repair_json")
def test_clean_repair_parse_json_with_repair(mock_repair_json, mock_clean_string):
    mock_clean_string.return_value = MALFORMED_JSON_STRING
    mock_repair_json.return_value = repaired

    result = clean_repair_parse_json(MALFORMED_JSON_STRING)
    expected = json.loads(repaired)

    assert isinstance(result, dict)
    assert result == expected
    assert result["experience_level"] == "mid_or_senior"
    assert result["work_model"] == "Hybrid"
    assert "responsibilities" in result
    assert isinstance(result["requirements"], list)

@patch("jobs.parser.clean_string")
@patch("jobs.parser.repair_json")
@patch("jobs.parser.sentry_sdk")
def test_clean_repair_parse_json_raises_on_load(mock_sentry_sdk, mock_repair_json, mock_clean_string):
    mock_clean_string.return_value = "invalid json"
    mock_repair_json.return_value = "still invalid"

    with pytest.raises(json.JSONDecodeError):
        clean_repair_parse_json("invalid json")

    scope = mock_sentry_sdk.push_scope.return_value.__enter__.return_value
    scope.set_tag.assert_called_with("component", "clean_repair_parse_json")
    scope.set_extra.assert_any_call("input_json", "invalid json")
    scope.set_extra.assert_any_call("error_stage", "repair or json.loads")
    mock_sentry_sdk.capture_exception.assert_called_once()

def test_parse_json_block_from_text_valid():
    response = f"Random header junk {VALID_JSON_STRING} Random footer junk"
    result = parse_json_block_from_text(response)

    assert isinstance(result, dict)
    assert result["work_model"] == "On-site"
    assert "requirements" in result

def test_parse_json_block_from_text_invalid_json():
    assert isinstance(MALFORMED_JSON_STRING, str)
    result = parse_json_block_from_text(MALFORMED_JSON_STRING)
    assert result == MALFORMED_JSON_STRING
    assert isinstance(result, str)

@patch("jobs.parser.sentry_sdk")
def test_parse_json_block_from_text_invalid_json_logs_to_sentry(mock_sentry):
    response = "Not really JSON at all: <<<<<<{what's this>>>"

    result = parse_json_block_from_text(response)
    assert result == response

    scope = mock_sentry.push_scope.return_value.__enter__.return_value
    scope.set_tag.assert_called_with("component", "parse_json_block_from_text")
    scope.set_extra.assert_called_with("raw_response", response)
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch("jobs.parser.parse_job_posting", new_callable=AsyncMock)
@patch("jobs.parser.parse_json_block_from_text")
async def test_parse_job_data_from_markdown_returns_dict_directly(mock_parse_json_block, mock_parse_posting):
    job_md = "mock markdown"
    mock_dict = {"experience_level": "mid_or_senior", "work_model": "Remote"}
    mock_parse_posting.return_value = "LLM string"
    mock_parse_json_block.return_value = mock_dict

    result = await parse_job_data_from_markdown(job_md, 1)
    assert result == mock_dict
    assert result["work_model"] == "Remote"

@pytest.mark.asyncio
@patch("jobs.parser.clean_repair_parse_json")
@patch("jobs.parser.parse_json_block_from_text")
@patch("jobs.parser.parse_job_posting", new_callable=AsyncMock)
async def test_parse_job_data_from_markdown_repairs_and_returns(
    mock_parse_posting, mock_parse_json_block, mock_clean_repair
):
    job_md = "broken markdown"
    mock_parse_posting.return_value = "broken string with json"
    mock_parse_json_block.return_value = "malformed json string"
    mock_clean_repair.return_value = json.loads(repaired)

    result = await parse_job_data_from_markdown(job_md, 1)

    assert isinstance(result, dict)
    assert result["experience_level"] == "mid_or_senior"
    assert "responsibilities" in result
    assert result["work_model"] == "Hybrid"

@pytest.mark.asyncio
@patch("jobs.parser.sentry_sdk")
@patch("jobs.parser.clean_repair_parse_json")
@patch("jobs.parser.parse_json_block_from_text")
@patch("jobs.parser.parse_job_posting", new_callable=AsyncMock)
async def test_parse_job_data_from_markdown_returns_none_if_repair_fails(
    mock_parse_posting, mock_parse_json_block, mock_clean_repair, mock_sentry
):
    mock_parse_posting.return_value = "raw llm string"
    mock_parse_json_block.return_value = "garbled"
    mock_clean_repair.return_value = None

    result = await parse_job_data_from_markdown("markdown", 1)
    assert result is None

    scope = mock_sentry.push_scope.return_value.__enter__.return_value
    scope.set_tag.assert_called_with("component", "parse_job_data_from_markdown")
    scope.set_extra.assert_called_with("input_markdown", "markdown")
    scope.capture_message.assert_called_once_with("Parsed job data is empty after JSON repair", level="warning")

