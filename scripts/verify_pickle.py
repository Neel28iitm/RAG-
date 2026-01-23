
import boto3
import pickle
import os
from dotenv import load_dotenv

load_dotenv("config/.env")
load_dotenv(".env")

def main():
    print("🌭 Verifying Pickle Data from S3...")
    key = "parent_store/5eb28cda-2670-4b3e-b860-d78a663a8856"
    bucket = "neel-rag-data-2026"
    
    s3 = boto3.client('s3', 
                         aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                         aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                         region_name=os.getenv("AWS_REGION", "ap-south-1"))

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = obj['Body'].read()
        print(f"✅ Downloaded {len(data)} bytes.")
        
        doc = pickle.loads(data)
        print("✅ Pickle Load Success!")
        print(f"📄 Content Preview: {doc.page_content[:100]}...")
        print(f"🏷️ Metadata: {doc.metadata}")
        
    except Exception as e:
        print(f"❌ Pickle Verify Failed: {e}")

if __name__ == "__main__":
    main()
