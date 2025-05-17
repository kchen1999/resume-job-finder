import os
import json
import yaml
import datetime
import pytest
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util
from scraper.utils import parse_job_json_from_markdown, override_experience_level_with_title, set_default_work_model, normalize_experience_level


# Threshold constants for matching
FUZZY_MATCH_THRESHOLD = 75
DESCRIPTION_THRESHOLD = 65
DESCRIPTION_SEMANTIC_THRESHOLD = 70
RESPONSIBILITY_SEMANTIC_THRESHOLD = 70
REQUIREMENT_SEMANTIC_THRESHOLD = 70

model = SentenceTransformer("all-MiniLM-L6-v2")

def load_test_data():
    """Load test cases from YAML test data file."""
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "..", "data", "test_groq_job_data.yaml")
    with open(data_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def simulate_job_title_enrichment(job_json, expected):
    """Simulate enriching the job JSON with a title if provided in expected."""
    if 'title' in expected:
        job_json['title'] = expected['title']
    return job_json


def semantic_similarity(text1, text2):
    """Compute semantic similarity score (0-100) between two texts using sentence-transformers."""
    emb1 = model.encode(text1, convert_to_tensor=True)
    emb2 = model.encode(text2, convert_to_tensor=True)
    return float(util.pytorch_cos_sim(emb1, emb2)[0][0]) * 100


def is_description_match(expected_desc, actual_desc):
    """Check if actual description matches expected via fuzzy or semantic similarity."""
    if not actual_desc.strip():
        return False, 0

    expected = expected_desc.lower()
    actual = actual_desc.lower()

    fuzzy_score = fuzz.partial_ratio(expected, actual)
    if fuzzy_score >= DESCRIPTION_THRESHOLD:
        return True, fuzzy_score

    semantic_score = semantic_similarity(expected, actual)
    return semantic_score >= DESCRIPTION_SEMANTIC_THRESHOLD, semantic_score


def is_semantic_match_list(expected_list, actual_list, threshold):
    """
    Compare lists of expected vs actual strings.
    Return match percentage and list of best scores per expected item.
    """
    match_count = 0
    scores = []

    for expected_item in expected_list:
        expected_item = expected_item.strip().lower()
        best_score = 0

        for actual_item in actual_list:
            actual_item = actual_item.strip().lower()

            fuzzy_score = fuzz.partial_ratio(expected_item, actual_item)

            if fuzzy_score == 100:
                best_score = 100
                break

            if fuzzy_score >= FUZZY_MATCH_THRESHOLD:
                best_score = max(best_score, fuzzy_score)
            else:
                semantic_score = semantic_similarity(expected_item, actual_item)
                if semantic_score >= threshold:
                    best_score = max(best_score, semantic_score)

        if best_score >= threshold:
            match_count += 1
        scores.append(best_score)

    match_ratio = (match_count / len(expected_list)) * 100 if expected_list else 100
    return match_ratio, scores


@pytest.mark.asyncio
async def run_all_tests_once(test_cases):
    """
    Run all test cases once and return a dictionary with averaged scores and mismatch counts.
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
            # Parse and enrich result
            result = await parse_job_json_from_markdown(markdown, 0)
            result = set_default_work_model(result)
            result = simulate_job_title_enrichment(result, expected)
            result = override_experience_level_with_title(result)
            result = normalize_experience_level(result)

            if "error" in result:
                case_errors.append(f"{case_info} JSON parsing failed: {result.get('error')}")

            # Description check
            description = result.get("description", "")
            passed, desc_score = is_description_match(expected["description"], description)
            description_scores.append(desc_score)
            if not passed:
                case_errors.append(
                    f"{case_info} [DESCRIPTION MISMATCH] Score: {desc_score:.2f}\n"
                    f"Expected: {expected['description']}\nGot: {description}"
                )

            # Responsibility check
            expected_resps = expected.get("responsibilities", [])
            actual_resps = result.get("responsibilities", [])
            if expected_resps:
                match_ratio, scores = is_semantic_match_list(expected_resps, actual_resps, RESPONSIBILITY_SEMANTIC_THRESHOLD)
                responsibility_scores.append(match_ratio)
                if match_ratio < RESPONSIBILITY_SEMANTIC_THRESHOLD:
                    case_errors.append(
                        f"{case_info} [RESPONSIBILITIES MISMATCH] Match Ratio: {match_ratio:.2f}%\n"
                        f"Expected: {expected_resps}\nActual: {actual_resps}\nScores: {scores}"
                    )
            else:
                responsibility_scores.append(100.0)

            # Requirement check
            expected_reqs = expected.get("requirements", [])
            actual_reqs = result.get("requirements", [])
            if expected_reqs:
                match_ratio, scores = is_semantic_match_list(expected_reqs, actual_reqs, REQUIREMENT_SEMANTIC_THRESHOLD)
                requirement_scores.append(match_ratio)
                if match_ratio < REQUIREMENT_SEMANTIC_THRESHOLD:
                    case_errors.append(
                        f"{case_info} [REQUIREMENTS MISMATCH] Match Ratio: {match_ratio:.2f}%\n"
                        f"Expected: {expected_reqs}\nActual: {actual_reqs}\nScores: {scores}"
                    )
            else:
                requirement_scores.append(100.0)

            # Experience level check
            expected_exp = expected["experience_level"].lower()
            actual_exp = result.get("experience_level", "").lower()
            if expected_exp != actual_exp:
                experience_mismatches += 1
                case_errors.append(
                    f"{case_info} [EXPERIENCE MISMATCH] Expected: '{expected_exp}', Got: '{actual_exp}'"
                )

            # Work model check
            expected_work = expected["work_model"].lower()
            actual_work = result.get("work_model", "").lower()
            if expected_work != actual_work:
                work_model_mismatches += 1
                case_errors.append(
                    f"{case_info} [WORK MODEL MISMATCH] Expected: '{expected_work}', Got: '{actual_work}'"
                )
            
            if case_errors:
                errors.extend(case_errors)

        except AssertionError as e:
            errors.append(f"{case_info} [UNEXPECTED ERROR]: {str(e)}")

    total_tests = len(description_scores)
    results = {
        "avg_desc_score": sum(description_scores) / total_tests if total_tests else 0,
        "avg_resp_score": sum(responsibility_scores) / total_tests if total_tests else 0,
        "avg_req_score": sum(requirement_scores) / total_tests if total_tests else 0,
        "exp_match_rate": ((total_tests - experience_mismatches) / total_tests * 100) if total_tests else 0,
        "work_model_match_rate": ((total_tests - work_model_mismatches) / total_tests * 100) if total_tests else 0,
        "total_tests": total_tests,
        "errors": errors,  # Include errors here
    }
    return results


@pytest.mark.asyncio
async def test_run_multiple_times_and_aggregate():
    """
    Run the entire test suite multiple times, aggregate scores and print summary statistics.
    Prints errors per run but does not raise immediately.
    """
    test_cases = load_test_data()["tests"]
    N = 3

    all_run_results = []
    errors = []

    for i in range(N):
        print(f"\nRunning test iteration {i + 1}/{N} ...")
        result = await run_all_tests_once(test_cases)
        all_run_results.append(result)
        if result["errors"]:
            errors.append(f"Run {i + 1} had errors:\n" + "\n\n---\n".join(result["errors"]))

    if errors:
        print(f"\n\n===== {len(errors)} RUN(S) HAD ERRORS =====\n" + "\n\n---\n".join(errors))

    metrics = ["avg_desc_score", "avg_resp_score", "avg_req_score", "exp_match_rate", "work_model_match_rate"]

    summary = {
        "timestamp": datetime.datetime.now().isoformat(),
        "num_runs": N,
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
    output_path = os.path.join(os.path.dirname(__file__), "results_summary.json")
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary stats
    print("\n========== Aggregated Extraction Summary ==========")
    print(f"Total tests run: {summary['total_tests_run']}")
    for metric in metrics:
        avg = summary["averages"][metric]
        std = summary["stddevs"][metric]
        print(f"{metric:30s}: {avg:.2f} ± {std:.2f}")
    print("====================================================")

    # Assert minimum expected performance
    assert summary["averages"]["avg_desc_score"] >= 80, "Average description score too low"
    assert summary["averages"]["avg_resp_score"] >= 80, "Average responsibility match too low"
    assert summary["averages"]["avg_req_score"] >= 80, "Average requirement match too low"
    assert summary["averages"]["exp_match_rate"] >= 90, "Experience level match rate too low"
    assert summary["averages"]["work_model_match_rate"] >= 90, "Work model match rate too low"







