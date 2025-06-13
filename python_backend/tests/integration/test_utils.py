import pytest
import os
from jobs.parser import parse_job_data_from_markdown

@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_job_json_from_markdown_real():
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_job_markdown.md")
    with open(file_path, "r", encoding="utf-8") as f:
        markdown = f.read()

    result = await parse_job_data_from_markdown(markdown, count=1)

    assert "description" in result
    assert "responsibilities" in result
    assert "requirements" in result
    assert "experience_level" in result
    assert "work_model" in result
    assert "other" in result
    
    assert isinstance(result, dict)
    assert isinstance(result["description"], str)
    assert isinstance(result["experience_level"], str)
    assert isinstance(result["work_model"], str)
    assert isinstance(result["responsibilities"], list)
    assert isinstance(result["requirements"], list)
    assert isinstance(result["other"], list)
   
