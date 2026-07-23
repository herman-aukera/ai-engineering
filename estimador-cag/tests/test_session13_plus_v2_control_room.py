from __future__ import annotations

from app.ui.control_room_v2 import (
    V2_STAGES,
    build_structure_action,
    editor_rows_from_estimation,
    modules_from_editor_rows,
    stage_progress,
)


def _estimation() -> dict:
    return {
        "stage": "structure",
        "requirements": [
            {"requirement_id": "req-auth", "text": "Authenticate users."},
            {"requirement_id": "req-audit", "text": "Audit changes."},
        ],
        "modules": [
            {
                "module_id": "mod-auth",
                "name": "Identity",
                "description": "Authentication and audit",
                "tasks": [
                    {
                        "task_id": "task-login",
                        "name": "Login",
                        "description": "Secure login",
                        "category": "backend",
                        "requirement_ids": ["req-auth", "req-audit"],
                        "estimate": {
                            "hours_low": 16,
                            "hours_expected": 20,
                            "hours_high": 24,
                            "hourly_rate_eur": 100,
                            "confidence": 0.8,
                        },
                    }
                ],
            }
        ],
    }


def test_v2_wizard_has_all_product_stages() -> None:
    assert V2_STAGES == (
        "Context",
        "Reformulation",
        "Structure",
        "Evidence",
        "Estimation",
        "Critic & Boss",
        "Human approval",
        "Audit",
    )
    assert stage_progress("structure") == 3 / 8
    assert stage_progress("completed") == 1.0


def test_visual_editor_round_trips_multiple_tasks_without_json() -> None:
    rows = editor_rows_from_estimation(_estimation())
    rows.append(
        {
            "module_id": "mod-auth",
            "module_name": "Identity",
            "module_description": "Authentication and audit",
            "task_id": "task-logout",
            "task_name": "Logout",
            "task_description": "Invalidate sessions",
            "category": "backend",
            "requirement_ids": "req-auth",
            "hours_low": 4,
            "hours_expected": 6,
            "hours_high": 8,
            "hourly_rate_eur": 100,
            "confidence": 0.9,
        }
    )

    modules = modules_from_editor_rows(rows)

    assert len(modules) == 1
    assert [task["task_id"] for task in modules[0]["tasks"]] == [
        "task-login",
        "task-logout",
    ]
    assert modules[0]["total_hours"] == 26
    assert modules[0]["total_cost_eur"] == 2600


def test_structure_action_uses_typed_visible_editor_values() -> None:
    action = build_structure_action(
        estimation=_estimation(),
        rows=editor_rows_from_estimation(_estimation()),
        expected_revision=4,
        reason="Reviewed visually.",
    )
    assert action["gate"] == "structure"
    assert action["action"] == "edit"
    assert action["expected_revision"] == 4
    assert action["modules"][0]["tasks"][0]["task_id"] == "task-login"
