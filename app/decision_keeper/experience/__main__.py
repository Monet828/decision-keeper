"""Experience 記録の CLI。プロセスをまたいで1つの run に追記する。

  python -m decision_keeper.experience note   --root R --run ID --text "..."
  python -m decision_keeper.experience shell  --root R --run ID --cwd D -- <argv...>
  python -m decision_keeper.experience change --root R --run ID --path P --status S --diff-file F
  python -m decision_keeper.experience target --root R --run ID --path REPO
  python -m decision_keeper.experience turn   --root R --run ID
  python -m decision_keeper.experience close  --root R --run ID [--exit-code N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .recorder import Recorder


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m decision_keeper.experience")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--root", type=Path, required=True)
        sp.add_argument("--run", required=True, help="run_xxxx 形式")
        return sp

    n = common(sub.add_parser("note"))
    n.add_argument("--text", required=True)
    n.add_argument("--kind", default="note")

    s = common(sub.add_parser("shell"))
    s.add_argument("--cwd", type=Path, default=None)
    s.add_argument("argv", nargs=argparse.REMAINDER)

    c = common(sub.add_parser("change"))
    c.add_argument("--path", required=True)
    c.add_argument("--status", default="modified")
    c.add_argument("--diff-file", type=Path, required=True)

    t = common(sub.add_parser("target"))
    t.add_argument("--path", type=Path, required=True)

    common(sub.add_parser("turn"))

    cl = common(sub.add_parser("close"))
    cl.add_argument("--exit-code", type=int, default=0)

    args = p.parse_args(argv)
    rec = Recorder.open_or_resume(args.root, args.run, cwd=getattr(args, "cwd", None))

    if args.cmd == "note":
        seq = rec.note(args.text, kind=args.kind)
        print(f"note seq={seq}")
    elif args.cmd == "shell":
        raw = [a for a in args.argv if a != "--"]
        if not raw:
            print("コマンドが指定されていません", file=sys.stderr)
            return 2
        code, out = rec.shell(raw, cwd=args.cwd)
        if out:
            print(out)
        return code
    elif args.cmd == "change":
        seq = rec.fs_change(args.path, args.status, args.diff_file.read_text(encoding="utf-8"))
        print(f"fs.change seq={seq} path={args.path}")
    elif args.cmd == "target":
        seq = rec.target_repo(args.path)
        print(f"target_repo seq={seq} path={args.path}")
    elif args.cmd == "turn":
        print(f"turn={rec.next_turn()}")
    elif args.cmd == "close":
        print(f"closed: {rec.close(exit_code=args.exit_code)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
