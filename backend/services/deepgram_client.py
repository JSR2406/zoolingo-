import os
from deepgram import DeepgramClient, PrerecordedOptions

class DeepgramService:
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = DeepgramClient(self.api_key)
            except Exception as e:
                print(f"Failed to init Deepgram: {e}")

    def transcribe(self, audio_path):
        """
        Transcribe audio file using Deepgram.
        """
        if not self.client:
            return "ASR Unavailable"

        try:
            with open(audio_path, "rb") as file:
                buffer_data = file.read()

            payload = {
                "buffer": buffer_data,
            }
            
            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
            )

            response = self.client.listen.prerecorded.v("1").transcribe_file(payload, options)
            return response.results.channels[0].alternatives[0].transcript
            
        except Exception as e:
            print(f"Deepgram Error: {e}")
            return "Error in transcription"

deepgram_service = DeepgramService()
