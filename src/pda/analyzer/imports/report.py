from typing import Any, Dict

from pda.structures import Graph


def build_cycle_report(graph: Graph[Any], *, length_bound: int, max_examples: int) -> Dict[str, Any]:
    components = graph.cycle_components(length_bound=length_bound, max_examples=max_examples)
    return {"cycle_count": len(components), "components": components}


def format_cycle_report(report: Dict[str, Any]) -> str:
    count = report["cycle_count"]
    if count == 0:
        return "No import cycles detected."

    lines = [f"Detected {count} import cycle group(s):"]
    for component in report["components"]:
        modules = ", ".join(component["modules"])
        lines.append(f"  [{component['component']}] {modules}")
        for example in component["examples"]:
            loop = " -> ".join(example + example[:1])
            lines.append(f"      {loop}")

    return "\n".join(lines)
