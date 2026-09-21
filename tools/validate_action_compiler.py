"""Offline software checks only; never starts native robot or model services."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--full-suite', action='store_true')
    p.add_argument('--lint', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    commands = [[sys.executable, '-m', 'pytest', '-q'] + ([] if args.full_suite else ['tests/action_compiler']),
                [sys.executable, '-m', 'physical_harness.action_compiler', 'demo', '--output',
                 str((args.output/'fixture').resolve())]]
    if args.lint:
        commands.append([sys.executable, '-m', 'ruff', 'check', '.'])
    rows = []
    for index, command in enumerate(commands):
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                    timeout=600, check=False)
            output, code = result.stdout+result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            output, code = 'Software validation subprocess timed out.\n', 124
        (args.output/f'check-{index}.log').write_text(output)
        rows.append({'command': command, 'returncode': code})
        if code:
            break
    passed = len(rows) == len(commands) and all(r['returncode'] == 0 for r in rows)
    report = {'passed': passed, 'scope': 'software-only', 'native_motion': False,
              'model_inference': False, 'checks': rows}
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
