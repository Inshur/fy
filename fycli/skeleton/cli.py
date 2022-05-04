#!/usr/bin/env python

import sys
from dataclasses import dataclass, field
from textwrap import dedent

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from ..environment.environment import Environment
from .skeleton import Skeleton


@dataclass
class SkeletonCLI:
    trace: bool
    command: str
    environment: Environment = field(init=False)

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy skeleton <command> [-h|--help]

                commands:
                  apply      apply skeleton to current directory
                  clean      remove skeleton from current directory
                  refresh    run clean then apply
                """
            ),
        )

        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args(sys.argv[2:3])
        subcommand = args.command

        subcommand_exists(self, parser, subcommand)

        self.environment = Environment()
        self.skeleton = Skeleton(environment=self.environment)

        getattr(self, subcommand)()

    def apply(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy skeleton apply [-h|--help]")
        parser.parse_args(sys.argv[3:4])

        print("\n==> skeleton apply\n")
        self.skeleton.apply()

    def clean(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy skeleton clean [-h|--help]")
        parser.parse_args(sys.argv[3:4])

        print("\n==> skeleton clean\n")
        self.skeleton.clean()

    def refresh(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy skeleton refresh [-h|--help]")
        parser.parse_args(sys.argv[3:4])

        self.clean()
        self.apply()
