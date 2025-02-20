#!/usr/bin/env python3
import os
import base64
import sys

# Define the paths for the resource file and directory.
ROOT_HTML = "root.html"
CLIENT_DIR = "client"
AIM_DIR = "metadata"

# This dictionary will map resource keys (used in packaged.py) to the file contents.
# The keys will be the resource paths as expected by the web app.
resources = {}

# Process the root.html file.
if not os.path.isfile(ROOT_HTML):
    print(f"Error: '{ROOT_HTML}' not found in the current directory.", file=sys.stderr)
    sys.exit(1)
with open(ROOT_HTML, "rb") as f:
    content = f.read()
    # Use the key /packaged/root.html as referenced in the app.
    resources["/packaged/root.html"] = base64.b64encode(content).decode("ascii")

# Process the client directory.
if os.path.isdir(CLIENT_DIR):
    for root, dirs, files in os.walk(CLIENT_DIR):
        for filename in files:
            filepath = os.path.join(root, filename)
            # Get a resource key that starts with "/packaged/client/"
            # For example, if filepath is "client/foo/bar.js", the key will be "/packaged/client/foo/bar.js"
            rel_path = os.path.relpath(filepath, CLIENT_DIR)
            # Replace backslashes with forward slashes (especially on Windows)
            rel_path = rel_path.replace(os.path.sep, '/')
            resource_key = f"/packaged/client/{rel_path}"
            with open(filepath, "rb") as f:
                content = f.read()
                resources[resource_key] = base64.b64encode(content).decode("ascii")
else:
    print(f"Warning: Directory '{CLIENT_DIR}' not found. No client files will be packaged.", file=sys.stderr)


# Generate the content for packaged.py.
# This file will embed a dictionary named _resources mapping resource paths to the binary content,
# and a context manager function open() that writes out the content to a temporary file while keeping the original extension.
output_lines = [
    "### LOCALINATOR DATA FILE ###",
    "# This is a huge blob of data containing the Localinator UI.",
    "# Custom datablobs are allowed for Localinator, though.",
    "import base64",
    "import tempfile",
    "import os",
    "from contextlib import contextmanager",
    "",
    "# Dictionary mapping resource paths to their binary content",
    "_resources = {"
]

# Add each resource entry.
for key in sorted(resources.keys()):
    b64data = resources[key]
    output_lines.append(f'    "{key}": base64.b64decode("{b64data}"),')
output_lines.append("}")
output_lines.append("")
output_lines.append("@contextmanager")
output_lines.append("def open(path):")
output_lines.append("    \"\"\"Return a temporary file containing the requested resource, preserving its extension.\"\"\"")
output_lines.append("    if path not in _resources:")
output_lines.append("        raise FileNotFoundError(f\"Resource {path} not found\")")
output_lines.append("    data = _resources[path]")
output_lines.append("    # Extract the file extension from the path (e.g., '.html', '.js', etc.)")
output_lines.append("    _, ext = os.path.splitext(path)")
output_lines.append("    # Create a temporary file with the proper extension")
output_lines.append("    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)")
output_lines.append("    try:")
output_lines.append("        tmp.write(data)")
output_lines.append("        tmp.close()")
output_lines.append("        yield tmp.name")
output_lines.append("    finally:")
output_lines.append("        try:")
output_lines.append("            os.unlink(tmp.name)")
output_lines.append("        except Exception:")
output_lines.append("            pass")
output_lines.append("")

# Write the output to packaged.py.
with open("packaged.py", "w", encoding="utf-8") as out_file:
    out_file.write("\n".join(output_lines))

print("packaged.py has been created successfully.")
