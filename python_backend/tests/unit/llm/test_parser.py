from unittest.mock import MagicMock, patch

import pytest
from llm.parser import infer_experience_level, infer_work_model, parse_job_posting


@pytest.mark.asyncio
@patch("llm.parser.client.chat.completions.create")
async def test_parse_job_posting(mock_groq_create: MagicMock) -> None:
    mock_json = (
        '{"description":"Build stuff.","responsibilities":["Code"],"requirements":["Python"],'
        '"experience_level":"mid_or_senior","work_model":"Remote","other":["Free breakfast"]}'
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=mock_json))]
    mock_groq_create.return_value = mock_response

    markdown = "## About the Role\nYou're going to build amazing products.\n\n### Requirements\n- Python\n"
    result = await parse_job_posting(markdown, count=1)

    assert result == mock_json
    mock_groq_create.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.parametrize(("count", "expected_model"), [
    (0, "llama-3.1-8b-instant"),
    (1, "llama3-70b-8192"),
    (2, "llama3-8b-8192"),
    (3, "llama-3.1-8b-instant"),
    (4, "llama3-70b-8192"),
])
@patch("llm.parser.client.chat.completions.create")
async def test_model_selection_based_on_count(mock_groq_create: MagicMock, count: int, expected_model: str) -> None:
    mock_json = (
        '{"description":"",'
        '"responsibilities":[]',
        '"requirements":[],'
        '"experience_level":"mid_or_senior",'
        '"work_model":"Remote",'
        '"other":[]}'
        )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=mock_json))]
    mock_groq_create.return_value = mock_response

    await parse_job_posting("dummy markdown", count)
    assert mock_groq_create.call_args.kwargs["model"] == expected_model

@pytest.mark.asyncio
@patch("llm.parser.client.chat.completions.create")
async def test_infer_work_model(mock_groq_create: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Remote"))]
    mock_groq_create.return_value = mock_response

    job_text = "We offer a flexible remote-first working environment..."
    result = await infer_work_model(job_text)

    assert result == "Remote"
    mock_groq_create.assert_called_once()


@pytest.mark.asyncio
@patch("llm.parser.client.chat.completions.create")
async def test_infer_experience_level(mock_groq_create: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="mid_or_senior"))]
    mock_groq_create.return_value = mock_response

    result = await infer_experience_level(
        job_title="Senior Software Engineer",
        job_text="We're looking for someone with 5+ years of backend experience."
    )
    assert result == "mid_or_senior"
    mock_groq_create.assert_called_once()

@pytest.mark.asyncio
@patch("llm.parser.client.chat.completions.create")
async def test_extract_missing_experience_level_invalid_output(mock_groq_create: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="expert"))]
    mock_groq_create.return_value = mock_response

    result = await infer_experience_level(
        job_title="Software Engineer",
        job_text="We're looking for someone with 5+ years of backend experience."
    )

    assert result is None
    mock_groq_create.assert_called_once()
