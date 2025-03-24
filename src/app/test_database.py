from database import get_database_connection, get_database_connection_aws
import traceback
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/vish.dharmapala.vega/LLM-backend/src/google_env.json"

def test_aws_connection():
    try:
        conn = get_database_connection_aws()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        print("AWS Database connection successful.")
        conn.close()
    except Exception as e:
        print(f"AWS Database connection failed: {e}")

def test_gcp_connection():
    try:
        engine = get_database_connection()
        with engine.connect() as connection:
            result = connection.execute("SELECT 1;")
            for row in result:
                print("GCP Database connection successful.")
    except Exception as e:
        print(f"GCP Database connection failed: {e}")
        print(traceback.format_exc())


if __name__ == '__main__':
    # test_aws_connection()
    test_gcp_connection()
