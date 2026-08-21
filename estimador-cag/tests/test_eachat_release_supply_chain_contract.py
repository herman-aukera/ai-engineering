from pathlib import Path


def test_eachat_release_attaches_sbom_and_provenance() -> None:
    workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/eachat-release-image.yml").read_text()
    assert "push: true" in workflow
    assert "sbom: true" in workflow
    assert "provenance: mode=max" in workflow
    assert "org.opencontainers.image.revision" in workflow
    assert "outputs.digest" in workflow
