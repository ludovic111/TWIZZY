"""
Default diagnostic checks for TWIZZY Doctor.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Callable, List, Dict

from .doctor import CheckResult, CheckSeverity


# Type alias for check functions
Check = Callable[[], CheckResult]

# Registry of all checks
_registered_checks: List[Check] = []


def register_check(func: Check) -> Check:
    """Decorator to register a check."""
    _registered_checks.append(func)
    return func


def check_python_version() -> CheckResult:
    """Check Python version is 3.11+."""
    version = sys.version_info
    passed = version >= (3, 11)
    
    return CheckResult(
        name="Python Version",
        passed=passed,
        severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
        message=f"Python {version.major}.{version.minor}.{version.micro}" + 
                ("" if passed else " - Python 3.11+ required"),
        details={"version": f"{version.major}.{version.minor}.{version.micro}"}
    )


def check_virtual_env() -> CheckResult:
    """Check if running in virtual environment."""
    in_venv = (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )
    
    return CheckResult(
        name="Virtual Environment",
        passed=in_venv,
        severity=CheckSeverity.WARNING,
        message="Running in virtual environment" if in_venv else "Not in virtual environment (recommended)",
        fix_available=not in_venv,
        fix_message="Create venv with: python3 -m venv .venv"
    )


def check_dependencies() -> CheckResult:
    """Check if required dependencies are installed."""
    required = [
        "fastapi",
        "uvicorn",
        "websockets",
        "httpx",
        "keyring",
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
            
    passed = len(missing) == 0
    
    return CheckResult(
        name="Dependencies",
        passed=passed,
        severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
        message=f"All dependencies installed" if passed else f"Missing: {', '.join(missing)}",
        details={"missing": missing},
        fix_available=not passed,
        fix_message=f"pip install {' '.join(missing)}"
    )


def check_api_key() -> CheckResult:
    """Check if API key is configured."""
    try:
        import keyring
        api_key = keyring.get_password('com.twizzy.agent', 'kimi_api_key')
        
        passed = api_key is not None and len(api_key) > 0
        
        return CheckResult(
            name="API Key",
            passed=passed,
            severity=CheckSeverity.CRITICAL if not passed else CheckSeverity.INFO,
            message="API key configured" if passed else "API key not configured",
            details={"configured": passed},
            fix_available=not passed,
            fix_message="Set API key in web UI or: python -c \"import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'YOUR_KEY')\""
        )
    except Exception as e:
        return CheckResult(
            name="API Key",
            passed=False,
            severity=CheckSeverity.ERROR,
            message=f"Error checking API key: {e}",
            fix_available=False
        )


def check_permissions_file() -> CheckResult:
    """Check if permissions config exists."""
    config_path = Path("config/permissions.json")
    
    passed = config_path.exists()
    
    return CheckResult(
        name="Permissions Config",
        passed=passed,
        severity=CheckSeverity.WARNING if not passed else CheckSeverity.INFO,
        message="Permissions config exists" if passed else "Permissions config not found",
        details={"path": str(config_path)},
        fix_available=not passed,
        fix_message=f"Create default config at {config_path}"
    )


def check_git_repo() -> CheckResult:
    """Check if running in a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            cwd=Path.cwd()
        )
        passed = result.returncode == 0
        
        return CheckResult(
            name="Git Repository",
            passed=passed,
            severity=CheckSeverity.WARNING,
            message="Running in git repository" if passed else "Not a git repository (needed for self-improvement)",
            fix_available=not passed,
            fix_message="git init"
        )
    except Exception as e:
        return CheckResult(
            name="Git Repository",
            passed=False,
            severity=CheckSeverity.WARNING,
            message=f"Error checking git: {e}",
            fix_available=False
        )


def check_logs_directory() -> CheckResult:
    """Check if logs directory exists and is writable."""
    logs_path = Path("logs")
    
    if not logs_path.exists():
        try:
            logs_path.mkdir(parents=True)
            created = True
        except Exception:
            created = False
    else:
        created = True
        
    writable = os.access(logs_path, os.W_OK) if logs_path.exists() else False
    passed = created and writable
    
    return CheckResult(
        name="Logs Directory",
        passed=passed,
        severity=CheckSeverity.WARNING,
        message="Logs directory exists and writable" if passed else "Logs directory issue",
        details={"path": str(logs_path), "exists": logs_path.exists(), "writable": writable},
        fix_available=not passed,
        fix_message=f"mkdir -p {logs_path} && chmod 755 {logs_path}"
    )


def check_gateway_channels() -> CheckResult:
    """Check if optional gateway dependencies are available."""
    optional = {
        "telegram": "python-telegram-bot",
        "slack": "slack-bolt",
        "discord": "discord.py",
    }
    
    available = {}
    for name, package in optional.items():
        try:
            __import__(name)
            available[name] = True
        except ImportError:
            available[name] = False
            
    all_available = all(available.values())
    
    return CheckResult(
        name="Gateway Channels",
        passed=all_available,
        severity=CheckSeverity.INFO,
        message=f"Available: {', '.join(k for k, v in available.items() if v)}" if any(available.values()) else "No channel adapters installed",
        details=available,
        fix_available=not all_available,
        fix_message=f"pip install {' '.join(optional.values())}"
    )


def check_voice_dependencies() -> CheckResult:
    """Check if voice dependencies are available."""
    try:
        import pyaudio
        has_pyaudio = True
    except ImportError:
        has_pyaudio = False
        
    try:
        import whisper
        has_whisper = True
    except ImportError:
        has_whisper = False
        
    passed = has_pyaudio  # Whisper is optional (can use API)
    
    return CheckResult(
        name="Voice Dependencies",
        passed=passed,
        severity=CheckSeverity.INFO,
        message="Voice support available" if passed else "Voice dependencies missing",
        details={"pyaudio": has_pyaudio, "whisper": has_whisper},
        fix_available=True,
        fix_message="pip install pyaudio openai-whisper"
    )


def check_browser_dependencies() -> CheckResult:
    """Check if browser automation dependencies are available."""
    try:
        from playwright.async_api import async_playwright
        has_playwright = True
    except ImportError:
        has_playwright = False
        
    return CheckResult(
        name="Browser Automation",
        passed=has_playwright,
        severity=CheckSeverity.INFO,
        message="Playwright available" if has_playwright else "Playwright not installed",
        details={"playwright": has_playwright},
        fix_available=not has_playwright,
        fix_message="pip install playwright && playwright install"
    )


def check_scheduler_dependencies() -> CheckResult:
    """Check if scheduler dependencies are available."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        has_apscheduler = True
    except ImportError:
        has_apscheduler = False
        
    return CheckResult(
        name="Task Scheduler",
        passed=has_apscheduler,
        severity=CheckSeverity.INFO,
        message="APScheduler available" if has_apscheduler else "APScheduler not installed",
        details={"apscheduler": has_apscheduler},
        fix_available=not has_apscheduler,
        fix_message="pip install apschedule"
    )
