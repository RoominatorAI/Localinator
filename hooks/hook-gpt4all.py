from PyInstaller.utils.hooks import collect_dynamic_libs

# Automatically collect all shared libraries
binaries = collect_dynamic_libs('gpt4all')
print(f"🚀 Hook executed at compile time: {binaries}")