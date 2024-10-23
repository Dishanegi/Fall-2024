import streamlit as st
from audio_recorder_streamlit import audio_recorder
import openai
import base64
import os

# Initialize the OpenAI client
def setup_openai_client():
    api_key = st.secrets["openai_api_key"]
    return openai.OpenAI(api_key=api_key)

# Function to transcribe audio to text
def transcribe_audio(client, audio_path):
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return transcript.text

# Taking response from OpenAI
def fetch_ai_response(client, input_text):
    messages = [{"role": "user", "content": input_text}]
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    return response.choices[0].message.content.strip()

# Convert text to audio
def text_to_audio(client, text, audio_path):
    response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
    response.stream_to_file(audio_path)

# Auto-play audio function
def auto_play_audio(audio_file):
    with open(audio_file, "rb") as audio_file:
        audio_bytes = audio_file.read()
    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    audio_html = f'<audio src="data:audio/mp3;base64,{base64_audio}" controls autoplay>'
    st.markdown(audio_html, unsafe_allow_html=True)

# Function to display messages
def display_messages(messages):
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant" and message.get("audio"):
                auto_play_audio(message["audio"])

# Main function

st.title("AI Chatbot with Text and Voice")
st.write("Type your message or use voice input.")

# Initialize session state variables
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_recorded_audio' not in st.session_state:
    st.session_state.last_recorded_audio = None
if 'awaiting_response' not in st.session_state:
    st.session_state.awaiting_response = False
if 'last_input' not in st.session_state:
    st.session_state.last_input = ""

# Setup OpenAI client using the API key from secrets
try:
    client = setup_openai_client()
except KeyError:
    st.error("OpenAI API key not found in secrets. Please add it to your secrets with the key 'openai_api_key'.")
    st.stop()

# Display chat messages
chat_container = st.container()
with chat_container:
    display_messages(st.session_state.messages)

# Input section at the bottom
with st.container():
    col1, col2 = st.columns([3, 1])
        
    with col1:
        text_input = st.text_input("Type your message here", key="text_input", value="")
        
    with col2:
        st.write("Or use voice input:")
        recorded_audio = audio_recorder(text="", recording_color="#e74c3c", neutral_color="#95a5a6")

# Handle text input
if text_input and text_input != st.session_state.last_input and not st.session_state.awaiting_response:
    st.session_state.awaiting_response = True
    st.session_state.last_input = text_input
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": text_input})
        
    # Get and display AI response
    ai_response = fetch_ai_response(client, text_input)
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
        
    st.session_state.awaiting_response = False
    st.rerun()

# Handle voice input
if recorded_audio is not None and recorded_audio != st.session_state.last_recorded_audio and not st.session_state.awaiting_response:
    st.session_state.awaiting_response = True
    st.session_state.last_recorded_audio = recorded_audio
        
    audio_file = "audio.mp3"
    with open(audio_file, "wb") as f:
        f.write(recorded_audio)

    # Process the new audio
    if os.path.exists(audio_file):
        transcribed_text = transcribe_audio(client, audio_file)
            
        # Add user message to chat without audio
        st.session_state.messages.append({"role": "user", "content": transcribed_text})

        # Get AI response
        ai_response = fetch_ai_response(client, transcribed_text)
            
        # Convert AI response to speech
        response_audio_file = "audio_response.mp3"
        text_to_audio(client, ai_response, response_audio_file)
            
        # Add AI response to chat with audio
        st.session_state.messages.append({"role": "assistant", "content": ai_response, "audio": response_audio_file})
        
    st.session_state.awaiting_response = False
    st.rerun()