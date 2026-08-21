"""Canonical V2-only transport for the EACHAT production service.

The legacy ``router`` module retains coursework evaluation and benchmark surfaces.
This router deliberately reuses only the mature V2 handlers so those historical
endpoints cannot leak into the production composition root.
"""

from fastapi import APIRouter

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2Response,
    EnergyChatV2ThreadStateResponse,
)
from app.energy_chat.router import (
    chat_v2_deterministic,
    chat_v2_live,
    get_v2_thread_state,
    replay_v2_thread,
)

router = APIRouter()
router.add_api_route(
    "/v2/chat",
    chat_v2_deterministic,
    methods=["POST"],
    response_model=EnergyChatV2Response,
)
router.add_api_route(
    "/v2/chat/live",
    chat_v2_live,
    methods=["POST"],
    response_model=EnergyChatV2Response,
)
router.add_api_route(
    "/v2/threads/{thread_id}/state",
    get_v2_thread_state,
    methods=["GET"],
    response_model=EnergyChatV2ThreadStateResponse,
)
router.add_api_route(
    "/v2/threads/{thread_id}/replay",
    replay_v2_thread,
    methods=["POST"],
    response_model=EnergyChatV2Response,
)
