import os

# Tests use their own throwaway SQLite file so they never touch the dev database.
os.environ["DATABASE_URL"] = "sqlite:///./test_smart_hospital.db"
if os.path.exists("test_smart_hospital.db"):
    os.remove("test_smart_hospital.db")
