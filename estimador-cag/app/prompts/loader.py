"""
LAYER: prompt rendering
RESPONSIBILITY: Render versioned estimation prompts from typed request objects.
WHY IT EXISTS: Keeps product prompt text out of routers and provider code while
               making prompt versions testable and reviewable.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.schemas.estimation import EstimationRequest

PROMPT_ROOT = Path(__file__).resolve().parent


def _build_environment() -> Environment:
    """Build the Jinja2 environment used by all versioned prompt templates."""

    return Environment(
        loader=FileSystemLoader(PROMPT_ROOT),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=select_autoescape(default=False),
    )


def render_estimation_prompt(
    request: EstimationRequest,
    version: str = "v1",
) -> tuple[str, str]:
    """
    Render the system and user prompts for a typed estimation request.

    Args:
        request: Validated product estimation request.
        version: Prompt version directory under app/prompts/estimation/.

    Returns:
        A tuple of rendered system and user prompt strings.
    """

    environment = _build_environment()
    template_prefix = f"estimation/{version}"

    context = request.model_dump(mode="json")
    context["prompt_version"] = version

    system_template = environment.get_template(f"{template_prefix}/system.j2")
    user_template = environment.get_template(f"{template_prefix}/user.j2")

    return (
        system_template.render(**context).strip(),
        user_template.render(**context).strip(),
    )
