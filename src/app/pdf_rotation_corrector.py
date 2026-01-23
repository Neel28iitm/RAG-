"""
PDF Rotation Detector and Corrector
Uses pytesseract OSD to detect page rotation and auto-corrects it
"""

import os
import tempfile
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import pytesseract
import logging

logger = logging.getLogger('app_logger')

class PDFRotationCorrector:
    """
    Detects and corrects rotated pages in PDF before parsing
    """
    
    def __init__(self, tesseract_path=None):
        """
        Args:
            tesseract_path: Path to tesseract executable (Windows: C:/Program Files/Tesseract-OCR/tesseract.exe)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def detect_page_rotation(self, image):
        """
        Detect rotation angle using Tesseract OSD, falling back to Gemini Vision
        """
        # Try Tesseract First
        try:
            # Get orientation and script detection
            osd = pytesseract.image_to_osd(image)
            # Parse rotation angle
            rotation = int([line for line in osd.split('\n') if 'Rotate' in line][0].split(':')[1].strip())
            return rotation
        except Exception as e:
            # Fallback to Gemini Vision if configured
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                return self.detect_rotation_with_gemini(image, api_key)
            
            logger.warning(f"OSD detection failed and no Gemini API key: {e}. Assuming 0° rotation.")
            return 0

    def detect_rotation_with_gemini(self, image, api_key):
        """Uses Gemini Flash to detect page rotation"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Downscale for speed/cost
            img_small = image.resize((512, 512))
            
            prompt = """
            Analyze this document image. Return ONLY a JSON object with a single key 'rotation_angle'.
            Valid values are 0, 90, 180, 270.
            Example: {"rotation_angle": 90}
            """
            
            response = model.generate_content([prompt, img_small])
            
            # Parse JSON response
            import json
            try:
                # Clean up response text (remove markdown blocks if any)
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                data = json.loads(text)
                angle = int(data.get("rotation_angle", 0))
            except Exception:
                # Fallback if valid JSON isn't returned, try direct int parse just in case
                try:
                    angle = int(response.text.strip())
                except:
                    angle = 0

            if angle in [0, 90, 180, 270]:
                return angle
            return 0
        except Exception as e:
            logger.debug(f"Gemini rotation check failed: {e}")
            return 0

    def process_pdf(self, pdf_path, output_path=None):
        """
        Process entire PDF: detect rotated pages and create corrected version
        """
        try:
            doc = fitz.open(pdf_path)
            
            # Create output PDF
            if output_path is None:
                output_fd, output_path = tempfile.mkstemp(suffix=".pdf")
                os.close(output_fd)
            
            corrected_doc = fitz.open()  # New empty PDF
            
            rotated_pages = []
            
            # Limit pages to process to avoid massive API costs/time for huge docs?
            # Report 32 is ~50 pages. Acceptable.
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Convert page to image for OSD
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                
                # Open with PIL
                from io import BytesIO
                image = Image.open(BytesIO(img_data))
                
                # Detect rotation
                rotation = self.detect_page_rotation(image)
                
                if rotation != 0:
                    rotated_pages.append((page_num + 1, rotation))
                    page.set_rotation((page.rotation - rotation) % 360)
                
                corrected_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            corrected_doc.save(output_path)
            corrected_doc.close()
            doc.close()
            
            if rotated_pages:
                logger.info(f"✅ Corrected {len(rotated_pages)} rotated pages using Hybrid (Tesseract/Gemini): {rotated_pages}")
            
            return output_path
        
        except Exception as e:
            logger.warning(f"⚠️ Rotation correction failed: {e}")
            return pdf_path


# Quick test function
def test_rotation_detection(pdf_path):
    """Test OSD on a PDF"""
    corrector = PDFRotationCorrector()
    
    print(f"Testing rotation detection on: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    # Test first 3 pages
    for i in range(min(3, len(doc))):
        page = doc[i]
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        
        from io import BytesIO
        from PIL import Image
        image = Image.open(BytesIO(img_data))
        
        rotation = corrector.detect_page_rotation(image)
        print(f"Page {i+1}: {rotation}° rotation detected")
    
    doc.close()


if __name__ == "__main__":
    # Example usage
    test_pdf = "data/raw/Report no 32.pdf"
    if Path(test_pdf).exists():
        test_rotation_detection(test_pdf)
