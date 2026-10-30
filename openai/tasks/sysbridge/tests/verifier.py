"""Dependency-free, data-only verifier, copied into the separate Harbor verifier.

Never import or execute a submission. Malformed answers receive zero; invalid
trusted grading material fails the process (an infrastructure error).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

MAX_BYTES = 64 * 1024
MAX_DEPTH = 12
SCORER_VERSION = "agentre-structured-v1"


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("non-finite number")


def parse(raw: bytes):
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized answer")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                      parse_constant=_constant)


def matches_shape(value, shape, depth=0):
    if depth > MAX_DEPTH:
        return False
    if isinstance(shape, dict):
        return (type(value) is dict and set(value) == set(shape)
                and all(matches_shape(value[k], v, depth + 1)
                        for k, v in shape.items()))
    if isinstance(shape, list):
        return (len(shape) == 1 and type(value) is list and len(value) <= 128
                and all(matches_shape(v, shape[0], depth + 1) for v in value))
    if shape == "integer":
        return type(value) is int and -(2**63) <= value < 2**64
    if shape == "boolean":
        return type(value) is bool
    if shape == "string":
        return type(value) is str and len(value) <= 256
    return False


def validate_contract(contract):
    if (contract.get("schema_version") != 1 or not contract.get("expected")
            or set(contract["expected"]) != set(contract.get("answer_shape", {}))):
        raise ValueError("invalid trusted contract")
    for group, expected in contract["expected"].items():
        if not matches_shape(expected, contract["answer_shape"][group]):
            raise ValueError("invalid trusted answer shape")


def grade(raw: bytes | None, contract: dict) -> dict:
    validate_contract(contract)
    result = {"scorer_version": SCORER_VERSION, "reward": 0.0,
              "partial_credit": 0.0, "valid_submission": False,
              "status": "missing_submission" if raw is None else "invalid_submission",
              "submission_sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None}
    if raw is None:
        return result
    try:
        answer = parse(raw)
        if (type(answer) is not dict or set(answer) != {"schema_version", "answers"}
                or type(answer["schema_version"]) is not int or answer["schema_version"] != 1
                or type(answer["answers"]) is not dict):
            return result
        groups = answer["answers"]
        if not set(groups) <= set(contract["expected"]):
            return result
        if not all(matches_shape(v, contract["answer_shape"][k]) for k, v in groups.items()):
            return result
    except (ValueError, UnicodeError, RecursionError):
        return result
    # One vote per complete reasoning group. No field-wise guessing bonus.
    matched = sum(k in groups and groups[k] == v for k, v in contract["expected"].items())
    result.update(reward=float(matched == len(contract["expected"])),
                  partial_credit=matched / len(contract["expected"]),
                  valid_submission=True, status="graded")
    return result


def read_submission(path: Path) -> bytes | None:
    """Reject symlinks, FIFOs, devices and oversize input without following them."""
    # Harbor transfers the submission directory into a fresh verifier. Check
    # parents as well, so a symlinked directory cannot redirect the read.
    if any(p.is_symlink() for p in (path, *path.parents)):
        return b""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError:
        return b""
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            return b""
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read(MAX_BYTES + 1)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path("/tests/contract.json"))
    parser.add_argument("--submission", type=Path,
                        default=Path("/workspace/submission/answer.json"))
    parser.add_argument("--output", type=Path, default=Path("/logs/verifier"))
    args = parser.parse_args()
    contract = parse(args.contract.read_bytes())
    result = grade(read_submission(args.submission), contract)
    args.output.mkdir(parents=True, exist_ok=True)
    # Keep the reward channel binary. Partial credit is separately named and
    # never mistaken for full-task success by a future GRPO consumer.
    (args.output / "reward.txt").write_text(f'{result["reward"]:.1f}\n')
    (args.output / "grade.json").write_text(json.dumps(result, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
