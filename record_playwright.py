import os
import sys
import time
import subprocess
import shutil
from playwright.sync_api import sync_playwright

def main():
    print("=" * 60)
    print("      Smart-Grid Agent: Playwright Headless Demo Video Recorder")
    print("=" * 60)
    
    # 1. Paths setup
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_video_dir = os.path.join(base_dir, "data", "video_temp")
    final_video_path = os.path.join(base_dir, "smart_grid_agent_demo.mp4")
    
    if os.path.exists(temp_video_dir):
        shutil.rmtree(temp_video_dir)
    os.makedirs(temp_video_dir, exist_ok=True)

    # 2. Start Flask Server in background
    print("[1/5] Starting API Server...")
    api_process = subprocess.Popen(
        [sys.executable, "api/server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(4) # Wait for server to bind

    # 3. Playwright Recording Flow
    print("[2/5] Initializing headless Playwright Chromium and recording canvas...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=temp_video_dir,
                record_video_size={"width": 1280, "height": 720}
            )
            page = context.new_page()
            
            print("[3/5] Navigating to Dashboard...")
            page.goto("http://localhost:5000", wait_until="networkidle")
            
            # Scene 1: Dashboard overview with metrics
            print("Recording Scene 1: System Overview (8 seconds)...")
            time.sleep(8)
            
            # Scene 2: Navigate to Action Queue
            print("Recording Scene 2: Action Queue (3 seconds)...")
            page.click("#nav-actions")
            time.sleep(3)
            
            # Scene 3: Click Approve Button on first action card
            print("Recording Scene 3: Approving Action (2 seconds)...")
            # Click any visible button that starts with btn-approve-
            approve_btn = page.locator("[id^=btn-approve-]").first
            if approve_btn.is_visible():
                approve_btn.click()
                time.sleep(2)
                
                # Confirm modal click
                print("Recording Scene 4: Confirming Approval in Modal (4 seconds)...")
                page.click("#modal-approve-btn")
                time.sleep(4)
            else:
                print("No pending action buttons found to click. Simulating delay...")
                time.sleep(6)
            
            # Scene 4: Navigate to Savings Dashboard
            print("Recording Scene 5: Savings Dashboard (6 seconds)...")
            page.click("#nav-savings")
            time.sleep(6)
            
            # Scene 5: Navigate to Audit Logs
            print("Recording Scene 6: Audit Logs (4 seconds)...")
            page.click("#nav-logs")
            time.sleep(4)
            
            print("Closing browser context...")
            context.close()
            browser.close()
            
    except Exception as e:
        print(f"\n[ERROR] Playwright execution failed: {e}")
        api_process.terminate()
        api_process.wait()
        return

    # 4. Terminate Flask server
    print("[4/5] Stopping API Server...")
    api_process.terminate()
    api_process.wait()

    # 5. Locate webm file and convert to MP4 using FFmpeg
    print("[5/5] Transcoding recorded video to MP4 using FFmpeg...")
    video_files = [f for f in os.listdir(temp_video_dir) if f.endswith(".webm")]
    if not video_files:
        print("[ERROR] No recorded video file found!")
        return
        
    webm_path = os.path.join(temp_video_dir, video_files[0])
    
    # Run ffmpeg to transcode webm to mp4
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", webm_path,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        final_video_path
    ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"\n🎉 SUCCESS! Video demo successfully recorded and saved to: {final_video_path}")
    except Exception as e:
        print(f"\n[ERROR] FFmpeg transcoding failed: {e}")
    finally:
        # Cleanup
        if os.path.exists(temp_video_dir):
            shutil.rmtree(temp_video_dir)

if __name__ == "__main__":
    main()
