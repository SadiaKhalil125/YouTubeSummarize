import os
from serpapi import GoogleSearch
from dotenv import load_dotenv
import google.generativeai as genai
# Pytube is no longer needed for downloading, but we'll leave the import for context
# from pytube import YouTube 
from pydub import AudioSegment
import time
import logging
import subprocess # Import the subprocess module
import streamlit as st

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
    # For demonstration, allowing manual input if .env fails
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not serpapi_key or not gemini_key:
        st.warning("Please enter your API keys to proceed.")
    else:
        st.success("API keys configured.")

# --- Core Functions ---
def get_video_url(query: str, api_key: str) -> str:
    # This function remains the same
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

# --- REVISED transcribe_video FUNCTION ---
def transcribe_video(video_url: str) -> str:
    """Downloads audio with yt-dlp, converts it, and returns the transcription from Gemini."""
    downloaded_file_path = None
    converted_file_path = None
    try:
        # 1. Download Audio using yt-dlp
        st.info("Downloading audio from YouTube using yt-dlp...")
        
        # Define the output file name, yt-dlp will add the correct extension
        output_template = "temp_audio.%(ext)s"
        
        # Command to execute yt-dlp
        # -x: extract audio
        # --audio-format best: get the best quality audio
        # -o: specify output file template
        command = [
            "yt-dlp",
            "-x",
            "--audio-format", "best",
            "-o", output_template,
            video_url
        ]
        
        # Execute the command
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        
        # Find the actual name of the downloaded file (since extension was unknown)
        # We need to find the file that starts with 'temp_audio'
        temp_dir_files = os.listdir('.')
        downloaded_file_path = next((f for f in temp_dir_files if f.startswith('temp_audio')), None)

        if not downloaded_file_path or not os.path.exists(downloaded_file_path) or os.path.getsize(downloaded_file_path) == 0:
            st.error("Audio download with yt-dlp failed. Could not find downloaded file or file is empty.")
            logging.error(f"yt-dlp stdout: {result.stdout}")
            logging.error(f"yt-dlp stderr: {result.stderr}")
            return None
        st.success(f"✅ Audio downloaded successfully: {downloaded_file_path}")

        # 2. Convert Audio
        st.info("Converting audio to a compatible format (FLAC)...")
        audio = AudioSegment.from_file(downloaded_file_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        converted_file_path = "converted_audio.flac"
        audio.export(converted_file_path, format="flac")
        
        if not os.path.exists(converted_file_path) or os.path.getsize(converted_file_path) == 0:
            st.error("Audio conversion failed, resulting in an empty file.")
            return None
        st.success("✅ Audio converted successfully.")

        # 3. Transcribe with Gemini (This part remains the same)
        st.info("Uploading audio to Gemini for transcription...")
        your_file = genai.upload_file(path=converted_file_path, display_name="youtube_audio")
        
        st.info("Processing the audio file...")
        while your_file.state.name == "PROCESSING":
            time.sleep(2)
            your_file = genai.get_file(name=your_file.name)
        
        if your_file.state.name == "FAILED":
            st.error("Gemini file processing failed. The file may be corrupt or in an unsupported format.")
            return None
        
        st.info("Transcribing the audio...")
        model = genai.GenerativeModel(model_name='models/gemini-2.5-flash')
        response = model.generate_content(["Transcribe the following audio:", your_file])
        
        genai.delete_file(your_file.name)
        return response.text

    except subprocess.CalledProcessError as e:
        st.error(f"yt-dlp failed to download the audio. This can happen with private or age-restricted videos.")
        logging.error(f"yt-dlp error: {e.stderr}")
        return None
    except Exception as e:
        st.error(f"An error occurred during the transcription process: {e}")
        logging.error(f"An error occurred during transcription: {e}", exc_info=True)
        return None
    finally:
        # 4. Cleanup local files
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)
        if converted_file_path and os.path.exists(converted_file_path):
            os.remove(converted_file_path)

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
        genai.configure(api_key=gemini_key)
        with st.status("Running the AI agent...", expanded=True) as status:
            st.write(f"➡️ Searching for a video about '{topic}'...")
            video_url = get_video_url(topic, serpapi_key)
            if video_url:
                st.write(f"✅ Video found: {video_url}")
                st.video(video_url)
                st.write("➡️ Starting transcription process...")
                transcript = transcribe_video(video_url)
                if transcript:
                    st.write("✅ Transcription successful.")
                    saved_file = save_transcription(topic, transcript)
                    st.write(f"💾 Transcription saved to file: **{saved_file}**")
                    st.subheader("Generated Transcript")
                    st.text_area("Transcript", transcript, height=400)
                    status.update(label="Process Complete!", state="complete")
                else:
                    st.error("Could not generate transcript. Please check the logs for errors.")
                    status.update(label="Process Failed", state="error")
            else:
                st.error(f"No video was found for the topic: '{topic}'")
                status.update(label="Process Failed", state="error")