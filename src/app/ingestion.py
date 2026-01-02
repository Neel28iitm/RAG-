"""
Module: Ingestion
Purpose: Handle loading of documents (PDFs) using LlamaParse with Vendor Multimodal (Cost Optimized).
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from llama_parse import LlamaParse
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger('app_logger')

class DocumentIngestion:
    def __init__(self, config):
        self.config = config
        self.data_raw = Path(config['paths']['data_raw'])
        self.tracking_file = Path(config['paths']['tracking_file'])
        self.should_clear_db = False # Flag to signal if DB needs clearing
        self.processed_files = self._load_tracking()

    def _load_tracking(self):
        current_chunk_size = self.config['parsing']['chunk_size']
        current_overlap = self.config['parsing']['chunk_overlap']
        
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    data = json.load(f)
                    
                # Backward compatibility: if list, assume legacy and force update
                if isinstance(data, list):
                    logger.info("⚠️  Legacy tracking format detected. Forcing re-ingestion.")
                    self.should_clear_db = True
                    return set()
                
                # Check config match
                stored_chunk_size = data.get('config', {}).get('chunk_size')
                stored_overlap = data.get('config', {}).get('chunk_overlap')
                
                if stored_chunk_size != current_chunk_size or stored_overlap != current_overlap:
                    logger.info(f"🔄 Config changed (Size: {stored_chunk_size}->{current_chunk_size}, Overlap: {stored_overlap}->{current_overlap}). Triggering Re-indexing.")
                    self.should_clear_db = True
                    return set()
                    
                return set(data.get('files', []))
                
            except Exception as e:
                logger.error(f"Error loading tracking file: {e}")
                return set()
                
        return set()

    def _save_tracking(self):
        # Ensure directory exists
        if not self.tracking_file.parent.exists():
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "files": list(self.processed_files),
            "config": {
                "chunk_size": self.config['parsing']['chunk_size'],
                "chunk_overlap": self.config['parsing']['chunk_overlap']
            }
        }
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f)

    async def process_file(self, file_path):
        """Processes a single PDF file using Optimized LlamaParse Settings"""
        filename = file_path.name
        if filename in self.processed_files:
            logger.info(f"⏭️  Skipping {filename} (Already processed)")
            return []

        logger.info(f"📄 Processing {filename} with LlamaParse (Vendor Multimodal Mode)...")
        
        # 1. OPTIMIZED PARSING CONFIGURATION
        # Using Gemini 2.5 Flash as Vendor Model to reduce LlamaCloud costs to ~1 credit/page
        parser = LlamaParse(
            result_type="markdown",
            verbose=True,
            language=self.config['parsing']['language'],
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name="gemini-2.5-flash", # User requested model
            vendor_multimodal_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        
        # 2. Execute Parse
        try:
            # LlamaParse.load_data is synchronous, but we can run it in executor if needed.
            # For this script, blocking is acceptable or we use the async version if available in newer lib.
            documents = await parser.aload_data(str(file_path)) 
        except Exception as e:
            logger.error(f"❌ Processing failed for {filename}: {e}")
            return []
        
        full_text_parts = []
        for doc in documents:
            # Inject Page Number into the text content so it persists through splitting
            # LlamaParse metadata usually has 'page_label'
            page_num = doc.metadata.get('page_label', 'Unknown')
            page_marker = f"\n\n--- [PAGE {page_num}] ---\n"
            full_text_parts.append(page_marker + doc.text)
            
        full_text = "".join(full_text_parts)
        
        # 3. Double-Pass Chunking
        logger.info("🔪 Chunking content...")
        
        # Step A: Header Splitter
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(full_text)
        
        # Step B: Recursive Splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config['parsing']['chunk_size'],
            chunk_overlap=self.config['parsing']['chunk_overlap']
        )
        
        final_chunks = text_splitter.split_documents(md_header_splits)
        
        # Add source metadata
        for chunk in final_chunks:
            chunk.metadata['source'] = filename
        
        # Mark as processed
        self.processed_files.add(filename)
        self._save_tracking()
        
        return final_chunks

    async def ingest_documents(self):
        """Main entry point to ingest all new documents"""
        if not self.data_raw.exists():
            logger.warning(f"Data directory {self.data_raw} does not exist.")
            return []

        files = list(self.data_raw.glob("*.pdf"))
        if not files:
            logger.info("No PDF files found in data/raw/")
            return []
            
        all_chunks = []
        for file in files:
            chunks = await self.process_file(file)
            all_chunks.extend(chunks)
            
        return all_chunks
