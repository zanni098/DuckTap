"""Additional language generator scaffolds.

These are intentionally small, runnable starting points for teams that want
the DuckTap API shape in TypeScript, Go, or Rust while the Python generator
remains the fully featured default.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ducktap.core import plugins
from ducktap.core.naming import cli_command_name
from ducktap.core.spec import APISpec


def _ops(spec: APISpec) -> list[dict[str, str]]:
    return [
        {
            "group": cli_command_name(op.tags[0] if op.tags else "general"),
            "command": cli_command_name(op.operation_id),
            "route": (
                f"{cli_command_name(op.tags[0])} {cli_command_name(op.operation_id)}"
                if op.tags else cli_command_name(op.operation_id)
            ),
            "method": op.method,
            "path": op.path,
            "summary": op.summary or op.description or f"{op.method} {op.path}",
        }
        for op in spec.operations
    ]


def _write(path: Path, text: str, written: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    written.append(str(path))


def _go_raw_string(value: str) -> str:
    return "`" + value.replace("`", "` + \"`\" + `") + "`"


class TypeScriptCLIGenerator:
    name = "typescript-cli"
    target = "typescript-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        root = Path(out_dir) / f"{spec.name}-dt-ts-cli"
        bin_name = f"{spec.name}-dt-ts-cli"
        ops = _ops(spec)
        written: list[str] = []
        _write(root / "package.json", json.dumps({
            "name": bin_name,
            "version": spec.version,
            "type": "module",
            "bin": {bin_name: "./src/index.js"},
            "scripts": {"start": "tsx src/index.ts"},
            "dependencies": {"commander": "^12.0.0"},
            "devDependencies": {"tsx": "^4.0.0", "typescript": "^5.0.0"},
        }, indent=2) + "\n", written)
        _write(root / "src" / "commands.ts", "export const commands = "
               + json.dumps(ops, indent=2) + " as const;\n", written)
        _write(root / "src" / "index.ts", f"""#!/usr/bin/env node
import {{ Command }} from "commander";
import {{ commands }} from "./commands.js";

const program = new Command();
program.name("{bin_name}").description({json.dumps(spec.display_name or spec.name)});
program.option("--json", "emit JSON", true);
program.command("agent-context").action(() => {{
  console.log(JSON.stringify({{ commands }}, null, 2));
}});
program.parse();
""", written)
        _write(root / "README.md", f"""# {bin_name}

TypeScript DuckTap scaffold for **{spec.display_name or spec.name}**.

The generated command manifest includes {len(ops)} operations, including:

```text
{chr(10).join(f"{op['group']} {op['command']}  # {op['method']} {op['path']}" for op in ops[:20])}
```
""", written)
        return written


class GoCLIGenerator:
    name = "go-cli"
    target = "go-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        root = Path(out_dir) / f"{spec.name}-dt-go-cli"
        bin_name = f"{spec.name}-dt-go-cli"
        ops = _ops(spec)
        ops_json = json.dumps(ops, indent=2)
        written: list[str] = []
        _write(root / "go.mod", f"module {bin_name}\n\ngo 1.22\n", written)
        _write(root / "cmd" / bin_name / "main.go", f"""package main

import (
	"encoding/json"
	"fmt"
	"os"
)

type Operation struct {{
	Group string `json:"group"`
	Command string `json:"command"`
	Route string `json:"route"`
	Method string `json:"method"`
	Path string `json:"path"`
	Summary string `json:"summary"`
}}

var operationsJSON = {_go_raw_string(ops_json)}

func main() {{
	var operations []Operation
	if err := json.Unmarshal([]byte(operationsJSON), &operations); err != nil {{
		fmt.Fprintln(os.Stderr, err)
		os.Exit(10)
	}}
	if len(os.Args) > 1 && os.Args[1] == "agent-context" {{
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		_ = enc.Encode(map[string]any{{"commands": operations}})
		return
	}}
	fmt.Println("{bin_name}: use agent-context for the generated operation manifest")
}}
""", written)
        _write(root / "README.md", f"# {bin_name}\n\nGo DuckTap scaffold for {spec.display_name or spec.name}.\n", written)
        return written


class RustCLIGenerator:
    name = "rust-cli"
    target = "rust-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        root = Path(out_dir) / f"{spec.name}-dt-rust-cli"
        bin_name = f"{spec.name}-dt-rust-cli"
        ops = _ops(spec)
        written: list[str] = []
        _write(root / "Cargo.toml", f"""[package]
name = "{bin_name}"
version = "{spec.version}"
edition = "2021"

[dependencies]
serde_json = "1"
""", written)
        _write(root / "src" / "main.rs", f"""fn main() {{
    let commands = r#"{json.dumps(ops)}"#;
    if std::env::args().nth(1).as_deref() == Some("agent-context") {{
        println!("{{}}", commands);
    }} else {{
        println!("{bin_name}: use agent-context for the generated operation manifest");
    }}
}}
""", written)
        _write(root / "README.md", f"# {bin_name}\n\nRust DuckTap scaffold for {spec.display_name or spec.name}.\n", written)
        return written


plugins.register_generator(TypeScriptCLIGenerator())
plugins.register_generator(GoCLIGenerator())
plugins.register_generator(RustCLIGenerator())
