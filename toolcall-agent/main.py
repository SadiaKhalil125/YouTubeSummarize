import os
from serpapi import GoogleSearch
from dotenv import load_dotenv
import google.generativeai as genai
from pydub import AudioSegment
import time
import logging
import subprocess 
import streamlit as st
from google import genai
from google.genai import types
# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main App Interface ---
st.set_page_config(page_title="YouTube Video Transcriber", layout="wide")
st.title("🔎 YouTube Video Search & Transcription Agent")
st.markdown("Enter a topic to find a relevant YouTube video, transcribe it, and save the transcript.")

# --- API Key Configuration in Sidebar ---
with st.sidebar:
    st.header("API Configuration")
    st.markdown("Please enter your API keys below.")
    load_dotenv()
    
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not serpapi_key or not gemini_key:
        st.warning("Please enter your API keys to proceed.")
    else:
        st.success("API keys configured.")

# --- Core Functions ---
def get_video_url(query: str, api_key: str) -> str:
    """Search for a YouTube video using SerpAPI."""
    params = {
        "engine": "youtube",
        "search_query": query,
        "api_key": api_key
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        video_results = results.get("video_results", [])
        if video_results:
            return video_results[0].get("link")
        return None
    except Exception as e:
        st.error(f"SerpApi Error: {e}")
        logging.error(f"SerpApi Error: {e}")
        return None

def transcribe_video(video_url: str) -> str:
    try:  
        client = genai.Client()  
        
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=types.Content(
            parts=[
            types.Part(
                file_data=types.FileData(file_uri=video_url)
            ),
            types.Part(text='Transcribe the audio from the provided YouTube video URL into text. Include every word spoken in the video.')
                ]
            )
        )
        logging.info(f"Gemini Response: {response}")
        return response.text
    except Exception as e:
        st.error(f"Error during transcription: {str(e)}")
        logging.error(f"Transcription error: {e}", exc_info=True)
        return None
    finally:
        st.info("Cleaning up temporary files...")

def save_transcription(topic: str, transcript: str):
    """Saves the transcription to a text file."""
    filename = f"{topic.replace(' ', '_')}_transcription.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(transcript)
    return filename

# --- User Input and Workflow ---
topic = st.text_input("Enter the topic for the video search:", placeholder="e.g., 'The future of AI'")

if st.button("Search and Transcribe", use_container_width=True):
    if not serpapi_key or not gemini_key:
        st.error("API keys are missing. Please configure them in the sidebar.")
    elif not topic:
        st.warning("Please enter a topic to search for.")
    else:
        # genai.configure(api_key=gemini_key)
        with st.status("Running the AI agent...", expanded=True) as status:
            st.write(f"Searching for a video about '{topic}'...")
            video_url = get_video_url(topic, serpapi_key)
            if video_url:
                st.write(f"Video found: {video_url}")
                st.video(video_url)
                st.write("Starting transcription process...")
                transcript = transcribe_video(video_url)
                if transcript:
                    st.write("Transcription successful!")
                    saved_file = save_transcription(topic, transcript)
                    st.write(f"💾 Transcription saved to: **{saved_file}**")
                    st.subheader("Generated Transcript")
                    st.text_area("Transcript", transcript, height=400)
                    status.update(label="Process Complete!", state="complete")
                else:
                    st.error("Could not generate transcript.")
                    status.update(label="Process Failed", state="error")
            else:
                st.error(f"No video found for: '{topic}'")
                status.update(label="Process Failed", state="error")