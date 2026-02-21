import re
from pathlib import Path
from string import Template
from typing import Any, Dict

import yaml


class DottedTemplate(Template):
    idpattern = r"(?a:[_a-z][_a-z0-9_.]*)"


class TemplateLoader:
    def __init__(self, theme_vars: Dict[str, Any]) -> None:
        self.theme_vars = self.flatten_dict(theme_vars)

    def load(self, template_path: Path) -> Dict[str, Any]:
        template_content = template_path.read_text()
        substituted = self._substitute(template_content, template_path)
        result: Dict[str, Any] = yaml.safe_load(substituted)
        return result

    def _substitute(self, template_content: str, template_path: Path) -> str:
        try:
            return DottedTemplate(template_content).substitute(self.theme_vars)
        except KeyError as e:
            raise self._format_missing_key_error(template_path, e) from e
        except ValueError as e:
            raise self._format_invalid_placeholder_error(template_path, template_content, e) from e

    def _format_missing_key_error(self, template_path: Path, error: KeyError) -> ValueError:
        available_vars = ", ".join(sorted(self.theme_vars.keys()))
        return ValueError(
            f"Missing template variable in '{template_path}': {error}. " f"Available variables: {available_vars}"
        )

    def _format_invalid_placeholder_error(
        self, template_path: Path, template_content: str, error: ValueError
    ) -> ValueError:
        error_msg = str(error)
        match = re.search(r"line (\d+), col (\d+)", error_msg)

        if not match:
            return ValueError(f"Template error in '{template_path}': {error}")

        line_num = int(match.group(1))
        col_num = int(match.group(2))
        lines = template_content.split("\n")

        if line_num < 1 or line_num > len(lines):
            return ValueError(f"Template error in '{template_path}': {error}")

        problem_line = lines[line_num - 1]
        pointer = " " * (col_num - 1) + "^"

        return ValueError(
            f"Invalid placeholder in '{template_path}' at line {line_num}, col {col_num}:\n"
            f"  {problem_line}\n"
            f"  {pointer}\n"
            f"Check for: double dots (path_groups..key), invalid characters, or malformed ${{...}} syntax"
        )

    @staticmethod
    def flatten_dict(nested: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, str]:
        items: list[tuple[str, str]] = []

        for key, value in nested.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(TemplateLoader.flatten_dict(value, new_key, sep=sep).items())
            else:
                string = str(value)
                if string.startswith("#"):
                    string = f'"{string}"'

                items.append((new_key, string))

        return dict(items)


def flatten_dict(nested: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, str]:
    return TemplateLoader.flatten_dict(nested, parent_key, sep)
