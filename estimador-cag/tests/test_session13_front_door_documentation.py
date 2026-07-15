from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPOSITORY_ROOT / "estimador-cag"

ROOT_README = REPOSITORY_ROOT / "README.md"
PROJECT_README = PROJECT_ROOT / "README.md"

COMPLIANCE_DOC = PROJECT_ROOT / "docs" / "session13_task13_compliance.md"
PLUS_DOC = PROJECT_ROOT / "docs" / "session13_plus_roadmap.md"
PRESENTATION_DOC = (
    PROJECT_ROOT / "docs" / "session13_presentation_guide_es.md"
)


def test_session13_front_door_documentation() -> None:
    for path in (
        ROOT_README,
        PROJECT_README,
        COMPLIANCE_DOC,
        PLUS_DOC,
        PRESENTATION_DOC,
    ):
        assert path.is_file(), f"Missing documentation: {path}"

    root_readme = ROOT_README.read_text(encoding="utf-8")
    project_readme = PROJECT_README.read_text(encoding="utf-8")
    compliance = COMPLIANCE_DOC.read_text(encoding="utf-8")
    plus = PLUS_DOC.read_text(encoding="utf-8")
    presentation = PRESENTATION_DOC.read_text(encoding="utf-8")

    root_front_door = root_readme.split(
        "## Historical Session 10 retrieval work",
        1,
    )[0]
    project_front_door = project_readme.split(
        "## Historical Session 12 agentic work",
        1,
    )[0]

    assert "Session 13" in root_front_door
    assert "session-13/pre-work" in root_front_door
    assert "gg-session-10/pre-work" not in root_front_door

    assert "Current Session 13 status" in project_front_door
    assert "/api/v1/estimate/graph" in project_front_door
    assert "Current Session 12 status" not in project_front_door
    assert "gg-session-12/pre-work" not in project_front_door

    assert "Mandatory compliance matrix" in compliance
    assert "AsyncPostgresSaver" in compliance
    assert "019f66df5be5e9f5db11c167f81b79dd" in compliance
    assert "667 passed, 9 skipped" in compliance

    assert "Non-mandatory Session 13 Plus roadmap" in plus
    assert "P0" in plus
    assert "P9" in plus
    assert "Send API" in plus
    assert "interrupt()" in plus

    assert "Guía de presentación" in presentation
    assert "¿Dónde haces las llamadas?" in presentation
    assert "¿Dónde construyes la respuesta?" in presentation
    assert "¿Cómo gestionas las decisiones?" in presentation
