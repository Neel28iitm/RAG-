"""
Script to test vision parsing on Report no 32.pdf
Tracks metrics and compares old vs new method costs
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Enable vision parsing
os.environ['ENABLE_VISION_PARSING'] = 'true'

sys.path.append('.')

from src.core.config import load_config
from src.app.ingestion import DocumentIngestion

async def test_report_32():
    print("="*80)
    print("VISION PARSING TEST: Report no 32.pdf")
    print("="*80)
    
    # Load config
    config = load_config()
    
    # Initialize ingestion
    ingestion = DocumentIngestion(config)
    
    # Find Report no 32.pdf
    pdf_path = Path("data/raw/Report no 32.pdf")
    
    if not pdf_path.exists():
        print(f"\n[ERROR] File not found: {pdf_path}")
        print("\nSearching for file...")
        
        # Search in data/raw
        for f in Path("data/raw").glob("**/*32*.pdf"):
            print(f"  Found: {f}")
            pdf_path = f
            break
    
    if not pdf_path.exists():
        print("\n[ERROR] Report no 32.pdf not found!")
        return
    
    print(f"\n[OK] Found: {pdf_path}")
    print(f"   Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    
    # Start timer
    start_time = time.time()
    
    print("\n" + "="*80)
    print("INGESTION START (Vision ENABLED)")
    print("="*80)
    
    try:
        # Process file
        result = await ingestion.process_file(
            str(pdf_path),
            check_processed=False  # Force re-process
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*80)
        print("INGESTION COMPLETE")
        print("="*80)
        
        print(f"\n[TIME] Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
        # Extract metrics from result if available
        if result:
            print(f"\n[INFO] Documents processed: {len(result) if isinstance(result, list) else 'N/A'}")
        
        # Cost calculation
        print("\n" + "="*80)
        print("COST ANALYSIS")
        print("="*80)
        
        # Estimate pages (will be in logs)
        print("\nCheck logs above for:")
        print("  - Total pages processed")
        print("  - Pages enhanced with Vision")
        print("  - Classification statistics")
        
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_report_32())
