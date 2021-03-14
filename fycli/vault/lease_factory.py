#!/usr/bin/env python

import os

from ..environment.environment import Environment
from .aws_lease import AWSVaultLease
from .gcp_lease import GCPVaultLease


class PlatformDetectionError(Exception):
    pass


def vault_lease():
    environment = Environment
    if environment.platform == "AWS":
        return AWSVaultLease(
            project_id=environment.project_id, role=environment.vault_role
        )
    if environment.platform == "GCP":
        return GCPVaultLease(
            project_id=environment.project_id, role=environment.vault_role
        )
    raise PlatformDetectionError(
        f"failed to detect platform from current working directory: {os.getcwd()}"
    )
