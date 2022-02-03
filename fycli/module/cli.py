#!/usr/bin/env python

import functools
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from shutil import copytree, rmtree
from textwrap import dedent

import semver
import yaml
from packaging import version
from rich.console import Console
from rich.table import Table

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists


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
        self.deployments = self._convert_deployment_dirs()

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
            usage="\n  fy module symlink -a application -v version -e environment [-h|--help]"
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
        app_directory = Path(
            self._iac_root(), "module/app", app, version, "manifests", environment
        )

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
            source = Path(self._iac_root(), "module/app", app, args.old)
            target = Path(self._iac_root(), "module/app", app, args.new)

            self._copy(source, target)
        except Exception as error:
            self._handle_error(error)

    def _copy(self, source, target, heading=True):
        print(source)
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
        latest_version = self._get_latest_version(app)
        target_version = self._bump_version(latest_version, bump_type)

        source = Path(self._iac_root(), "module/app", app, latest_version)
        target = Path(self._iac_root(), "module/app", app, target_version)

        self._copy(source, target)

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

    def _versions(self, app):
        print(f"==> available versions for application: {app}\n")
        dirs = [
            str(dir).split("/")[-1]
            for dir in Path(self._iac_root(), "module/app", app).iterdir()
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

    def _promote(self, app, old_env, new_envs, bump_type):
        old_version = self._get_deployment(old_env, app).version
        source = Path(self._iac_root(), "module/app", app, old_version)

        for new_env in self._get_envs(new_envs, app):
            if old_env == new_env:
                continue
            print(f"==> promoting {app}:{old_version}: {old_env} -> {new_env}")
            self._symlink(app, old_version, new_env, heading=False)
            print()

        if bump_type != "none":
            new_version = self._bump_version(old_version, bump_type)
            target = Path(self._iac_root(), "module/app", app, new_version)
            print(
                f"==> creating new module for {old_env}: {app}:{new_version} ({bump_type} version bump)"
            )
            print()
            self._copy(source, target, heading=False)
            print()
            print(f"==> setting application version for {old_env}: {app}:{new_version}")
            self._symlink(app, new_version, old_env, heading=False)

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

    def _get_deployment(self, environment, app):
        for deployment in self._convert_deployment_dirs(
            app=app, environment=environment
        ):
            if deployment.app == app and deployment.environment == environment:
                return deployment
        return None

    def _iac_root(self):
        if os.environ.get("FY_IAC_ROOT"):
            return os.environ.get("FY_IAC_ROOT")

        pwd = os.environ.get("PWD")
        if Path(pwd, ".fy.lock").exists() and Path(pwd, "deployment").exists():
            return pwd

        count = 0
        for dir in Path(pwd).parts:
            current_dir = str(Path(*Path(pwd).parts[:count]))
            if (
                Path(current_dir, "deployment").exists()
                and Path(current_dir, ".fy.lock").exists()
            ):
                return current_dir
            count += 1

        print(
            "error: unable to determine IAC root dir, please set FY_IAC_ROOT or re-run from a sub-directory of the IAC directory"
        )
        exit(1)

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

    # FIXME: terrible method name
    def _convert_deployment_dirs(
        self, app: str = None, version: str = None, environment: str = None
    ):
        deployment_dir = os.path.join(self._iac_root(), "deployment")
        deployments = []

        paths = []

        for path, names, filenames in os.walk(deployment_dir, followlinks=True):
            for name in names:
                paths.append(Path(path, name))
            for name in filenames:
                paths.append(Path(path, name))

        for path in paths:
            if not self._is_app_path(path):
                continue

            deployment = Deployment(path)

            if app and app != deployment.app:
                continue

            if environment and environment != deployment.environment:
                continue

            if version and version != deployment.version:
                continue

            deployments.append(deployment)

        return deployments

    def _is_app_path(self, path):
        path = Path(path)

        if not path.match("deployment/*/*/*/*/*/*/*"):
            return False

        if Path(path, "kustomization.yaml").exists():
            return True

        if path.is_symlink() and "module/app" in str(path.resolve()):
            return True

        return False

    @staticmethod
    def _is_version(name: str):
        try:
            semver.parse(name)
            return True
        except ValueError:
            return False

    def _get_latest_version(self, app):
        app_glob = os.path.join("module/app", app, "*")

        files = Path(self._iac_root()).glob(app_glob)

        versions = [x.name for x in files if x.is_dir() and self._is_version(x.name)]

        compare = functools.cmp_to_key(semver.compare)

        versions.sort(key=compare)

        return versions[len(versions) - 1]

    def _handle_error(self, error):
        print("\n==> exception caught!")
        self._cleanup()
        print("\n==> stack trace\n")
        raise error

    def _cleanup(self):
        print("\n==> initializing clean-up")


@dataclass
class Deployment:
    app: str
    version: str
    environment: str
    type: str
    path: Path

    def __init__(self, path):
        self.path = Path(path)

        if not self._is_app_path(path):
            return

        self._refresh()

    def _refresh(self):
        app, environment, version, _ = self._get_deployment(self.path)

        self.app = app
        self.environment = environment
        self.version = version
        self.type = self._type()

    def is_valid(self):
        return self._is_app_path(self.path)

    def _type(self):
        if self.path.is_symlink():
            return "symlink"

        if self.path.joinpath("kustomization.yaml").exists():
            return "kustomize"

    # FIXME: deduplicate
    def _is_app_path(self, path):
        path = Path(path)

        if not path.match("deployment/*/*/*/*/*/*/*"):
            return False

        if Path(path, "kustomization.yaml").exists():
            return True

        if path.is_symlink() and "module/app" in str(path.resolve()):
            return True

        return False

    def _get_deployment(self, path):
        path = Path(path)

        name = path.name
        environment = self._get_deployment_environment(path)
        _, version, deployment_type = self._get_deployment_module(path)

        return name, environment, version, deployment_type

    def _get_deployment_module(self, deployment_path):
        if Path(deployment_path).is_symlink():
            module_path = Path(deployment_path).resolve()
            deployment_type = "symlink"
        elif Path(deployment_path, "kustomization.yaml").exists():
            kustomization_path = Path(deployment_path, "kustomization.yaml")
            contents = self._load_yaml(kustomization_path)
            module_path = contents.get("bases")[0]
            deployment_type = "kustomize"
        else:
            return None

        matches = re.search(r"module/app/([^\/]+)/([^\/]+)", str(module_path))

        if not matches:
            return None

        app = matches.group(1)
        version = matches.group(2)

        return app, version, deployment_type

    @staticmethod
    def _get_deployment_environment(path):
        matches = re.search(r"deployment/[^\/]+/([^\/]+)", str(path))

        if not matches:
            return None

        return matches.group(1)

    @staticmethod
    def _load_yaml(path):
        with open(path) as f:
            return yaml.load(f, Loader=yaml.FullLoader)
