"""
Example: Integrate voice feedback with AI strategy decisions
"""

from voice_service import RaceEngineerVoice
from pathlib import Path

def announce_strategy_decision(decision: dict):
    """
    Convert AI strategy decision to voice announcement.
    
    Args:
        decision: Dict with keys like 'action', 'tire_compound', 'lap'
    """
    engineer = RaceEngineerVoice()
    
    # Generate appropriate message
    if decision['action'] == 'pit':
        text = f"Box this lap for {decision['tire_compound']}. In, in, in!"
    elif decision['action'] == 'stay_out':
        text = "Stay out. These tires are still competitive"
    elif decision['action'] == 'push':
        text = f"Push mode. We need {decision.get('gap_target', 3)} seconds"
    else:
        text = decision.get('message', 'Copy that')
    
    # Synthesize and save
    audio_path = Path(f"data/audio/lap_{decision.get('lap', 0)}_command.mp3")
    engineer.synthesize_strategy_message(text, audio_path)
    
    return audio_path