"""Nonilion Virtual Office Room communication client and payload builder."""

import logging
from typing import Dict, Any, List, Optional
import httpx

from app.config import NONILION_CALLBACK_URL, PUBLIC_BASE_URL
from app.database.store import db

logger = logging.getLogger("NonilionOfficeClient")


def build_nonilion_response(
    text: str,
    content: str = "",
    files: Optional[List[Dict[str, str]]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    voice_text: str = ""
) -> Dict[str, Any]:
    """Constructs a compliant Nonilion Virtual Office JSON response payload."""
    files_payload = []
    if files:
        for f in files:
            name = f.get("name", "artifact")
            url = f.get("url")
            if not url:
                url = f"{PUBLIC_BASE_URL}/files/{name}"
            files_payload.append({"name": name, "url": url})

    actions_payload = actions or []
    
    # If no custom voice_text provided, generate a clean summary from text
    v_text = voice_text or text[:120].replace("*", "").replace("#", "")

    return {
        "text": text,
        "content": content or text,
        "files": files_payload,
        "actions": actions_payload,
        "voice_text": v_text,
    }


async def push_async_room_notification(payload: Dict[str, Any]):
    """Asynchronously pushes real-time lifecycle event updates to Nonilion room callback if configured."""
    if not NONILION_CALLBACK_URL:
        return

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(NONILION_CALLBACK_URL, json=payload)
            if resp.status_code == 200:
                logger.info("Pushed async room notification to Nonilion.")
            else:
                logger.warning(f"Nonilion callback returned status {resp.status_code}.")
    except Exception as exc:
        logger.warning(f"Failed to deliver async room notification: {exc}")
