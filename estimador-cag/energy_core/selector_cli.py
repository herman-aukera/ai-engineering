"""CLI for the provider selector — text-based status card.

Usage:
    python -m energy_core.selector_cli list
    python -m energy_core.selector_cli show <model_id>
    python -m energy_core.selector_cli select [--provider auto] [--profile medium]
"""

from __future__ import annotations  # noqa: I001

import argparse
import json
import sys

from energy_core.selector_api import SelectRequest, SelectorAPI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EACODE Provider Selector CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all available provider models")

    show_p = sub.add_parser("show", help="Show capability detail for one model")
    show_p.add_argument("model_id", help="Model ID (e.g. k3, deepseek-v4-pro)")

    sel_p = sub.add_parser("select", help="Resolve a provider selection to a planned route")
    sel_p.add_argument("--provider", default="auto")
    sel_p.add_argument("--profile", default="medium")
    sel_p.add_argument("--context-profile", default="medium")
    sel_p.add_argument("--fallback", default="none")
    sel_p.add_argument("--premium-reason", default=None)
    sel_p.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    api = SelectorAPI()

    if args.command == "list":
        models = api.list_models()
        if args.format if hasattr(args, 'format') else True:
            print(_format_model_table(models))
        return 0

    if args.command == "show":
        detail = api.get_model(args.model_id)
        if detail is None:
            print(f"Unknown model: {args.model_id}", file=sys.stderr)
            return 1
        print(_format_detail(detail))
        return 0

    if args.command == "select":
        resp = api.select(SelectRequest(
            provider=args.provider,
            profile=args.profile,
            context_profile=getattr(args, 'context_profile', 'medium'),
            fallback_policy=args.fallback,
            premium_reason=args.premium_reason,
        ))
        fmt = getattr(args, 'format', 'text')
        if fmt == "json":
            print(resp.model_dump_json(indent=2))
        else:
            print(_format_route(resp))
        return 0 if resp.status == "ok" else 1

    return 0


def _format_model_table(models) -> str:
    lines = [
        f"{'Provider':<12} {'Surface':<18} {'Model':<28} {'Efforts':<24} {'Context':>8} {'Cache':>6}",
        "-" * 110,
    ]
    for m in models:
        efforts = ",".join(m.reasoning_efforts)
        cache = "yes" if m.supports_prompt_cache else "no"
        lines.append(
            f"{m.provider:<12} {m.surface:<18} {m.model_id:<28} {efforts:<24} {m.context_window:>8,} {cache:>6}"
        )
    return "\n".join(lines)


def _format_detail(detail) -> str:
    return "\n".join([
        f"Model:       {detail.model_id}",
        f"Provider:    {detail.provider}",
        f"Surface:     {detail.surface}",
        f"Aliases:     {', '.join(detail.aliases) or 'none'}",
        f"Family:      {detail.model_family}",
        f"Context:     {detail.context_window:,} tokens",
        f"Max output:  {detail.max_output_tokens:,} tokens",
        f"Reasoning:   modes={detail.reasoning_modes}, efforts={detail.reasoning_efforts}",
        f"Speed:       {detail.speed_class}",
        f"Tools:       {_yn(detail.supports_tools)}",
        f"Structured:  {_yn(detail.supports_structured_output)}",
        f"Vision:      {_yn(detail.supports_vision)}",
        f"Cache:       {_yn(detail.supports_prompt_cache)}",
        f"Pricing:     in={detail.pricing['input_per_1k']} cached={detail.pricing['cached_input_per_1k']} out={detail.pricing['output_per_1k']} ({detail.pricing['unit']})",
        f"Available:   {detail.availability_state}",
        f"Entitlement: {detail.entitlement_state}",
        f"Freshness:   {detail.freshness_state}",
        f"Source:      {detail.source_id} v{detail.source_version}",
    ])


def _format_route(resp) -> str:
    lines = [f"Status: {resp.status}"]
    if resp.error:
        lines.append(f"Error:  {resp.error}")
    if resp.route:
        r = resp.route
        lines.extend([
            f"Provider:       {r.provider}",
            f"Surface:        {r.resolved_surface}",
            f"Model:          {r.model_id}",
            f"Mode:           {r.reasoning_mode}",
            f"Effort:         {r.reasoning_effort}",
            f"Profile:        {r.profile}",
            f"Snapshot hash:  {r.capability_snapshot_hash}",
            f"Fallback:       {'yes' if r.fallback_used else 'no'}{' — ' + r.fallback_reason if r.fallback_reason else ''}",
        ])
    lines.append(f"\nAvailable models: {len(resp.available_models)}")
    return "\n".join(lines)


def _yn(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
