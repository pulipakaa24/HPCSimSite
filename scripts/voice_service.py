"""
ElevenLabs Voice Service for F1 Race Engineer

Converts AI strategy recommendations to natural speech.
"""

import os
from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from dotenv import load_dotenv

load_dotenv()

class RaceEngineerVoice:
    def __init__(self, voice_id: str = "mbBupyLcEivjpxh8Brkf"):  # Default: Rachel
        """
        Initialize ElevenLabs voice service.
        
        Args:
            voice_id: ElevenLabs voice ID (Rachel is default, professional female voice)
        """
        self.client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        self.voice_id = voice_id
        
    def synthesize_strategy_message(
        self, 
        text: str, 
        output_path: Path,
        stability: float = 0.4,
        similarity_boost: float = 0.95
    ) -> Path:
        """
        Convert strategy text to speech.
        
        Args:
            text: Message to synthesize (e.g., "Box this lap, box this lap")
            output_path: Where to save audio file
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity (0-1)
        
        Returns:
            Path to generated audio file
        """
        audio = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id="eleven_multilingual_v2",  # Fast, low-latency model
            voice_settings={
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": 0.7,
                "use_speaker_boost": True
            }
        )
        
        # Save audio
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the audio generator to file
        save(audio, str(output_path))
        
        return output_path
    
    def race_engineer_commands(self) -> dict:
        """Common F1 race engineer commands"""
        return {
            "box_now": "Box this lap, box this lap",
            "stay_out": "Stay out, stay out. We're looking good on these tires",
            "push": "Push now, push. We need to build a gap",
            "save_tires": "Manage those tires. Lift and coast into the corners",
            "traffic_ahead": "Traffic ahead. Blue flags expected",
            "safety_car": "Safety car, safety car. We're checking strategy",
            "undercut_threat": "Undercut threat from behind. We may need to respond",
            "fastest_lap": "You're on for fastest lap. Push this lap",
        }


# Example usage
if __name__ == "__main__":
    engineer = RaceEngineerVoice()
    
    # Generate pit call
    audio_file = engineer.synthesize_strategy_message(
        text="Mama Mia! That was a close one! Let's keep going and finish this out strong, like a cheetah on espresso!",
        output_path=Path("data/audio/pit_call.mp3")
    )
    
    print(f"✓ Generated: {audio_file}")