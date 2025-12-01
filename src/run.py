#!/usr/bin/env python3
# Simple runner to produce baseline outputs.
# Extend this to call your own normalization/classification steps.

import subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent  # Go up from infoblox_test_env -> Solution -> root

def main():
    # Step 1: IPv4 normalization (example starter)
    subprocess.check_call([
        sys.executable, 
        str(HERE / "run_ipv4_validation.py"), 
        str(PROJECT_ROOT / "inventory_raw.csv")
    ])
    print("IPv4 normalization complete. Next: add your steps to reach full target schema.")

if __name__ == "__main__":
    main()
