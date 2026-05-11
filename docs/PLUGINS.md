# Writing a DuckTap plugin

DuckTap plugins extend the pipeline without forking. Two extension points:

1. **Discoverers** — turn some input into an `APISpec`.
2. **Generators** — turn an `APISpec` into output files.

## Minimal discoverer

```python
# my_plugin/openapi_yaml_anchor.py
from typing import Any
from ducktap.core import plugins
from ducktap.core.spec import APISpec


class ExampleDiscoverer:
    name = "example"

    def can_handle(self, source: str) -> bool:
        return source.endswith(".example")

    def discover(self, source: str, **opts: Any) -> APISpec:
        return APISpec(name="example", display_name="Example")


plugins.register_discoverer(ExampleDiscoverer())
```

Register via entry point so DuckTap autoloads it:

```toml
# my_plugin/pyproject.toml
[project.entry-points."ducktap.plugins"]
example = "my_plugin.openapi_yaml_anchor"
```

`pip install my-plugin` and `ducktap plugins list` will show it.

## Minimal generator

```python
from pathlib import Path
from ducktap.core import plugins
from ducktap.core.spec import APISpec


class ReadmeGenerator:
    name = "readme"
    target = "readme"

    def generate(self, spec: APISpec, out_dir: str, **opts: dict) -> list[str]:
        p = Path(out_dir) / f"{spec.name}-README.md"
        p.write_text(f"# {spec.display_name}\n\n{spec.description}\n")
        return [str(p)]


plugins.register_generator(ReadmeGenerator())
```

Use it: `ducktap press <src> --targets readme`.

## Hooks

```python
from ducktap.core import plugins

def on_done(target, files):
    print(f"[my-plugin] {target} -> {len(files)} files")

plugins.register_hook("generate.done", on_done)
```

Events: `discovery.start`, `discovery.done`, `generate.start`, `generate.done`.

## Conventions

- `name` must be unique. Use the same `name` your `--from <name>` flag accepts.
- `can_handle` must be cheap (no network). Heavy work belongs in `discover`.
- Generators write to `out_dir`. Return a list of every file written so the
  scorecard and shipcheck can find them.
- Don't catch `KeyboardInterrupt` — let users `Ctrl-C` cleanly.
