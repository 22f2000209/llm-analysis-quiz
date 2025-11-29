"""
Multi-fallback audio transcription tool.
Your sophisticated approach with multiple fallback mechanisms.
"""

from langchain_core.tools import tool
import os
import requests

@tool
def transcribe_audio(audio_url: str) -> str:
    """
    Transcribe audio file using multi-fallback approach.
    
    Fallback chain:
    1. SpeechRecognition (Google Web Speech API) - Free, local
    2. Gemini API - If available
    3. OpenAI Whisper API - Last resort
    
    Parameters
    ----------
    audio_url : str
        URL to the audio file
    
    Returns
    -------
    str
        Transcribed text or error message
    """
    print(f"\n[AUDIO] Transcribing: {audio_url}")
    
    try:
        # Download audio file first
        from hybrid_tools.download_file import download_file
        audio_path = download_file.invoke({"url": audio_url})
        
        if "Error" in audio_path:
            return f"Failed to download audio: {audio_path}"
        
        print(f"[AUDIO] Downloaded to: {audio_path}")
        
        # Try Method 1: SpeechRecognition (free, local)
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                print(f"[AUDIO] ✓ Transcribed with SpeechRecognition: {text[:100]}...")
                return text
        except ImportError:
            print("[AUDIO] SpeechRecognition not available, trying Gemini...")
        except Exception as e:
            print(f"[AUDIO] SpeechRecognition failed: {e}, trying Gemini...")
        
        # Try Method 2: Gemini API via OpenAI-compatible endpoint (FIRST - best for long audio)
        try:
            import base64
            from openai import OpenAI
            
            api_key = os.getenv("GOOGLE_API_KEY")
            
            if api_key:
                print("[AUDIO] Trying Gemini API via OpenAI-compatible compatible endpoint...")
                
                # Use OpenAI client with Gemini base URL
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                
                # Read and encode audio
                with open(audio_path, "rb") as f:
                    audio_data = f.read()
                base64_audio = base64.b64encode(audio_data).decode('utf-8')
                
                response = client.chat.completions.create(
                    model="gemini-2.5-flash",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Transcribe this audio file exactly. Return ONLY the transcription text, no explanations."
                                },
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": base64_audio,
                                        "format": "mp3"
                                    }
                                }
                            ]
                        }
                    ]
                )
                
                text = response.choices[0].message.content
                print(f"[AUDIO] ✓ Transcribed with Gemini: {text[:100]}...")
                return text
        except Exception as e:
            print(f"[AUDIO] Gemini failed: {e}, trying Whisper...")

        
        # Try Method 3: OpenAI Whisper API
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                text = transcript.text
                print(f"[AUDIO] ✓ Transcribed with Whisper: {text[:100]}...")
                return text
        except Exception as e:
            print(f"[AUDIO] Whisper failed: {e}")
        
        return "Error: All transcription methods failed"
        
    except Exception as e:
        error_msg = f"Error transcribing audio: {str(e)}"
        print(f"[AUDIO] ✗ {error_msg}")
        return error_msg
