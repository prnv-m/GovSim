"""
Test Gemini LLM directly - no agents, no git, just API
"""

import logging
import sys
from config import Config
from src.llm_client import CodeGenerator

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_single_request():
    """Test a single LLM request with debugging"""
    
    print("\n" + "="*70)
    print("TEST 1: Single LLM Request (with debug)")
    print("="*70 + "\n")
    
    generator = CodeGenerator()
    
    print("Calling LLM to generate simple Python function...")
    print("(This will take 10-30 seconds)\n")
    
    code = generator.generate_for_agent(
        agent_name="TestAgent1",
        task="Build a simple utility function",
        feature="sum_numbers",
        context="Takes a list of integers, returns their sum",
        language="python"
    )
    
    if code:
        print("\n✓ SUCCESS! Generated code:\n")
        print("-" * 70)
        print(code)
        print("-" * 70)
        return True
    else:
        print("\n✗ FAILED - No code returned")
        return False

def test_multiple_requests():
    """Test multiple requests to see if API is stable"""
    
    print("\n" + "="*70)
    print("TEST 2: Multiple Requests (stress test)")
    print("="*70 + "\n")
    
    generator = CodeGenerator()
    
    tasks = [
        {
            "agent_name": "Agent1",
            "feature": "authentication",
            "task": "Build user auth system"
        },
        {
            "agent_name": "Agent2",
            "feature": "database",
            "task": "Build database abstraction layer"
        },
        {
            "agent_name": "Agent3",
            "feature": "api_handler",
            "task": "Build REST API handler"
        }
    ]
    
    success_count = 0
    
    for i, task in enumerate(tasks, 1):
        print(f"\nRequest {i}/3: {task['agent_name']} - {task['feature']}")
        print("Waiting for response...", end=" ", flush=True)
        
        code = generator.generate_for_agent(
            agent_name=task['agent_name'],
            task=task['task'],
            feature=task['feature'],
            context="Standard implementation",
            language="python"
        )
        
        if code:
            print("✓")
            print(f"  Generated {len(code)} chars of code")
            success_count += 1
        else:
            print("✗ (timeout or error)")
    
    print(f"\nResults: {success_count}/{len(tasks)} successful")
    return success_count == len(tasks)

def test_with_increased_timeout():
    """Test with longer timeout"""
    
    print("\n" + "="*70)
    print("TEST 3: Increased Timeout (60 seconds)")
    print("="*70 + "\n")
    
    # Temporarily increase timeout
    original_timeout = Config.CODE_GENERATION_TIMEOUT
    Config.CODE_GENERATION_TIMEOUT = 60
    
    print(f"Timeout set to: {Config.CODE_GENERATION_TIMEOUT}s")
    
    generator = CodeGenerator()
    
    print("\nGenerating code with longer timeout...")
    
    code = generator.generate_for_agent(
        agent_name="SlowAgent",
        task="Build complex voting system",
        feature="vote_counter",
        context="Must be tamper-proof and efficient",
        language="python"
    )
    
    # Restore
    Config.CODE_GENERATION_TIMEOUT = original_timeout
    
    if code:
        print("\n✓ SUCCESS with longer timeout!\n")
        print(code[:500] + "..." if len(code) > 500 else code)
        return True
    else:
        print("\n✗ Still timing out - API may be slow or overloaded")
        return False

def main():
    print("\n" + "="*70)
    print("GEMINI LLM DIRECT TEST")
    print("="*70)
    print(f"\nAPI Key: {Config.GEMINI_API_KEYS[:20]}...")
    print(f"Model: {Config.GEMINI_MODEL_NAME}")
    print(f"Timeout: {Config.CODE_GENERATION_TIMEOUT}s")
    
    # Run tests
    test1 = test_single_request()
    
    if not test1:
        print("\n" + "="*70)
        print("DEBUGGING STEPS:")
        print("="*70)
        print("\n1. Check API Key")
        print("   - Go to https://aistudio.google.com/app/apikey")
        print("   - Verify key is valid and not expired")
        print("   - Copy correct key to config.py")
        
        print("\n2. Check API Quota")
        print("   - Gemini API has rate limits")
        print("   - Try again in 1-2 minutes")
        print("   - Or increase timeout: CODE_GENERATION_TIMEOUT = 60")
        
        print("\n3. Check Network")
        print("   - Try: curl -i https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent")
        
        print("\n4. Test with Increased Timeout")
        print("   - Run test 3 below for 60-second timeout")
        
        return 1
    
    print("\n✓ Single request works, trying multiple requests...")
    test2 = test_multiple_requests()
    
    if test2:
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - LLM IS WORKING!")
        print("="*70)
        print("\nYou can now run: python main.py")
        return 0
    else:
        print("\nTrying with increased timeout...")
        test3 = test_with_increased_timeout()
        
        if test3:
            print("\n✓ Works with longer timeout!")
            print("  Update config.py: CODE_GENERATION_TIMEOUT = 60")
            return 0
        else:
            print("\n✗ LLM not working - check debugging steps above")
            return 1

if __name__ == "__main__":
    sys.exit(main())
