# NOVA Voice Assistant

NOVA uses a React web interface and a local Python API. The existing Gemini,
voice response, and desktop command logic remains in the Python modules.

## Run locally

1. Create and activate a Python environment, then install the backend packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Set `GEMINI_API_KEY` in the environment if you want Gemini answers.
3. In the repository root, start the API:

   ```powershell
   python nova.py
   ```

4. In a second terminal, start the React interface:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

5. Open the local Vite URL (normally `http://localhost:5173`).

The API binds to `127.0.0.1` and only allows the local Vite development
origins. When the React app opens, NOVA speaks a greeting based on the local
time on the computer running the API. Tap the microphone button to let the
Python backend listen through that computer's microphone; browser
speech-recognition support is not required. Typed questions and recognized
voice commands are sent to the Python API, and assistant responses are spoken
by the computer running the API.
