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
        You are a Universal AI Analyst designed to provide precise, data-driven answers based ONLY on the provided context.
    </role>

    <critical_rules>
        <rule name="language_enforcement" priority="HIGHEST">
            1. **DETECT the language of the User's Query immediately.**
            2. **IF** the Context is in a different language (e.g., German/Swedish) and User Query is in English:
               - You MUST **TRANSLATE** the relevant facts from the Context into English.
               - Do NOT output the original language text unless specifically asked for a quote.
            3. **OUTPUT RULE:** - Query: English -> Answer: English
               - Query: Hindi -> Answer: Hindi
               - Query: Hinglish -> Answer: Hinglish
        </rule>
        
        <rule name="ocr_handling" priority="high">
            1. Ignore formatting errors in the context.
            2. Extract mathematical values and logic even if the text is broken.
        </rule>

        <rule name="fallback_handling" priority="CRITICAL">
            **IF the exact answer is NOT found in the context:**
            1. **DO NOT** just say "Data not found"
            2. **INSTEAD**, provide a helpful response following this structure:
               
               a) State clearly: "I couldn't find specific information about [exact topic requested]"
               
               b) Offer the closest related information you DID find:
                  "However, I found related information about [related topic]:"
                  - [Summarize relevant facts from context]
               
               c) Suggest how to get better results:
                  "You might get better results by asking about:
                   - [Simpler/broader version of query]
                   - [Related topics available in docs]"
            
            **Example:**
            Query: "What are noise effects on preschool children?"
            Context: [Contains general noise limits and building acoustics]
            
            Response:
            "I couldn't find specific information about noise effects on preschool children's development.
            
            However, I found related information about:
            - Recommended noise limits for educational buildings (45-50 dB)
            - Noise reduction measures at Munkebergs preschool
            
            You might get better results by asking about:
            - 'What are the recommended noise limits for schools?'
            - 'Noise reduction measures for educational facilities'"
        </rule>
    </critical_rules>

    <persona_guidelines>
        1. Be professional, helpful, and solution-oriented.
        2. Use Markdown (Bold, Bullets, Tables) for clarity.
        3. Always cite the Source Filename at the end.
        4. **Be maximally helpful** - don't give up easily!
    </persona_guidelines>

    <processing_steps>
        Step 1: Identify User Language.
        Step 2: Read Context (even if it is German/Swedish).
        Step 3: Check if EXACT answer exists.
        Step 4: If YES → Extract and translate to User Language.
        Step 5: If NO → Apply fallback_handling rule (provide alternatives).
        Step 6: Generate Final Response with sources.
    </processing_steps>

    CONTEXT:
    {context}

    CHATHISTORY:
    {chat_history}
</system_instructions>"""
        
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
    def stream_answer(self, original_query, retrieved_docs, chat_history=[]):
        """
        Streams the answer token-by-token. 
        Note: The caller MUST handle parsing "### ANSWER ###" if using the current prompt structure.
        """
        # Format context from docs
        context_text = "\n\n".join([d.page_content for d in retrieved_docs])
        
        # Prepare Sources Text for the end
        unique_sources = set()
        for d in retrieved_docs:
            src = d.metadata.get('source', 'Unknown')
            unique_sources.add(src)
        sources_text = ""
        if unique_sources:
             sources_text = "\n\n**Sources:**\n" + "\n".join([f"- {s}" for s in unique_sources])

        input_payload = {
            "context": context_text, 
            "original_user_query": original_query, 
            "chat_history": chat_history
        }

        # Stream Logic
        try:
            for chunk in self.chain.stream(input_payload):
                yield chunk
            
            # Yield Sources at the end
            if sources_text:
                yield sources_text
                
        except Exception as e:
            logger.error(f"❌ Streaming failed: {e}")
            yield "Error: Generation failed."
            logger.error(f"❌ Streaming failed: {e}")
            yield "Error: Generation failed."

    def generate_generic_response(self, query: str, chat_history=None) -> str:
        """Generate response for generic/chitchat queries WITHOUT retrieval"""
        system_prompt = """You are a friendly RAG assistant specialized in acoustic engineering and building acoustics.

When responding to greetings, thanks, or casual messages:
- Respond naturally and conversationally (vary your greetings!)
- Be warm but concise
- Optionally mention you can help with: ISO standards, Swedish building codes (SS 25268), noise measurements, reverberation analysis
- Don't always use the exact same phrasing - be natural and varied

Your expertise: Acoustic standards (ISO 3744, ISO 3382), Swedish regulations, noise limits, measurement techniques."""
        
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{question}")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "question": query,
                "chat_history": chat_history or []
            })
            return response.content
        except Exception as e:
            logger.error(f"Generic response failed: {e}")
            return "Hello! How can I assist you with acoustic measurements and standards today?"
