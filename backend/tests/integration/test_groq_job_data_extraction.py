import pytest
import os
import yaml
from rapidfuzz import fuzz
from scraper.utils import parse_job_json_from_markdown  

# === Global configuration ===
FUZZY_MATCH_THRESHOLD = 75
MATCH_PROPORTION = 0.7

def load_test_data():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "..", "data", "test_groq_job_data.yaml")
    with open(data_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def experience_level_matches(expected: str, actual: str) -> bool:
    experience_groups = {
        "junior": {"junior"},
        "mid": {"mid", "mid_or_senior"},   
        "senior": {"senior", "mid_or_senior"} 
    }
    return actual.lower() in experience_groups.get(expected.lower(), {expected.lower()})

@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", load_test_data()["tests"])
async def test_extract_fields_from_job_link_with_groq(test_case):
    markdown = test_case["markdown"]
    expected = test_case["expected"]

    result = await parse_job_json_from_markdown(markdown, 1)
    print("Parsed result:")
    print(result)

    if "error" in result:
        pytest.fail(f"JSON parsing failed: {result['error']}")

    similarity = fuzz.partial_ratio(expected['description'].lower(), result.get('description', '').lower())
    assert similarity >= FUZZY_MATCH_THRESHOLD, f"Description similarity too low: {similarity}.\nExpected: {expected['description']}\nGot: {result.get('description')}"

    min_responsibility_matches = int(len(expected['responsibilities']) * MATCH_PROPORTION)
    responsibility_match_count = sum(
        any(fuzz.partial_ratio(expected_resp.lower(), r.lower()) >= FUZZY_MATCH_THRESHOLD for r in result.get('responsibilities', []))
        for expected_resp in expected['responsibilities']
    )
    assert responsibility_match_count >= min_responsibility_matches, f"Only {responsibility_match_count}/{len(expected['responsibilities'])} responsibilities matched"

    min_requirement_matches = int(len(expected['requirements']) * MATCH_PROPORTION)
    requirement_match_count = sum(
        any(fuzz.partial_ratio(expected_req.lower(), r.lower()) >= FUZZY_MATCH_THRESHOLD for r in result.get('requirements', []))
        for expected_req in expected['requirements']
    )
    assert requirement_match_count >= min_requirement_matches, f"Only {requirement_match_count}/{len(expected['requirements'])} requirements matched"

    assert experience_level_matches(expected['experience_level'], result.get('experience_level', '')), \
        f"Expected experience level '{expected['experience_level']}', got '{result.get('experience_level')}'"

    assert expected['work_model'].lower() == result.get('work_model', '').lower(), \
        f"Expected work model '{expected['work_model']}', got '{result.get('work_model')}'"




