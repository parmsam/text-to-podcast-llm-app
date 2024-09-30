from shiny import App, ui, render, reactive
from gtts import gTTS
import io
import base64
from openai import OpenAI
import os
import json

try:
    from setup import api_key1
except ImportError:
    api_key1 = os.getenv("OPENAI_API_KEY")
    
app_info = """
This app creates a short podcast clip between two hosts, A and B, discussing 
source material that you provide. Note that it might take a minute or two to
generate the podcast transcript and audio clip
"""
default_word_limit = 350
json_schema = """
       {
            "transcript": [
                {
                "speaker": "A",
                "dialogue": "Welcome to our podcast!"
                },
                {
                "speaker": "B",
                "dialogue": "Thank you! It's great to be here."
                }
            ]
        }
"""

app_ui = ui.page_fluid(
    ui.h1("Text to Podcast Converter"),
    ui.markdown(app_info),
    ui.layout_sidebar(
        ui.sidebar(
        ui.input_password(
            "api_key", 
            "OpenAI API Key",
            value = api_key1,
        ),
        ui.input_text_area(
            "text_input",
            "Enter the text you want to convert to a podcast",
            value="Artificial Intelligence is rapidly advancing and changing various aspects of our lives.",
            height="200px"
        ),
        ui.input_slider(
            "word_limit",
            "Default word limit",
            value=default_word_limit,
            min=300,
            max=500
        ),
        ui.input_action_button("generate", "Generate Podcast"),
        open="always"
    ),
    ui.h3("Your Podcast Audio Clip"),
    ui.output_text("transcript"),
    ui.output_ui("audio"),
    ),
)

def server(input, output, session):
    transcript_data = reactive.Value("Awaiting podcast transcript...")
    audio_data = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.generate)
    def generate_podcast():
        api_key = input.api_key()
        if not api_key:
            ui.notification_show("Please enter your OpenAI API key.", type="error")
            return
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Create a short engaging podcast transcript between two hosts, A and B, discussing the following source material:
        {input.text_input()}
        
        Format the transcript as follows:
        {json_schema}
        Keep the entire transcript dialogue under {input.word_limit} words.
        Try to use sentences that can be easily used with speech synthesis.
          - Show excitement and enthusiasm during the conversation.
        Only return the JSON response. Nothing else but JSON. 
          - Do not include ```json ``` (triple tick marks).
        Ensure it is compliant with JSON rules."""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates podcast transcripts."},
                    {"role": "user", "content": prompt}
                ]
            )
            generated_transcript = response.choices[0].message.content.strip()
        except Exception as e:
            ui.notification_show(f"Error: {str(e)}", type="error")
        
        combined_audio = io.BytesIO()
        # Load the JSON data
        generated_transcript = json.loads(generated_transcript)
        # format the transcript as string with A: and B: as speaker
        fmtd_transcript = ""
        for entry in generated_transcript["transcript"]:
            speaker = entry["speaker"]
            dialogue = entry["dialogue"]
            fmtd_transcript += f"{speaker}: {dialogue}\n"
        transcript_data.set(fmtd_transcript)

        for entry in generated_transcript["transcript"]:
            speaker = entry["speaker"]
            text = entry["dialogue"]
            # make it sound like an irish person
            tts = gTTS(text=text.strip(), lang='en', tld='ie', slow=False)
            mp3_fp = io.BytesIO()
            # Clear the previous audio file
            mp3_fp.truncate(0)
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            # For speaker B, we'll use a different voice (tld parameter)
            if speaker.strip().upper() == 'B':
                # make it sound like an Australian
                tts = gTTS(text=text.strip(), lang='en', tld='us', slow=False)
                mp3_fp = io.BytesIO()
                tts.write_to_fp(mp3_fp)
                mp3_fp.seek(0)
            combined_audio.write(mp3_fp.getvalue())
        combined_audio.seek(0)
        audio_data.set(combined_audio.getvalue())

    @output
    @render.text
    def transcript():
        return transcript_data()

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
