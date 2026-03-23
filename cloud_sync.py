import os
import time
from datetime import datetime
from pymongo import MongoClient, ReplaceOne
from pymongo.errors import ConnectionFailure, OperationFailure

# ---------------------------------------------------------
# Standalone Cloud Sync Utility for EXAM PORTAL
# ---------------------------------------------------------
# This script runs entirely independently of the FastAPI app.
# It continuously reads the local MongoDB instance and mirrors
# the 'students' collection (which contains exam results) 
# straight into MongoDB Atlas in near realtime.
# 
# Even if the FastAPI server crashes or stops, this script
# will continue working to securely push your data to the cloud.

def load_env():
    """Manually parse .env file so we don't need python-dotenv as a hard dependency."""
    env_vars = {}
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars

env = load_env()

LOCAL_URI = env.get("MONGODB_URL", "mongodb://localhost:27017")
CLOUD_URI = env.get("conectionvar")
DB_NAME = env.get("DATABASE_NAME", "exam_portal")

if not CLOUD_URI:
    print("❌ Critical Error: 'conectionvar' (Cloud MongoDB URI) not found in .env")
    exit(1)

# Establish synchronous connections
print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔌 Connecting to Local MongoDB...")
local_client = MongoClient(LOCAL_URI, serverSelectionTimeoutMS=5000)

print(f"[{datetime.now().strftime('%H:%M:%S')}] ☁️  Connecting to Cloud MongoDB Atlas...")
cloud_client = MongoClient(CLOUD_URI, serverSelectionTimeoutMS=5000)

local_db = local_client[DB_NAME]
cloud_db = cloud_client[DB_NAME]

def run_sync_loop():
    while True:
        try:
            # 1. Fetch all students from local DB
            # For this scale, fetching the whole collection is extremely fast
            local_students = list(local_db.students.find({}))
            
            if not local_students:
                time.sleep(2)
                continue
                
            # 2. Prepare bulk upsert operations for Cloud
            operations = []
            for student in local_students:
                # We use ReplaceOne to completely overwrite the cloud document with the latest local state
                # The 'upsert=True' ensures that if it doesn't exist in cloud, it is created.
                operations.append(ReplaceOne({"mobile": student["mobile"]}, student, upsert=True))
                
            # 3. Execute Bulk Write to Cloud
            if operations:
                result = cloud_db.students.bulk_write(operations, ordered=False)
                # print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Real-time Sync: {len(operations)} records matched, {result.modified_count} modified in Cloud.")
                
        except (ConnectionFailure, OperationFailure) as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Connection Interrupted: {e}")
            print("⏳ Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            continue
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Unexpected Sync Error: {e}")
            print("⏳ Retrying in 5 seconds...")
            time.sleep(5)
            continue
            
        # Wait 2 seconds before the next sync check
        time.sleep(2)

def input_with_timeout(prompt, timeout, default):
    import sys
    import time
    try:
        import msvcrt
        print(prompt, end="", flush=True)
        start_time = time.time()
        input_str = ""
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char in (b'\r', b'\n'):
                    print()
                    return input_str if input_str else default
                elif char == b'\x08': # backspace
                    if len(input_str) > 0:
                        input_str = input_str[:-1]
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                else:
                    try:
                        decoded = char.decode('utf-8')
                        input_str += decoded
                        sys.stdout.write(decoded)
                        sys.stdout.flush()
                    except:
                        pass
            if (time.time() - start_time) > timeout:
                print(f"\n[No input received in {timeout} seconds. Defaulting to '{default}']")
                return default
            time.sleep(0.05)
    except ImportError:
        # Fallback for non-Windows (or if msvcrt isn't available)
        return input(prompt).strip() or default

def interactive_menu():
    import random
    while True:
        print("\n=====================================================")
        print("🚀 Standalone Cloud Sync Utility - Main Menu")
        print("=====================================================")
        print("1. Clear Cloud Database Completely (Preserve Local)")
        print("2. Start Real-time Data Polling to Cloud")
        print("3. Exit")
        choice = input_with_timeout("Enter your choice (1/2/3) [Auto-starts Option 2 in 30s]: ", 30, '2').strip()

        if choice == '1':
            verification_code = str(random.randint(1000, 9999))
            print("\n⚠️ WARNING: This will permanently DELETE all exam records in the Cloud.")
            print(f"To confirm, please enter the following verification code: {verification_code}")
            confirm = input("> ").strip()
            
            if confirm == verification_code:
                try:
                    cloud_deleted = cloud_db.students.delete_many({})
                    print(f"\n✅ CLOUD DATA WIPED SUCCESSFULLY.")
                    print(f"- Cloud records deleted: {cloud_deleted.deleted_count}")
                    print(f"- (Local records securely preserved)")
                except Exception as e:
                    print(f"\n❌ Error wiping database: {e}")
            else:
                print("\n❌ Verification failed. Action aborted.")
                
        elif choice == '2':
            print("\n=====================================================")
            print("🚀 Standalone Cloud Sync Active")
            print("📡 Mode: Polling (Every 2 Seconds)")
            print("🔒 This script is crash-resistant and runs infinitely.")
            print("=====================================================")
            run_sync_loop()
            
        elif choice == '3':
            print("\nExiting script.")
            break
        else:
            print("\nInvalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    try:
        interactive_menu()
    except KeyboardInterrupt:
        print("\n⏹️ Sync stopped gracefully by user.")
    finally:
        local_client.close()
        cloud_client.close()
