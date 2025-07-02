import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import yaml
from jobs.enricher import normalize_experience_level, override_experience_level_with_title, set_default_work_model
from jobs.parser import parse_job_data_from_markdown
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util
from tzlocal import get_localzone

logger = logging.getLogger(__name__)

PERFECT_MATCH = 100
FUZZY_MATCH_THRESHOLD = 75
DESCRIPTION_THRESHOLD = 65
DES_SEMANTIC_THRESHOLD = 70
RES_SEMANTIC_THRESHOLD = 70
REQ_SEMANTIC_THRESHOLD = 70
MIN_MATCH_SCORE = 80
MIN_MATCH_RATE = 90

model = SentenceTransformer("all-MiniLM-L6-v2")

def load_test_data() -> list:
    """Load test cases from YAML test data file."""
    data_path = Path(__file__).parent.parent.parent / "data" / "test_groq_job_data.yaml"
    with data_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def simulate_job_title_enrichment(job_data: dict, expected: dict) -> dict:
    """Simulate enriching the job JSON with a title if provided in expected."""
    if "title" in expected:
        job_data["title"] = expected["title"]
    return job_data


def semantic_similarity(text1: str, text2: str) -> float:
    """Compute semantic similarity score (0-100) between two texts using sentence-transformers."""
    emb1 = model.encode(text1, convert_to_tensor=True)
    emb2 = model.encode(text2, convert_to_tensor=True)
    return float(util.pytorch_cos_sim(emb1, emb2)[0][0]) * 100


def is_description_match(expected_desc: str, actual_desc: str) -> tuple:
    """Check if actual description matches expected via fuzzy or semantic similarity."""
    if not actual_desc.strip():
        return False, 0

    expected = expected_desc.lower()
    actual = actual_desc.lower()

    fuzzy_score = fuzz.partial_ratio(expected, actual)
    if fuzzy_score >= DESCRIPTION_THRESHOLD:
        return True, fuzzy_score

    semantic_score = semantic_similarity(expected, actual)
    return semantic_score >= DES_SEMANTIC_THRESHOLD, semantic_score


def is_semantic_match_list(expected_list: dict, actual_list: dict, threshold: int) -> tuple:
    """Compare lists of expected vs actual strings.

    Return match percentage and list of best scores per expected item.
    """
    match_count = 0
    scores = []

    for expected_item in expected_list:
        cleaned_expected = expected_item.strip().lower()
        best_score = 0

        for actual_item in actual_list:
            cleaned_actual = actual_item.strip().lower()

            fuzzy_score = fuzz.partial_ratio(cleaned_expected, cleaned_actual)

            if fuzzy_score == PERFECT_MATCH:
                best_score = PERFECT_MATCH
                break

            if fuzzy_score >= FUZZY_MATCH_THRESHOLD:
                best_score = max(best_score, fuzzy_score)
            else:
                semantic_score = semantic_similarity(cleaned_expected, cleaned_actual)
                if semantic_score >= threshold:
                    best_score = max(best_score, semantic_score)

        if best_score >= threshold:
            match_count += 1
        scores.append(best_score)

    match_ratio = (match_count / len(expected_list)) * 100 if expected_list else 100
    return match_ratio, scores

def run_description_check(expected: dict, actual: dict, case_info: str) -> tuple:
    expected_desc = expected.get("description", "")
    actual_desc = actual.get("description", "")
    passed, score = is_description_match(expected_desc, actual_desc)
    errors = []

    if not passed:
        errors.append(
            f"{case_info} [DESCRIPTION MISMATCH] Score: {score:.2f}\n"
            f"Expected: {expected_desc}\nGot: {actual_desc}"
        )

    return score, errors


def run_responsibilities_check(expected: dict, actual: dict, case_info: str) -> tuple:
    expected_resps = expected.get("responsibilities", [])
    actual_resps = actual.get("responsibilities", [])
    match_ratio, scores = is_semantic_match_list(expected_resps, actual_resps, RES_SEMANTIC_THRESHOLD)
    errors = []

    if expected_resps and match_ratio < RES_SEMANTIC_THRESHOLD:
        errors.append(
            f"{case_info} [RESPONSIBILITIES MISMATCH] Match Ratio: {match_ratio:.2f}%\n"
            f"Expected: {expected_resps}\nActual: {actual_resps}\nScores: {scores}"
        )

    return match_ratio, errors


def run_requirements_check(expected: dict, actual: dict, case_info: str) -> tuple:
    expected_reqs = expected.get("requirements", [])
    actual_reqs = actual.get("requirements", [])
    match_ratio, scores = is_semantic_match_list(expected_reqs, actual_reqs, REQ_SEMANTIC_THRESHOLD)
    errors = []

    if expected_reqs and match_ratio < REQ_SEMANTIC_THRESHOLD:
        errors.append(
            f"{case_info} [REQUIREMENTS MISMATCH] Match Ratio: {match_ratio:.2f}%\n"
            f"Expected: {expected_reqs}\nActual: {actual_reqs}\nScores: {scores}"
        )

    return match_ratio, errors


def run_experience_check(expected: dict, actual: dict, case_info: str) -> tuple:
    expected_exp = expected.get("experience_level", "").lower()
    actual_exp = actual.get("experience_level", "").lower()
    errors = []

    if expected_exp != actual_exp:
        errors.append(
            f"{case_info} [EXPERIENCE MISMATCH] Expected: '{expected_exp}', Got: '{actual_exp}'"
        )
        return 1, errors

    return 0, []


