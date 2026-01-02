"""
Module: Generation
Purpose: LLM interaction and answer generation using Gemini 1.5/2.0 Flash.
"""

import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

logger = logging.getLogger('app_logger')

class GenerationService:
    def __init__(self, config):
        self.config = config
        self._initialize_llm()
        self._build_chain()
        self._build_expansion_chain()

    def _initialize_llm(self):
        model_name = self.config['llm']['model_name']
        logger.info(f"🤖 Initializing LLM: {model_name}")
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=self.config['llm']['temperature'],
            max_tokens=self.config['llm']['max_tokens'],
            convert_system_message_to_human=False # Disable conversion to use native System Instructions
        )

    def _build_chain(self):
        """Builds the RAG chain"""
        # System prompt designed for Cross-Lingual/Chain-of-Thought
        system_instruction = """<system_instructions>
    <role>
        You are a Universal AI Analyst designed to provide precise, data-driven answers.
    </role>

    <critical_rules>
        <rule name="ocr_handling" priority="highest">
            1. You are an expert at parsing raw OCR text from technical PDFs.
            2. IGNORE formatting errors (broken lines, weird symbols) and EXTRACT the underlying mathematical relationships.
            3. If a formula is partially visible, RECONSTRUCT it based on context. NEVER refuse to answer due to "poor formatting".
        </rule>
        <rule name="language_enforcement" priority="high">
            1. DETECT the language of the 'original_user_query'.
            2. IGNORE the language of the 'context' documents.
            3. YOUR ENTIRE RESPONSE MUST BE IN THE DETECTED LANGUAGE OF THE 'original_user_query'.
            4. If the context is in German but query is in Hindi, TRANSLATE output to Hindi.
        </rule>
    </critical_rules>

    <output_format>
        1. THOUGHT PROCESS
        (Internal Monologue - Do not show to user)
        - Analyze the User's Query Language.
        - Analyze the Context Language.
        - Decide translation strategy.

        ### ANSWER ###

        (Provide the final response here in the identified User Language)
        (Use standard Markdown formatting like bullets, bold text, etc.)
        (Do NOT use placeholders like [Analysis] or [Conclusion], just write the content naturally.)
        (Do NOT output JSON or code blocks.)
    </output_format>

    CONTEXT:
    {context}

    CHATHISTORY:
    {chat_history}
    """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_instruction),
            # Yaha hum 'original_user_query' pass karenge prompt mein
            ("human", "Original Query: {original_user_query}") 
        ])
        
        self.chain = (
            {
                "context": lambda x: x["context"], 
                "original_user_query": lambda x: x["original_user_query"], 
                "chat_history": lambda x: "\n".join([f"{msg.type}: {msg.content}" for msg in x["chat_history"]])
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def _build_expansion_chain(self):
        """Builds the Query Translation/Expansion chain"""
        template = """You are a maritime technical search assistant. 
        Your goal is to optimize the user's query to find relevant information in a GERMAN Technical Manual.
        
        INSTRUCTIONS:
        1. Identify technical maritime terms in the query.
        2. Translate the entire query or key terms into precise GERMAN technical terminology (e.g., 'Bow thruster' -> 'Bugstrahlruder', 'Noise limits' -> 'Lärmgrenzwerte').
        3. If the query is already in German, improve it for search.
        4. OUPUT ONLY the optimized German search query. Do not add explanations.
        
        User Query: {question}
        
        Optimized German Search Query:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        self.expansion_chain = (
            {"question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def expand_query(self, query):
        """Expands the query using the LLM"""
        try:
            expanded_query = self.expansion_chain.invoke(query)
            logger.info(f"Original Query: '{query}' -> Expanded: '{expanded_query}'")
            return expanded_query.strip()
        except Exception as e:
            logger.error(f"⚠️ Query expansion failed: {e}")
            return query # Fallback to original

    def generate_answer(self, original_query, retrieved_docs, chat_history=[]):
        """
        Modified to separate the 'Search Query' from the 'Original Query'
        """
        # Format context from docs
        context_text = "\n\n".join([d.page_content for d in retrieved_docs])
        
        logger.info(f"generating answer for query: '{original_query}' with {len(retrieved_docs)} context chunks.")
        
        try:
            # Append Sources to the response
            unique_sources = set()
            for d in retrieved_docs:
                src = d.metadata.get('source', 'Unknown')
                unique_sources.add(src)
            
            # 1. Get LLM Response
            # Notice hum "question" key ki jagah "original_user_query" bhej rahe hain
            raw_response = self.chain.invoke({
                "context": context_text, 
                "original_user_query": original_query, 
                "chat_history": chat_history
            })
            
            # 2. Parse Logic (Separator Split)
            final_answer = raw_response
            if "### ANSWER ###" in raw_response:
                # Take everything AFTER the separator
                final_answer = raw_response.split("### ANSWER ###")[1].strip()
            
            # 3. Append Metadata
            if unique_sources:
                sources_text = "\n\n**Sources:**\n" + "\n".join([f"- {s}" for s in unique_sources])
                return final_answer + sources_text
                
            return final_answer
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return "Sorry, I encountered an error while generating the answer."
