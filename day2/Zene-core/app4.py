import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import time
import logging
import requests
import base64
from main_gemini import Mioo
from dotenv import load_dotenv
import threading
import uuid
import queue

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Mioo UPSC Tutor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create a thread-safe queue for audio files
# This will be accessible from any thread
audio_file_queue = queue.Queue()

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'conversation_agent' not in st.session_state:
    st.session_state.conversation_agent = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = "user_" + datetime.now().strftime("%Y%m%d%H%M%S")
if 'current_agent_type' not in st.session_state:
    st.session_state.current_agent_type = "zene"
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gpt-4o"
if 'show_sidebar' not in st.session_state:
    st.session_state.show_sidebar = True
if 'voice_enabled' not in st.session_state:
    st.session_state.voice_enabled = False
if 'selected_voice' not in st.session_state:
    st.session_state.selected_voice = "alloy"
if 'audio_queue' not in st.session_state:
    st.session_state.audio_queue = []
if 'current_audio_key' not in st.session_state:
    st.session_state.current_audio_key = None

# Voice API endpoint
VOICE_API_ENDPOINT = "http://localhost:4000/generate-audio/"

# Voice generation function
def generate_voice(text, voice="alloy"):
    try:
        # Split text into manageable chunks for better streaming experience
        chunks = split_text_into_chunks(text, max_length=300)
        audio_files = []
        
        for chunk in chunks:
            if not chunk.strip():
                continue
                
            response = requests.post(
                VOICE_API_ENDPOINT,
                json={"text": chunk, "voice": voice}
            )
            
            if response.status_code == 200:
                audio_file = response.json()["filepath"]
                logger.info(f"Generated voice file: {audio_file}")
                audio_files.append(audio_file)
            else:
                logger.error(f"Error generating voice: {response.text}")
        
        return audio_files
    except Exception as e:
        logger.error(f"Error generating voice: {str(e)}")
        return []

# Function to split text into smaller chunks for better voice generation
def split_text_into_chunks(text, max_length=300):
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(' '.join(current_chunk)) >= max_length:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# Async voice processing thread function
def process_voice_in_background(text, voice):
    try:
        logger.info(f"Starting voice generation for text: {text[:50]}...")
        audio_files = generate_voice(text, voice)
        logger.info(f"Generated {len(audio_files)} audio files")
        
        # Flag to indicate if at least one file was added
        files_added = False
        
        if audio_files:
            # Instead of directly updating session state, add to thread-safe queue
            for audio_file in audio_files:
                # Generate a unique ID for this audio file
                audio_id = str(uuid.uuid4())
                new_audio = {
                    "id": audio_id,
                    "file": audio_file,
                    "played": False,
                    "timestamp": datetime.now().timestamp()
                }
                # Add to queue instead of session state
                audio_file_queue.put(new_audio)
                logger.info(f"Added audio file to queue: {audio_file}")
                files_added = True
            
            logger.info(f"Added {len(audio_files)} files to queue")
            
            # Create a file to signal that new audio is available
            # This is a more reliable way to trigger a rerun than relying on session state
            if files_added:
                signal_file = "audio_signal.txt"
                try:
                    with open(signal_file, "w") as f:
                        f.write(f"New audio available: {datetime.now().isoformat()}")
                    logger.info("Created signal file to trigger rerun")
                except Exception as e:
                    logger.error(f"Error creating signal file: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in voice background processing: {str(e)}", exc_info=True)

# Function to check for new audio files in the queue and add them to session state
def check_audio_queue():
    try:
        # Initialize audio queue in session state if not present
        if 'audio_queue' not in st.session_state:
            st.session_state.audio_queue = []
            
        # Get all items from the queue without blocking
        new_items = 0
        while not audio_file_queue.empty():
            try:
                audio_item = audio_file_queue.get_nowait()
                st.session_state.audio_queue.append(audio_item)
                new_items += 1
                logger.info(f"Moved audio item from queue to session state: {audio_item['file']}")
            except queue.Empty:
                break
        
        if new_items > 0:
            logger.info(f"Added {new_items} items from queue to session state, total: {len(st.session_state.audio_queue)}")
            # Force a rerun to play the new audio
            st.session_state.new_audio_available = True
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking audio queue: {str(e)}", exc_info=True)
        return False

# Function to directly play an audio file for testing
def play_test_audio():
    try:
        test_text = "This is a test of the voice system. If you can hear this, the voice system is working correctly."
        logger.info("Generating test audio directly")
        
        # Generate audio directly (not in background)
        response = requests.post(
            VOICE_API_ENDPOINT,
            json={"text": test_text, "voice": st.session_state.selected_voice}
        )
        
        if response.status_code == 200:
            audio_file = response.json()["filepath"]
            logger.info(f"Test audio file generated: {audio_file}")
            
            # Return the audio bytes directly instead of returning a file path
            return play_audio_directly(audio_file)[0]
        else:
            logger.error(f"Error generating test audio: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error in test audio generation: {str(e)}", exc_info=True)
        return None

