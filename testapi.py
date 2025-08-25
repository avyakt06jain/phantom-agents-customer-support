import requests
import json
import time
import os

# --- Configuration ---
# The URL where your FastAPI application is running
API_URL = "https://avyakt06jain-phantom-agents-customer-support.hf.space/process"

# The Bearer token for authorization (use your actual key)
API_KEY = "06864514c746f45fb93a6e0421a052c7875d3d1fd841d870f397c9d50e4146f8" # <-- IMPORTANT: Replace with your actual API_KEY from .env

# The headers for the request (Content-Type is handled by `requests` library for multipart/form-data)
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# --- Test Data ---
# IMPORTANT: Make sure you have a file named 'policy.pdf' in the same directory as this script.
# You can download the sample file from: https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D
LOCAL_DOC_PATH = "policy.pdf" 

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
    Simulates a back-and-forth conversation with the API using file uploads.
    """
    if not os.path.exists(LOCAL_DOC_PATH):
        print(f"❌ Error: Test document '{LOCAL_DOC_PATH}' not found.")
        print("Please download the sample policy PDF and place it in the same directory as this script.")
        return

    print("--- Starting Conversational API Test (File Upload) ---")
    
    chat_history = []
    
    for i, query in enumerate(CONVERSATIONAL_QUERIES):
        print(f"\n--- Turn {i+1} ---")
        print(f"User > {query}")

        # Prepare form data
        data = {
            "query": query,
            "history": json.dumps(chat_history) # History must be a JSON string
        }
        
        files = {}
        # **IMPORTANT**: Only send the document file on the VERY FIRST request
        if i == 0:
            print(f"(Uploading '{LOCAL_DOC_PATH}' for initial processing...)")
            files['document'] = (os.path.basename(LOCAL_DOC_PATH), open(LOCAL_DOC_PATH, 'rb'), 'application/pdf')

        start_time = time.time()
        
        try:
            # Send the POST request with multipart/form-data
            # `requests` handles the Content-Type header automatically when using `files`
            response = requests.post(API_URL, headers=headers, data=data, files=files, timeout=300)
            
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
                break # Stop the test on error

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break
        finally:
            # Important: Close the file if it was opened
            if 'document' in files and files['document'][1]:
                files['document'][1].close()
        
        time.sleep(1)

    print("\n--- Test Finished ---")

if __name__ == "__main__":
    run_conversational_test()
