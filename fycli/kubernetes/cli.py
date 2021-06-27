#!/usr/bin/env python

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

import yaml

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from ..dependencies.dependencies import Dependencies
from ..environment.environment import Environment, EnvironmentError

try:
    from sh import kubectl, kube_score, kapp
except ImportError as error:
    for command in ["gcloud", "kube-score", "kubectl", "kapp"]:
        if re.search(r".*'" + command + "'.*", str(error)):
            print(f"Could not find {command}(1) in path, please install {command}!")
            exit(127)


@dataclass
class K8sCLI:
    trace: bool
    command: str
    environment: Environment = field(init=False)
    manifest_type: any = field(init=False)

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy k8s <command> [-h|--help]

                commands:
                  plan       dry-run - output manifests
                  apply      apply deployment
                  delete     delete deployment

                  diff       show differences between local and remote config
                  score      run kube-score
                  use        switch kubectl to use current deployment directory context
                """
            ),
        )

        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args(sys.argv[2:3])
        subcommand = args.command

        subcommand_exists(self, parser, subcommand)

        self.environment = Environment()
        self.environment.initialize_gcp()

        getattr(self, subcommand)()

    def _setup(self, args, disable_gcloud_sandbox=False):
        if not args.skip_version_check:
            Dependencies().check()

        if self.environment.deployment_type != "k8s_app":
            raise EnvironmentError("is this an 'k8s_app' deployment directory?")

        self._detect_manifest_dir_type()

        if not args.skip_environment:
            print(self.environment.pretty_print(args, obfuscate=True))

        if (not args.skip_vault and self.environment.use_vault) or args.force_vault:
            print("\n==> vault refresh\n")
            self.environment.vault_refresh()

        if disable_gcloud_sandbox:
            try:
                del self.environment.env["KUBECONFIG"]
            except KeyError:
                pass

        self.environment.activate_container_cluster_context()

    def _detect_manifest_dir_type(self):
        fy_deployment_config_file = Path(
            self.environment.deployment_path, ".fy.yaml.skip"
        )
        kustomization_config_file = Path(
            self.environment.deployment_path, "kustomization.yaml"
        )

        if Path(fy_deployment_config_file).exists():
            with open(fy_deployment_config_file) as file:
                try:
                    config = yaml.safe_load(file)
                    self.manifest_type = (
                        config.get("kubernetes").get("deployment").get("type")
                    )
                except AttributeError as error:
                    raise EnvironmentError(
                        "file .fy.yaml.skip exists but has no key: kubernetes.deployment.type"
                    ) from error
        elif Path(kustomization_config_file).exists():
            self.manifest_type = "kustomize"
        else:
            self.manifest_type = "kubectl"

        if self.manifest_type not in [
            "kustomize-kapp",
            "kapp",
            "kustomize",
            "kubectl",
        ]:
            raise EnvironmentError(
                f"file .fy.yaml.skip config set to unknown type: {self.manifest_type}"
            )

    def use(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s use [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
        parser.add_argument(
            "-s", "--skip-version-check", help="skip dependency version check", action="store_true"
        )
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument(
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        try:
            self._setup(args, disable_gcloud_sandbox=True)
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def diff(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s diff [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
        parser.add_argument(
            "-s", "--skip-version-check", help="skip dependency version check", action="store_true"
        )
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument(
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._diff()
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def apply(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s apply [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
        parser.add_argument(
            "-s", "--skip-version-check", help="skip dependency version check", action="store_true"
        )
        parser.add_argument(
            "--skip-diff", help="skip diff", action="store_true"
        )
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument(
            "--skip-kube-score", help="skip kube-score", action="store_true"
        )
        parser.add_argument(
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        try:
            self._setup(args)

            if not args.skip_kube_score:
                print("\n==> kube-score\n")
                self._kube_score()

            kubectl_args = filter(None, [os.environ.get("KUBECTL_CLI_ARGS_APPLY")])

            if self.manifest_type == "kubectl":
                if not args.skip_diff:
                    self._diff()

                print("\n==> kubectl apply\n")
                print(
                    kubectl.apply(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "-f",
                        ".",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kustomize":
                if not args.skip_diff:
                    self._diff()

                print("\n==> kustomize | kubectl apply\n")
                print(
                    kubectl.apply(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "-k",
                        ".",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kapp":
                print("\n==> kapp deploy\n")
                app_name = Path(self.environment.deployment_path).parts[-1]
                print(
                    kapp.deploy(
                        *kubectl_args,
                        "--diff-changes",
                        "--kubeconfig-context",
                        self.environment.kubectl_context,
                        "-a",
                        app_name,
                        "-f",
                        ".",
                        "--yes",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kustomize-kapp":
                print("\n==> kustomize | kapp deploy\n")
                app_name = Path(self.environment.deployment_path).parts[-1]
                print(
                    kapp.deploy(
                        kubectl.kustomize(
                            *kubectl_args,
                            "--context",
                            self.environment.kubectl_context,
                            ".",
                            _env=self.environment.env,
                        ),
                        "--diff-changes",
                        "--kubeconfig-context",
                        self.environment.kubectl_context,
                        "-a",
                        app_name,
                        "-f",
                        "-",
                        "--yes",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def plan(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s plan [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
        parser.add_argument(
            "-s", "--skip-version-check", help="skip dependency version check", action="store_true"
        )
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument(
            "--skip-diff", help="skip diff", action="store_true"
        )
        parser.add_argument(
            "--skip-kube-score", help="skip kube-score", action="store_true"
        )
        parser.add_argument(
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        try:
            self._setup(args)

            if not args.skip_kube_score:
                print("\n==> kube-score\n")
                self._kube_score()

            kubectl_args = filter(None, [os.environ.get("KUBECTL_CLI_ARGS_APPLY")])

            if self.manifest_type == "kubectl":
                if not args.skip_diff:
                    self._diff()

                print("\n==> kubectl apply --dry-run")
                print(
                    kubectl.apply(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "--dry-run",
                        "-f",
                        ".",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kustomize":
                if not args.skip_diff:
                    self._diff()

                print("\n==> kubectl kustomize | kubectl apply --dry-run\n")
                print(
                    kubectl.apply(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "--dry-run",
                        "-k",
                        ".",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kapp":
                # NOTE: this is the equiv of plan
                print("\n==> kapp deploy --diff-run\n")
                app_name = Path(self.environment.deployment_path).parts[-1]
                print(
                    kapp.deploy(
                        *kubectl_args,
                        "--diff-run",
                        "--kubeconfig-context",
                        self.environment.kubectl_context,
                        "-a",
                        app_name,
                        "-f",
                        ".",
                        "--yes",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kustomize-kapp":
                print("\n==> kustomize | kapp deploy\n")
                app_name = Path(self.environment.deployment_path).parts[-1]
                print(
                    kapp.deploy(
                        kubectl.kustomize(
                            *kubectl_args,
                            "--context",
                            self.environment.kubectl_context,
                            ".",
                            _env=self.environment.env,
                        ),
                        "--diff-run",
                        "--kubeconfig-context",
                        self.environment.kubectl_context,
                        "-a",
                        app_name,
                        "-f",
                        "-",
                        "--yes",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def delete(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s delete [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
        parser.add_argument(
            "-s", "--skip-version-check", help="skip dependency version check", action="store_true"
        )
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument(
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        try:
            self._setup(args)

            kubectl_args = filter(None, [os.environ.get("KUBECTL_CLI_ARGS_DELETE")])

            if self.manifest_type == "kubectl":
                print("\n==> kubectl delete\n")
                print(
                    kubectl.delete(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "-f",
                        ".",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kustomize":
                print("\n==> kustomize | kubectl delete\n")
                print(
                    kubectl.delete(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "-k",
                        ".",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kapp" or self.manifest_type == "kustomize-kapp":
                print("\n==> kapp delete\n")
                app_name = Path(self.environment.deployment_path).parts[-1]
                print(
                    kapp.delete(
                        *kubectl_args,
                        "--diff-changes",
                        "--kubeconfig-context",
                        self.environment.kubectl_context,
                        "-a",
                        app_name,
                        "--yes",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def _diff(self):
        try:
            print("\n==> deployment diff\n")

            kubectl_args = filter(None, [os.environ.get("KUBECTL_CLI_ARGS_DELETE")])

            if self.manifest_type == "kubectl":
                print("diff-type: kubectl")
                changes = (
                    kubectl.diff(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "-f",
                        ".",
                        _env=self.environment.env,
                        _ok_code=[0, 1],
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kustomize":
                print("diff-type: kustomize")
                changes = (
                    kubectl.diff(
                        *kubectl_args,
                        "--context",
                        self.environment.kubectl_context,
                        "-k",
                        ".",
                        _env=self.environment.env,
                        _ok_code=[0, 1],
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kapp":
                print("diff-type: kapp")
                app_name = Path(self.environment.deployment_path).parts[-1]
                changes = (
                    kapp.deploy(
                        *kubectl_args,
                        "--diff-run",
                        "--kubeconfig-context",
                        self.environment.kubectl_context,
                        "-a",
                        app_name,
                        "-f",
                        ".",
                        "--yes",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

            elif self.manifest_type == "kustomize-kapp":
                print("diff-type: kustomize-kapp")
                app_name = Path(self.environment.deployment_path).parts[-1]
                changes = (
                    kapp.deploy(
                        kubectl.kustomize(
                            *kubectl_args,
                            "--context",
                            self.environment.kubectl_context,
                            ".",
                            _env=self.environment.env,
                        ),
                        "--diff-run",
                        "--kubeconfig-context",
                        self.environment.kubectl_context,
                        "-a",
                        app_name,
                        "-f",
                        "-",
                        "--yes",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )

        except Exception as error:
            self._handle_error(error)

        if changes:
            print(changes)
        else:
            print("no changes!")

    def score(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s score [-h|--help]")
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )

        try:
            self._detect_manifest_dir_type()
            print("\n==> kube-score\n")
            self._kube_score()
        except Exception as error:
            self._handle_error(error)

    def _kube_score(self):
        try:
            if (
                self.manifest_type == "kustomize"
                or self.manifest_type == "kustomize-kapp"
            ):
                kubectl_args = filter(
                    None,
                    [os.environ.get("KUBECTL_CLI_ARGS_KUSTOMIZE")],
                )
                print(
                    kube_score(
                        kubectl.kustomize(*kubectl_args),
                        "score",
                        "--kubernetes-version=v1.14",
                        "-v",
                        "-",
                        _ok_code=[0, 1],
                        _env=self.environment.env,
                    ).stdout.decode("UTF-8")
                )

            else:
                kubectl_args = filter(
                    None,
                    [os.environ.get("KUBECTL_CLI_ARGS_KUSTOMIZE")],
                )
                for manifest in list(
                    Path(self.environment.deployment_path).glob("*.yaml")
                ):
                    output = kube_score(
                        "score",
                        "--kubernetes-version=v1.14",
                        "-v",
                        manifest,
                        _ok_code=[0, 1],
                        _env=self.environment.env,
                    ).stdout.decode("UTF-8")

                    if output:
                        print(output)
        except Exception as error:
            self._handle_error(error)

    def _client_email(self):
        with open(self.environment.google_application_credentials, "r") as file:
            return json.load(file)["client_email"]

    def _gcp_account_active(self):
        return self.environment.gcp_account_original

    def _handle_error(self, error):
        print("\n==> exception caught!")
        self._cleanup()
        print("\n==> stack trace\n")
        raise

    def _cleanup(self):
        print("\n==> initializing clean-up")
        if self.environment.use_vault:
            self.environment.vault_cleanup()
        else:
            print("\nnothing to do")
