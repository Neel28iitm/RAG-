"""
Hybrid PDF Ingestion - Combines LlamaParse + Gemini Vision intelligently
"""

import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
import fitz  # PyMuPDF

from src.app.page_classifier import PageComplexityClassifier
from src.app.vision_parser import VisionChartParser

logger = logging.getLogger('app_logger')

class HybridPDFProcessor:
    """
    Intelligent PDF processing that routes pages to appropriate parser:
    - Simple pages → LlamaParse (fast, cheap)
    - Complex pages (charts/tables) → Gemini Vision (accurate)
    """
    
    def __init__(
        self,
        enable_vision: bool = None,
        complexity_threshold: int = 4
    ):
        """
        Args:
            enable_vision: Enable Vision API (defaults to env ENABLE_VISION_PARSING)
            complexity_threshold: Score for classifying as complex
        """
        # Feature flag
        self.enable_vision = enable_vision
        if self.enable_vision is None:
            self.enable_vision = os.getenv('ENABLE_VISION_PARSING', 'false').lower() == 'true'
        
        # Initialize components
        self.classifier = PageComplexityClassifier(complexity_threshold)
        
        if self.enable_vision:
            try:
                self.vision_parser = VisionChartParser()
                logger.info("✅ Vision API enabled for hybrid parsing")
            except Exception as e:
                logger.warning(f"Vision API initialization failed: {e}. Falling back to LlamaParse only.")
                self.enable_vision = False
                self.vision_parser = None
        else:
            self.vision_parser = None
            logger.info("Vision API disabled, using LlamaParse only")
    
    def enhance_llama_pages(
        self,
        llama_result: List[Dict],
        pdf_path: str
    ) -> List[Dict]:
        """
        Take LlamaParse output and enhance complex pages with Vision
        
        Args:
            llama_result: List of page dicts from LlamaParse
            pdf_path: Path to original PDF
        
        Returns:
            Enhanced page list with Vision data appended
        """
        if not self.enable_vision:
            logger.info("Vision disabled, returning LlamaParse results as-is")
            return llama_result
        
        # Step 1: Classify pages
        logger.info(f"Classifying {len(llama_result)} pages...")
        
        pages_for_classification = [
            {
                'page_number': i + 1,
                'content': page.get('content', page.get('text', '')),
                'metadata': page.get('metadata', {})
            }
            for i, page in enumerate(llama_result)
        ]
        
        classifications = self.classifier.classify_batch(pages_for_classification)
        stats = self.classifier.get_statistics(classifications)
        
        logger.info(f"Classification results: {stats['simple']} simple, "
                   f"{stats.get('complex', 0)} complex, {stats.get('mixed', 0)} mixed")
        
        # Identify pages needing Vision
        vision_pages = [
            page_num for page_num, info in classifications.items()
            if info['classification'] in ['complex', 'mixed']
        ]
        
        if not vision_pages:
            logger.info("No complex pages detected, skipping Vision processing")
            return llama_result
        
        logger.info(f"Processing {len(vision_pages)} pages with Vision API: {vision_pages}")
        
        # Step 2: Convert needed pages to images
        temp_dir = Path('data/temp/vision_processing')
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        page_images = self._pdf_to_images(pdf_path, vision_pages, temp_dir)
        
        # Step 3: Process each complex page with Vision
        enhanced_count = 0
        
        for page_num in vision_pages:
            page_idx = page_num - 1
            
            if page_idx >= len(llama_result):
                logger.warning(f"Page {page_num} out of range, skipping")
                continue
            
            img_path = page_images.get(page_num)
            if not img_path:
                logger.warning(f"No image for page {page_num}, skipping Vision")
                continue
            
            # Determine chart type hint from classification
            classification_info = classifications[page_num]
            reason = classification_info['reason'].lower()
            
            if 'tabell' in reason or 'table' in reason:
                chart_type = 'table'
            elif 'bild' in reason or 'chart' in reason:
                chart_type = 'bar'
            else:
                chart_type = 'auto'
            
            try:
                logger.info(f"  Processing page {page_num} as {chart_type}...")
                
                vision_result = self.vision_parser.extract_chart_data(
                    img_path,
                    chart_type=chart_type
                )
                
                if vision_result['success']:
                    # Convert to markdown
                    enhanced_content = self.vision_parser.convert_to_markdown(
                        vision_result['data']
                    )
                    
                    # Get existing content
                    original_content = llama_result[page_idx].get('content') or \
                                     llama_result[page_idx].get('text', '')
                    
                    # APPEND Vision data (don't replace!)
                    combined_content = f"{original_content}\n\n### 🔍 Enhanced Vision Extraction\n\n{enhanced_content}"
                    
                    # Update page
                    if 'content' in llama_result[page_idx]:
                        llama_result[page_idx]['content'] = combined_content
                    else:
                        llama_result[page_idx]['text'] = combined_content
                    
                    llama_result[page_idx]['vision_enhanced'] = True
                    llama_result[page_idx]['vision_data'] = vision_result['data']
                    
                    enhanced_count += 1
                    logger.info(f"  ✅ Page {page_num} enhanced successfully")
                else:
                    logger.warning(f"  ❌ Vision failed for page {page_num}: {vision_result.get('error')}")
                    llama_result[page_idx]['vision_error'] = vision_result.get('error')
            
            except Exception as e:
                logger.error(f"  ❌ Exception processing page {page_num}: {e}")
                llama_result[page_idx]['vision_error'] = str(e)
        
        logger.info(f"✅ Enhanced {enhanced_count}/{len(vision_pages)} complex pages with Vision")
        
        # Cleanup temp images
        try:
            for img_path in page_images.values():
                if Path(img_path).exists():
                    Path(img_path).unlink()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
        
        return llama_result
    
    def _pdf_to_images(
        self,
        pdf_path: str,
        page_numbers: List[int],
        output_dir: Path,
        dpi: int = 300
    ) -> Dict[int, str]:
        """
        Convert specific PDF pages to PNG images
        
        Args:
            pdf_path: Path to PDF file
            page_numbers: List of page numbers (1-indexed)
            output_dir: Directory to save images
            dpi: Image resolution
        
        Returns:
            Dict mapping page_number -> image_path
        """
        images = {}
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in page_numbers:
                try:
                    # fitz uses 0-indexing
                    page = doc[page_num - 1]
                    
                    # Render page to image
                    pix = page.get_pixmap(dpi=dpi)
                    
                    # Save as PNG
                    img_path = output_dir / f"page_{page_num}.png"
                    pix.save(str(img_path))
                    
                    images[page_num] = str(img_path)
                    logger.debug(f"Converted page {page_num} to {img_path}")
                
                except Exception as e:
                    logger.error(f"Failed to convert page {page_num}: {e}")
            
            doc.close()
        
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
        
        return images


# Simple test
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python hybrid_ingestion.py <pdf_path>")
        print("\nTest mode: Will classify pages but not run Vision (set ENABLE_VISION_PARSING=true to enable)")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Mock LlamaParse result for testing
    print(f"Testing hybrid processor on: {pdf_path}")
    
    processor = HybridPDFProcessor()
    
    # Would normally come from LlamaParse
    mock_pages = [
        {'content': 'Normal text page', 'metadata': {}},
        {'content': 'Bild 17.17 shows noise levels', 'metadata': {'has_table': True}},
        {'content': 'Another text page', 'metadata': {}}
    ]
    
    enhanced = processor.enhance_llama_pages(mock_pages, pdf_path)
    
    print(f"\nProcessed {len(enhanced)} pages")
    for i, page in enumerate(enhanced):
        vision_status = "✅ Vision enhanced" if page.get('vision_enhanced') else "❌ No vision"
        print(f"  Page {i+1}: {vision_status}")
