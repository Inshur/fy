#!/usr/bin/env python

import json
import os
import re
import sys
from dataclasses import dataclass, field
from textwrap import dedent

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from ..environment.environment import Environment, EnvironmentError

try:
    from sh import kubectl, kube_score
except ImportError as error:
    for command in ["gcloud", "kube-score", "kubectl"]:
        if re.search(r".*'" + command + "'.*", str(error)):
            print(f"could not find {command}(1) in path, please install {command}!")
            exit(127)


@dataclass
class K8sCLI:
    trace: bool
    command: str
    environment: Environment = field(init=False)

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
        if self.environment.deployment_type != "k8s_app":
            raise EnvironmentError("is this an 'k8s_app' deployment directory?")

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

    def use(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s use [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            print("\n==> kubectl diff\n")
            self._diff()
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def apply(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s apply [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument(
            "--skip-kube-score", help="skip kube-score", action="store_true"
        )
        parser.add_argument("--skip-kube-diff", help="skip diff", action="store_true")
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

            if not args.skip_kube_diff:
                print("\n==> kubectl diff\n")
                self._diff()

            print("\n==> kubectl apply\n")
            if os.environ.get("KUBECTL_CLI_ARGS_APPLY"):
                print(
                    kubectl.apply(
                        os.environ.get("KUBECTL_CLI_ARGS_APPLY"),
                        "--context",
                        self.environment.kubectl_context,
                        "-k",
                        ".",
                        _env=self.environment.env,
                    )
                    .stdout.decode("UTF-8")
                    .rstrip()
                )
            else:
                print(
                    kubectl.apply(
                        "--context",
                        self.environment.kubectl_context,
                        "-k",
                        ".",
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
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument("--skip-kube-diff", help="skip diff", action="store_true")
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

            print("\n==> kubectl kustomize\n")
            args = filter(
                None,
                [
                    os.environ.get("KUBECTL_CLI_ARGS_PLAN"),
                    "--context",
                    self.environment.kubectl_context,
                    ".",
                ],
            )
            print(
                kubectl.kustomize(*args, _env=self.environment.env,)
                .stdout.decode("UTF-8")
                .rstrip()
            )

            if not args.skip_kube_diff:
                print("\n==> kubectl diff\n")
                self._diff()
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def delete(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy k8s delete [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            print("\n==> kubectl delete\n")
            args = filter(
                None,
                [
                    os.environ.get("KUBECTL_CLI_ARGS_DELETE"),
                    "--context",
                    self.environment.kubectl_context,
                    "-k",
                    ".",
                ],
            )
            print(
                kubectl.delete(*args, _env=self.environment.env,)
                .stdout.decode("UTF-8")
                .rstrip()
            )
        except Exception as error:
            self._handle_error(error)

        self._cleanup()

    def _diff(self):
        try:
            args = filter(
                None,
                [
                    os.environ.get("KUBECTL_CLI_ARGS_DIFF"),
                    "--context",
                    self.environment.kubectl_context,
                    "-k",
                    ".",
                ],
            )
            changes = (
                kubectl.diff(*args, _ok_code=[0, 1], _env=self.environment.env,)
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
            print("\n==> kube-score\n")
            self._kube_score()
        except Exception as error:
            self._handle_error(error)

    def _kube_score(self):
        try:
            args = filter(None, [os.environ.get("KUBECTL_CLI_ARGS_KUSTOMIZE"),],)
            print(
                kube_score(
                    kubectl.kustomize(*args),
                    "score",
                    "--kubernetes-version=v1.14",
                    "-v",
                    "-",
                    _ok_code=[0, 1],
                    _env=self.environment.env,
                ).stdout.decode("UTF-8")
            )
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
