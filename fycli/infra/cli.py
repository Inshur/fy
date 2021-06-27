#!/usr/bin/env python

import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from ..dependencies.dependencies import Dependencies
from ..environment.environment import Environment, EnvironmentError
from ..skeleton.skeleton import Skeleton
from ..terraform.terraform import Terraform

@dataclass
class InfraCLI:
    trace: bool
    command: str
    environment: Environment = field(init=False)

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy infra <command> [-h|--help]

                commands:
                  init            initialize deployment with remote backend state
                  plan            dry-run
                  apply           apply deployment
                  destroy         destroy deployment
                  tfsec           run tfsec
                  modules-update   update modules.json file
                """
            )
        )

        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args(sys.argv[2:3])
        subcommand = args.command.replace("-", "_")

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

        if (not args.skip_vault and self.environment.use_vault) or args.force_vault:
            print("\n==> vault refresh\n")
            self.environment.vault_refresh()

        if (not args.skip_skeleton) or args.force_skeleton:
            print("\n==> skeleton clean\n")
            skeleton = Skeleton(environment=self.environment)
            skeleton.clean()

            print("\n==> skeleton apply\n")
            skeleton.apply()

        self.terraform = Terraform(environment=self.environment)

    def init(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy infra init [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._terraform_init()
            self._cleanup()
        except Exception as error:
            self._handle_error(error, args)

    def plan(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy infra plan [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        parser.add_argument(
            "--force-terraform-init",
            help="force terraform to initialize even if .terraform is already present",
            action="store_true",
        )
        parser.add_argument(
            "--skip-terraform-init", help="skip terraform init", action="store_true"
        )
        parser.add_argument(
            "--skip-terraform-validate",
            help="skip terraform validate",
            action="store_true",
        )
        parser.add_argument(
            "--skip-tfsec",
            help="skip tfsec",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._terraform_skip_or_init(args)
            self._terraform_skip_or_validate(args)
            self._terraform_skip_or_tfsec(args)
            self._terraform_plan()
            self._cleanup()
        except Exception as error:
            self._handle_error(error, args)

    def plan_and_apply(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy infra plan-and-apply [-h|--help]"
        )
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        parser.add_argument(
            "--force-terraform-init",
            help="force terraform to initialize even if .terraform is already present",
            action="store_true",
        )
        parser.add_argument(
            "--skip-terraform-init", help="skip terraform init", action="store_true"
        )
        parser.add_argument(
            "--skip-terraform-validate",
            help="skip terraform validate",
            action="store_true",
        )
        parser.add_argument(
            "--skip-tfsec",
            help="skip tfsec",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._terraform_skip_or_init(args)
            self._terraform_skip_or_validate(args)
            self._terraform_skip_or_tfsec(args)
            self._terraform_plan()
            self._terraform_apply()
            self._modules_update()
            self._cleanup()
        except Exception as error:
            self._handle_error(error, args)

    def apply(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy infra apply [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        parser.add_argument(
            "--force-terraform-init",
            help="force terraform to initialize even if .terraform is already present",
            action="store_true",
        )
        parser.add_argument(
            "--skip-terraform-init", help="skip terraform init", action="store_true"
        )
        parser.add_argument(
            "--skip-terraform-validate",
            help="skip terraform validate",
            action="store_true",
        )
        parser.add_argument(
            "--skip-tfsec",
            help="skip tfsec",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._terraform_skip_or_init(args)
            self._terraform_skip_or_validate(args)
            self._terraform_skip_or_tfsec(args)
            self._terraform_apply()
            self._modules_update()
            self._cleanup()
        except Exception as error:
            self._handle_error(error, args)

    def modules_update(self):
        parser = ExtendedHelpArgumentParser(
            usage="\n  fy infra modules-update [-h|--help]"
        )
        parser.add_argument(
            "--skip-skeleton", help="skip skeleton", action="store_false"
        )
        parser.add_argument(
            "--force-skeleton",
            help="force skeleton update even if _variables.auto.tfvars is already present",
            action="store_true",
        )
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
        parser.add_argument(
            "-s", "--skip-version-check", help="skip dependency version check", action="store_true"
        )
        parser.add_argument(
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        parser.add_argument(
            "--skip-environment", help="skip environment", action="store_true"
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._modules_update()
            self._cleanup()
        except Exception as error:
            self._handle_error(error, args)

    def tfsec(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy infra tfsec [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
            action="store_true",
        )
        parser.add_argument(
            "--force-terraform-init",
            help="force terraform to initialize even if .terraform is already present",
            action="store_true",
        )
        parser.add_argument(
            "--skip-terraform-init", help="skip terraform init", action="store_true"
        )
        parser.add_argument(
            "--skip-terraform-validate",
            help="skip terraform validate",
            action="store_true",
        )
        parser.add_argument(
            "--skip-tfsec",
            help="skip tfsec",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._terraform_skip_or_init(args)
            self._terraform_skip_or_validate(args)
            self._tfsec(args)
            self._cleanup()
        except Exception as error:
            self._handle_error(error, args)

    def destroy(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy infra destroy [-h|--help]")
        parser.add_argument("--skip-vault", help="skip vault", action="store_true")
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
            "--force-vault",
            help="force use of vault even if a gcp account is already active",
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
        parser.add_argument(
            "--skip-terraform-validate",
            help="skip terraform validate",
            action="store_true",
        )
        args = parser.parse_args(sys.argv[3:])

        self._setup(args)

        try:
            self._terraform_skip_or_init(args)
            self._terraform_skip_or_validate(args)
            self._terraform_destroy()
            self._cleanup()
        except Exception as error:
            self._handle_error(error, args)

    def _terraform_skip_or_init(self, args):
        # if (
        #    not args.skip_terraform_init and not self._terraform_initialized()
        # ) or args.force_terraform_init:
        #    self._terraform_init()
        # FIXME: quick fix to always run init
        if (not args.skip_terraform_init) or args.force_terraform_init:
            self._terraform_init()

    def _terraform_init(self):
        print("\n==> terraform init\n")
        self.terraform.init()

    def _terraform_skip_or_validate(self, args):
        if not args.skip_terraform_validate:
            self._terraform_validate()

    def _terraform_validate(self):
        print("\n==> terraform validate\n")
        self.terraform.validate()

    def _terraform_skip_or_plan(self, args):
        if not args.skip_terraform_plan:
            self._terraform_plan()

    def _terraform_plan(self):
        print("\n==> terraform plan\n")
        self.terraform.plan()

    def _modules_update(self):
        print("\n==> update terraform module data\n")
        self.terraform.modules_update()

    def _terraform_skip_or_apply(self, args):
        if not args.skip_terraform_apply:
            self._terraform_apply()

    def _terraform_apply(self):
        print("\n==> terraform apply\n")
        self.terraform.apply()

    def _tfsec(self, args):
        if not args.skip_tfsec:
            print("==> tfsec")
            self.terraform.tfsec()

    def _terraform_skip_or_tfsec(self, args):
        if not args.skip_tfsec:
            self._tfsec(args)

    def _terraform_skip_or_destroy(self, args):
        if not args.skip_terraform_destroy:
            self._terraform_destroy()

    def _terraform_destroy(self):
        print("\n==> terraform destroy\n")
        self.terraform.destroy()

    @staticmethod
    def _skeleton_exists():
        return Path("_variables.auto.tfvars").exists()

    @staticmethod
    def _terraform_initialized():
        return Path(".terraform").exists()

    def _handle_error(self, error, args):
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
