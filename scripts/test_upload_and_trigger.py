import requests
import time
from fpdf import FPDF
import os

# Configuration
API_URL = "http://localhost:8000"
TEST_FILENAME = "test_auto_trigger.pdf"

def create_dummy_pdf(filename):
    """Creates a simple dummy PDF for testing."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="This is a test document for automatic ingestion trigger.", ln=1, align="C")
    pdf.output(filename)
    print(f"📄 Created dummy PDF: {filename}")

def test_upload():
    """Uploads the file and checks the response."""
    print(f"🚀 Uploading {TEST_FILENAME} to {API_URL}/upload...")
    
    file_path = TEST_FILENAME
    if not os.path.exists(file_path):
        create_dummy_pdf(file_path)
        
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (TEST_FILENAME, f, 'application/pdf')}
            response = requests.post(f"{API_URL}/upload", files=files)
            
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload Successful!")
            print(f"   Response: {data}")
            return True
        else:
            print(f"❌ Upload Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Is it running on localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_status():
    """Polls the status of the uploaded document."""
    print(f"🔍 Checking status for {TEST_FILENAME}...")
    
    for i in range(5):
        try:
            response = requests.get(f"{API_URL}/document/status/{TEST_FILENAME}")
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                print(f"   Attempt {i+1}: Status = {status}")
                
                if status in ['PENDING', 'PROCESSING', 'COMPLETED']:
                    print("✅ Automatic trigger verified! Document is in queue/processing.")
                    return
            else:
                print(f"   Attempt {i+1}: Status check failed ({response.status_code})")
        except Exception as e:
            print(f"   Attempt {i+1}: Error {e}")
            
        time.sleep(2)
        
    print("⚠️ Status did not progress as expected (or API is down).")

if __name__ == "__main__":
    if test_upload():
        time.sleep(1)
        check_status()
    
    # Cleanup
    if os.path.exists(TEST_FILENAME):
        os.remove(TEST_FILENAME)
        print(f"🧹 Cleaned up {TEST_FILENAME}")
