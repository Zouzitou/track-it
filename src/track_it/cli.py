from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from track_it.application import run_gui
from track_it.diagnostics import collect_diagnostics, self_test
from track_it.errors import TrackItError
from track_it.inference.models import MODELS, ModelManager
from track_it.persistence.project import ProjectStore
from track_it.utils.cancellation import CancellationToken


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="track-it", description="Local AI video masking and motion tracking"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("gui")
    sub.add_parser("diagnostics")
    sub.add_parser("self-test")
    models = sub.add_parser("models").add_subparsers(dest="models_command", required=True)
    models.add_parser("list")
    download = models.add_parser("download")
    download.add_argument("model_id", choices=sorted(MODELS))
    models.add_parser("verify")
    project = sub.add_parser("project").add_subparsers(dest="project_command", required=True)
    validate = project.add_parser("validate")
    validate.add_argument("path", type=Path)
    export = sub.add_parser("export")
    export.add_argument("project", type=Path)
    export.add_argument("--preset", required=True, choices=["mask-png"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in (None, "gui"):
            return run_gui()
        if args.command == "diagnostics":
            print(collect_diagnostics(redact=True))
            return 0
        if args.command == "self-test":
            ok, results = self_test()
            print("\n".join(results))
            return 0 if ok else 1
        if args.command == "models":
            manager = ModelManager()
            if args.models_command == "list":
                print(
                    json.dumps(
                        {
                            key: {
                                "installed": manager.path_for(key).exists(),
                                "path": str(manager.path_for(key)),
                            }
                            for key in MODELS
                        },
                        indent=2,
                    )
                )
                return 0
            if args.models_command == "download":
                path = manager.download(
                    args.model_id,
                    CancellationToken(),
                    lambda done, total: print(f"\r{done}/{total}", end=""),
                )
                print(f"\nVerified {path}")
                return 0
            for model_id in MODELS:
                if manager.path_for(model_id).exists():
                    print(f"{model_id}: {manager.verify(model_id)}")
            return 0
        if args.command == "project":
            project = ProjectStore().load(args.path)
            print(f"Valid project schema {project.schema_version}: {len(project.objects)} objects")
            return 0
        if args.command == "export":
            ProjectStore().load(args.project)
            print(
                "Project validated. Use the desktop export dialog to choose object, range, bit depth, and audio handling."
            )
            return 0
    except (TrackItError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 2
