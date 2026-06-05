import os
import sys
import time
import subprocess
import webbrowser
import threading
import requests

def get_pending_action():
    try:
        r = requests.get("http://localhost:5000/api/actions/pending")
        if r.status_code == 200:
            actions = r.json().get("pending", [])
            if actions:
                return actions[0]["id"]
    except Exception as e:
        print(f"Error fetching pending actions: {e}")
    return None

def auto_approve_worker():
    # Wait for browser to open and dashboard to load
    time.sleep(12)
    action_id = get_pending_action()
    if action_id:
        print(f"\n[DEMO ENGINE] Auto-approving pending action: {action_id}...")
        try:
            r = requests.post("http://localhost:5000/api/actions/approve", json={"action_id": action_id})
            if r.status_code == 200:
                print("[DEMO ENGINE] Action approved and executed successfully!")
            else:
                print(f"[DEMO ENGINE] Approval failed: {r.text}")
        except Exception as e:
            print(f"[DEMO ENGINE] Network error during approval: {e}")
    else:
        print("\n[DEMO ENGINE] No pending actions found to auto-approve.")

def main():
    print("=" * 60)
    print("         Smart-Grid Agent: Automated Demo Recorder")
    print("=" * 60)
    print("This script will:")
    print("1. Start the Flask API server.")
    print("2. Open your web browser to the dashboard.")
    print("3. Record your screen (2560x1440) using ffmpeg for 30 seconds.")
    print("4. Auto-approve a pending action mid-recording to show the live UI update.")
    print("\nIMPORTANT: Please make sure your browser window is visible and full-screen!")
    print("Starting in 5 seconds... Press Ctrl+C to cancel.")
    time.sleep(5)

    # Start flask server
    print("\n[1/4] Starting API Server...")
    api_process = subprocess.Popen(
        [sys.executable, "api/server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3) # Wait for server to bind

    # Open Browser
    print("[2/4] Opening Web Browser...")
    webbrowser.open("http://localhost:5000")

    # Start auto-approval thread
    approve_thread = threading.Thread(target=auto_approve_worker, daemon=True)
    approve_thread.start()

    # Start ffmpeg recording
    video_path = os.path.join(os.path.dirname(__file__), "smart_grid_agent_demo.mp4")
    print(f"[3/4] Recording screen (2560x1440) to {video_path}...")
    print("RECORDING STARTED - Please do not move/minimize the browser window!")
    
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "x11grab",
        "-video_size", "2560x1440",
        "-i", ":0.0",
        "-t", "30",
        "-pix_fmt", "yuv420p",
        video_path
    ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print("\n[4/4] Recording completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] FFmpeg recording failed: {e}")
    finally:
        # Cleanup
        print("Cleaning up processes...")
        api_process.terminate()
        api_process.wait()
        print("Finished.")

if __name__ == "__main__":
    main()
