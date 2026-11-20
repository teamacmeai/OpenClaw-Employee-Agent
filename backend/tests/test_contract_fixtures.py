"""Checks that the shared fixtures satisfy both the JSON Schemas and the Pydantic models."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.schemas.eval_contract import EvalRequest, EvalResponse

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = json.loads((REPO_ROOT / "fixtures" / "sample_payloads.json").read_text())
REQUEST_SCHEMA = json.loads((REPO_ROOT / "contracts" / "eval_request.schema.json").read_text())
RESPONSE_SCHEMA = json.loads((REPO_ROOT / "contracts" / "eval_response.schema.json").read_text())
CASES = FIXTURES["cases"]
IDS = [case["id"] for case in CASES]


def test_schemas_are_valid():
    Draft202012Validator.check_schema(REQUEST_SCHEMA)
    Draft202012Validator.check_schema(RESPONSE_SCHEMA)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_input_matches_schema_and_model(case):
    Draft202012Validator(REQUEST_SCHEMA).validate(case["input"])
    EvalRequest.model_validate(case["input"])


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_expected_output_matches_schema_and_model(case):
    Draft202012Validator(RESPONSE_SCHEMA).validate(case["expected_output"])
    EvalResponse.model_validate(case["expected_output"])


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_output_does_not_invent_data(case):
    """Guards against hallucination: output may only reuse IDs, paths and projects from the input."""
    request, response = case["input"], case["expected_output"]
    assert response["request_id"] == request["request_id"]

    known_paths = {event["path"] for event in request["activity"]["file_events"]}
    known_projects = {event["project"] for event in request["activity"]["file_events"]}
    window = request["window"]

    for block in response["work_blocks"]:
        assert set(block["files_referenced"]) <= known_paths
        assert block["project"] is None or block["project"] in known_projects
        assert window["start"] <= block["start"] < block["end"] <= window["end"]
