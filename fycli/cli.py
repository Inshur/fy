#!/usr/bin/env python

import os
import shutil
import sys
from textwrap import dedent

from .argparser import ExtendedHelpArgumentParser, UnrecognisedCommandError
from .dependencies.cli import DependenciesCLI  # noqa: F401
from .environment.cli import EnvCLI  # noqa: F401
from .environment.environment import EnvironmentError
from .infra.cli import InfraCLI  # noqa: F401
from .kubernetes.cli import K8sCLI  # noqa: F401
from .skeleton.cli import SkeletonCLI  # noqa: F401
from .vault.cli import VaultCLI  # noqa: F401
from .vault.vault_lease import VaultError
from .version import __version__


class DeepArgParser:
    def __init__(self):
        try:
            self.parse_args()
        except (EnvironmentError, UnrecognisedCommandError,) as error:
            print(f"{error.__class__.__name__}: {error}")
            exit(1)

    def parse_args(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy <command> [-h|--help|-v|--version]

                commands:
                  env           establish environment from deployment context
                  skeleton      manage deployment context symlinks and boilerplate manifests
                  vault         manage access to deployment target via vault
                  infra         manage infrastructure from deployment context
                  k8s           manage kubernetes deployment from app dir
                  dependencies  check fy dependencies
                """
            ),
        )

        parser.add_argument("-v", "--version", action="version", version=__version__)
        parser.add_argument("command", help="subcommand to run")

        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)

        trace = self._set_trace()

        args = parser.parse_args(sys.argv[1:2])
        subcommand = args.command
        class_name = f"{subcommand.capitalize()}CLI"

        # can't use subcommand_exists here since sys.modules has no trace attribute
        try:
            if subcommand:
                getattr(sys.modules[__name__], class_name)
        except AttributeError:
            if not trace:
                parser.error(f"Command not found: {subcommand}")
            raise

        self._header()

        try:
            getattr(sys.modules[__name__], class_name)(trace=trace, command=subcommand)
        except EnvironmentError as error:
            if not trace:
                print(f"Error: {error}")
                exit(1)
            raise
        except VaultError as error:
            if not trace:
                print(f"\nError: {error}")
                exit(1)
            raise

    def _set_trace(self):
        trace = False
        if sys.argv[1:2]:
            first_arg = sys.argv[1:2][0]
            if first_arg == "-t" or first_arg == "--trace":
                trace = True

            # check for trace flag and remove from argv if present
            # so arg parsing can still function properly with subcommands
            sys.argv = [arg for arg in sys.argv if arg not in ["-t", "--trace"]]

        return trace

    @staticmethod
    def _header():
        columns = shutil.get_terminal_size((80, 20)).columns
        with open(os.path.join(os.path.dirname(__file__), "header.txt")) as header_file:
            print(header_file.read().center(columns))
        print()
        print(f"                                  {__version__}")
        print()
