"""
AI-Based Smart Traffic Management System (AI-STMS)
Main Application Launcher
"""

import uvicorn
import os
import sys
import webbrowser
import threading
import time

def open_browser(url: str, delay: float = 1.2):
    def _open():
        time.sleep(delay)
        print(f"Opening browser to {url} ...")
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()

def main():
    print("=" * 70)
    print("  🚦 AI-BASED SMART TRAFFIC MANAGEMENT SYSTEM (AI-STMS)")
    print("  ⚡ Adaptive Signal Control | Computer Vision | Green Corridor")
    print("=" * 70)

    # Check sample video
    sample_vid = os.path.join("data", "sample_videos", "traffic_sample.mp4")
    if not os.path.exists(sample_vid):
        print("Generating initial sample traffic footage...")
        from data.generate_sample_video import generate_traffic_video
        generate_traffic_video(sample_vid)

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"
    print(f"\n🚀 Server launching at: {url}")
    print("Press Ctrl+C to terminate.\n")

    open_browser(url)
    uvicorn.run("server.app:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
