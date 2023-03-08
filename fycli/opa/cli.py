#!/usr/bin/env python

import sys
from dataclasses import dataclass, field
from textwrap import dedent
from pathlib import Path

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from ..dependencies.dependencies import Dependencies
from ..environment.environment import Environment, EnvironmentError
from ..skeleton.skeleton import Skeleton
from ..terraform.terraform import Terraform
from .opa import Opa


@dataclass
class OpaCLI:
    trace: bool
    command: str
    environment: Environment = field(init=False)
    opa: Opa = field(init=False)

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy opa <command> [-h|--help]

                commands:
                  run      Run OPA verification
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

    def _setup(self, args):
        if not args.skip_version_check:
            Dependencies().check()

        if self.environment.deployment_type != "infra":
            raise EnvironmentError("is this an 'infra' deployment directory?")

        if not args.skip_environment:
            print(self.environment.pretty_print(args, obfuscate=True))

        if (not args.skip_skeleton) or args.force_skeleton:
            print("\n==> skeleton clean\n")
            skeleton = Skeleton(environment=self.environment)
            skeleton.clean()

            print("\n==> skeleton apply\n")
            skeleton.apply()

        self.terraform = Terraform(environment=self.environment)
        terraform_initialized = Path(".terraform").exists()
        if (not args.skip_terraform_init) or args.force_terraform_init:
            print("\n==> terraform init\n")
            self.terraform.init()

    def run(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy opa rn [-h|--help]")
        parser.add_argument(
            "-s", "--skip-version-check", help="skip dependency version check", action="store_true"
        )
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        parser.add_argument(
            "--skip-skeleton", help="skip skeleton", action="store_true"
        )
        parser.add_argument(
            "--force-skeleton",
            help="force skeleton update even if _variables.auto.tfvars is already present",
            action="store_true",
        )
        parser.add_argument(
            "--skip-terraform-init", help="skip terraform init", action="store_true"
        )
        parser.add_argument(
            "--force-terraform-init",
            help="force terraform to initialize even if .terraform is already present",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self.opa = Opa(environment=self.environment, terraform=self.terraform)
            self.opa.run()
        except Exception as error:
            self._handle_error(error, args)

    def _handle_error(self, error, args):
        print("\n==> exception caught!")
        print("\n==> stack trace\n")
        raise