# Audio management - Add a more direct audio player
def play_audio_directly(audio_file_path):
    """Directly play audio without relying on session state queues"""
    try:
        if os.path.exists(audio_file_path):
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            
            # Generate a unique key for this audio file
            unique_key = f"direct_audio_{datetime.now().timestamp()}"
            return audio_bytes, unique_key
        else:
            logger.error(f"Audio file not found: {audio_file_path}")
            return None, None
    except Exception as e:
        logger.error(f"Error playing audio directly: {str(e)}", exc_info=True)
        return None, None

# Function to directly play an audio file for testing
def play_test_audio():
    try:
        test_text = "This is a test of the voice system. If you can hear this, the voice system is working correctly."
        logger.info("Generating test audio directly")
        
        # Generate audio directly (not in background)
        response = requests.post(
            VOICE_API_ENDPOINT,
            json={"text": test_text, "voice": st.session_state.selected_voice}
        )
        
        if response.status_code == 200:
            audio_file = response.json()["filepath"]
            logger.info(f"Test audio file generated: {audio_file}")
            
            if os.path.exists(audio_file):
                with open(audio_file, "rb") as f:
                    audio_bytes = f.read()
                return audio_bytes
            else:
                logger.error(f"Test audio file not found: {audio_file}")
                return None
        else:
            logger.error(f"Error generating test audio: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error in test audio generation: {str(e)}", exc_info=True)
        return None

