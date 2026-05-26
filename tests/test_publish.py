import json
import zipfile
from pathlib import Path

from ducktap.cli import app
from ducktap.core.pipeline import press

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


def test_publish_dry_run_packages_generated_artifacts(tmp_path):
    from typer.testing import CliRunner

    out = tmp_path / "out"
    dist = tmp_path / "dist"
    press(str(FIXTURE), str(out), name="petstore")

    result = CliRunner().invoke(
        app,
        [
            "publish",
            "petstore",
            "--out-dir",
            str(out),
            "--dist-dir",
            str(dist),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    manifest = dist / "petstore-publish-manifest.json"
    archive = dist / "petstore-ducktap-artifacts.zip"
    assert manifest.exists()
    assert archive.exists()
    text = manifest.read_text(encoding="utf-8")
    assert '"dry_run": true' in text
    assert '"scorecard"' in text
    data = json.loads(text)
    assert "typescript_cli" in data["artifacts"]
    assert "go_cli" in data["artifacts"]
    assert "rust_cli" in data["artifacts"]
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "petstore-dt-ts-cli/package.json" in names
    assert "petstore-dt-go-cli/go.mod" in names
    assert "petstore-dt-rust-cli/Cargo.toml" in names
