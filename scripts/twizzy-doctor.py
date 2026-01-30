#!/usr/bin/env python3
"""
TWIZZY Doctor - Diagnostic and repair tool.

Usage:
    python scripts/twizzy-doctor.py           # Run all checks
    python scripts/twizzy-doctor.py --fix     # Run checks and auto-fix issues
    python scripts/twizzy-doctor.py --report  # Export report to file
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doctor import get_doctor


async def main():
    parser = argparse.ArgumentParser(description="TWIZZY Doctor - System diagnostics")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues")
    parser.add_argument("--report", metavar="PATH", help="Export report to file")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    
    args = parser.parse_args()
    
    doctor = get_doctor()
    results = await doctor.run_checks(auto_fix=args.fix)
    
    if args.json:
        import json
        print(json.dumps(doctor.get_summary(), indent=2))
        
    if args.report:
        if doctor.export_report(args.report):
            print(f"\n📄 Report exported to: {args.report}")
        else:
            print(f"\n❌ Failed to export report")
            
    # Exit with error code if there were critical errors
    critical = sum(1 for r in results if not r.passed and r.severity.value == "critical")
    sys.exit(1 if critical > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
