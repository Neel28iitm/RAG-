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
 
  
         d e f   g e n e r a t e _ g e n e r i c _ r e s p o n s e ( s e l f ,   q u e r y :   s t r ,   c h a t _ h i s t o r y = N o n e )   - >   s t r :  
                 " " "  
                 G e n e r a t e   r e s p o n s e   f o r   g e n e r i c / c h i t c h a t   q u e r i e s   W I T H O U T   r e t r i e v a l  
                 F a s t   p a t h   f o r   g r e e t i n g s ,   t h a n k s ,   s i m p l e   a c k n o w l e d g m e n t s  
                  
                 A r g s :  
                         q u e r y :   U s e r ' s   g e n e r i c   q u e r y   ( e . g . ,   " H i " ,   " T h a n k s " )  
                         c h a t _ h i s t o r y :   O p t i o n a l   c h a t   h i s t o r y   f o r   c o n t e x t  
                          
                 R e t u r n s :  
                         F r i e n d l y   g e n e r i c   r e s p o n s e  
                 " " "  
                 s y s t e m _ p r o m p t   =   " " " Y o u   a r e   a   h e l p f u l   R A G   a s s i s t a n t   s p e c i a l i z e d   i n   a c o u s t i c   e n g i n e e r i n g   a n d   b u i l d i n g   a c o u s t i c s .  
  
 F o r   g e n e r i c   m e s s a g e s   l i k e   g r e e t i n g s ,   t h a n k s ,   o r   s i m p l e   q u e s t i o n s :  
 -   R e s p o n d   n a t u r a l l y   a n d   b r i e f l y  
 -   B e   f r i e n d l y   b u t   c o n c i s e      
 -   O f f e r   t o   h e l p   w i t h   q u e s t i o n s   a b o u t :  
     *   I S O   s t a n d a r d s   ( I S O   3 7 4 4 ,   I S O   3 3 8 2 )  
     *   S w e d i s h   b u i l d i n g   a c o u s t i c s   ( S S   2 5 2 6 8 )  
     *   N o i s e   m e a s u r e m e n t s   a n d   l i m i t s  
     *   R e v e r b e r a t i o n   t i m e   r e q u i r e m e n t s  
     *   A c o u s t i c   r e p o r t s   a n d   d a t a  
  
 E x a m p l e s :  
 -   U s e r :   " H i "   �      " H e l l o !   I   c a n   h e l p   y o u   f i n d   i n f o r m a t i o n   a b o u t   a c o u s t i c   s t a n d a r d s ,   n o i s e   m e a s u r e m e n t s ,   a n d   b u i l d i n g   r e g u l a t i o n s .   W h a t   w o u l d   y o u   l i k e   t o   k n o w ? "  
 -   U s e r :   " T h a n k s "   �      " Y o u ' r e   w e l c o m e !   F e e l   f r e e   t o   a s k   i f   y o u   n e e d   a n y t h i n g   e l s e   a b o u t   a c o u s t i c s   o r   n o i s e   s t a n d a r d s . "  
 -   U s e r :   " O K "   �      " G r e a t !   L e t   m e   k n o w   i f   y o u   h a v e   a n y   o t h e r   q u e s t i o n s   a b o u t   a c o u s t i c   m e a s u r e m e n t s   o r   s t a n d a r d s . "  
 " " "  
                  
                 p r o m p t   =   C h a t P r o m p t T e m p l a t e . f r o m _ m e s s a g e s ( [  
                         ( " s y s t e m " ,   s y s t e m _ p r o m p t ) ,  
                         M e s s a g e s P l a c e h o l d e r ( v a r i a b l e _ n a m e = " c h a t _ h i s t o r y " ,   o p t i o n a l = T r u e ) ,  
                         ( " h u m a n " ,   " { q u e s t i o n } " )  
                 ] )  
                  
                 c h a i n   =   p r o m p t   |   s e l f . l l m  
                  
                 t r y :  
                         r e s p o n s e   =   c h a i n . i n v o k e ( {  
                                 " q u e s t i o n " :   q u e r y ,  
                                 " c h a t _ h i s t o r y " :   c h a t _ h i s t o r y   o r   [ ]  
                         } )  
                         r e t u r n   r e s p o n s e . c o n t e n t  
                 e x c e p t   E x c e p t i o n   a s   e :  
                         l o g g e r . e r r o r ( f " G e n e r i c   r e s p o n s e   g e n e r a t i o n   f a i l e d :   { e } " )  
                         #   F a l l b a c k   r e s p o n s e  
                         r e t u r n   " H e l l o !   H o w   c a n   I   a s s i s t   y o u   w i t h   a c o u s t i c   m e a s u r e m e n t s   a n d   b u i l d i n g   s t a n d a r d s   t o d a y ? "  
 