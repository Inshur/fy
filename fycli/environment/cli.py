#!/usr/bin/env python

import sys
from dataclasses import dataclass, field
from textwrap import dedent

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from .environment import Environment


@dataclass
class EnvCLI:
    trace: bool
    command: str
    environment: Environment = field(init=False)

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy env <command> [-h|--help]

                commands:
                  pp         pretty print output
                  sh         output in shell sourceable format
                  json       output json format
                """
            ),
        )

        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args(sys.argv[2:3])
        subcommand = args.command

        subcommand_exists(self, parser, subcommand)

        getattr(self, subcommand)()

    def pp(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy env pp [-h|--help|-r|--raw]")
        parser.add_argument(
            "-r", "--raw", help="do not obfuscate secrets", action="store_false"
        )
        args = parser.parse_args(sys.argv[3:])

        self.environment = Environment()

        print(self.environment.pretty_print(args, obfuscate=args.raw))

    def sh(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy env sh [-h|--help|-r|--raw]")
        parser.add_argument(
            "-r", "--raw", help="do not obfuscate secrets", action="store_false"
        )
        args = parser.parse_args(sys.argv[3:])

        self.environment = Environment()

        print(self.environment.sh(args, obfuscate=args.raw))

    def json(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy env json [-h|--help]")
        parser.add_argument(
            "-r", "--raw", help="do not obfuscate secrets", action="store_false"
        )
        args = parser.parse_args(sys.argv[3:])

        self.environment = Environment()

        print(self.environment.json(args, obfuscate=args.raw))
