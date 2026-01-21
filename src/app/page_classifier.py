"""
Page Classifier - Detect chart/table heavy pages for Vision API processing
"""

import re
from typing import Dict, List, Tuple

class PageComplexityClassifier:
    """
    Classify PDF pages as simple (text) or complex (charts/tables)
    to route to appropriate parser (LlamaParse vs Vision)
    """
    
    # Keywords indicating charts/tables
    CHART_KEYWORDS = [
        'bild', 'figure', 'fig.', 'chart', 'graph', 'diagram',
        'abbildung', 'tabell', 'table', 'tab.', 'grafik'
    ]
    
    TABLE_KEYWORDS = [
        'tabell', 'table', 'tab.', 'übersicht', 'liste'
    ]
    
    def __init__(self, complexity_threshold: int = 4):
        """
        Args:
            complexity_threshold: Score needed to classify as 'complex'
                                 4-5 is recommended (conservative)
        """
        self.threshold = complexity_threshold
    
    def classify_page(
        self, 
        page_content: str, 
        page_metadata: Dict = None
    ) -> Tuple[str, int, str]:
        """
        Classify a single page
        
        Args:
            page_content: Extracted text from page
            page_metadata: Optional metadata (has_table, etc.)
        
        Returns:
            Tuple of (classification, score, reason)
            - classification: 'simple', 'complex', or 'mixed'
            - score: Complexity score (0-10)
            - reason: Human-readable explanation
        """
        score = 0
        reasons = []
        
        page_metadata = page_metadata or {}
        content_lower = page_content.lower()
        
        # Check 1: Metadata indicates table
        if page_metadata.get('has_table', False):
            score += 3
            reasons.append("Metadata: Table detected")
        
        # Check 2: Chart keywords present
        chart_found = False
        for keyword in self.CHART_KEYWORDS:
            if keyword in content_lower:
                score += 2
                chart_found = True
                reasons.append(f"Keyword: '{keyword}'")
                break
        
        # Check 3: Table keywords
        if not chart_found:
            for keyword in self.TABLE_KEYWORDS:
                if keyword in content_lower:
                    score += 2
                    reasons.append(f"Keyword: '{keyword}'")
                    break
        
        # Check 4: High number-to-text ratio (indicates data/chart)
        numbers = re.findall(r'\d+', page_content)
        words = page_content.split()
        if len(words) > 0:
            number_ratio = len(numbers) / len(words)
            if number_ratio > 0.25:  # >25% numbers
                score += 2
                reasons.append(f"High numeric content ({number_ratio:.0%})")
        
        # Check 5: Short content (likely image-heavy)
        if len(page_content.strip()) < 300:
            score += 1
            reasons.append(f"Short content ({len(page_content)} chars)")
        
        # Check 6: Multiple pipe characters (markdown tables)
        pipe_count = page_content.count('|')
        if pipe_count > 10:
            score += 2
            reasons.append(f"Markdown table detected ({pipe_count} pipes)")
        
        # Classify based on score
        if score >= self.threshold + 1:
            classification = 'complex'
        elif score >= self.threshold - 1:
            classification = 'mixed'
        else:
            classification = 'simple'
        
        reason_str = "; ".join(reasons) if reasons else "No complexity indicators"
        
        return classification, score, reason_str
    
    def classify_batch(
        self, 
        pages: List[Dict]
    ) -> Dict[int, Dict]:
        """
        Classify multiple pages
        
        Args:
            pages: List of dicts with 'page_number', 'content', 'metadata'
        
        Returns:
            Dict mapping page_number -> {classification, score, reason}
        """
        results = {}
        
        for page in pages:
            page_num = page.get('page_number', 0)
            content = page.get('content', '')
            metadata = page.get('metadata', {})
            
            classification, score, reason = self.classify_page(content, metadata)
            
            results[page_num] = {
                'classification': classification,
                'score': score,
                'reason': reason
            }
        
        return results
    
    def get_statistics(self, classifications: Dict[int, Dict]) -> Dict:
        """
        Get statistics from batch classification
        
        Returns:
            Dict with counts and percentages
        """
        total = len(classifications)
        if total == 0:
            return {}
        
        simple = sum(1 for c in classifications.values() if c['classification'] == 'simple')
        mixed = sum(1 for c in classifications.values() if c['classification'] == 'mixed')
        complex_count = sum(1 for c in classifications.values() if c['classification'] == 'complex')
        
        return {
            'total': total,
            'simple': simple,
            'mixed': mixed,
            'complex': complex_count,
            'simple_pct': simple / total * 100,
            'mixed_pct': mixed / total * 100,
            'complex_pct': complex_count / total * 100,
            'vision_needed': mixed + complex_count,
            'vision_needed_pct': (mixed + complex_count) / total * 100
        }


# Example usage
if __name__ == "__main__":
    classifier = PageComplexityClassifier()
    
    # Test case 1: Simple text page
    simple_page = """
    This is a standard paragraph from an ISO document.
    It contains normal text without any charts or tables.
    The content is straightforward technical writing.
    """
    result = classifier.classify_page(simple_page)
    print(f"Simple page: {result}")
    
    # Test case 2: Page with chart reference
    chart_page = """
    Bild 17.17 shows the noise distribution across different areas.
    The chart contains the following values:
    Dieselbox: 112 dBA
    Kammer: 65 dBA
    """
    result = classifier.classify_page(chart_page)
    print(f"Chart page: {result}")
    
    # Test case 3: Page with table
    table_page = """
    Tabell 2 - Ljudklass C i bostäder
    
    | Utrymme | R'w + C50-3150 |
    |---------|----------------|
    | Bostad  | 53 dB          |
    """
    result = classifier.classify_page(table_page)
    print(f"Table page: {result}")
