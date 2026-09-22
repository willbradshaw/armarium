"""Acceptance smoke test: isolated wheel install, unrelated cwd, fresh vault copies."""

import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path


def main() -> None:
    """Install the built artifact and prove it runs without importing checkout code."""
    repository = Path(__file__).resolve().parents[1]
    wheel = next((repository / "dist").glob("armarium-*.whl"))
    with tempfile.TemporaryDirectory(prefix="armarium wheel ") as temporary:
        work = Path(temporary)
        environment = work / "environment"
        venv.create(environment, with_pip=True)
        python = environment / "bin/python"
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        subprocess.run(
            [str(python), "-m", "pip", "install", str(wheel)],
            check=True,
            cwd=work,
            env=env,
        )
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "import armarium, sys; assert armarium.__file__.startswith(sys.prefix)",
            ],
            check=True,
            cwd=work,
            env=env,
        )
        for source in sorted((repository / "vaults").iterdir()):
            if not source.is_dir() or source.name.startswith("."):
                continue
            copied = work / f"{source.name} vault with spaces"
            shutil.copytree(source, copied)
            before = {
                p.relative_to(copied): p.read_bytes()
                for p in copied.rglob("*")
                if p.is_file()
            }
            subprocess.run(
                [str(environment / "bin/armarium"), "validate", str(copied)],
                check=True,
                cwd=work,
                env=env,
            )
            after = {
                p.relative_to(copied): p.read_bytes()
                for p in copied.rglob("*")
                if p.is_file()
            }
            assert before == after
        print("Wheel installation and read-only vault checks passed.")


if __name__ == "__main__":
    main()
