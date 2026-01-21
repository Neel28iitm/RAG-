"""
Query Classification Module - Conservative Approach
===========================================
Only classifies queries as 'generic' when 100% certain.
When in doubt, defaults to 'knowledge' (uses retrieval).

Safety Principle: Better to retrieve unnecessarily than miss a knowledge query!
"""
import re
from typing import Literal
import logging

logger = logging.getLogger('query_classifier')

QueryType = Literal['generic', 'knowledge']

class QueryClassifier:
    """
    Conservative query classifier
    
    Design Principles:
    1. Only skip retrieval for OBVIOUS generic queries
    2. Any ambiguity → use retrieval (safe default)
    3. Presence of ANY knowledge indicator → use retrieval
    4. Short queries with question marks → use retrieval
    """
    
    def __init__(self):
        # STRICT patterns - only exact matches qualify as generic
        self.strict_generic_patterns = [
            # Single-word greetings
            r'^hi\.?$',
            r'^hello\.?$',
            r'^hey\.?$',
            r'^hej\.?$',  # Swedish
            r'^hallo\.?$',  # German
            
            # Thanks (exact)
            r'^thanks?\.?$',
            r'^thank you\.?$',
            r'^tack\.?$',  # Swedish
            r'^danke\.?$',  # German
            
            # Acknowledgments (exact)
            r'^ok\.?$',
            r'^okay\.?$',
            r'^sure\.?$',
            r'^got it\.?$',
            
            # Goodbyes
            r'^bye\.?$',
            r'^goodbye\.?$',
            r'^see you\.?$',
            
            # Yes/No (single word only)
            r'^yes\.?$',
            r'^no\.?$',
            r'^ja\.?$',  # Swedish/German
            r'^nej\.?$',  # Swedish
            r'^nein\.?$',  # German
        ]
        
        # Knowledge indicators - if ANY of these present, use retrieval
        self.knowledge_indicators = [
            # Question words
            'what', 'who', 'where', 'when', 'why', 'how', 'which',
            'vad', 'vem', 'var', 'när', 'varför', 'hur',  # Swedish
            'was', 'wer', 'wo', 'wann', 'warum', 'wie',  # German
            
            # Domain keywords
            'iso', 'ss', 'standard', 'requirement', 'requirements',
            'noise', 'sound', 'level', 'levels', 'measurement',
            'report', 'document', 'table', 'value', 'limit',
            'building', 'office', 'preschool', 'förskola', 'kontor',
            'reverberation', 'efterklangstid', 'nachhallzeit',
            'acoustic', 'akustik', 'buller', 'lärm',
            
            # Measurement units (indicates technical query)
            'db', 'decibel', 'hz', 'khz', 'meter', 'second',
            
            # Action verbs (indicates information seeking)
            'tell', 'show', 'explain', 'find', 'get', 'give',
            'compare', 'list', 'describe', 'calculate',
        ]
        
        # Phrases that seem generic but might be knowledge queries
        self.ambiguous_patterns = [
            r'who are you',  # Could be asking about contact person
            r'what.*do',  # "What do you recommend?" vs "What do 3744 say?"
            r'can you',  # "Can you help?" vs "Can you find..."
            r'help me',  # Ambiguous intent
        ]
    
    def classify(self, query: str) -> QueryType:
        """
        Classify query with CONSERVATIVE approach
        
        Returns:
            'generic' - ONLY if 100% certain (exact pattern match)
            'knowledge' - Default for everything else
        """
        if not query or not query.strip():
            return 'knowledge'  # Empty query → safe default
        
        # Normalize for comparison
        q = query.lower().strip()
        q_clean = re.sub(r'[^\w\s]', '', q)
        words = q_clean.split()
        
        # SAFETY CHECK 1: Question mark → ALWAYS knowledge (even "hi?")
        if '?' in query:
            logger.info(f"Query '{query}' contains '?' → knowledge")
            return 'knowledge'
        
        # Remove trailing punctuation for pattern matching (after ?  check)
        q_for_match = re.sub(r'[!.]+$', '', q).strip()
        
        # SAFETY CHECK 2: Exact pattern match required for 'generic'
        is_strict_generic = any(
            re.match(pattern, q_for_match, re.IGNORECASE) 
            for pattern in self.strict_generic_patterns
        )
        
        if is_strict_generic:
            # Even if pattern matches, double-check for knowledge indicators
            if self._has_knowledge_indicators(q_clean):
                logger.info(f"Query '{query}' matched generic pattern but has knowledge indicators → knowledge")
                return 'knowledge'
            
            logger.info(f"Query '{query}' classified as generic (exact match)")
            return 'generic'
        
        # SAFETY CHECK 3: Any knowledge indicator → retrieval
        if self._has_knowledge_indicators(q_clean):
            logger.info(f"Query '{query}' has knowledge indicators → knowledge")
            return 'knowledge'
        
        # SAFETY CHECK 4: Multiple words without generic pattern → knowledge
        if len(words) > 2:
            logger.info(f"Query '{query}' is multi-word, not matched → knowledge")
            return 'knowledge'
        
        # SAFETY CHECK 5: Check for ambiguous patterns
        if self._is_ambiguous(q):
            logger.info(f"Query '{query}' is ambiguous → knowledge (safe default)")
            return 'knowledge'
        
        # DEFAULT: When in doubt, use retrieval!
        logger.info(f"Query '{query}' uncertain → knowledge (conservative default)")
        return 'knowledge'
    
    def _has_knowledge_indicators(self, query_normalized: str) -> bool:
        """Check if query contains ANY knowledge-seeking indicators"""
        return any(
            indicator in query_normalized.split()
            for indicator in self.knowledge_indicators
        )
    
    def _is_ambiguous(self, query_normalized: str) -> bool:
        """Check if query matches ambiguous patterns"""
        return any(
            re.search(pattern, query_normalized, re.IGNORECASE)
            for pattern in self.ambiguous_patterns
        )
    
    def classify_with_confidence(self, query: str) -> tuple[QueryType, float]:
        """
        Classify with confidence score
        
        Returns:
            (query_type, confidence)
            - generic with confidence 1.0 = exact pattern match
            - knowledge with confidence 1.0 = has indicators
            - knowledge with confidence 0.5 = uncertain (default)
        """
        result = self.classify(query)
        
        if result == 'generic':
            # Only classified as generic if exact match
            return ('generic', 1.0)
        
        # Knowledge query
        if self._has_knowledge_indicators(query.lower()):
            return ('knowledge', 1.0)  # High confidence
        elif '?' in query:
            return ('knowledge', 0.9)  # High confidence (question)
        else:
            return ('knowledge', 0.5)  # Uncertain, but safe default
