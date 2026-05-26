import subprocess
from pathlib import Path

from ducktap.core.pipeline import press

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


def test_multilang_generators_emit_runnable_project_scaffolds(tmp_path):
    out = tmp_path / "out"

    result = press(
        str(FIXTURE),
        str(out),
        name="petstore",
        targets=["typescript-cli", "go-cli", "rust-cli"],
    )

    assert set(result.artifacts) == {"typescript-cli", "go-cli", "rust-cli"}

    ts_root = out / "petstore-dt-ts-cli"
    assert (ts_root / "package.json").exists()
    assert "petstore-dt-ts-cli" in (ts_root / "README.md").read_text(encoding="utf-8")
    assert "pet add-pet" in (ts_root / "src" / "commands.ts").read_text(encoding="utf-8")

    go_root = out / "petstore-dt-go-cli"
    assert (go_root / "go.mod").exists()
    assert "func main()" in (go_root / "cmd" / "petstore-dt-go-cli" / "main.go").read_text(
        encoding="utf-8"
    )
    proc = subprocess.run(["go", "test", "./..."], cwd=go_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    rust_root = out / "petstore-dt-rust-cli"
    assert (rust_root / "Cargo.toml").exists()
    assert "petstore-dt-rust-cli" in (rust_root / "src" / "main.rs").read_text(
        encoding="utf-8"
    )
