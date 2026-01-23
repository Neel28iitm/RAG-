"""
Test script for hybrid vision parsing system
Tests classifier and vision extraction without running full ingestion
"""

import sys
sys.path.append('.')

from src.app.page_classifier import PageComplexityClassifier
from src.app.vision_parser import VisionChartParser
import json

print("="*80)
print("HYBRID VISION PARSING - TEST SUITE")
print("="*80)

# Test 1: Page Classifier
print("\n" + "="*80)
print("TEST 1: PAGE CLASSIFIER")
print("="*80)

classifier = PageComplexityClassifier()

test_pages = [
    {
        'name': 'Simple text page',
        'content': '''
        This is a standard paragraph from an ISO document.
        It contains normal text without any charts or tables.
        The content is straightforward technical writing about acoustic measurements.
        '''
    },
    {
        'name': 'Chart page (Bild 17.17)',
        'content': '''
        Bild 17.17: Schallpegelverteilung auf Schiffen mit diesel-elektrischem Antrieb
        
        The chart shows noise distribution across different areas of the ship.
        Values are measured in dBA.
        '''
    },
    {
        'name': 'Table page (SS 25268)',
        'content': '''
        Tab ell 2 - Ljudklass C i bostäder
        
        | Utrymme | R'w + C50-3150 |
        |---------|----------------|
        | Bostad - Bostad | 53 dB |
        | Bostad - Trapphus | 48 dB |
        '''
    },
    {
        'name': 'Mixed page',
        'content': '''
        According to Table 3, the following values apply:
        
        Bild 5.2 illustrates the relationship between frequency and absorption.
        
        Multiple numeric values: 112, 93, 74, 68, 65, 55
        '''
    }
]

for test in test_pages:
    classification, score, reason = classifier.classify_page(test['content'])
    print(f"\n{test['name']}:")
    print(f"  Classification: {classification}")
    print(f"  Score: {score}")
    print(f"  Reason: {reason}")

print("\n" + "-"*80)
print("SUMMARY")
print("-"*80)

pages_for_stats = [
    {'page_number': i+1, 'content': t['content'], 'metadata': {}}
    for i, t in enumerate(test_pages)
]

classifications = classifier.classify_batch(pages_for_stats)
stats = classifier.get_statistics(classifications)

print(f"Total pages: {stats['total']}")
print(f"Simple: {stats.get('simple', 0)} ({stats.get('simple_pct', 0):.1f}%)")
print(f"Complex: {stats.get('complex', 0)} ({stats.get('complex_pct', 0):.1f}%)")
print(f"Mixed: {stats.get('mixed', 0)} ({stats.get('mixed_pct', 0):.1f}%)")
print(f"Vision needed: {stats.get('vision_needed', 0)} pages ({stats.get('vision_needed_pct', 0):.1f}%)")

# Test 2: Vision Parser (if Google API key available)
print("\n\n" + "="*80)
print("TEST 2: VISION PARSER")
print("="*80)

import os
if not os.getenv('GOOGLE_API_KEY'):
    print("\n⚠️  GOOGLE_API_KEY not set, skipping Vision tests")
    print("   Set GOOGLE_API_KEY environment variable to test Vision extraction")
else:
    try:
        parser = VisionChartParser()
        print("✅ Vision parser initialized successfully")
        print(f"   Using model: {parser.model_name}")
        
        print("\n📝 Vision parser is ready to extract from chart images")
        print("   Usage: parser.extract_chart_data('path/to/image.png', chart_type='bar')")
        
    except Exception as e:
        print(f"❌ Vision parser initialization failed: {e}")

# Test 3: Hybrid Processor
print("\n\n" + "="*80)
print("TEST 3: HYBRID PROCESSOR")
print("="*80)

from src.app.hybrid_ingestion import HybridPDFProcessor

print(f"Vision enabled in environment: {os.getenv('ENABLE_VISION_PARSING', 'false')}")

processor = HybridPDFProcessor()

if processor.enable_vision:
    print("✅ Hybrid processor initialized with Vision support")
else:
    print("⚠️  Hybrid processor initialized WITHOUT Vision (LlamaParse only)")
    print("   Set ENABLE_VISION_PARSING=true to enable")

print("\n" + "="*80)
print("ALL TESTS COMPLETE")
print("="*80)

print("\n📋 Next steps:")
print("1. Set ENABLE_VISION_PARSING=true in .env to enable Vision")
print("2. Test on actual PDF with: python src/app/hybrid_ingestion.py <pdf_path>")
print("3. When ready, integration is already in ingestion.py (no changes needed!)")
print("4. Re-run ingestion to process with hybrid approach")

print("\n✅ Implementation complete - ready to use!")
