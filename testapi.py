import requests
import json
import time

# --- Configuration ---
# The URL where your FastAPI application is running
API_URL = "https://avyakt06jain-phantom-agents-customer-support.hf.space/process"

# The Bearer token for authorization (use your actual key)
API_KEY = "06864514c746f45fb93a6e0421a052c7875d3d1fd841d870f397c9d50e4146f8"

# The headers for the request
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# --- Test Data ---
DOCUMENT_URL = "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D"

# A list of questions to simulate a conversation
CONVERSATIONAL_QUERIES = [
    "What is the grace period for premium payment under this policy?",
    "That's helpful. Now, what about pre-existing diseases? What's the waiting period for them?",
    "My sister is pregnant. Does this policy cover maternity expenses?",
    "This is unacceptable! I need to speak to a manager about this.", # Test escalation
    "Okay, let's go back. Are medical expenses for an organ donor covered?"
]

def run_conversational_test():
    """
    Simulates a back-and-forth conversation with the API.
    """
    print("--- Starting Conversational API Test ---")
    
    chat_history = []
    
    for i, query in enumerate(CONVERSATIONAL_QUERIES):
        print(f"\n--- Turn {i+1} ---")
        print(f"User > {query}")

        payload = {
            "query": query,
            "history": chat_history
        }

        # **IMPORTANT**: Only send the document_url on the VERY FIRST request
        if i == 0:
            payload["document_url"] = DOCUMENT_URL
            print("(Sending document_url for initial processing...)")

        start_time = time.time()
        
        try:
            # Send the POST request
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=300)
            
            end_time = time.time()
            print(f"Request completed in {end_time - start_time:.2f} seconds.")

            # Handle the response
            if response.status_code == 200:
                response_data = response.json()
                answer = response_data.get("answer", "No answer found.")
                doc_hash = response_data.get("document_hash")
                
                print(f"Agent > {answer}")
                print(f"(Context: Document Hash {doc_hash})")

                # Update chat history for the next turn
                chat_history.append({"role": "user", "content": query})
                chat_history.append({"role": "model", "content": answer})

            else:
                print(f"❌ Request failed with Status Code: {response.status_code}")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except json.JSONDecodeError:
                    print(response.text)
                # Stop the test if an error occurs
                break

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break
        
        # Pause to simulate a real user
        time.sleep(1)

    print("\n--- Test Finished ---")

if __name__ == "__main__":
    run_conversational_test()
