#!/usr/bin/env python

import sys
from argparse import ArgumentParser


class UnrecognisedCommandError(Exception):
    pass


class UnrecognisedSubcommandError(Exception):
    pass


def subcommand_exists(object, parser, subcommand, command_type="Subcommand"):
    try:
        if subcommand:
            getattr(object, subcommand)
    except AttributeError as error:
        if not object.trace:
            parser.error(f"{command_type} not found: {subcommand}")
        raise UnrecognisedSubcommandError from error


class ExtendedHelpArgumentParser(ArgumentParser):
    def error(self, message):
        sys.stderr.write("Error: %s\n\n" % message)
        self.print_help()
        exit(2)
