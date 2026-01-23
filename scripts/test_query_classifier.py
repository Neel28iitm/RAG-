"""
Test suite for Query Classifier
Ensures no false positives (knowledge queries marked as generic)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.query_classifier import QueryClassifier

def test_strict_generic():
    """Test cases that SHOULD be classified as generic"""
    classifier = QueryClassifier()
    
    generic_queries = [
        "hi",
        "Hi",
        "hello",
        "Hello!",
        "hey",
        "thanks",
        "thank you",
        "Thanks!",
        "ok",
        "OK",
        "okay",
        "bye",
        "goodbye",
        "yes",
        "no",
    ]
    
    print("=" * 60)
    print("TEST: Strict Generic Queries (Should ALL be 'generic')")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query in generic_queries:
        result = classifier.classify(query)
        status = "✅ PASS" if result == 'generic' else "❌ FAIL"
        print(f"{status} | '{query:20}' → {result}")
        if result == 'generic':
            passed += 1
        else:
            failed += 1
    
    print(f"\nGeneric Test: {passed}/{len(generic_queries)} passed")
    return failed == 0


def test_knowledge_queries():
    """Test cases that MUST be classified as knowledge (CRITICAL!)"""
    classifier = QueryClassifier()
    
    knowledge_queries = [
        # Explicit questions
        "What is ISO 3744?",
        "Who is the contact person?",
        "How to measure noise?",
        "Where is the data?",
        "When was it measured?",
        
        # Domain-specific
        "ISO 3744 standard",
        "noise levels for offices",
        "SS 25268 requirements",
        "Mora skidgymnasium report",
        "reverberation time",
        "efterklangstid",
        
        # With keywords
        "show me the table",
        "find the document",
        "what are the limits",
        "tell me about measurements",
        
        # Edge cases
        "hi, what is ISO 3744?",  # Mixed - should be knowledge!
        "thanks! show me data",  # Mixed - should be knowledge!
        "ok, but what about noise?",  # Mixed - should be knowledge!
    ]
    
    print("\n" + "=" * 60)
    print("TEST: Knowledge Queries (MUST ALL be 'knowledge')")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query in knowledge_queries:
        result = classifier.classify(query)
        status = "✅ PASS" if result == 'knowledge' else "❌ FAIL (CRITICAL!)"
        print(f"{status} | '{query:40}' → {result}")
        if result == 'knowledge':
            passed += 1
        else:
            failed += 1
    
    print(f"\nKnowledge Test: {passed}/{len(knowledge_queries)} passed")
    
    if failed > 0:
        print(f"\n⚠️  CRITICAL: {failed} knowledge queries misclassified!")
        print("   This could cause retrieval to be skipped for real questions!")
    
    return failed == 0


def test_edge_cases():
    """Test challenging edge cases"""
    classifier = QueryClassifier()
    
    edge_cases = [
        ("?", 'knowledge'),  # Question mark alone
        ("hi?", 'knowledge'),  # Greeting with question mark  
        ("who are you", 'knowledge'),  # Seems generic but could be knowledge
        ("what do you know", 'knowledge'),  # Ambiguous
        ("help", 'knowledge'),  # Could be asking for help finding data
        ("help me", 'knowledge'),  # Same
        ("can you help", 'knowledge'),  # Ambiguous
        ("hello world", 'knowledge'),  # Multi-word, not exact pattern
        ("hi there", 'knowledge'),  # Not exact "hi"
        ("thank you very much", 'knowledge'),  # Not exact "thank you"
    ]
    
    print("\n" + "=" * 60)
    print("TEST: Edge Cases (Conservative = 'knowledge' for safety)")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query, expected in edge_cases:
        result = classifier.classify(query)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} | '{query:30}' → {result:10} (expected: {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"\nEdge Case Test: {passed}/{len(edge_cases)} passed")
    return failed == 0


def test_multilingual():
    """Test Swedish and German queries"""
    classifier = QueryClassifier()
    
    multilingual_tests = [
        # Swedish
        ("hej", 'generic'),
        ("tack", 'generic'),
        ("Vad är ISO 3744?", 'knowledge'),
        ("bullernivoer för kontor", 'knowledge'),
        
        # German  
        ("hallo", 'generic'),
        ("danke", 'generic'),
        ("Was ist ISO 3744?", 'knowledge'),
        ("Lärmpegel für Büros", 'knowledge'),
    ]
    
    print("\n" + "=" * 60)
    print("TEST: Multilingual Support")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query, expected in multilingual_tests:
        result = classifier.classify(query)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} | '{query:35}' → {result:10} (expected: {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"\nMultilingual Test: {passed}/{len(multilingual_tests)} passed")
    return failed == 0


if __name__ == "__main__":
    print("\n" + "🧪 QUERY CLASSIFIER TEST SUITE" + "\n")
    
    results = []
    results.append(("Generic Queries", test_strict_generic()))
    results.append(("Knowledge Queries", test_knowledge_queries()))
    results.append(("Edge Cases", test_edge_cases()))
    results.append(("Multilingual", test_multilingual()))
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} | {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Classifier is safe to deploy.")
    else:
        print("\n⚠️  SOME TESTS FAILED! Review and fix before deployment.")
    
    print("\nSafety Note: Classifier is CONSERVATIVE.")
    print("When in doubt, it uses retrieval (knowledge) - this is by design!")
