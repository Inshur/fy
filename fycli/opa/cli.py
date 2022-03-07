import os
from jinja2 import Environment, FileSystemLoader
import yaml
from pathlib import Path
from ..environment.environment import Environment as LocalEnvironment


class Opa:
    local_environment = LocalEnvironment

    def __init__(self):

        template_dir = os.path.join(os.path.dirname(__file__), "..",
                                    self.local_environment.opa_template_dir)
        file_loader = FileSystemLoader(template_dir)
        env = Environment(loader=file_loader)
        template = env.get_template(self.local_environment.opa_template_file)

        opa_rules = self.__get_ruleset()
        output = template.render(opa_rules=opa_rules)
        with open("policy_rules.rego", "w") as file:
            file.write(output)

    # Updates folders with a list of paths containing a rules yaml ruleset
    def __find_opa_file_parent(self, path: Path,
                               dirs,
                               # FIXME: replace dir_stop by stopping when there's no more opa rules file
                               dir_stop="deployment",
                               rules_file=local_environment.opa_rules_file):
        if (path / rules_file).is_file():
            dirs.append(path / rules_file)
        parent = path.parent
        if parent.name != dir_stop:
            self.__find_opa_file_parent(path.parent, dirs)

    def __get_ruleset(self):
        dirs = []
        self.__find_opa_file_parent(Path.cwd(), dirs)
        rules = {}
        for f in dirs[::-1]:
            with open(f) as file:
                content = yaml.load(file, Loader=yaml.FullLoader)
                rules = rules | content
        for key, value in rules.items():
            if type(rules[key]) is bool:
                rules[key] = "true" if rules[key] else "false"
            else:
                rules[key] = f"\"{value}\""
        return rules