def run_work_model_check(expected: dict, actual: dict, case_info: str) -> tuple:
    expected_work = expected.get("work_model", "").lower()
    actual_work = actual.get("work_model", "").lower()
    errors = []

    if expected_work != actual_work:
        errors.append(
            f"{case_info} [WORK MODEL MISMATCH] Expected: '{expected_work}', Got: '{actual_work}'"
        )
        return 1, errors

    return 0, []


@pytest.mark.asyncio
async def run_all_tests_once(test_cases: list) -> dict:
    """Run all test cases once and return a dictionary with averaged scores and mismatch counts.

    Collect all assertion errors but do not raise them, always return results and errors.
    """
    description_scores = []
    responsibility_scores = []
    requirement_scores = []
    experience_mismatches = 0
    work_model_mismatches = 0
    errors = []

    for i, test_case in enumerate(test_cases):
        markdown = test_case["markdown"]
        expected = test_case["expected"]
        case_info = f"[Test Case {i + 1}]"
        case_errors = []

        try:
            result = await parse_job_data_from_markdown(markdown, 0)
            result = set_default_work_model(result)
            result = simulate_job_title_enrichment(result, expected)
            result = override_experience_level_with_title(result)
            result = normalize_experience_level(result)

            if "error" in result:
                case_errors.append(f"{case_info} JSON parsing failed: {result.get('error')}")

            # Run modular checks
            desc_score, desc_errors = run_description_check(expected, result, case_info)
            description_scores.append(desc_score)
            case_errors.extend(desc_errors)

            resp_score, resp_errors = run_responsibilities_check(expected, result, case_info)
            responsibility_scores.append(resp_score)
            case_errors.extend(resp_errors)

            req_score, req_errors = run_requirements_check(expected, result, case_info)
            requirement_scores.append(req_score)
            case_errors.extend(req_errors)

            exp_mismatch, exp_errors = run_experience_check(expected, result, case_info)
            experience_mismatches += exp_mismatch
            case_errors.extend(exp_errors)

            work_mismatch, work_errors = run_work_model_check(expected, result, case_info)
            work_model_mismatches += work_mismatch
            case_errors.extend(work_errors)

            if case_errors:
                errors.extend(case_errors)

        except AssertionError as e:
            errors.append(f"{case_info} [UNEXPECTED ERROR]: {e!s}")

    total_tests = len(description_scores)
    return {
        "avg_desc_score": sum(description_scores) / total_tests if total_tests else 0,
        "avg_resp_score": sum(responsibility_scores) / total_tests if total_tests else 0,
        "avg_req_score": sum(requirement_scores) / total_tests if total_tests else 0,
        "exp_match_rate": ((total_tests - experience_mismatches) / total_tests * 100) if total_tests else 0,
        "work_model_match_rate": ((total_tests - work_model_mismatches) / total_tests * 100) if total_tests else 0,
        "total_tests": total_tests,
        "errors": errors,
    }


@pytest.mark.asyncio
async def test_run_multiple_times_and_aggregate() -> None:
    """Run the entire test suite multiple times, aggregate scores and print summary statistics.

    Prints errors per run but does not raise immediately.
    """
    test_cases = load_test_data()["tests"]
    num_runs = 3

    all_run_results = []
    errors = []

    for i in range(num_runs):
        logger.info("Running test iteration %d/%d ...", i + 1, num_runs)
        result = await run_all_tests_once(test_cases)
        all_run_results.append(result)
        if result["errors"]:
            joined_errors = "\n\n---\n".join(result["errors"])
            errors.append(f"Run {i + 1} had errors:\n{joined_errors}")

    if errors:
        logger.error("===== %d RUN(S) HAD ERRORS =====\n%s", len(errors), "\n\n---\n".join(errors))

    metrics = ["avg_desc_score", "avg_resp_score", "avg_req_score", "exp_match_rate", "work_model_match_rate"]

    summary = {
        "timestamp": datetime.now(get_localzone()).isoformat(),
        "num_runs": num_runs,
        "per_run_results": all_run_results,
        "averages": {},
        "stddevs": {},
    }

    for metric in metrics:
        values = [run[metric] for run in all_run_results]
        summary["averages"][metric] = float(np.mean(values))
        summary["stddevs"][metric] = float(np.std(values, ddof=1))

    #Add total number of tests run to summary
    summary["total_tests_run"] = summary["num_runs"] * all_run_results[0]["total_tests"]

    # Save summary to JSON
    output_path = Path(__file__).parent/ "results_summary.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Print summary stats
    logger.info("\n========== Aggregated Extraction Summary ==========")
    logger.info("Total tests run: %d", summary["total_tests_run"])
    for metric in metrics:
        avg = summary["averages"][metric]
        std = summary["stddevs"][metric]
        logger.info("%-30s: %.2f ± %.2f", metric, avg, std)
    logger.info("====================================================")

    # Assert minimum expected performance
    assert summary["averages"]["avg_desc_score"] >= MIN_MATCH_SCORE, "Average description score too low"
    assert summary["averages"]["avg_resp_score"] >= MIN_MATCH_SCORE, "Average responsibility match too low"
    assert summary["averages"]["avg_req_score"] >= MIN_MATCH_SCORE, "Average requirement match too low"
    assert summary["averages"]["exp_match_rate"] >= MIN_MATCH_RATE, "Experience level match rate too low"
    assert summary["averages"]["work_model_match_rate"] >= MIN_MATCH_RATE, "Work model match rate too low"







