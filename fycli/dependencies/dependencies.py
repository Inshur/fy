#!/usr/bin/env python

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pkg_resources import parse_version

try:
    from sh import fy, gcloud, kube_score, kubectl, terraform, tfsec, vault
except ImportError as error:
    for command in [
        "fy",
        "gcloud",
        "kube_score",
        "kubectl",
        "terraform",
        "tfsec",
        "vault",
    ]:
        if re.search(r".*'" + command + "'.*", str(error)):
            print(f"Could not find {command}(1) in path, please install {command}!")
            exit(127)


@dataclass
class Dependencies:
    def check(self):
        lockfile = self._lockfile()

        if not lockfile:
            print("Error: no fy dependency lockfile detected!")
            exit(1)

        failed = False
        config = self._load(lockfile)

        print("==> version checks\n")

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
                kubectl.version(output="json").stdout.decode("UTF-8").strip()
            )
            version = self._remove_prefix(output["clientVersion"]["gitVersion"], "v")

        elif executable == "terraform":
            output = json.loads(
                terraform.version(json=True).stdout.decode("UTF-8").strip()
            )
            version = output["terraform_version"]

        elif executable == "vault":
            output = vault.version().stdout.decode("UTF-8").strip()
            version = self._remove_prefix(self._strip_ansi_reset(output), "Vault v")

        elif executable == "kube-score":
            output = kube_score.version().stdout.decode("UTF-8").strip()
            version = output.split(" ")[2].rstrip(",")

        elif executable == "tfsec":
            output = tfsec(version=True).stdout.decode("UTF-8").strip()
            version = self._remove_prefix(output, "v")

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
