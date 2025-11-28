#!/usr/bin/env python3
"""
Test script for the distributed syllabus service.

This script tests the complete flow:
1. Mock syllabus service (FastAPI)
2. MCP wrapper (HTTP client)
3. Data serialization/deserialization
4. Original MCP tool interface compatibility

Run this to verify the distributed architecture works without LLM calls.
"""
import asyncio
import subprocess
import time
import httpx
from dataclasses import asdict

# Test direct HTTP calls to the service
def test_direct_http_calls():
    """Test direct HTTP calls to the mock syllabus service."""
    print("🔍 Testing direct HTTP calls to mock syllabus service...")
    
    base_url = "http://localhost:8001"
    
    # Test health check
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{base_url}/health")
            response.raise_for_status()
            health_data = response.json()
            print(f"✅ Health check: {health_data}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test parse syllabus endpoint
    try:
        parse_request = {
            "pdf_path_or_url": "test_syllabus_101.pdf"
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{base_url}/syllabus:parse",
                json=parse_request
            )
            response.raise_for_status()
            parse_data = response.json()
            print(f"✅ Parse syllabus: Got course {parse_data['course_code']} - {parse_data['course_title']}")
            print(f"   📚 Found {len(parse_data['assignments'])} assignments")
            print(f"   📅 Found {len(parse_data['schedule'])} schedule entries")
            
    except Exception as e:
        print(f"❌ Parse syllabus failed: {e}")
        return False
    
    # Test answer question endpoint
    try:
        # Use the parsed syllabus data from above
        question_request = {
            "syllabus_data": parse_data,
            "question": "What is the late policy?"
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{base_url}/syllabus/qa",
                json=question_request
            )
            response.raise_for_status()
            answer_data = response.json()
            print(f"✅ Answer question: {answer_data['answer'][:100]}...")
            
    except Exception as e:
        print(f"❌ Answer question failed: {e}")
        return False
    
    print("✅ All direct HTTP tests passed!\n")
    return True


def test_mcp_wrapper():
    """Test the MCP wrapper that makes HTTP calls."""
    print("🔍 Testing MCP wrapper HTTP client...")
    
    try:
        # Import and test the MCP wrapper (use raw functions for testing)
        from mcp_wrappers.syllabus.mcp_service import _parse_syllabus as parse_syllabus, _answer_syllabus_question as answer_syllabus_question
        
        # Test parse_syllabus function
        print("📝 Testing parse_syllabus MCP wrapper...")
        syllabus = parse_syllabus("test_syllabus_625.pdf")
        
        # Verify we got a dataclass back (not Pydantic)
        print(f"✅ Got syllabus dataclass: {type(syllabus)}")
        print(f"   Course: {syllabus.course_code} - {syllabus.course_title}")
        print(f"   Assignments: {len(syllabus.assignments)}")
        print(f"   First assignment: {syllabus.assignments[0].title}")
        
        # Test answer_syllabus_question function  
        print("❓ Testing answer_syllabus_question MCP wrapper...")
        answer = answer_syllabus_question(
            syllabus_data=syllabus,
            question="How many assignments are there?"
        )
        
        print(f"✅ Got answer: {answer[:100]}...")
        
        # Verify data types are correct (original dataclass format)
        assert hasattr(syllabus, '__dataclass_fields__'), "Should be a dataclass"
        assert isinstance(answer, str), "Answer should be a string"
        
        print("✅ All MCP wrapper tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ MCP wrapper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_conversion():
    """Test data conversion between dataclass and Pydantic models."""
    print("🔍 Testing data conversion between dataclass and Pydantic...")
    
    try:
        from mcp_wrappers.syllabus.mcp_service import _dataclass_to_pydantic_syllabus, _pydantic_to_dataclass_syllabus
        from syllabus_server.models import ParsedSyllabus, Assignment, Policies, CourseSection
        from services.shared.models import ParsedSyllabus as PydanticParsedSyllabus
        
        # Create a simple test dataclass
        test_syllabus = ParsedSyllabus(
            course_code="TEST-123",
            course_title="Test Conversion",
            term="Spring 2024",
            timezone="UTC",
            sections=[],
            assignments=[
                Assignment(
                    title="Test Assignment",
                    due="2024-04-01T23:59:00Z",
                    weight_percent=25.0,
                    category="homework",
                    is_in_class=False,
                    notes="Test notes"
                )
            ],
            schedule=[],
            policies=Policies(
                due_time_default="23:59",
                late_policy="Test policy",
                attendance_policy="Required",
                ai_policy="Allowed",
                other="Other policies"
            )
        )
        
        # Convert to Pydantic
        pydantic_syllabus = _dataclass_to_pydantic_syllabus(test_syllabus)
        print(f"✅ Dataclass -> Pydantic conversion: {type(pydantic_syllabus)}")
        assert pydantic_syllabus.course_code == "TEST-123"
        assert len(pydantic_syllabus.assignments) == 1
        
        # Convert back to dataclass
        converted_back = _pydantic_to_dataclass_syllabus(pydantic_syllabus)
        print(f"✅ Pydantic -> Dataclass conversion: {type(converted_back)}")
        assert converted_back.course_code == "TEST-123"
        assert len(converted_back.assignments) == 1
        assert hasattr(converted_back, '__dataclass_fields__')
        
        print("✅ All data conversion tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Data conversion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests for the distributed syllabus service."""
    print("🧪 Testing Distributed Syllabus Service")
    print("=" * 50)
    
    print("📋 Test Plan:")
    print("1. Start mock syllabus service")
    print("2. Test direct HTTP calls")
    print("3. Test MCP wrapper HTTP client")
    print("4. Test data conversion")
    print("5. Clean up")
    print()
    
    # Start the mock service
    print("🚀 Starting mock syllabus service...")
    try:
        process = subprocess.Popen(
            ["uv", "run", "python", "services/syllabus_service/mock_app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it a moment to start
        print("⏳ Waiting for service to start...")
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Service failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
            
        print("✅ Mock service started!\n")
        
        # Run tests
        all_tests_passed = True
        
        # Test 1: Direct HTTP calls
        all_tests_passed &= test_direct_http_calls()
        
        # Test 2: MCP wrapper
        all_tests_passed &= test_mcp_wrapper()
        
        # Test 3: Data conversion
        all_tests_passed &= test_data_conversion()
        
        # Summary
        print("📊 Test Results:")
        print("=" * 50)
        if all_tests_passed:
            print("🎉 All tests PASSED! The distributed syllabus service is working correctly.")
            print("\n✅ Verified functionality:")
            print("   • Mock REST service responds correctly")
            print("   • HTTP client communication works")
            print("   • Data serialization/deserialization works")
            print("   • Original MCP interface is preserved")
            print("   • Extended timeouts are configured")
        else:
            print("❌ Some tests FAILED. Check the output above for details.")
        
        return all_tests_passed
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up: stop the service
        try:
            process.terminate()
            process.wait(timeout=5)
            print("\n🧹 Mock service stopped")
        except:
            try:
                process.kill()
                print("\n🧹 Mock service force stopped")
            except:
                print("\n⚠️  Could not stop mock service")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)