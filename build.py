# Similar to packager.py but builds app.py, should be run after packager.py as it uses the packaged.py for embedded client

import os
import shutil
import base64

# Load the content of packaged.py and run it.
packaged = {}
with open("packaged.py", "r") as f:
    packaged_content = f.read()
    exec(packaged_content, packaged)

with open("app-comp.py", "w") as f:
    with open("app.py", "r") as original:
        file = original.read()

        f.write('### EMBEDDED\nimport base64\nembedded = {"_resources": {')
        for name, bytecontent in packaged["_resources"].items():
            f.write(f"\n    \"{name}\": base64.b64decode({base64.b64encode(bytecontent)}),")
        f.write("\n}") 
        # write open
        output_lines = ["}", "", "import os", "import tempfile", "from contextlib import contextmanager", ""]
        output_lines.append("@contextmanager")
        output_lines.append("def embedopen(path):")
        output_lines.append("    \"\"\"Return a temporary file containing the requested resource, preserving its extension.\"\"\"")
        output_lines.append("    if path not in embedded['_resources']:")
        output_lines.append("        raise FileNotFoundError(f\"Resource {path} not found\")")
        output_lines.append("    data = embedded['_resources'][path]")
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
        output_lines.append("embedded['open'] = embedopen")
        output_lines.append("embedded['constraints'] = {'REQUIRES_SERVER':'"+packaged["constraints"]["REQUIRES_SERVER"]+"'}") # newline
        for line in output_lines:
            f.write(line + "\n")
        f.write("\n### END OF EMBEDDED\n\n")
        f.write(file)

print("Finished writing app-comp.py with embedded client.")
