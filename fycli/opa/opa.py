#!/usr/bin/env python

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from jinja2 import Environment as JinjaEnv, FileSystemLoader
from ..environment.environment import Environment
from ..terraform.terraform import Terraform
from subprocess import check_output, CalledProcessError


@dataclass
class Opa:
    environment: Environment
    terraform: Terraform
    rego_file: dict = field(init=False)

    def __post_init__(self):
        self.environment.initialize_gcp()
        self.environment.initialize_opa()

    def run(self):
        rules = self._get_ruleset()
        self.rego_files = self._generate_rego_files(rules)
        print("\n==> terraform plan\n")
        self.terraform.plan_out()
        response = True
        print("\n==> opa run\n")
        for key, filename in self.rego_files.items():
            package_name = key.replace("-", "_")
            output = self._exec(f"opa eval -i tfplan.json -d {filename} --fail-defined 'data.{package_name}.success'")
            if not output:
                response = False
                error_output = self._exec(f"opa eval -i tfplan.json -d {filename} 'data.{package_name}.deny'")
                error = json.loads(error_output)
                print("--- OPA validation errors ---\n")
                print(*error['result'][0]['expressions'][0]['value'], sep="\n")

        self.cleanup()
        if not response:
            exit(1)
        else:
            print("--- OPA verification complete ---")

    def cleanup(self):
        self._delete_file(os.path.join(self.environment.deployment_path,'tfplan.binary'))
        self._delete_file(os.path.join(self.environment.deployment_path, 'tfplan.json'))
        for key, filename in self.rego_files.items():
            self._delete_file(os.path.join(self.environment.deployment_path, filename))

    def _delete_file(self, filepath):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            else:
                print("Can not delete the file as it doesn't exists")
        except:
            print("Error while deleting file ", filepath)

    def _generate_rego_files(self, rules):
        template_dir = os.path.join(self.environment.iac_root_dir, self.environment.opa_config["template_dir"])
        file_loader = FileSystemLoader(template_dir)
        env = JinjaEnv(loader=file_loader)
        rego_files = {}
        for rule in rules:
            template = env.get_template(f"{rule}.rego.j2")
            output = template.render(opa_rules=rules[rule])
            rego_files[rule] = f"{rule}.rego"
            with open(rego_files[rule], "w") as file:
                file.write(output)

        return rego_files

    # Updates folders with a list of paths containing a rules yaml ruleset
    def _find_opa_file_parent(self, path: Path,
                              dirs,
                              dir_stop="deployment"):
        rules_file_name = self.environment.opa_config["rules_file_name"]
        if (path / rules_file_name).is_file():
            dirs.append(path / rules_file_name)
        parent = path.parent
        if parent.name != dir_stop:
            self._find_opa_file_parent(path.parent, dirs)

    def _get_ruleset(self):
        dirs = []
        self._find_opa_file_parent(Path.cwd(), dirs)
        rules = {}
        for f in dirs[::-1]:
            with open(f) as file:
                content = yaml.load(file, Loader=yaml.FullLoader)
                if not rules:
                    rules = content
                else:
                    rules = self._merge(rules, content)

        rules = self._process_value(rules)
        return rules

    def _merge(self, a, b, path=None):
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self._merge(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass  # same leaf value
                else:
                    a[key] = b[key]
            else:
                a[key] = b[key]
        return a

    def _process_value(self, a):
        for key, value in a.items():
            if isinstance(value, dict):
                self._process_value(value)
            elif type(value) is bool:
                a[key] = "true" if a[key] else "false"
            else:
                a[key] = f"\"{value}\""
        return a

    def _exec(self, command):
        try:
            out = check_output(command, shell=True, universal_newlines=True)
            return out
        except CalledProcessError:
            return False
