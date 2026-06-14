import json

from energy_core import schema_cli


def test_schema_cli_prints_full_bundle_json(capsys) -> None:
    exit_code = schema_cli.main(["--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_bundle_version"] == "1.0.0"
    assert "candidate_state" in payload["models"]
    assert "energy_decision" in payload["models"]


def test_schema_cli_prints_single_schema_text(capsys) -> None:
    exit_code = schema_cli.main(["--schema", "evidence_record", "--format", "text"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Schema: evidence_record" in output
    assert "- evidence_id" in output
    assert "- status" in output
