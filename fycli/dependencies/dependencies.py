#!/usr/bin/env python

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pkg_resources import parse_version

try:
    from sh import (fy, gcloud, kube_score, kubectl, terraform, tfenv, tfsec,
                    which, opa)
except ImportError as error:
    for command in [
        "fy",
        "gcloud",
        "kube_score",
        "kubectl",
        "terraform",
        "tfsec",
        "which",
        "tfenv",
        "opa"
    ]:
        if re.search(r".*'" + command + "'.*", str(error)):
            print(f"Could not find {command}(1) in path, please install {command}!")
            exit(127)


@dataclass
class Dependencies:
    def check(self):
        lockfile = self._lockfile()

        if not lockfile:
            return

        failed = False
        config = self._load(lockfile)

        print(f"==> version checks (lockfile: {lockfile})\n")

        for exe, version in config.items():
            if not version:
                raise ValueError(f"Invalid version for {exe}: {version}")

            local_version = self._local_version(exe)

            if parse_version(version) != local_version:
                print(f"Please change {exe} {local_version} to version {version}")
                failed = True
            else:
                print(f"{exe} {local_version}")

        if failed:
            exit(1)

    def _local_version(self, executable):
        if executable == "fy":
            output = fy(version=True).stdout.decode("UTF-8").strip()
            version = self._remove_prefix(output, "fycli ")

        elif executable == "gcloud":
            output = json.loads(
                gcloud.version(format="json").stdout.decode("UTF-8").strip()
            )
            version = output["Google Cloud SDK"]

        elif executable == "kubectl":
            output = json.loads(
                kubectl.version(client=True, output="json")
                .stdout.decode("UTF-8")
                .strip()
            )
            version = self._remove_suffix(
                self._remove_prefix(output["clientVersion"]["gitVersion"], "v"),
                "-dispatcher",
            )

        elif executable == "terraform":
            # Check if terraform is a symlink or tfenv bash script.. if so then run
            # tfenv install first to ensure that the correct version of terraform is
            # installed.
            #
            # This is necessary because otherwise if the terraform version isn't
            # installed but tfenv is in use then the terraform version check will fail
            # due to stdout being filled with garbage from tfenv during terraform binary
            # install.
            terraform_path = str(which("terraform"))
            if Path(terraform_path).is_symlink():
                if "tfenv" in Path(terraform_path).resolve().parts:
                    tfenv.install()
            elif "tfenv" in Path(terraform_path).parts:
                tfenv.install()

            output = json.loads(
                terraform.version(json=True).stdout.decode("UTF-8").strip()
            )
            version = output["terraform_version"]

        elif executable == "kube-score":
            output = kube_score.version().stdout.decode("UTF-8").strip()
            version = output.split(" ")[2].rstrip(",")

        elif executable == "tfsec":
            output = tfsec(version=True).stdout.decode("UTF-8").strip()
            version = self._remove_prefix(output, "v")

        elif executable == "opa":
            output = opa.version().stdout.decode("UTF-8").strip()
            version = self._remove_prefix(output.splitlines()[0], "Version:")

        else:
            raise KeyError(f"Executable not found in fy lockfile: {executable}")

        semver = parse_version(version)

        return semver

    @staticmethod
    def _load(lockfile):
        with open(lockfile, "r") as file:
            return yaml.load(file.read(), Loader=yaml.SafeLoader)

    @staticmethod
    def _lockfile():
        cwd = Path(os.environ["PWD"])
        while str(cwd) != "/":
            lockfile = Path(cwd, ".fy.lock")
            if Path(lockfile).exists():
                return lockfile
            cwd = Path(*list(cwd.parts[:-1]))
        return False

    @staticmethod
    def _strip_ansi_reset(text):
        return re.sub("\\x1b\\[0m", "", text)

    @staticmethod
    def _remove_prefix(text, prefix):
        if text.startswith(prefix):
            text = text[len(prefix) :]
        return text

    @staticmethod
    def _remove_suffix(text, suffix):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
        return text
