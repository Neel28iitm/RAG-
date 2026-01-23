import boto3
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def check_aws_connection():
    print("--- AWS DOCTOR START ---")
    try:
        # 1. Setup Client
        region = os.getenv('AWS_REGION', 'ap-south-1')
        print(f"Region: {region}")
        
        s3 = boto3.client(
            's3', 
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        target_bucket = os.getenv('S3_BUCKET_NAME', 'neel-rag-data-2026')
        print(f"Target Bucket: {target_bucket}")

        headers = None
        try:
            # Try a lightweight call
            s3.get_bucket_location(Bucket=target_bucket)
            # If successful, we can't easily get headers standard way unless we look at response metadata
            # but usually we want to see if it FAILS. 
            # Actually, let's just list objects to force a signature check or get header from error.
            response = s3.list_objects_v2(Bucket=target_bucket, MaxKeys=1)
            headers = response['ResponseMetadata']['HTTPHeaders']
            print("Auth seems WORKING (ListObjects success)")
        except Exception as e:
            # If ClientError, we can extract headers
            if hasattr(e, 'response'):
                headers = e.response['ResponseMetadata']['HTTPHeaders']
                print(f"Auth Failed/Error Intercepted: {e}")
            else:
                print(f"Connection Failed (No Response): {e}")
                return

        if headers:
            server_date = headers['date']
            # Format: 'Sun, 11 Jan 2026 22:55:00 GMT'
            aws_time = datetime.strptime(server_date, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
            local_time = datetime.now(timezone.utc)
            
            diff = (local_time - aws_time).total_seconds()
            abs_diff = abs(diff)
            
            print(f"Local Timestamp: {local_time}")
            print(f"AWS Timestamp:   {aws_time}")
            print(f"Difference: {diff:.2f} seconds")

            if abs_diff > 300:
                print("ERROR: Time difference is > 5 minutes (Clock Skew)!")
            else:
                print("SUCCESS: Time is synced (Delta < 5 mins).")
        
        # Check Keys
        secret = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        if " " in secret:
             print("FATAL: Secret key contains spaces!")
        if '"' in secret:
             print("INFO: Secret key contains quotes")

    except Exception as e:
        print(f"Doctor Crash: {e}")

if __name__ == "__main__":
    check_aws_connection()
