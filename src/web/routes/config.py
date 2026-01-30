"""Configuration API routes for TWIZZY."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.config import load_permissions, save_permissions, PermissionsConfig

router = APIRouter()


@router.get("/permissions")
async def get_permissions():
    """Get current permissions configuration."""
    try:
        config = load_permissions()
        return config.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/permissions")
async def update_permissions(permissions: dict):
    """Update permissions configuration."""
    try:
        config = PermissionsConfig.from_dict(permissions)
        if save_permissions(config):
            return {"success": True, "message": "Permissions updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save permissions")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CapabilityToggle(BaseModel):
    capability: str
    enabled: bool


@router.post("/permissions/toggle")
async def toggle_capability(toggle: CapabilityToggle):
    """Toggle a specific capability on/off."""
    try:
        config = load_permissions()
        if toggle.capability in config.capabilities:
            config.capabilities[toggle.capability].enabled = toggle.enabled
            if save_permissions(config):
                return {
                    "success": True,
                    "capability": toggle.capability,
                    "enabled": toggle.enabled
                }
        raise HTTPException(status_code=404, detail=f"Capability not found: {toggle.capability}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-key/status")
async def get_api_key_status():
    """Check if API key is configured."""
    from ...core.config import get_kimi_api_key

    try:
        key = get_kimi_api_key()
        return {
            "configured": bool(key),
            "key_prefix": key[:10] + "..." if key else None
        }
    except Exception as e:
        return {"configured": False, "error": str(e)}


class ApiKeyRequest(BaseModel):
    api_key: str


@router.post("/api-key")
async def set_api_key(request: ApiKeyRequest):
    """Set the Kimi API key."""
    from ...core.config import set_kimi_api_key

    try:
        # Store in keychain (most secure)
        if set_kimi_api_key(request.api_key, method="keychain"):
            return {"success": True, "message": "API key saved to Keychain"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save API key")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-key/env")
async def set_api_key_env(request: ApiKeyRequest):
    """Set the Kimi API key in .env file (for development)."""
    from ...core.config import set_kimi_api_key

    try:
        if set_kimi_api_key(request.api_key, method="env"):
            return {"success": True, "message": "API key saved to .env file"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save API key")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
