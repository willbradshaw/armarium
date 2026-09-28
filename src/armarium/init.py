"""Create an independent vault from the starter shipped with Armarium."""

import shutil
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


def init_vault(destination: Path) -> Path:
    """Copy the starter into a new directory without modifying an existing path.

    Args:
        destination: New vault directory. Missing parents are created.

    Returns:
        Path: The resolved absolute path of the created vault.

    Raises:
        FileExistsError: The destination exists, including a dangling symlink.
        OSError: Directory creation fails, resources are unavailable, or copying
            fails. A failed copy removes the directory created by this call.
        KeyboardInterrupt: An interrupted copy is cleaned up before propagating.
    """
    destination = destination.expanduser().absolute()
    with as_file(_starter()) as source:
        # mkdir is the exclusive claim: even an empty directory or dangling
        # symlink must be refused, without relying on an earlier existence check.
        destination.mkdir(parents=True)
        try:
            shutil.copytree(source, destination, dirs_exist_ok=True)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return destination.resolve()
