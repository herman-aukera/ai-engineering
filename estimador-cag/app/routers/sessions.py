"""
LAYER: routers/session-memory
RESPONSIBILITY: Expose Session 05 conversational estimation endpoints.
WHY IT EXISTS: Keeps multipart session flow separate from the legacy /api/v1
               estimator route while reusing the same service layer.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.guardrails.input import evaluate_input_guardrails
from app.schemas.estimation import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.attachments import (
    AttachmentExtractionError,
    extract_upload_text,
    format_attachments_for_prompt,
)
from app.services.llm_service import estimate_product
from app.services.sessions import global_session_store

router = APIRouter(tags=["sessions"])
TierName = Literal["flash", "pro", "backup", "backup_pro"]



def _assistant_content_for_model_history(result: dict) -> str:
    """Return assistant history in model friendly structured form, not UI Markdown."""

    structured_result = result.get("result")
    if hasattr(structured_result, "model_dump_json"):
        return structured_result.model_dump_json()

    if isinstance(structured_result, dict):
        return json.dumps(structured_result, ensure_ascii=False)

    return str(result.get("text") or "")


@router.post("/sessions")
def create_session() -> dict[str, str]:
    """Create an empty volatile in process estimation session."""

    session = global_session_store.create_session()
    return {"session_id": session.session_id}


@router.get("/sessions/{session_id}")
def read_session(session_id: str) -> dict:
    """Return lightweight session diagnostics for the Streamlit metadata panel."""

    try:
        session = global_session_store.require_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown session_id") from exc

    return {
        "session_id": session.session_id,
        "project_metadata": session.project_metadata.model_dump(mode="json"),
        "history_turns": session.history.turn_count,
        "max_history_turns": session.history.max_turns,
    }


@router.post("/sessions/{session_id}/estimate")
async def estimate_session(
    session_id: str,
    transcript: Annotated[str, Form(min_length=20)],
    project_type: Annotated[ProjectType, Form()] = ProjectType.WEB_SAAS,
    detail_level: Annotated[DetailLevel, Form()] = DetailLevel.MEDIUM,
    output_format: Annotated[OutputFormat, Form()] = OutputFormat.PHASES_TABLE,
    tier: Annotated[TierName | None, Form()] = None,
    prompt_version: Annotated[str, Form(pattern=r"^v[0-9]+$")] = "v1",
    attachments: Annotated[list[UploadFile] | None, File()] = None,
) -> dict:
    """Estimate one turn in a session using multipart transcript plus attachments."""

    try:
        session = global_session_store.require_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown session_id") from exc

    guardrail_decision = evaluate_input_guardrails(transcript)
    if not guardrail_decision.allowed:
        raise HTTPException(status_code=400, detail=guardrail_decision.to_detail())

    extracted_attachments = []
    for upload in attachments or []:
        try:
            extracted_attachments.append(await extract_upload_text(upload))
        except AttachmentExtractionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    attachments_text = format_attachments_for_prompt(extracted_attachments)
    attachment_names = [attachment.filename for attachment in extracted_attachments]

    try:
        request = EstimationRequest(
            description=transcript,
            project_type=project_type,
            detail_level=detail_level,
            output_format=output_format,
            tier=tier,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    conversation_history = session.history.to_messages_list(system_prompt="")[1:]

    try:
        result = estimate_product(
            request,
            tier=tier,
            prompt_version=prompt_version,
            project_metadata=session.project_metadata,
            attachments_text=attachments_text,
            conversation_history=conversation_history,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=502, detail=f"Provider timed out: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Provider failed: {exc}") from exc

    assistant_text = result.get("text") or ""
    assistant_history_content = _assistant_content_for_model_history(result)
    session.add_turn(user_content=transcript, assistant_content=assistant_history_content)
    session.update_metadata(
        transcript=f"{transcript}\n\n{attachments_text}",
        assistant_text=assistant_text,
        attachment_names=attachment_names,
    )

    result["session_id"] = session.session_id
    result["project_metadata"] = session.project_metadata.model_dump(mode="json")
    result["history_turns"] = session.history.turn_count
    result["max_history_turns"] = session.history.max_turns
    result["attachments_processed"] = attachment_names
    return result
