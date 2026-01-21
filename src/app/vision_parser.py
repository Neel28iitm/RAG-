"""
Vision Parser - Extract structured data from charts/tables using Gemini Vision
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import google.generativeai as genai
from PIL import Image

logger = logging.getLogger('app_logger')

class VisionChartParser:
    """
    Extract structured data from charts and complex tables using Gemini Vision API
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        """
        Initialize Vision Parser
        
        Args:
            api_key: Google API key (defaults to env GOOGLE_API_KEY)
            model_name: Gemini model to use
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
    
    def extract_chart_data(
        self, 
        image_path: str, 
        chart_type: str = 'auto',
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract data from chart image
        
        Args:
            image_path: Path to chart image (PNG, JPG)
            chart_type: 'bar', 'line', 'table', 'mixed', or 'auto'
            custom_prompt: Optional custom extraction prompt
        
        Returns:
            Dict with 'success', 'data', 'raw_response', 'error' (if failed)
        """
        try:
            # Load image
            if not Path(image_path).exists():
                return {
                    'success': False,
                    'error': f"Image not found: {image_path}"
                }
            
            image = Image.open(image_path)
            
            # Select prompt
            if custom_prompt:
                prompt = custom_prompt
            elif chart_type == 'bar':
                prompt = self._get_bar_chart_prompt()
            elif chart_type == 'table':
                prompt = self._get_table_prompt()
            else:
                prompt = self._get_auto_detect_prompt()
            
            # Call Gemini Vision
            logger.info(f"Calling Gemini Vision for {image_path} (type: {chart_type})")
            response = self.model.generate_content([prompt, image])
            
            # Parse response
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"Vision extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'raw_response': None
            }
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's response, extracting JSON if present"""
        try:
            # Try to extract JSON from response
            # Gemini often wraps JSON in markdown code blocks
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_str = response_text.split('```')[1].split('```')[0].strip()
            else:
                json_str = response_text.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            return {
                'success': True,
                'data': data,
                'raw_response': response_text
            }
        except json.JSONDecodeError as e:
            # Gemini didn't return valid JSON
            logger.warning(f"Failed to parse JSON: {e}")
            return {
                'success': False,
                'error': f"Invalid JSON response: {e}",
                'raw_response': response_text
            }
    
    def _get_bar_chart_prompt(self) -> str:
        """Prompt optimized for bar charts"""
        return """You are analyzing a BAR CHART from a technical document.

CRITICAL TASK: Extract EVERY single bar with extreme precision.

OUTPUT FORMAT (strict JSON):
{
  "chart_title": "exact title text",
  "y_axis_label": "label with units",
  "x_axis_label": "label",
  "bars": [
    {
      "label": "exact bar label (preserve language)",
      "value": numeric_value,
      "unit": "dBA | dB | Hz | etc."
    }
  ]
}

CRITICAL REQUIREMENTS:
1. Extract ALL bars - do not skip any, even if label is small, rotated, or partially visible
2. If a bar has no visible label, use "Unlabeled Bar" as label but still include it
3. Extract exact numeric values - do not round unless necessary
4. Preserve original language (German, Swedish, English, etc.)
5. Include units if visible (dBA, dB, Hz, etc.)
6. If bar chart has multiple series, indicate in label (e.g., "Series1: Label")

EXAMPLE OUTPUT:
{
  "chart_title": "Bild 17.17: Schallpegelverteilung auf Schiffen",
  "y_axis_label": "Sound Level (dBA)",
  "x_axis_label": "Location",
  "bars": [
    {"label": "Dieselbox", "value": 112, "unit": "dBA"},
    {"label": "2. Wohnraum", "value": 74, "unit": "dBA"},
    {"label": "Kammer", "value": 65, "unit": "dBA"}
  ]
}

Now analyze the provided image and return ONLY the JSON output."""
    
    def _get_table_prompt(self) -> str:
        """Prompt optimized for tables"""
        return """You are analyzing a TABLE from a technical document.

CRITICAL TASK: Extract the complete table structure.

OUTPUT FORMAT (strict JSON):
{
  "table_title": "exact title",
  "headers": ["column1", "column2", "..."],
  "rows": [
    {"column1": "value", "column2": "value", "..."}
  ],
  "footer_notes": "any notes below table"
}

CRITICAL REQUIREMENTS:
1. Include ALL rows and columns - do not skip any
2. Handle merged cells by repeating value across merged range
3. Preserve numeric precision - do not round
4. Include units in cell values if present
5. Maintain original language
6. Handle multi-line cells by joining with space

EXAMPLE OUTPUT:
{
  "table_title": "Table 2 - Sound Class C Requirements",
  "headers": ["Space Type", "R'w + C50-3150 (dB)"],
  "rows": [
    {"Space Type": "Bostad - Bostad", "R'w + C50-3150 (dB)": "53"},
    {"Space Type": "Bostad - Trapphus", "R'w + C50-3150 (dB)": "48"}
  ],
  "footer_notes": "According to SS 25268:2023"
}

Now analyze the provided image and return ONLY the JSON output."""
    
    def _get_auto_detect_prompt(self) -> str:
        """Generic prompt for auto-detection"""
        return """You are analyzing a technical diagram, chart, or table.

TASK:
1. Identify the type of visual element (bar chart, line graph, table, mixed, other)
2. Extract ALL data in structured format appropriate for that type

OUTPUT FORMAT (strict JSON):
{
  "element_type": "bar_chart | line_graph | table | mixed | other",
  "title": "exact title or caption",
  "data": {
    // Structure appropriate for element_type
    // For bar chart: use bars array
    // For table: use headers + rows
    // For other: use descriptive structure
  },
  "notes": "any annotations or legends"
}

CRITICAL REQUIREMENTS:
- Extract EVERY data point, label, and value
- Do not skip small or unclear text
- Preserve original language
- Include units where visible
- Be exhaustive, not selective

Now analyze the provided image and return ONLY the JSON output."""
    
    def convert_to_markdown(self, structured_data: Dict) -> str:
        """
        Convert structured data to markdown for storage
        
        Args:
            structured_data: Parsed JSON from vision extraction
        
        Returns:
            Markdown formatted string
        """
        if not structured_data:
            return ""
        
        # Bar chart → Markdown table
        if 'bars' in structured_data:
            title = structured_data.get('chart_title', 'Chart Data')
            md = f"### {title}\n\n"
            md += "| Label | Value |\n"
            md += "|-------|-------|\n"
            
            for bar in structured_data.get('bars', []):
                label = bar.get('label', 'Unknown')
                value = bar.get('value', '')
                unit = bar.get('unit', '')
                md += f"| {label} | {value} {unit} |\n"
            
            return md
        
        # Table → Markdown table
        elif 'headers' in structured_data and 'rows' in structured_data:
            title = structured_data.get('table_title', 'Table Data')
            md = f"### {title}\n\n"
            
            headers = structured_data['headers']
            md += "| " + " | ".join(headers) + " |\n"
            md += "|" + "|".join(["---"] * len(headers)) + "|\n"
            
            for row in structured_data.get('rows', []):
                values = [str(row.get(h, '')) for h in headers]
                md += "| " + " | ".join(values) + " |\n"
            
            if 'footer_notes' in structured_data:
                md += f"\n*{structured_data['footer_notes']}*\n"
            
            return md
        
        # Generic fallback
        else:
            title = structured_data.get('title', 'Data')
            md = f"### {title}\n\n"
            md += "```json\n"
            md += json.dumps(structured_data, indent=2, ensure_ascii=False)
            md += "\n```\n"
            return md


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python vision_parser.py <image_path> [chart_type]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    chart_type = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    
    parser = VisionChartParser()
    result = parser.extract_chart_data(image_path, chart_type=chart_type)
    
    if result['success']:
        print("✅ Extraction successful!")
        print(json.dumps(result['data'], indent=2, ensure_ascii=False))
        
        print("\n--- Markdown Output ---")
        markdown = parser.convert_to_markdown(result['data'])
        print(markdown)
    else:
        print(f"❌ Extraction failed: {result['error']}")
