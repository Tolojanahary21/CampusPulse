"""Archive/restaure le volume privé, utilisé par database-backup.ps1."""

import argparse
from pathlib import Path, PurePosixPath
import tarfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("backup", "verify", "restore"))
    parser.add_argument("--storage", default="/app/storage")
    parser.add_argument("--archive", default="/backup/uploads.tar.gz")
    args = parser.parse_args()
    storage = Path(args.storage).resolve()
    archive = Path(args.archive)
    storage.mkdir(parents=True, exist_ok=True)
    if args.action == "backup":
        with tarfile.open(archive, "w:gz", dereference=False) as target:
            for item in sorted(storage.rglob("*")):
                if item.is_symlink() or not (item.is_file() or item.is_dir()):
                    raise ValueError("Le stockage contient une entrée non régulière.")
                target.add(item, arcname=item.relative_to(storage).as_posix(), recursive=False)
        return
    if any(storage.iterdir()):
        raise ValueError("La restauration exige un volume uploads entièrement vide.")
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or "\\" in member.name:
                raise ValueError("Chemin interdit dans l’archive.")
            if not (member.isfile() or member.isdir()):
                raise ValueError("Liens et entrées spéciales interdits dans l’archive.")
            resolved = (storage / member.name).resolve()
            if not resolved.is_relative_to(storage):
                raise ValueError("Le chemin sort du stockage cible.")
        if args.action == "restore":
            source.extractall(storage, members=members, filter="data")


if __name__ == "__main__":
    main()
