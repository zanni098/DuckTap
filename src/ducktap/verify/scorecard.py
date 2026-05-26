"""Quality scorecard for a generated CLI.

Scores the spec and the generated artifacts on a 0-100 scale across several
dimensions, mirroring Printing Press's `scorecard` command.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from ducktap.core.spec import APISpec


@dataclass
class Score:
    dimension: str
    score: int    # 0-100
    weight: float
    notes: str = ""


@dataclass
class Scorecard:
    overall: int
    grade: str
    scores: list[Score]

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "grade": self.grade,
            "scores": [asdict(s) for s in self.scores],
        }


def _grade(n: int) -> str:
    if n >= 90:
        return "A"
    if n >= 80:
        return "B"
    if n >= 70:
        return "C"
    if n >= 60:
        return "D"
    return "F"


def score(spec: APISpec, out_dir: str) -> Scorecard:
    scores: list[Score] = []
    out = Path(out_dir)
    package_name = spec.name.replace("-", "_")
    cli_dir = out / f"{spec.name}-dt-cli"
    cli_pkg = cli_dir / f"{package_name}_dt_cli"

    # 1. Operation coverage
    nops = len(spec.operations)
    cov = min(100, nops * 5) if nops else 0
    scores.append(Score("coverage", cov, 0.15,
                        notes=f"{nops} operations exposed"))

    # 2. Documentation: ops with summary/description
    documented = sum(1 for op in spec.operations if op.summary or op.description)
    docrate = int((documented / max(nops, 1)) * 100) if nops else 0
    scores.append(Score("documentation", docrate, 0.15,
                        notes=f"{documented}/{nops} operations have docs"))

    # 3. Auth clarity
    auth_score = 100 if spec.auth_schemes and all(s.env_var for s in spec.auth_schemes) else (
        70 if spec.auth_schemes else 50
    )
    scores.append(Score("auth", auth_score, 0.10,
                        notes=f"{len(spec.auth_schemes)} auth scheme(s)"))

    # 4. Param specificity (typed/enum/required)
    total_params = sum(len(op.params) for op in spec.operations)
    typed = sum(1 for op in spec.operations for p in op.params
                if (p.type and p.type != "string") or p.enum)
    typing_score = int((typed / max(total_params, 1)) * 100) if total_params else 80
    scores.append(Score("typed_params", typing_score, 0.10,
                        notes=f"{typed}/{total_params} params typed/enum"))

    # 5. Output artifacts exist
    mcp_dir = out / f"{spec.name}-dt-mcp"
    skill_dir = out / "skills" / f"ducktap-{spec.name}"
    have = sum(1 for d in (cli_dir, mcp_dir, skill_dir) if d.exists())
    art_score = int((have / 3) * 100)
    scores.append(Score("artifacts", art_score, 0.15,
                        notes=f"{have}/3 expected artifact dirs present"))

    # 6. Naming uniqueness
    names = [op.operation_id for op in spec.operations]
    unique = len(set(names))
    naming_score = int((unique / max(len(names), 1)) * 100) if names else 100
    scores.append(Score("naming", naming_score, 0.10,
                        notes=f"{unique}/{len(names)} unique operation ids"))

    # 7. Agent-native affordances in the generated CLI.
    main_text = (cli_pkg / "main.py").read_text(encoding="utf-8") if (cli_pkg / "main.py").exists() else ""
    commands_text = (
        (cli_pkg / "commands.py").read_text(encoding="utf-8") if (cli_pkg / "commands.py").exists() else ""
    )
    agent_tokens = (
        "--agent", "--format", "--select", "--compact", "--dry-run",
        "agent-context", "auth-doctor", "which", "profile",
    )
    agent_hits = sum(1 for token in agent_tokens if token in main_text or token in commands_text)
    agent_score = int((agent_hits / len(agent_tokens)) * 100)
    scores.append(Score("agent_native", agent_score, 0.15,
                        notes=f"{agent_hits}/{len(agent_tokens)} agent affordances present"))

    # 8. Local response lake: cached/saved data is queryable without another API call.
    mirror_text = (
        (cli_pkg / "mirror.py").read_text(encoding="utf-8") if (cli_pkg / "mirror.py").exists() else ""
    )
    data_tokens = ("records", "save_records", "query", "search", "saved_at")
    command_tokens = ("data", "query", "search")
    data_hits = sum(1 for token in data_tokens if token in mirror_text)
    command_hits = sum(1 for token in command_tokens if token in commands_text)
    data_score = int(((data_hits + command_hits) / (len(data_tokens) + len(command_tokens))) * 100)
    scores.append(Score("local_data", data_score, 0.10,
                        notes=f"{data_hits + command_hits}/{len(data_tokens) + len(command_tokens)} data features present"))

    overall = int(sum(s.score * s.weight for s in scores))
    return Scorecard(overall=overall, grade=_grade(overall), scores=scores)
