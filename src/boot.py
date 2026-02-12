
import os
import sys

def bootstrap_environment():
    """
    Ensure the environment is set up correctly before importing heavy dependencies.
    Specifically targets Windows DLL issues for pywin32 and agentscope.
    """
    print("[Boot] Bootstrapping environment...")
    print(f"[Boot] Python Executable: {sys.executable}")
    
    # --- Windows DLL Patch for pywin32 ---
    if os.name == 'nt':
        try:
            # 策略 1: 基于 sys.executable 推断 site-packages (最可靠)
            site_packages = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
            
            if not os.path.exists(site_packages):
                # 策略 2: 遍历 sys.path
                for p in sys.path:
                    if 'site-packages' in p and os.path.isdir(p):
                        site_packages = p
                        break
            
            print(f"[Boot] Target site-packages: {site_packages}")

            if site_packages and os.path.exists(site_packages):
                # 关键路径
                pywin32_system32 = os.path.join(site_packages, 'pywin32_system32')
                win32 = os.path.join(site_packages, 'win32')
                win32_lib = os.path.join(site_packages, 'win32', 'lib')
                
                paths_to_add = [pywin32_system32, win32, win32_lib]
                
                # 1. 使用 os.add_dll_directory (Python 3.8+)
                for path in paths_to_add:
                    if os.path.exists(path):
                        try:
                            if hasattr(os, 'add_dll_directory'):
                                os.add_dll_directory(path)
                                print(f"[Boot] Added DLL directory: {path}")
                        except Exception as e:
                            print(f"[Boot] Failed to add_dll_directory {path}: {e}")
                            
                        # 2. 添加到 PATH 环境变量 (Legacy fallback)
                        os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
                        
                        # 3. 添加到 sys.path (确保能 import 模块)
                        if path not in sys.path:
                            sys.path.append(path)

                # 4. 强制加载 DLL (核武器选项)
                # 有时候 add_dll_directory 不够，需要显式加载 pywintypesXX.dll
                try:
                    import ctypes
                    # 尝试找到 pywintypesXX.dll
                    for f in os.listdir(pywin32_system32):
                        if f.startswith("pywintypes") and f.endswith(".dll"):
                            dll_path = os.path.join(pywin32_system32, f)
                            try:
                                ctypes.WinDLL(dll_path)
                                print(f"[Boot] Force loaded DLL: {dll_path}")
                            except Exception as e:
                                print(f"[Boot] Failed to load DLL {dll_path}: {e}")
                except Exception as e:
                    print(f"[Boot] DLL force load skipped: {e}")

            # 再次尝试导入
            import pywintypes
            print("[Boot] pywintypes imported successfully after patch.")
            
        except Exception as e:
            print(f"[Boot] Warning: Failed to patch pywin32 environment: {e}")
            import traceback
            traceback.print_exc()

    print("[Boot] Environment ready.")
