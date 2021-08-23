#!/usr/bin/env python

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from shutil import copytree, rmtree
from textwrap import dedent

import semver
from packaging import version
from rich.console import Console
from rich.table import Table

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from .utils import get_deployments, get_latest_version


@dataclass
class ModuleCLI:
    trace: bool
    command: str
    deployments: any = field(init=False)

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy module <command> [-h|--help]

                commands:
                  list       list applications and show which environments reference
                             which module versions

                  copy       create a copy of a module version, specifying target
                             version

                  bump       create a copy of a module bumping the version using bump
                             type of either major, minor, or patch

                  symlink    create a symlink from a deployment to an application module
                             version

                  promote    promote a module version to target environment(s) and create
                             a new version for the original environment. Target supports
                             single env, CSV, or env-type, e.g: test0, test0,test1, or test
                """
            ),
        )

        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args(sys.argv[2:3])
        subcommand = args.command

        subcommand_exists(self, parser, subcommand)

        getattr(self, subcommand)()

    def _setup(self):
        self.deployments = get_deployments()

    def list(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy k8s list [-a application] [-h|--help]"
        )
        parser.add_argument("-a", "--application", help="specify application")

        args = parser.parse_args(sys.argv[3:])

        try:
            self._setup()
            self._list(args)
        except Exception as error:
            self._handle_error(error)

    def _environment_number_collections(self):
        environment_number_collections = {}

        for deployment in self.deployments:
            environment_number = re.match(r"[a-z]+([0-9]+)$", deployment.environment)[1]

            if environment_number not in environment_number_collections.keys():
                environment_number_collections[environment_number] = "-"

        return environment_number_collections

    def _get_deployments(self):
        environment_number_collections = self._environment_number_collections()

        collection = {}
        for deployment in self.deployments:
            environment_type = re.sub(r"[0-9]+$", "", deployment.environment)
            environment_number = re.match(r"[a-z]+([0-9]+)$", deployment.environment)[1]

            if deployment.app not in collection.keys():
                collection[deployment.app] = {
                    "dev": environment_number_collections.copy(),
                    "test": environment_number_collections.copy(),
                    "prod": environment_number_collections.copy(),
                }

            collection[deployment.app][environment_type][
                environment_number
            ] = deployment.version

        return collection

    # desired output:
    # foo | dev0 / 1.0  | test0 / 2.0 | prod0 / 3.0 |
    #     | -           | test1 / 2.0 | prod1 / 3.0 |
    #     | -           | test2 / 2.0 | prod2 / 3.0 |

    # data structure:
    # {
    #   "app1": {
    #     "dev":   { 0: "0.0.1", 1: "-", 2: "-",         200: "1.0.0" }
    #     "test":  { 0: "0.0.1", 1: "0.0.2", 2: "0.0.3", 200: "-"}
    #     "prod":  { 0: "0.0.1", 1: "0.0.2", 2: "0.0.3", 200: "-"}
    #   },
    #   "app2": {}
    # }

    def _list(self, args):
        table = Table()
        table.add_column("App")
        table.add_column("Dev")
        table.add_column("Test")
        table.add_column("Prod")
        table.add_column("Env. No.")

        environment_number_collections = self._environment_number_collections()

        for app, environments in self._get_deployments().items():
            if app in [
                "secret-manager",
                "descheduler-duplicate-pods",
                "monitoring",
            ]:
                continue

            if args.application and args.application != app:
                continue

            # probably could replace this with transpose?
            first_iteration = True
            for environment_number in sorted(environment_number_collections.keys()):
                if first_iteration:
                    row = [app]
                else:
                    row = [""]
                for environment in ["dev", "test", "prod"]:
                    version = environments[environment][environment_number]
                    if version == "-":
                        row.append("-")
                    else:
                        row.append(f"{environment}{environment_number} / {version}")

                table.add_row(*row, environment_number)
                first_iteration = False

            table.add_row(*["", "", "", "", ""])

        console = Console()
        console.print(table)

    def symlink(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy k8s symlink -a application -v version -e environment [-h|--help]"
        )
        parser.add_argument(
            "-a", "--application", help="specify application", required=True
        )
        parser.add_argument("-v", "--version", help="specify version", required=True)
        parser.add_argument(
            "-e", "--environment", help="specify environment", required=True
        )

        args = parser.parse_args(sys.argv[3:])

        try:
            self._setup()
            app = args.application
            version = args.version
            environment = args.environment
            self._symlink(app, version, environment)
        except Exception as error:
            self._handle_error(error)

    def _symlink(self, app, version, environment, heading=True):
        app_directory = Path("module/app", app, version, "manifests", environment)

        # don't bother checking to see if module has been templated until templating is
        # built into FY
        # if not app_directory.exists():
        #    print(
        #        f"error: target application directory does not exist: {app_directory}"
        #    )
        #    exit(1)

        deployment_path = self._get_deployment(environment, app).path

        os.unlink(deployment_path)

        relative_path = Path(
            os.path.relpath(os.environ.get("PWD"), deployment_path.parent)
        ).joinpath(app_directory)

        if heading:
            print(f"\n==> creating symlink: {deployment_path} -> {relative_path}")
        else:
            print(f"\ncreating symlink: {deployment_path} -> {relative_path}")
        os.symlink(relative_path, deployment_path)

    def copy(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy module copy -a application -o old_version -n new_version [-h|--help]"
        )
        parser.add_argument(
            "-a", "--application", help="specify application", required=True
        )
        parser.add_argument(
            "-o", "--old", help="specify old module version", required=True
        )
        parser.add_argument(
            "-n", "--new", help="specify new module version", required=True
        )

        args = parser.parse_args(sys.argv[3:])

        try:
            app = args.application
            source = Path("module/app", app, args.old)
            target = Path("module/app", app, args.new)

            self._copy(source, target)
        except Exception as error:
            self._handle_error(error)

    def _copy(self, source, target, heading=True):
        if not Path(source).exists():
            print(f"error: source module does not exist: {source}")
            exit(1)

        if Path(target).exists():
            print(f"error: target module already exists: {target}")
            exit(1)

        if heading:
            print(f"==> copying module: {source} -> {target}")
        else:
            print(f"copying module: {source} -> {target}")
        copytree(source, target)

        manifest_dir = Path(target, "manifests")

        if Path(manifest_dir).exists():
            print(f"\n==> cleaning manifest dirs: {manifest_dir}")
            rmtree(manifest_dir)

    def bump(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy module bump -a application -t (major|minor|patch) [-h|--help]"
        )
        parser.add_argument(
            "-a", "--application", help="specify application", required=True
        )
        parser.add_argument(
            "-t",
            "--type",
            help="specify bump type",
            required=True,
            choices=["major", "minor", "patch"],
        )

        args = parser.parse_args(sys.argv[3:])

        try:
            app = args.application
            bump_type = args.type
            self._bump(app, bump_type)
        except Exception as error:
            self._handle_error(error)

    def _bump(self, app, bump_type):
        latest_version = get_latest_version(app)
        target_version = self._bump_version(latest_version, bump_type)

        source = Path("module/app", app, latest_version)
        target = Path("module/app", app, target_version)

        self._copy(app, source, target)

    @staticmethod
    def _bump_version(version, bump_type):
        return str(getattr(semver.VersionInfo.parse(version), f"bump_{bump_type}")())

    def versions(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy module versions -a application [-h|--help]"
        )
        parser.add_argument(
            "-a", "--application", help="specify application", required=True
        )

        args = parser.parse_args(sys.argv[3:])

        try:
            app = args.application
            self._versions(app)
        except Exception as error:
            self._handle_error(error)

    @staticmethod
    def _versions(app):
        print(f"==> available versions for application: {app}\n")
        dirs = [
            str(dir).split("/")[-1]
            for dir in Path("module/app", app).iterdir()
            if str(dir).split("/")[-1] != "archived"
        ]

        for file in sorted(dirs, key=lambda x: version.Version(x)):
            print(f" * {file}")
        print()

    def promote(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy module promote -a application -o old_env -n new_env -t (major|minor|patch|none) [-h|--help]"
        )
        parser.add_argument(
            "-a", "--application", help="specify application", required=True
        )
        parser.add_argument(
            "-o", "--old-env", help="specify old environment", required=True
        )
        parser.add_argument(
            "-n",
            "--new-envs",
            help="specify new environment(s) (csv) or environment-type",
            required=True,
        )
        parser.add_argument(
            "-t",
            "--type",
            help="specify bump type",
            required=True,
            choices=["major", "minor", "patch", "none"],
        )

        args = parser.parse_args(sys.argv[3:])

        try:
            self._setup()
            app = args.application
            old_env = args.old_env
            new_envs = args.new_envs
            bump_type = args.type
            self._promote(app, old_env, new_envs, bump_type)
        except Exception as error:
            self._handle_error(error)

    def _get_envs(self, envs, app):
        # CSV
        if re.search(",", envs):
            return envs.split(",")

        # single env
        elif re.search(r"[0-9]", envs):
            return [envs]

        # must be env_type
        else:
            deployments = self._get_deployments()
            return [
                f"{envs}{env_no}"
                for (env_no, version) in deployments[app][envs].items()
                if version != "-"
            ]

    def _promote(self, app, old_env, new_envs, bump_type):
        old_version = self._get_deployment(old_env, app).version
        source = Path("module/app", app, old_version)

        for new_env in self._get_envs(new_envs, app):
            if old_env == new_env:
                continue
            print(f"==> promoting {app}:{old_version}: {old_env} -> {new_env}")
            self._symlink(app, old_version, new_env, heading=False)
            print()

        if bump_type != "none":
            new_version = self._bump_version(old_version, bump_type)
            target = Path("module/app", app, new_version)
            print(
                f"==> creating new module for {old_env}: {app}:{new_version} ({bump_type} version bump)"
            )
            print()
            self._copy(source, target, heading=False)
            print()
            print(f"==> setting application version for {old_env}: {app}:{new_version}")
            self._symlink(app, new_version, old_env, heading=False)

    @staticmethod
    def _get_deployment(environment, app):
        for deployment in get_deployments(app=app, environment=environment):
            if deployment.app == app and deployment.environment == environment:
                return deployment

        return None

    def _handle_error(self, error):
        print("\n==> exception caught!")
        self._cleanup()
        print("\n==> stack trace\n")
        raise error

    def _cleanup(self):
        print("\n==> initializing clean-up")
