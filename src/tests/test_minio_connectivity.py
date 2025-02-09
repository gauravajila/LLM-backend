from minio import Minio
from minio.error import S3Error

# MinIO Configuration
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "BVxA5YuSF5vkzXkXMym7"
MINIO_SECRET_KEY = "jLDOAIEsfef50DK90gIPb5ucON7K1WuC93dOKa8F"
MINIO_SECURE = False  # True if using HTTPS
MINIO_BUCKET =  "customer-document-storage"

def test_minio_connectivity():
    try:
        # Initialize MinIO client
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )

        # List all buckets
        print("Listing buckets...")
        buckets = client.list_buckets()
        for bucket in buckets:
            print(f" - {bucket.name}")

        # Check if the target bucket exists
        print(f"\nChecking if bucket '{MINIO_BUCKET}' exists...")
        if client.bucket_exists(MINIO_BUCKET):
            print(f"Bucket '{MINIO_BUCKET}' exists.")
        else:
            print(f"Bucket '{MINIO_BUCKET}' does not exist. Creating it...")
            client.make_bucket(MINIO_BUCKET)
            print(f"Bucket '{MINIO_BUCKET}' created successfully.")

        # Upload a test file
        test_file_content = b"This is a test file for MinIO connectivity."
        test_file_key = "test_file.txt"
        print(f"\nUploading test file '{test_file_key}' to bucket '{MINIO_BUCKET}'...")
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=test_file_key,
            data=bytes(test_file_content),
            length=len(test_file_content),
            content_type="text/plain",
        )
        print(f"File '{test_file_key}' uploaded successfully.")

        # Download the test file to verify upload
        print(f"\nDownloading test file '{test_file_key}'...")
        response = client.get_object(bucket_name=MINIO_BUCKET, object_name=test_file_key)
        downloaded_content = response.read()
        response.close()
        response.release_conn()

        if downloaded_content == test_file_content:
            print("File downloaded successfully and content matches.")
        else:
            print("Content mismatch. Check the uploaded file.")

    except S3Error as e:
        print(f"S3Error: {e}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    else:
        print("\nMinIO connectivity test passed successfully.")

if __name__ == "__main__":
    test_minio_connectivity()
