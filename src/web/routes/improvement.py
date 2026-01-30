"""Self-improvement API routes for TWIZZY."""
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@router.get("/improvements")
async def get_improvements():
    """Get list of self-improvements from git history."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--grep=AUTO-IMPROVEMENT", "-20"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        if result.returncode != 0:
            return {"improvements": [], "error": result.stderr}

        improvements = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    improvements.append({
                        "hash": parts[0],
                        "message": parts[1]
                    })

        return {"improvements": improvements}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/improvements/{commit_hash}")
async def get_improvement_details(commit_hash: str):
    """Get details of a specific improvement."""
    try:
        # Get commit message
        msg_result = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit_hash],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        # Get diff
        diff_result = subprocess.run(
            ["git", "show", "--stat", commit_hash],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        return {
            "hash": commit_hash,
            "message": msg_result.stdout.strip(),
            "diff_stat": diff_result.stdout,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ImprovementRequest(BaseModel):
    focus: str | None = None


@router.post("/improve-now")
async def trigger_improvement(request: ImprovementRequest):
    """Trigger an immediate self-improvement."""
    from ..websocket import get_manager

    try:
        manager = get_manager()
        agent = await manager._ensure_agent()

        # Import improvement scheduler
        from ...improvement.scheduler import get_scheduler

        scheduler = get_scheduler(agent)
        result = await scheduler.improve_now(focus=request.focus)

        # Broadcast improvement to all clients
        if result.get("success"):
            await manager.broadcast_improvement(result)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback/{commit_hash}")
async def rollback_to_commit(commit_hash: str):
    """Rollback to a specific commit."""
    try:
        # Verify commit exists
        verify = subprocess.run(
            ["git", "cat-file", "-t", commit_hash],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        if verify.returncode != 0:
            raise HTTPException(status_code=404, detail="Commit not found")

        # Perform rollback
        result = subprocess.run(
            ["git", "reset", "--hard", commit_hash],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Rolled back to {commit_hash}",
                "note": "Server will reload automatically"
            }
        else:
            raise HTTPException(status_code=500, detail=result.stderr)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback-last")
async def rollback_last_improvement():
    """Rollback the last improvement."""
    try:
        # Find last improvement commit
        result = subprocess.run(
            ["git", "log", "--oneline", "--grep=AUTO-IMPROVEMENT", "-1"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        if not result.stdout.strip():
            raise HTTPException(status_code=404, detail="No improvements to rollback")

        commit_hash = result.stdout.split()[0]

        # Get the parent commit
        parent = subprocess.run(
            ["git", "rev-parse", f"{commit_hash}^"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        if parent.returncode != 0:
            raise HTTPException(status_code=500, detail="Failed to find parent commit")

        parent_hash = parent.stdout.strip()

        # Rollback to parent
        rollback = subprocess.run(
            ["git", "reset", "--hard", parent_hash],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        if rollback.returncode == 0:
            return {
                "success": True,
                "message": f"Rolled back improvement {commit_hash}",
                "rolled_back_to": parent_hash,
                "note": "Server will reload automatically"
            }
        else:
            raise HTTPException(status_code=500, detail=rollback.stderr)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
