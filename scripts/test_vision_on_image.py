
import os
import fitz  # PyMuPDF
from pathlib import Path
from dotenv import load_dotenv
from src.app.vision_parser import VisionChartParser

# Load env
load_dotenv('config/.env')

pdf_path = Path("data/raw/Taschenbuch der Technischen Akustik - Lärmbekämpfung auf Schiffen.pdf")
page_num = 2  # 1-based
img_path = Path("data/temp/test_page_2.png")

print(f"📄 Converting Page {page_num} of {pdf_path}...")

# Ensure dir
img_path.parent.mkdir(parents=True, exist_ok=True)

# Convert
try:
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    pix = page.get_pixmap(dpi=300)
    pix.save(str(img_path))
    doc.close()
    print(f"✅ Created {img_path}")
except Exception as e:
    print(f"❌ PDF Exception: {e}")
    exit(1)

print(f"🔍 Testing Vision on {img_path}...")

parser = VisionChartParser()  # Defaults to gemini-2.5-flash
result = parser.extract_chart_data(str(img_path), chart_type='auto')

if result['success']:
    print("✅ Success!")
    print(result['data'])
else:
    print(f"❌ Failed: {result['error']}")
    if result.get('raw_response'):
        print(f"Raw Response: {result['raw_response']}")
