import os
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
load_dotenv(env_path)

def test_search_api():
    # Get API key from environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set")
    
    # Test parameters
    test_query = "test query"
    
    # Test both official and custom endpoints
    endpoints = [
        {
            "name": "Official Google Custom Search API",
            "base_url": "https://www.googleapis.com/customsearch/v1"
        },
        {
            "name": "Custom Search API",
            "base_url": "https://customsearch-googleapis.apiannie.com/customsearch/v1"
        }
    ]
    
    # Test different parameter combinations
    test_cases = [
        {
            "name": "Basic query only",
            "params": {
                'key': api_key,
                'q': test_query
            }
        },
        {
            "name": "Query with user's cx",
            "params": {
                'key': api_key,
                'q': test_query,
                'cx': 'c6d8fc3b5a4cb4090'
            }
        }
    ]
    
    # Run tests for each endpoint
    for endpoint in endpoints:
        print(f"\n{'='*50}")
        print(f"Testing {endpoint['name']}")
        print(f"{'='*50}")
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            print(f"Parameters: {test_case['params']}")
            
            url = f"{endpoint['base_url']}?{urlencode(test_case['params'])}"
            print(f"Request URL: {url}")
            
            try:
                response = requests.get(url, verify=False)
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text[:500]}...")  # Print first 500 chars of response
            except Exception as e:
                print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_search_api() 