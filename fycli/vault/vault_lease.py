#!/usr/bin/env python

import json
import re
import sys
from dataclasses import dataclass, field

try:
    from sh import ErrorReturnCode_2, vault
except ImportError as error:
    if re.search(r".*'vault'.*", str(error)):
        print("could not find vault(1) in path, please install vault!")
        exit(127)
    raise ImportError(error)


class VaultError(Exception):
    pass


class GCPServiceAccountKeyRateLimitError(Exception):
    pass


@dataclass
class VaultLease:
    path: str = field(init=False)
    lease: str = field(init=False)
    lease_id: str = field(init=False)

    def __str__(self):
        return f"vault path: {self.path}, lease id: {self.lease_id}]"

    def revoke(self):
        print(f"\nvault lease revoke {self.lease_id}")
        print(vault.lease.revoke(self.lease_id))
        self._revoke_cleanup()

    def _set_lease(self):
        try:
            print(f"vault read {self.path}")
            self.lease = json.loads(
                vault.read("-format=json", self.path, _err=sys.stderr).stdout.decode(
                    "UTF-8"
                )
            )
        except ErrorReturnCode_2:
            exit(2)

    def _set_lease_id(self, silent=False):
        self.lease_id = self.lease["lease_id"]
        if not silent:
            print(f"vault lease id: {self.lease_id}")
