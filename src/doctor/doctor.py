"""
TWIZZY Doctor - System diagnostic tool.

Performs health checks and repairs for TWIZZY installation.
"""

import asyncio
import logging
import platform
import subprocess
import sys
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckSeverity(Enum):
    """Severity levels for diagnostic checks."""
    INFO = "info"           # Informational
    WARNING = "warning"     # Warning, not critical
    ERROR = "error"         # Error, may affect functionality
    CRITICAL = "critical"   # Critical, system may not work


@dataclass
class CheckResult:
    """Result of a diagnostic check."""
    name: str
    passed: bool
    severity: CheckSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_available: bool = False
    fix_applied: bool = False
    fix_message: Optional[str] = None


class Doctor:
    """
    Diagnostic tool for TWIZZY.
    
    Performs various checks to ensure the system is healthy and
    can automatically fix common issues.
    """
    
    def __init__(self):
        self._checks: List[Callable[[], CheckResult]] = []
        self._fixers: Dict[str, Callable[[], bool]] = {}
        self._last_results: List[CheckResult] = []
        
    def register_check(self, name: str, check_func: Callable[[], CheckResult], 
                       fix_func: Optional[Callable[[], bool]] = None) -> None:
        """
        Register a diagnostic check.
        
        Args:
            name: Check name
            check_func: Function that returns CheckResult
            fix_func: Optional function to fix the issue
        """
        self._checks.append(check_func)
        if fix_func:
            self._fixers[name] = fix_func
            
    async def run_checks(self, auto_fix: bool = False) -> List[CheckResult]:
        """
        Run all diagnostic checks.
        
        Args:
            auto_fix: Automatically apply fixes if available
            
        Returns:
            List of check results
        """
        results = []
        
        print("🔍 Running TWIZZY diagnostics...\n")
        
        for check_func in self._checks:
            try:
                result = await asyncio.get_event_loop().run_in_executor(None, check_func)
                results.append(result)
                
                # Print result
                icon = "✅" if result.passed else "❌"
                print(f"{icon} {result.name}")
                if not result.passed:
                    print(f"   {result.severity.value.upper()}: {result.message}")
                    
                    # Auto-fix if requested and available
                    if auto_fix and result.fix_available and result.name in self._fixers:
                        print(f"   🔧 Attempting fix...")
                        try:
                            fixed = await asyncio.get_event_loop().run_in_executor(
                                None, self._fixers[result.name]
                            )
                            if fixed:
                                result.fix_applied = True
                                print(f"   ✅ Fixed!")
                            else:
                                print(f"   ❌ Fix failed")
                        except Exception as e:
                            print(f"   ❌ Fix error: {e}")
                            
            except Exception as e:
                logger.error(f"Check failed: {e}")
                results.append(CheckResult(
                    name=check_func.__name__,
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"Check failed with error: {e}"
                ))
                
        self._last_results = results
        
        # Print summary
        print("\n" + "="*50)
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        warnings = sum(1 for r in results if not r.passed and r.severity == CheckSeverity.WARNING)
        errors = sum(1 for r in results if not r.passed and r.severity in (CheckSeverity.ERROR, CheckSeverity.CRITICAL))
        
        print(f"Results: {passed} passed, {failed} failed ({warnings} warnings, {errors} errors)")
        
        if errors > 0:
            print("⚠️  Critical issues found! TWIZZY may not work correctly.")
        elif warnings > 0:
            print("⚡ Some warnings found, but TWIZZY should work.")
        else:
            print("🎉 All checks passed! TWIZZY is healthy.")
            
        return results
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of last check run."""
        if not self._last_results:
            return {"status": "not_run"}
            
        passed = sum(1 for r in self._last_results if r.passed)
        failed = len(self._last_results) - passed
        
        return {
            "status": "healthy" if failed == 0 else "degraded" if failed < 3 else "unhealthy",
            "total_checks": len(self._last_results),
            "passed": passed,
            "failed": failed,
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "severity": r.severity.value,
                    "message": r.message
                }
                for r in self._last_results
            ]
        }
        
    def export_report(self, path: str) -> bool:
        """Export diagnostic report to file."""
        try:
            import json
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "platform": platform.system(),
                    "version": platform.version(),
                    "python": sys.version,
                },
                "summary": self.get_summary()
            }
            
            Path(path).write_text(json.dumps(report, indent=2))
            return True
        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return False


# Global instance
_doctor: Optional[Doctor] = None


def get_doctor() -> Doctor:
    """Get or create global doctor instance."""
    global _doctor
    if _doctor is None:
        _doctor = Doctor()
        _register_default_checks(_doctor)
    return _doctor


def _register_default_checks(doctor: Doctor):
    """Register default diagnostic checks."""
    from .checks import (
        check_python_version,
        check_virtual_env,
        check_dependencies,
        check_api_key,
        check_permissions_file,
        check_git_repo,
        check_logs_directory
    )
    
    doctor.register_check("python_version", check_python_version)
    doctor.register_check("virtual_env", check_virtual_env)
    doctor.register_check("dependencies", check_dependencies)
    doctor.register_check("api_key", check_api_key)
    doctor.register_check("permissions", check_permissions_file)
    doctor.register_check("git_repo", check_git_repo)
    doctor.register_check("logs_dir", check_logs_directory)
