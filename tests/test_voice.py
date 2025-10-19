#!/usr/bin/env python3
"""
Quick test script for ElevenLabs voice announcements.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, '.')

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Check API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("✗ ELEVENLABS_API_KEY not found in environment")
        print("Create a .env file with: ELEVENLABS_API_KEY=your_key_here")
        sys.exit(1)
    
    # Initialize client with same settings as voice_service.py
    client = ElevenLabs(api_key=api_key)
    voice_id = "mbBupyLcEivjpxh8Brkf"  # Rachel voice
    
    # Test message
    test_message = "Lap 3. Strategy: Conservative One Stop. Brake bias forward for turn in. Current tire degradation suggests extended first stint."
    
    print(f"Testing ElevenLabs voice announcement...")
    print(f"Voice ID: {voice_id} (Rachel)")
    print(f"Message: {test_message}")
    print("-" * 60)
    
    # Synthesize
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=test_message,
        model_id="eleven_multilingual_v2",
        voice_settings={
            "stability": 0.4,
            "similarity_boost": 0.95,
            "style": 0.7,
            "use_speaker_boost": True
        }
    )
    
    # Save audio
    output_dir = Path("data/audio")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_voice.mp3"
    
    save(audio, str(output_path))
    print(f"✓ Audio saved to: {output_path}")
    
    # Play audio
    print("✓ Playing audio...")
    if sys.platform == "darwin":  # macOS
        os.system(f"afplay {output_path}")
    elif sys.platform == "linux":
        os.system(f"mpg123 {output_path} || ffplay -nodisp -autoexit {output_path}")
    elif sys.platform == "win32":
        os.system(f"start {output_path}")
    
    print("✓ Voice test completed successfully!")
    
except ImportError as e:
    print(f"✗ elevenlabs not available: {e}")
    print("Install with: pip install elevenlabs python-dotenv")
except Exception as e:
    print(f"✗ Voice test failed: {e}")
    import traceback
    traceback.print_exc()
