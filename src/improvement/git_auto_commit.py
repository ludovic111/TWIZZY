"""Git auto-commit and push system for TWIZZY self-improvements.

This module handles automatic GitHub commits after each self-improvement:
- Commits changes with descriptive messages
- Pushes to GitHub automatically
- Handles authentication via SSH or token
- Provides status notifications
- Falls back gracefully on failures
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GitCommitResult:
    """Result of a git commit and push operation."""
    success: bool
    commit_hash: Optional[str]
    message: str
    pushed: bool
    timestamp: datetime
    files_changed: list[str]
    error: Optional[str] = None


class GitAutoCommit:
    """Automatic git commit and push for self-improvements."""
    
    def __init__(self, project_root: Path):
        """Initialize the git auto-commit system.
        
        Args:
            project_root: Root directory of the git repository
        """
        self.project_root = project_root
        self._enabled = True
        self._last_result: Optional[GitCommitResult] = None
        
    def is_enabled(self) -> bool:
        """Check if auto-commit is enabled."""
        return self._enabled
        
    def set_enabled(self, enabled: bool):
        """Enable or disable auto-commit."""
        self._enabled = enabled
        logger.info(f"Git auto-commit {'enabled' if enabled else 'disabled'}")
        
    async def _run_git(self, *args, check: bool = True) -> tuple[bool, str, str]:
        """Run a git command.
        
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "git", *args,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            
            if process.returncode != 0 and check:
                return False, stdout_str, stderr_str
            return True, stdout_str, stderr_str
            
        except Exception as e:
            return False, "", str(e)
    
    async def is_git_repo(self) -> bool:
        """Check if project root is a git repository."""
        success, _, _ = await self._run_git("rev-parse", "--git-dir", check=False)
        return success
    
    async def has_remote(self) -> bool:
        """Check if repository has a remote configured."""
        success, output, _ = await self._run_git("remote", check=False)
        return success and bool(output.strip())
    
    async def get_remote_url(self) -> Optional[str]:
        """Get the origin remote URL."""
        success, output, _ = await self._run_git("remote", "get-url", "origin", check=False)
        return output if success else None
    
    async def has_changes_to_commit(self) -> bool:
        """Check if there are changes to commit."""
        success, output, _ = await self._run_git("status", "--porcelain", check=False)
        return success and bool(output.strip())
    
    async def get_changed_files(self) -> list[str]:
        """Get list of changed files."""
        success, output, _ = await self._run_git("status", "--porcelain", check=False)
        if not success:
            return []
        
        files = []
        for line in output.split("\n"):
            if line.strip():
                # Format: XY filename or XY "filename with spaces"
                status = line[:2]
                filename = line[3:].strip().strip('"')
                files.append(f"[{status.strip()}] {filename}")
        return files
    
    async def get_current_branch(self) -> Optional[str]:
        """Get the current git branch."""
        success, output, _ = await self._run_git("branch", "--show-current", check=False)
        return output if success else None
    
    async def stage_all_changes(self) -> bool:
        """Stage all changes in the repository."""
        success, _, stderr = await self._run_git("add", "-A")
        if not success:
            logger.error(f"Failed to stage changes: {stderr}")
            return False
        return True
    
    async def commit(self, message: str, description: str = "") -> tuple[bool, Optional[str]]:
        """Commit staged changes.
        
        Args:
            message: Commit message (first line)
            description: Extended commit description
            
        Returns:
            Tuple of (success, commit_hash)
        """
        full_message = message
        if description:
            full_message += f"\n\n{description}"
        
        success, _, stderr = await self._run_git("commit", "-m", full_message)
        if not success:
            logger.error(f"Failed to commit: {stderr}")
            return False, None
        
        # Get the commit hash
        success, commit_hash, _ = await self._run_git("rev-parse", "HEAD")
        if success:
            return True, commit_hash[:8]
        return True, None
    
    async def push(self, branch: Optional[str] = None) -> tuple[bool, str]:
        """Push commits to remote.
        
        Args:
            branch: Branch to push (defaults to current)
            
        Returns:
            Tuple of (success, message)
        """
        if not branch:
            branch = await self.get_current_branch()
            if not branch:
                return False, "Could not determine current branch"
        
        # Check if remote exists
        if not await self.has_remote():
            return False, "No remote configured"
        
        # Push to remote
        success, stdout, stderr = await self._run_git("push", "origin", branch)
        
        if success:
            return True, f"Pushed to origin/{branch}"
        
        # Check for common errors
        if "rejected" in stderr.lower():
            # Try to pull first
            logger.warning("Push rejected, attempting to pull and retry...")
            pull_success, _, pull_err = await self._run_git("pull", "origin", branch, "--rebase")
            if pull_success:
                # Retry push
                success, stdout, stderr = await self._run_git("push", "origin", branch)
                if success:
                    return True, f"Pushed to origin/{branch} (after rebase)"
            return False, f"Push rejected and rebase failed: {pull_err}"
        
        if "could not resolve" in stderr.lower() or "could not read" in stderr.lower():
            return False, f"Authentication failed - check SSH key or token: {stderr}"
        
        return False, f"Push failed: {stderr}"
    
    async def commit_and_push_improvement(
        self,
        title: str,
        description: str,
        improvement_id: str,
        files_changed: list[str],
    ) -> GitCommitResult:
        """Commit and push an improvement automatically.
        
        Args:
            title: Short title of the improvement
            description: Detailed description
            improvement_id: Unique ID for the improvement
            files_changed: List of files that were changed
            
        Returns:
            GitCommitResult with status
        """
        timestamp = datetime.now()
        
        if not self._enabled:
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message="Auto-commit is disabled",
                pushed=False,
                timestamp=timestamp,
                files_changed=files_changed,
                error="Auto-commit disabled"
            )
        
        # Check if we're in a git repo
        if not await self.is_git_repo():
            error_msg = "Not a git repository"
            logger.error(error_msg)
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message=error_msg,
                pushed=False,
                timestamp=timestamp,
                files_changed=files_changed,
                error=error_msg
            )
        
        # Check if there are changes to commit
        if not await has_changes_to_commit(self):
            return GitCommitResult(
                success=True,
                commit_hash=None,
                message="No changes to commit",
                pushed=False,
                timestamp=timestamp,
                files_changed=[],
                error=None
            )
        
        # Get current changed files for the result
        changed_files = await self.get_changed_files()
        
        # Stage all changes
        if not await self.stage_all_changes():
            error_msg = "Failed to stage changes"
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message=error_msg,
                pushed=False,
                timestamp=timestamp,
                files_changed=changed_files,
                error=error_msg
            )
        
        # Build commit message
        commit_message = f"🤖 AUTO-IMPROVEMENT: {title}"
        commit_description = f"""{description}

📊 Improvement Details:
- ID: {improvement_id}
- Files Changed: {len(files_changed)}
- Timestamp: {timestamp.isoformat()}

📝 Changed Files:
{chr(10).join(f"  - {f}" for f in files_changed)}

🤖 Auto-generated by TWIZZY self-improvement system
✅ Committed and pushed automatically
"""
        
        # Commit
        commit_success, commit_hash = await self.commit(commit_message, commit_description)
        
        if not commit_success:
            error_msg = "Failed to commit changes"
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message=error_msg,
                pushed=False,
                timestamp=timestamp,
                files_changed=changed_files,
                error=error_msg
            )
        
        logger.info(f"Committed improvement: {commit_hash}")
        
        # Push to remote
        push_success, push_message = await self.push()
        
        if not push_success:
            # Commit succeeded but push failed - this is recoverable
            logger.warning(f"Committed but push failed: {push_message}")
            return GitCommitResult(
                success=True,  # Commit succeeded
                commit_hash=commit_hash,
                message=f"Committed locally but push failed: {push_message}",
                pushed=False,
                timestamp=timestamp,
                files_changed=changed_files,
                error=push_message
            )
        
        logger.info(f"Pushed improvement to GitHub: {commit_hash}")
        
        result = GitCommitResult(
            success=True,
            commit_hash=commit_hash,
            message=f"Successfully committed and pushed: {title}",
            pushed=True,
            timestamp=timestamp,
            files_changed=changed_files,
            error=None
        )
        
        self._last_result = result
        return result
    
    async def commit_and_push_manual_changes(
        self,
        message: str,
        description: str = ""
    ) -> GitCommitResult:
        """Commit and push manual changes (non-improvement commits).
        
        Args:
            message: Commit message
            description: Extended description
            
        Returns:
            GitCommitResult with status
        """
        timestamp = datetime.now()
        
        if not await self.is_git_repo():
            error_msg = "Not a git repository"
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message=error_msg,
                pushed=False,
                timestamp=timestamp,
                files_changed=[],
                error=error_msg
            )
        
        if not await self.has_changes_to_commit():
            return GitCommitResult(
                success=True,
                commit_hash=None,
                message="No changes to commit",
                pushed=False,
                timestamp=timestamp,
                files_changed=[],
                error=None
            )
        
        changed_files = await self.get_changed_files()
        
        if not await self.stage_all_changes():
            error_msg = "Failed to stage changes"
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message=error_msg,
                pushed=False,
                timestamp=timestamp,
                files_changed=changed_files,
                error=error_msg
            )
        
        commit_success, commit_hash = await self.commit(message, description)
        
        if not commit_success:
            error_msg = "Failed to commit"
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message=error_msg,
                pushed=False,
                timestamp=timestamp,
                files_changed=changed_files,
                error=error_msg
            )
        
        push_success, push_message = await self.push()
        
        return GitCommitResult(
            success=True,
            commit_hash=commit_hash,
            message=f"Committed: {message}" + (" (pushed)" if push_success else f" (push failed: {push_message})"),
            pushed=push_success,
            timestamp=timestamp,
            files_changed=changed_files,
            error=None if push_success else push_message
        )
    
    def get_last_result(self) -> Optional[GitCommitResult]:
        """Get the result of the last commit operation."""
        return self._last_result
    
    async def get_commit_history(self, limit: int = 10) -> list[dict]:
        """Get recent commit history.
        
        Args:
            limit: Number of commits to retrieve
            
        Returns:
            List of commit info dicts
        """
        success, output, _ = await self._run_git(
            "log",
            f"-{limit}",
            "--pretty=format:%H|%s|%an|%ai",
            check=False
        )
        
        if not success or not output:
            return []
        
        commits = []
        for line in output.split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "author": parts[2],
                    "timestamp": parts[3],
                    "is_improvement": "AUTO-IMPROVEMENT" in parts[1] or "🤖" in parts[1]
                })
        
        return commits


# Global instance
_auto_commit: Optional[GitAutoCommit] = None


def get_git_auto_commit(project_root: Optional[Path] = None) -> GitAutoCommit:
    """Get the global GitAutoCommit instance.
    
    Args:
        project_root: Project root directory (auto-detected if not provided)
        
    Returns:
        GitAutoCommit instance
    """
    global _auto_commit
    if _auto_commit is None:
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        _auto_commit = GitAutoCommit(project_root)
    return _auto_commit


# Convenience function for quick commits
async def auto_commit_improvement(
    title: str,
    description: str,
    improvement_id: str,
    files_changed: list[str],
    project_root: Optional[Path] = None
) -> GitCommitResult:
    """Quick function to commit and push an improvement.
    
    Args:
        title: Improvement title
        description: Improvement description
        improvement_id: Unique improvement ID
        files_changed: List of changed files
        project_root: Project root (auto-detected if not provided)
        
    Returns:
        GitCommitResult
    """
    committer = get_git_auto_commit(project_root)
    return await committer.commit_and_push_improvement(
        title, description, improvement_id, files_changed
    )
