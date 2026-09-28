"""Create an independent vault from the starter shipped with Armarium."""

import shutil
import tempfile
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path


def _starter() -> Traversable:
    """Find packaged starter files, or their source in a development checkout.

    Returns:
        Traversable: The starter directory, including hidden settings files.

    Raises:
        FileNotFoundError: Neither the installed resources nor checkout contains
            the starter. A broken installation must not create an empty vault.
    """
    packaged = files("armarium").joinpath("starter")
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[2] / "vaults/starter"
    if checkout.is_dir():
        return checkout
    raise FileNotFoundError("starter files are missing; reinstall Armarium")


def init_vault(destination: Path, *, force: bool = False) -> Path:
    """Copy the starter into a new directory, optionally replacing an old one.

    Args:
        destination: New vault directory. Missing parents are created.
        force: Replace an existing directory and all its contents. Files and
            symlinks are always refused. Copy failures preserve the old directory.

    Returns:
        Path: The resolved absolute path of the created vault.

    Raises:
        FileExistsError: The destination exists without force, or is a file or
            symlink, including a dangling symlink.
        OSError: Directory creation fails, resources are unavailable, or copying
            fails. A failed copy removes the directory created by this call.
        KeyboardInterrupt: An interrupted copy is cleaned up before propagating.
    """
    destination = destination.expanduser().absolute()
    with as_file(_starter()) as source:
        if force and destination.is_dir() and not destination.is_symlink():
            workspace = Path(
                tempfile.mkdtemp(prefix=".armarium-init-", dir=destination.parent)
            )
            replacement, backup = workspace / "replacement", workspace / "original"
            try:
                shutil.copytree(source, replacement)
                destination.rename(backup)
                try:
                    replacement.rename(destination)
                except BaseException:
                    backup.rename(destination)
                    raise
                shutil.rmtree(backup)
            finally:
                # Preserve the original if restoration or backup removal fails.
                if not backup.exists():
                    shutil.rmtree(workspace)
            return destination.resolve()
        # mkdir is the exclusive claim: even an empty directory or dangling
        # symlink must be refused, without relying on an earlier existence check.
        destination.mkdir(parents=True)
        try:
            shutil.copytree(source, destination, dirs_exist_ok=True)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return destination.resolve()
