#!/usr/bin/env python

import sys
from dataclasses import dataclass
from textwrap import dedent

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from .dependencies import Dependencies


@dataclass
class DependenciesCLI:
    trace: bool
    command: str

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy dependencies <command> [-h|--help]

                commands:
                  check      check versions
                """
            ),
        )

        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args(sys.argv[2:3])
        subcommand = args.command

        subcommand_exists(self, parser, subcommand)

        getattr(self, subcommand)()

    def check(self):
        Dependencies().check()
