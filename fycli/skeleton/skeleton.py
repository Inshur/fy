#!/usr/bin/env python

import errno
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePath
import shutil

from ..environment.environment import Environment


@dataclass
class Skeleton:
    environment: Environment
    path: str = field(init=False)
    files: str = field(init=False)

    def __post_init__(self):
        self.environment.initialize_gcp()
        self.environment.initialize_skeleton()
        self._set_skeleton_path()
        self._set_files()

    def apply(self):
        self._generate_boilerplate_files()

        for file in self.files:
            dest = os.path.basename(file)
            self._symlink_f(file, dest)

        self._copy_f(
            str(
                PurePath(os.path.join(self.path, "gitignore")).relative_to(
                    self.environment.deployment_path
                )
            ),
            ".gitignore",
        )

        self._symlink_f(
            str(
                PurePath(os.path.join(self.path, "terraform.lock.hcl")).relative_to(
                    self.environment.deployment_path
                )
            ),
            ".terraform.lock.hcl",
        )

    def clean(self):
        files = list(Path(".").glob("_*"))

        for file in files:
            self._unlink(file)

        self._unlink(".gitignore")
        self._unlink(".terraform.lock.hcl")

        if (
                len(files) == 0
                and not Path(".gitignore").exists()
                and not Path(".terraform.lock.hcl").exists()
        ):
            print("nothing to do")

    def refresh(self):
        self.clean()
        self.apply()

    def _set_skeleton_path(self):
        self.path = Path(
            os.path.join(
                self.environment.deployment_path,
                "../../../../../skeleton/",
            )
        )

    def _generate_boilerplate_files(self):
        tfvars_file = "_variables.auto.tfvars"
        with open(tfvars_file, "w") as file:
            file.write("# NOTE: this file is automatically generated\n")
            for var in [
                "project_number",
                "project_id",
                "region",
                "environment",
                "environment_type",
                "deployment",
            ]:
                value = getattr(self.environment, var)
                print(f"writing: {tfvars_file} - {var}={value}")
                file.write(f'{var}="{value}"\n')

    def _set_files(self):
        self.files = [
            PurePath(file).relative_to(self.environment.deployment_path)
            for file in self.path.iterdir()
            if os.path.basename(str(file)).startswith("_")
        ]

    def _symlink_f(self, src, dest):
        try:
            print(f"symlink: {src} -> {dest}")
            os.symlink(src, dest)
        except OSError as error:
            if error.errno == errno.EEXIST:
                os.remove(dest)
                os.symlink(src, dest)

    def _unlink(self, file):
        try:
            os.remove(file)
            print(f"unlink: {file}")
        except FileNotFoundError:
            pass

    def _copy_f(self, src, dest):
        print(f"copy: {src} -> {dest}")
        shutil.copy(src, dest, follow_symlinks=True)