# Hide hamburger menu and footer
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom audio player styles */
    .voice-controls {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }
    .voice-controls button {
        margin-right: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize additional session state variables
if 'new_audio_available' not in st.session_state:
    st.session_state.new_audio_available = False
if 'currently_playing' not in st.session_state:
    st.session_state.currently_playing = None
if 'last_played_id' not in st.session_state:
    st.session_state.last_played_id = None

# Check for new audio files in the queue
new_audio_added = check_audio_queue()
if new_audio_added:
    st.session_state.new_audio_available = True

# Create a sidebar toggle button
if st.button("Toggle Sidebar", key="toggle_sidebar"):
    st.session_state.show_sidebar = not st.session_state.show_sidebar

# Only display sidebar if show_sidebar is True
if st.session_state.show_sidebar:
    with st.sidebar:
        st.title("🧠 Mioo UPSC Tutor")
        st.markdown("Powered by OpenAI and Google Gemini models")
        
        # User ID selection
        st.header("User Identification")
        if st.checkbox("Use custom User ID", False):
            custom_user_id = st.text_input("Enter Custom User ID", value=st.session_state.user_id)
            if custom_user_id != st.session_state.user_id:
                st.session_state.user_id = custom_user_id
                st.session_state.conversation_agent = Mioo(user_id=custom_user_id)
                st.success(f"User ID set to: {custom_user_id}")
        
        # Display current user ID
        st.info(f"Current User ID: {st.session_state.user_id}")
        
        # Agent selector
        st.header("Agent Selection")
        agent_options = ["zene", "commet", "finn", "milo", "thalia", "auto"]
        selected_agent = st.selectbox(
            "Select Agent", 
            options=agent_options,
            index=agent_options.index(st.session_state.current_agent_type) if st.session_state.current_agent_type in agent_options else 0,
            help="Choose which agent to converse with"
        )
        
        if selected_agent != st.session_state.current_agent_type:
            st.session_state.current_agent_type = selected_agent
            st.success(f"Switched to {selected_agent} agent")
        
        # Model settings
        st.header("Model Settings")
        model_options = ["gpt-4o", "gpt-4o-mini", "gemini-2.0-flash"]
        selected_model = st.selectbox(
            "Select Model", 
            options=model_options,
            index=model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0,
            help="Choose the model to use for responses"
        )
        
        if st.button("Update Model"):
            st.session_state.selected_model = selected_model
            st.success(f"Model updated to {selected_model}")
        
        # Voice settings
        st.header("Voice Settings")
        voice_enabled = st.checkbox("Enable Voice Output", value=st.session_state.voice_enabled)
        if voice_enabled != st.session_state.voice_enabled:
            st.session_state.voice_enabled = voice_enabled
            
        voice_options = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        selected_voice = st.selectbox(
            "Select Voice", 
            options=voice_options,
            index=voice_options.index(st.session_state.selected_voice) if st.session_state.selected_voice in voice_options else 0
        )
        if selected_voice != st.session_state.selected_voice:
            st.session_state.selected_voice = selected_voice
        
        # Voice testing section
        st.subheader("Voice Testing")
        
        # Add a test voice button for background processing
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Background Test"):
                test_text = "This is a background test of the voice generation system. I'm your UPSC assistant, and I'm ready to help you with your preparation."
                # Start voice generation in background
                voice_thread = threading.Thread(
                    target=process_voice_in_background,
                    args=(test_text, st.session_state.selected_voice)
                )
                voice_thread.daemon = True
                voice_thread.start()
                st.info("Voice test initiated. Audio should play shortly.")
        
        # Add a direct test button that bypasses background processing
        with col2:
            if st.button("Direct Test"):
                with st.spinner("Generating test audio..."):
                    audio_bytes = play_test_audio()
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                        st.success("Test audio played successfully!")
                    else:
                        st.error("Failed to generate test audio.")
        
        # Voice queue info
        if st.session_state.audio_queue:
            unplayed = sum(1 for item in st.session_state.audio_queue if not item.get("played"))
            st.info(f"Audio queue: {len(st.session_state.audio_queue)} files ({unplayed} unplayed)")
            if st.button("Clear Audio Queue"):
                st.session_state.audio_queue = []
                st.success("Audio queue cleared")
        
        # Agent information
        st.header("Agent Information")
        st.markdown("""
        - **Zene**: Primary router agent
        - **Commet**: Complex inquiry handler
        - **Finn**: Knowledge retrieval agent
        - **Milo**: Content generation agent
        - **Thalia**: Gemini-powered assistant
        """)
        
        # Reset options
        st.header("Reset Options")
        if st.button("Clear Conversation"):
            agent_type = st.session_state.current_agent_type
            if agent_type == "auto":
                st.session_state.conversation_agent.delete_conversation("all")
            else:
                st.session_state.conversation_agent.delete_conversation(agent_type)
            st.session_state.chat_history = []
            st.success(f"Conversation cleared!")

# Main content area layout
if st.session_state.show_sidebar:
    main_col, details_col = st.columns([3, 2])
else:
    main_col = st.container()

with main_col:
    # Display chat title
    st.title("Mioo UPSC Assistant")
    
    # Create dedicated containers for the audio player - move to top
    audio_status = st.empty()
    audio_container = st.container()
    
    # Initialize agent if not already present
    if not st.session_state.conversation_agent:
        st.session_state.conversation_agent = Mioo(user_id=st.session_state.user_id)
    
    # User input area
    with st.form("user_input_form", clear_on_submit=True):
        user_input = st.text_area("Ask me anything about UPSC preparation:", height=100, placeholder="Type your question here...")
        cols = st.columns([1, 1, 4])
        with cols[0]:
            submit_button = st.form_submit_button("Send", use_container_width=True)
        with cols[1]:
            clear_button = st.form_submit_button("Clear Chat", use_container_width=True)
    
    # Clear conversation if requested
    if clear_button:
        agent_type = st.session_state.current_agent_type
        if agent_type == "auto":
            st.session_state.conversation_agent.delete_conversation("all")
        else:
            st.session_state.conversation_agent.delete_conversation(agent_type)
        st.session_state.chat_history = []
        st.success(f"Conversation cleared!")
    
    # Process user input when submitted
    if submit_button and user_input:
        with st.spinner('Processing your question...'):
            try:
                # Process the message
                start_time = time.time()
                
                # Determine which agent to use
                active_agent_type = st.session_state.current_agent_type
                
                if active_agent_type == "auto":
                    # Add user message to chat history
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_input,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    
                    # Use the __call__ method to handle agent workflow
                    # Properly unpack the tuple - last_agent_response is a string with the final response
                    last_agent_response, conversation_flow = st.session_state.conversation_agent(user_input)
                    
                    # Store the conversation flow in session state
                    st.session_state.conversation_flow = conversation_flow
                    
                    # Add final response to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": last_agent_response,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "agent_type": conversation_flow[-1]["role"] if conversation_flow else "unknown"
                    })
                    
                    # Generate voice in background if enabled
                    if st.session_state.voice_enabled:
                        voice_thread = threading.Thread(
                            target=process_voice_in_background,
                            args=(last_agent_response, st.session_state.selected_voice)
                        )
                        voice_thread.daemon = True
                        voice_thread.start()
                    
                else:
                    # Use a specific agent
                    model_name = st.session_state.selected_model
                    if active_agent_type == "thalia" and model_name != "gemini-2.0-flash":
                        model_name = "gemini-2.0-flash"  # Always use Gemini for Thalia
                    
                    response_str = st.session_state.conversation_agent.get_agent_response(
                        active_agent_type, 
                        user_input,
                        model_name=model_name
                    )
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_input,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    
                    # Add response to chat history
                    st.session_state.chat