import os
import sys
from pathlib import Path

# Add backend directory to Python path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import gradio as gr
import uvicorn
from app.main import create_app

# Create the full FastAPI application
app = create_app()

# Mount a lightweight Gradio interface for Hugging Face Spaces compliance
with gr.Blocks(title="DigiRaksha AI Sentinel API") as demo:
    gr.Markdown(
        """
        # 🛡️ DigiRaksha Forensic AI Sentinel Backend
        ### Active Cloud API Service for Cloudflare Pages
        - **Interactive API Docs**: [/docs](/docs)
        - **Health Check Status**: [/api/v1/meta](/api/v1/meta)
        - **Live Telephony Stream**: `wss://.../api/v1/stream/live-call`
        - **System Status**: `ONLINE` 🟢
        """
    )

# Mount Gradio app at /gradio so root and /api/v1 routes remain completely intact
app = gr.mount_gradio_app(app, demo, path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
