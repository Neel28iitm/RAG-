import os
import sys
import pandas as pd
from datasets import Dataset 
import phoenix as px
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Import Application Modules
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.core.config import load_config
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv(dotenv_path="config/.env")

def run_evaluation():
    print("Starting RAG Evaluation with Phoenix & Ragas...")

    # 1. Phoenix Tracing Setup
    # session = px.launch_app()
    # tracer_provider = register()
    # LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    # print(f"Phoenix UI is running at: {session.url}")
    print("Skipping Phoenix for debug run...")

    # 2. Services Init
    config = load_config("config/settings.yaml")
    retriever_service = RetrievalService(config)
    gen_service = GenerationService(config)

    # 3. Test Data (Sample - Expand this for production)
    # TODO: Load from a file in future
    test_questions = [
        "What are the safety requirements for bow thrusters?"
    ]
    
    # Simple Ground Truths (For demonstration of metrics)
    ground_truths = [
        "Safety requirements include emergency stop buttons, protective covers, and regular inspections."
    ]

    # 4. Data Collection (Run your pipeline)
    answers = []
    contexts = []

    print("Running Pipeline on Test Data...")
    for query in test_questions:
        try:
            print(f"Processing: {query}")
            # A. Retrieval Component
            # Note: Using expand_query as per actual flow
            expanded_query = gen_service.expand_query(query) 
            docs = retriever_service.get_relevant_docs(expanded_query) 
            
            # Extract text from docs
            retrieved_text = [doc.page_content for doc in docs]
            contexts.append(retrieved_text)

            # B. Generation Component
            # Pass empty chat history for evaluation context
            ans = gen_service.generate_answer(query, docs, chat_history=[])
            answers.append(ans)
        except Exception as e:
            print(f"Error processing {query}: {e}")
            answers.append("Error")
            contexts.append(["Error"])

    # 5. Prepare Dataset for Ragas
    data_dict = {
        "question": test_questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(data_dict)

    print("Initializing Ragas Evaluator (Gemini)...")
    # 6. Configure Ragas with Gemini (Cost saving)
    # Using the same model config as the app for consistency/availability
    llm_model = config['llm']['model_name']
    evaluator_llm = ChatGoogleGenerativeAI(model=llm_model)
    evaluator_embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # 7. Run Evaluation
    print("Running Ragas Evaluation...")
    results = evaluate(
        dataset=dataset,
        metrics=[
            context_precision, # Retrieval Quality
            context_recall,    # Retrieval Quality
            faithfulness,      # Hallucination Check
            answer_relevancy,  # Answer Quality
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings
    )

    # 8. View & Save Results
    df = results.to_pandas()
    df.to_csv("evaluation_results.csv", index=False)
    print("\nEvaluation Complete! Results saved to 'evaluation_results.csv'")
    print(results)
    
    # Keep session open for a bit if running manually (optional)
    input("\nPress Enter to exit and stop Phoenix server...")

if __name__ == "__main__":
    run_evaluation()
