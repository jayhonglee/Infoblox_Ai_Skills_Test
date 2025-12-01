#!/usr/bin/env python3
"""
Main orchestrator for inventory data processing pipeline.
Processes inventory_raw.csv through comprehensive validation and normalization.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent

def main():
    """Run the comprehensive data processing pipeline."""
    input_csv = PROJECT_ROOT / "inventory_raw.csv"
    output_csv = PROJECT_ROOT / "inventory_clean.csv"
    anomalies_json = PROJECT_ROOT / "anomalies.json"
    
    # Run comprehensive processing
    print("Starting comprehensive data processing...")
    subprocess.check_call([
        sys.executable,
        str(HERE / "data_processor.py"),
        str(input_csv)
    ])
    
    print(f"✓ Processing complete!")
    print(f"  - Output: {output_csv}")
    print(f"  - Anomalies: {anomalies_json}")

if __name__ == "__main__":
    main()
