#!/usr/bin/env python

import sys
from dataclasses import dataclass, field
from textwrap import dedent

from ..argparser import ExtendedHelpArgumentParser, subcommand_exists
from ..environment.environment import Environment
from .vault_leases import VaultLeases


@dataclass
class VaultCLI:
    trace: bool
    command: str
    environment: Environment = field(init=False)

    def __post_init__(self):
        parser = ExtendedHelpArgumentParser(
            usage=dedent(
                """
                  fy vault <command> [-h|--help]

                commands:
                  read       read new cloud credentials
                  revoke     revoke local cloud credentials
                  list       list local credentials
                  roll-key   roll service-account access key
                """
            ),
        )

        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args(sys.argv[2:3])
        subcommand = args.command

        subcommand_exists(self, parser, subcommand)

        self.environment = Environment()
        self.environment.initialize_gcp()
        self.environment.initialize_vault()

        self.vault_leases = VaultLeases(environment=self.environment)

        getattr(self, subcommand)()

    # FIXME
    # * replace this with something to write out ${HOME}/.vault-token?
    # def login(self):
    #    parser = ExtendedHelpArgumentParser(usage="\n  fy vault login [-h|--help]")
    #    parser.parse_args(sys.argv[3:4])
    #    print("login..")
    #    exit(0)

    def read(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy vault read [-h|--help]")
        parser.parse_args(sys.argv[3:])

        print("\n==> vault leases read\n")
        self.vault_leases.read()

    def revoke(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy vault revoke [-h|--help]")
        parser.parse_args(sys.argv[3:])

        print("\n==> vault leases load\n")
        self.vault_leases.load()

        print("\n==> vault leases revoke")
        self.vault_leases.revoke()

    def list(self):
        parser = ExtendedHelpArgumentParser(usage="\n  fy vault list [-h|--help]")
        parser.parse_args(sys.argv[3:])

        print("\n==> vault leases load")
        self.vault_leases.load()

        print("\n==> vault leases list\n")
        self.vault_leases.list()

    # FIXME
    # * implement this
    # def roll_key(self):
    #    parser = ExtendedHelpArgumentParser(usage="\n  fy vault list [-h|--help]")
    #    parser.parse_args(sys.argv[3:])
    #    print("roll-key")
    #    exit(0)
