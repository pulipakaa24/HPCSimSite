#!/usr/bin/env python3
"""
Startup supervisor for HPC Simulation Services.
Manages both enrichment service and AI intelligence layer.
"""
import subprocess
import sys
import time
import signal
import os

processes = []

def cleanup(signum=None, frame=None):
    """Clean up all child processes."""
    print("\n🛑 Shutting down all services...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception as e:
            print(f"Error stopping process: {e}")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    print("🚀 Starting HPC Simulation Services...")
    
    # Start enrichment service
    print("📊 Starting Enrichment Service on port 8000...")
    enrichment_proc = subprocess.Popen(
        [sys.executable, "scripts/serve.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(enrichment_proc)
    print(f"   ├─ PID: {enrichment_proc.pid}")
    
    # Give it time to start
    time.sleep(5)
    
    # Check if still running
    if enrichment_proc.poll() is not None:
        print("❌ Enrichment service failed to start")
        cleanup()
        return 1
    print("   └─ ✅ Enrichment service started successfully")
    
    # Start AI Intelligence Layer
    print("🤖 Starting AI Intelligence Layer on port 9000...")
    ai_proc = subprocess.Popen(
        [sys.executable, "ai_intelligence_layer/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(ai_proc)
    print(f"   ├─ PID: {ai_proc.pid}")
    
    # Give it time to start
    time.sleep(3)
    
    # Check if still running
    if ai_proc.poll() is not None:
        print("❌ AI Intelligence Layer failed to start")
        cleanup()
        return 1
    print("   └─ ✅ AI Intelligence Layer started successfully")
    
    print("\n✨ All services running!")
    print("   📊 Enrichment Service: http://0.0.0.0:8000")
    print("   🤖 AI Intelligence Layer: ws://0.0.0.0:9000/ws/pi")
    print("\nPress Ctrl+C to stop all services\n")
    
    # Monitor processes
    try:
        while True:
            # Check if any process has died
            for proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️  Process {proc.pid} died unexpectedly!")
                    cleanup()
                    return 1
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
