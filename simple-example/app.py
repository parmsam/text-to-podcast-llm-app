from shiny import App, ui, render, reactive
from gtts import gTTS
import tempfile
import io
import base64

app_ui = ui.page_fluid(
    ui.h2("Podcast Transcript to Speech Converter"),
    ui.input_text_area(
        "transcript",
        "Enter transcript (prefix lines with 'A:' or 'B:' for different speakers)",
        value=(
            "A: Welcome to our podcast! Today we're discussing AI advancements.\n"
            "B: That's right! It's an exciting topic that's evolving rapidly.\n"
            "A: Let's start with the basics. What is AI?\n"
            "B: AI, or Artificial Intelligence, refers to computer systems designed to mimic human intelligence.\n"
            "A: Interesting! Can you give an example of AI in everyday life?\n"
            "B: Sure! Virtual assistants like Siri or Alexa are great examples of AI in action."
        ),
        height="200px",
    ),
    ui.input_action_button("generate", "Generate Audio"),
    ui.output_ui("audio"),
)

def server(input, output, session):
    audio_data = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.generate)
    def generate_audio():
        transcript = input.transcript()
        lines = transcript.split('\n')
        
        combined_audio = io.BytesIO()
        
        for line in lines:
            if line.strip():
                speaker, text = line.split(':', 1)
                tts = gTTS(text=text.strip(), lang='en', slow=False, tld='ie')
                
                mp3_fp = io.BytesIO()
                tts.write_to_fp(mp3_fp)
                mp3_fp.seek(0)
                
                # For speaker B, we'll use a different voice (tld parameter)
                if speaker.strip().upper() == 'B':
                    tts = gTTS(text=text.strip(), lang='en', slow=False, tld='ca')
                    mp3_fp = io.BytesIO()
                    tts.write_to_fp(mp3_fp)
                    mp3_fp.seek(0)
                
                combined_audio.write(mp3_fp.getvalue())
        
        combined_audio.seek(0)
        audio_data.set(combined_audio.getvalue())

    @output
    @render.ui
    @reactive.event(audio_data)
    def audio():
        if audio_data() is not None:
            b64_audio = base64.b64encode(audio_data()).decode('ascii')
            return ui.tags.audio(
                ui.tags.source(
                    src=f"data:audio/mp3;base64,{b64_audio}",
                    type="audio/mp3"
                ),
                controls=True
            )
        return None

app = App(app_ui, server)
