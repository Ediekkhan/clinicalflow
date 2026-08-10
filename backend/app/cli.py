from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services.demo_cleanup import build_demo_manifest, dry_run_demo_cleanup
from app.services.terminology_import import (
    TerminologyImportError,
    checksum_bytes,
    import_payload,
    local_payload,
    publish_release,
    read_source,
    rollback_release,
    validate_release,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="python -m app.cli")
    groups = root.add_subparsers(dest="group", required=True)
    terminology = groups.add_parser("terminology")
    commands = terminology.add_subparsers(dest="command", required=True)
    for command, system in (
        ("import-icd11", "ICD-11"),
        ("import-snomed", "SNOMED-CT"),
        ("import-hpo", "HPO"),
        ("import-country", None),
    ):
        item = commands.add_parser(command)
        item.add_argument("--file", required=True)
        item.add_argument("--version", required=True)
        item.add_argument("--source-url")
        if system:
            item.set_defaults(expected_system=system)
    local = commands.add_parser("import-local")
    local.add_argument("--version", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--release-id", required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("--release-id", required=True)
    publish.add_argument("--publisher-id", required=True)
    rollback = commands.add_parser("rollback")
    rollback.add_argument("--release-id", required=True)
    rollback.add_argument("--to-release-id", required=True)
    production = groups.add_parser("production")
    production_commands = production.add_subparsers(dest="command", required=True)
    production_commands.add_parser("audit-demo-data")
    remove_demo = production_commands.add_parser("remove-demo-data")
    remove_demo.add_argument("--dry-run", action="store_true", required=True)
    return root


async def execute(args: argparse.Namespace) -> dict:
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            if args.group == "production":
                if args.command == "audit-demo-data":
                    return await build_demo_manifest(session)
                if args.command == "remove-demo-data":
                    return await dry_run_demo_cleanup(session)
            if args.command.startswith("import-") and args.command != "import-local":
                if args.command == "import-icd11" and not os.getenv("WHO_ICD11_CLIENT_ID"):
                    raise TerminologyImportError("WHO_ICD11_CLIENT_ID is required for ICD-11 imports")
                if args.command == "import-snomed" and not os.getenv("SNOMED_LICENSE_REFERENCE"):
                    raise TerminologyImportError("SNOMED_LICENSE_REFERENCE is required for SNOMED CT imports")
                payload, checksum = read_source(Path(args.file))
                result = await import_payload(
                    session,
                    payload=payload,
                    version=args.version,
                    checksum=checksum,
                    source_url=args.source_url,
                    expected_system=getattr(args, "expected_system", None),
                )
                return result.__dict__ | {"release_id": str(result.release_id)}
            if args.command == "import-local":
                payload = local_payload()
                encoded = json.dumps(payload, sort_keys=True).encode()
                result = await import_payload(
                    session,
                    payload=payload,
                    version=args.version,
                    checksum=checksum_bytes(encoded),
                    expected_system="CLINICALFLOW_LOCAL",
                )
                return result.__dict__ | {"release_id": str(result.release_id)}
            if args.command == "validate":
                return await validate_release(session, UUID(args.release_id))
            if args.command == "publish":
                release = await publish_release(session, UUID(args.release_id), UUID(args.publisher_id))
                return {"release_id": str(release.id), "status": release.status}
            if args.command == "rollback":
                await rollback_release(session, UUID(args.release_id), UUID(args.to_release_id))
                return {"release_id": args.release_id, "status": "RETIRED", "restored_release_id": args.to_release_id}
            raise TerminologyImportError("Unsupported terminology command")
    finally:
        await engine.dispose()


def main() -> int:
    args = parser().parse_args()
    try:
        print(json.dumps(asyncio.run(execute(args)), default=str))
        return 0
    except (TerminologyImportError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
