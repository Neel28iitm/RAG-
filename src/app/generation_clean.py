            logger.error(f"❌ Streaming failed: {e}")
            yield "Error: Generation failed."

    def generate_generic_response(self, query: str, chat_history=None) -> str:
        """Generate response for generic/chitchat queries WITHOUT retrieval"""
        system_prompt = """You are a helpful RAG assistant specialized in acoustic engineering.

For generic messages (greetings, thanks):
- Respond naturally and briefly
- Offer to help with acoustic standards, noise measurements, building regulations

Examples:
- Hi -> Hello! I can help you find information about acoustic standards and noise measurements.
- Thanks -> You're welcome! Feel free to ask if you need anything else."""
        
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
