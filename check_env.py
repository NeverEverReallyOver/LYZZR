
import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")

print("\n--- Testing pywin32 ---")
try:
    import pywintypes
    print("Successfully imported pywintypes")
except ImportError as e:
    print(f"Failed to import pywintypes: {e}")
    
try:
    import win32api
    print("Successfully imported win32api")
except ImportError as e:
    print(f"Failed to import win32api: {e}")

print("\n--- Testing AgentScope ---")
try:
    import agentscope
    print("Successfully imported agentscope")
except ImportError as e:
    print(f"Failed to import agentscope: {e}")
except Exception as e:
    print(f"Error importing agentscope: {e}")
