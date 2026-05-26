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
    scores.append(Score("auth", auth_score, 0.12,
                        notes=f"{len(spec.auth_schemes)} auth scheme(s)"))

    # 4. Param specificity (typed/enum/required)
    total_params = sum(len(op.params) for op in spec.operations)
    typed = sum(1 for op in spec.operations for p in op.params
                if (p.type and p.type != "string") or p.enum)
    typing_score = int((typed / max(total_params, 1)) * 100) if total_params else 80
    scores.append(Score("typed_params", typing_score, 0.12,
                        notes=f"{typed}/{total_params} params typed/enum"))

    # 5. Output artifacts exist
    out = Path(out_dir)
    cli_dir = out / f"{spec.name}-dt-cli"
    mcp_dir = out / f"{spec.name}-dt-mcp"
    skill_dir = out / "skills" / f"ducktap-{spec.name}"
    have = sum(1 for d in (cli_dir, mcp_dir, skill_dir) if d.exists())
    art_score = int((have / 3) * 100)
    scores.append(Score("artifacts", art_score, 0.12,
                        notes=f"{have}/3 expected artifact dirs present"))

    # 6. Naming uniqueness
    names = [op.operation_id for op in spec.operations]
    unique = len(set(names))
    naming_score = int((unique / max(len(names), 1)) * 100) if names else 100
    scores.append(Score("naming", naming_score, 0.12,
                        notes=f"{unique}/{len(names)} unique operation ids"))

    # Tier 2: Domain correctness
    # Check RESTful patterns, response schemas, and base_url validity
    restful_score = 0
    if spec.operations:
        rest_methods = [op.method for op in spec.operations]
        has_get = 'GET' in rest_methods
        has_post = 'POST' in rest_methods
        path_params_ok = sum(1 for op in spec.operations
                             if '{' in op.path and any(p.location == 'path' for p in op.params))
        total_path_ops = sum(1 for op in spec.operations if '{' in op.path)
        path_score = int((path_params_ok / max(total_path_ops, 1)) * 100) if total_path_ops else 100
        restful_score = int((path_score + (30 if has_get else 0) + (30 if has_post else 0) + 40) / 3)
    else:
        restful_score = 0

    has_responses = sum(1 for op in spec.operations if op.responses) if spec.operations else 0
    response_score = int((has_responses / max(nops, 1)) * 100) if nops else 0

    base_url_score = 100 if spec.base_url and spec.base_url.startswith(('http://', 'https://')) else 50

    domain_score = int((restful_score + response_score + base_url_score) / 3)
    scores.append(Score('domain_correctness', domain_score, 0.22,
                        notes=f'restful={restful_score}, responses={response_score}, base_url={base_url_score}'))

    overall = int(sum(s.score * s.weight for s in scores))
    return Scorecard(overall=overall, grade=_grade(overall), scores=scores)
