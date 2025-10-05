# import os
# from serpapi import GoogleSearch
# from dotenv import load_dotenv
# import google.generativeai as genai
# from pydub import AudioSegment
# import time
# import logging
# import subprocess 
# import streamlit as st

# # --- Setup Logging ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # --- Main App Interface ---
# st.set_page_config(page_title="YouTube Video Transcriber", layout="wide")
# st.title("🔎 YouTube Video Search & Transcription Agent")
# st.markdown("Enter a topic to find a relevant YouTube video, transcribe it, and save the transcript.")

# # --- API Key Configuration in Sidebar ---
# with st.sidebar:
#     st.header("API Configuration")
#     st.markdown("Please enter your API keys below.")
#     load_dotenv()
    
#     serpapi_key = os.getenv("SERPAPI_API_KEY")
#     gemini_key = os.getenv("GEMINI_API_KEY")

#     if not serpapi_key or not gemini_key:
#         st.warning("Please enter your API keys to proceed.")
#     else:
#         st.success("API keys configured.")

# # --- Core Functions ---
# def get_video_url(query: str, api_key: str) -> str:
#     """Search for a YouTube video using SerpAPI."""
#     params = {
#         "engine": "youtube",
#         "search_query": query,
#         "api_key": api_key
#     }
#     try:
#         search = GoogleSearch(params)
#         results = search.get_dict()
#         video_results = results.get("video_results", [])
#         if video_results:
#             return video_results[0].get("link")
#         return None
#     except Exception as e:
#         st.error(f"SerpApi Error: {e}")
#         logging.error(f"SerpApi Error: {e}")
#         return None

# def transcribe_video(video_url: str) -> str:
#     """Downloads audio with yt-dlp and transcribes with Gemini."""
#     downloaded_file_path = None
#     converted_file_path = None
#     try:
#         st.info("Downloading audio from YouTube...")
        
#         output_template = "temp_audio.%(ext)s"
        
#         # Enhanced command with cookies and user agent to bypass 403
#         command = [
#             "yt-dlp",
#             "-f", "bestaudio/best",  # Changed format selector
#             "-x",  # Extract audio
#             "--audio-format", "mp3",
#             "--audio-quality", "0",
#             "-o", output_template,
#             "--no-playlist",
#             "--extractor-args", "youtube:player_client=android",  # Use Android client
#             "--no-check-certificate",
#             video_url
#         ]
        
#         logging.info(f"Running: {' '.join(command)}")
#         result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
#         if result.returncode != 0:
#             st.error("yt-dlp download failed. See error details below.")
#             with st.expander("Show yt-dlp error"):
#                 st.code(result.stderr if result.stderr else result.stdout)
            
#             logging.error(f"yt-dlp Error: {result.stderr if result.stderr else result.stdout}")
#             return None
        
#         # Find downloaded file
#         temp_files = [f for f in os.listdir('.') if f.startswith('temp_audio')]
#         if not temp_files:
#             st.error("Audio file not found after download.")
#             return None
        
#         downloaded_file_path = temp_files[0]
#         st.success(f"Audio downloaded: {downloaded_file_path} ({os.path.getsize(downloaded_file_path):,} bytes)")
        
#         # Convert audio
#         st.info("Converting audio to FLAC format...")
#         audio = AudioSegment.from_file(downloaded_file_path)
#         audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
#         converted_file_path = "converted_audio.flac"
#         audio.export(converted_file_path, format="flac")
#         st.success(f"Audio converted: {os.path.getsize(converted_file_path):,} bytes")
        
#         # Upload to Gemini
#         st.info("Uploading audio to Gemini...")
#         your_file = genai.upload_file(path=converted_file_path, display_name="youtube_audio")
        
#         # Wait for processing
#         st.info("Processing audio file...")
#         max_wait = 300
#         waited = 0
#         while your_file.state.name == "PROCESSING" and waited < max_wait:
#             time.sleep(2)
#             waited += 2
#             your_file = genai.get_file(name=your_file.name)
        
#         if your_file.state.name == "FAILED":
#             st.error("Gemini failed to process the audio file.")
#             genai.delete_file(your_file.name)
#             return None
        
#         # Transcribe
#         st.info("Transcribing audio with Gemini...")
#         model = genai.GenerativeModel(model_name='models/gemini-2.5-flash')
#         response = model.generate_content([
#             "Transcribe the following audio completely and accurately. Include all spoken words:",
#             your_file
#         ])
        
#         genai.delete_file(your_file.name)
#         return response.text

#     except subprocess.TimeoutExpired:
#         st.error("Download timed out after 5 minutes.")
#         return None
#     except Exception as e:
#         st.error(f"Error during transcription: {str(e)}")
#         logging.error(f"Transcription error: {e}", exc_info=True)
#         return None
#     finally:
#         # Cleanup
#         if downloaded_file_path and os.path.exists(downloaded_file_path):
#             try:
#                 os.remove(downloaded_file_path)
#             except:
#                 pass
#         if converted_file_path and os.path.exists(converted_file_path):
#             try:
#                 os.remove(converted_file_path)
#             except:
#                 pass

# def save_transcription(topic: str, transcript: str):
#     """Saves the transcription to a text file."""
#     filename = f"{topic.replace(' ', '_')}_transcription.txt"
#     with open(filename, "w", encoding="utf-8") as f:
#         f.write(transcript)
#     return filename

# # --- User Input and Workflow ---
# topic = st.text_input("Enter the topic for the video search:", placeholder="e.g., 'The future of AI'")

# if st.button("Search and Transcribe", use_container_width=True):
#     if not serpapi_key or not gemini_key:
#         st.error("API keys are missing. Please configure them in the sidebar.")
#     elif not topic:
#         st.warning("Please enter a topic to search for.")
#     else:
#         genai.configure(api_key=gemini_key)
#         with st.status("Running the AI agent...", expanded=True) as status:
#             st.write(f"Searching for a video about '{topic}'...")
#             video_url = get_video_url(topic, serpapi_key)
#             if video_url:
#                 st.write(f"Video found: {video_url}")
#                 st.video(video_url)
#                 st.write("Starting transcription process...")
#                 transcript = transcribe_video(video_url)
#                 if transcript:
#                     st.write("Transcription successful!")
#                     saved_file = save_transcription(topic, transcript)
#                     st.write(f"💾 Transcription saved to: **{saved_file}**")
#                     st.subheader("Generated Transcript")
#                     st.text_area("Transcript", transcript, height=400)
#                     status.update(label="Process Complete!", state="complete")
#                 else:
#                     st.error("Could not generate transcript.")
#                     status.update(label="Process Failed", state="error")
#             else:
#                 st.error(f"No video found for: '{topic}'")
#                 status.update(label="Process Failed", state="error")