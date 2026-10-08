import os
import subprocess

from voice_engine import speak


def create_python_project(name, status_label=None, root=None):
    try:
        if os.path.exists(name):
            speak("Project already exists", status_label, root)
            return

        os.makedirs(f"{name}/src", exist_ok=True)
        os.makedirs(f"{name}/tests", exist_ok=True)

        with open(f"{name}/src/main.py", "w", encoding="utf-8") as f:
            f.write("""def main():
    print("Hello from your Python project")

if __name__ == "__main__":
    main()
""")

        with open(f"{name}/requirements.txt", "w", encoding="utf-8") as f:
            f.write("# Add your dependencies here")

        with open(f"{name}/README.md", "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\nPython Project created by Nova AI")

        speak("Python project created successfully", status_label, root)

    except Exception as e:
        speak("Error creating Python project", status_label, root)
        print(e)


def create_react_project(name="my-react-app", status_label=None, root=None):
    try:
        speak("Creating React project. This may take a few minutes.", status_label, root)
        subprocess.run(["npx", "create-react-app", name], check=False)
        speak("React project created successfully", status_label, root)

    except Exception as e:
        speak("Error creating React project", status_label, root)
        print(e)


def create_node_project(name, status_label=None, root=None):
    try:
        if os.path.exists(name):
            speak("Project already exists", status_label, root)
            return

        os.makedirs(name, exist_ok=True)

        server_code = """
const express = require("express");
const app = express();

app.get("/", (req, res) => {
    res.send("Node server running");
});

app.listen(3000, () => {
    console.log("Server running on port 3000");
});
"""

        with open(os.path.join(name, "server.js"), "w", encoding="utf-8") as f:
            f.write(server_code)

        subprocess.run(["npm", "init", "-y"], cwd=name, check=False)
        subprocess.run(["npm", "install", "express"], cwd=name, check=False)

        speak("Node project created successfully", status_label, root)

    except Exception as e:
        speak("Error creating Node project", status_label, root)
        print(e)