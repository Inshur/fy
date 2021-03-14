#!/usr/bin/env python

import os
import re
import sys
from dataclasses import dataclass
from subprocess import Popen

from ..environment.environment import Environment

try:
    from sh import tfsec
except ImportError as error:
    for command in ["tfsec"]:
        if re.search(r".*'" + command + "'.*", str(error)):
            print(f"could not find {command}(1) in path, please install {command}!")
            exit(127)


@dataclass
class Terraform:
    environment: Environment

    def init(self):
        command = "".join(
            [
                "terraform init",
                " -backend-config=",
                f"bucket={self.environment.org_id}-terraform-state-"
                f"{self.environment.region}-{self.environment.environment}-{self.environment.deployment}",
                " -backend-config=prefix=terraform.state",
            ]
        )
        print(command)
        self._exec(command)

    def modules_update(self):
        if os.environ.get("TERRAFORM_CLI_ARGS_PLAN"):
            self._exec(
                f"terraform plan {os.environ.get('TERRAFORM_CLI_ARGS_PLAN')} -out=tfplan.zip"
            )
        else:
            self._exec("terraform plan -out=tfplan.zip")

        print()
        print("extracting modules.json..")
        self._exec("unzip -qqc tfplan.zip tfconfig/modules.json > modules.json")

        print("removing tfplan.zip")
        self._exec("rm -f tfplan.zip")

    def validate(self):
        self._exec("terraform validate")

    def plan(self):
        if os.environ.get("TERRAFORM_CLI_ARGS_PLAN"):
            self._exec(f"terraform plan {os.environ.get('TERRAFORM_CLI_ARGS_PLAN')}")
        else:
            self._exec("terraform plan")

    # FIXME
    # * probably replace this with --terraform-args argument?
    def apply(self):
        if os.environ.get("TERRAFORM_CLI_ARGS_APPLY"):
            self._exec(f"terraform apply {os.environ.get('TERRAFORM_CLI_ARGS_APPLY')}")
        else:
            self._exec("terraform apply")

    def destroy(self):
        if os.environ.get("TERRAFORM_CLI_ARGS_DESTROY"):
            self._exec(
                f"terraform destroy {os.environ.get('TERRAFORM_CLI_ARGS_DESTROY')}"
            )
        else:
            self._exec("terraform destroy")

    def tfsec(self):
        # * ignore GCP002 error about unencrypted buckets since buckets are
        #   encrypted by default, see: https://github.com/liamg/tfsec/issues/137
        output = (
            tfsec(".", "--exclude=GCP002", _ok_code=[0, 1])
            .stdout.decode("UTF-8")
            .rstrip()
        )

        # trim this pointless output when no problems detected: '0 potential problems detected:'
        if output.find("No problems detected!") == -1:
            print(output)
        else:
            print("\nNo problems detected!")

    # NOTE
    # * using popen to try to fix github action output ordering..
    # * this can probably be changed back to use 'sh' since execution
    #    is now wrapped in script(1)
    def _exec(self, command):
        process = Popen(
            command,
            shell=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=self.environment.env,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        out, err = process.communicate()

        if process.returncode != 0:
            exit(process.returncode)
