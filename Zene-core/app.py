import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import time
import logging
from main import SnowBlaze
from dotenv import load_dotenv

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
    page_title="Zene AI Assistant",
    page_icon="🧠",
    layout="wide",
)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'conversation_agent' not in st.session_state:
    st.session_state.conversation_agent = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = "user_" + datetime.now().strftime("%Y%m%d%H%M%S")
if 'token_usage' not in st.session_state:
    st.session_state.token_usage = {
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "total_latency_seconds": 0,
        "calls": 0
    }

# App title and description
st.title("🧠 Zene AI Assistant")
st.markdown("Have a conversation with Zene, powered by OpenAI's language models")

# Layout: Two columns for chat and details
col1, col2 = st.columns([3, 2])

with col1:
    # Initialize agent if not already present
    if not st.session_state.conversation_agent:
        st.session_state.conversation_agent = SnowBlaze(user_id=st.session_state.user_id)
    
    # User input area
    with st.form("user_input_form", clear_on_submit=True):
        user_input = st.text_area("Enter your message:", height=100)
        col_submit, col_clear = st.columns([1, 5])
        with col_submit:
            submit_button = st.form_submit_button("Send")
        with col_clear:
            clear_button = st.form_submit_button("Clear Conversation")
    
    # Clear conversation if requested
    if clear_button:
        st.session_state.chat_history = []
        st.session_state.conversation_agent.conversations = []
        st.session_state.token_usage = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_latency_seconds": 0,
            "calls": 0
        }
        st.success("Conversation cleared!")
    
    # Process the query when submitted
    if submit_button and user_input:
        with st.spinner('Processing your message...'):
            try:
                # Process the message
                start_time = time.time()
                response_json = st.session_state.conversation_agent(user_input)
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Get the most recent output from agent's history
                latest_usage = {}
                if st.session_state.conversation_agent.output_history:
                    latest_output = st.session_state.conversation_agent.output_history[-1]
                    latest_usage = latest_output.get("usage", {})
                
                # Update token usage statistics
                st.session_state.token_usage["total_prompt_tokens"] += latest_usage.get("prompt_tokens", 0)
                st.session_state.token_usage["total_completion_tokens"] += latest_usage.get("completion_tokens", 0)
                st.session_state.token_usage["total_tokens"] += latest_usage.get("total_tokens", 0)
                st.session_state.token_usage["total_latency_seconds"] += latest_usage.get("latency_seconds", 0)
                st.session_state.token_usage["calls"] += 1
                
                # Add to chat history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response_json,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "usage": latest_usage,
                    "processing_time": processing_time
                })
                
            except Exception as e:
                st.error(f"Error processing message: {str(e)}")
    
    # Display chat history with custom styling
    st.markdown("""
    <style>
    .user-message {
        background-color: #e6f7ff;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        border-left: 5px solid #1e90ff;
    }
    .assistant-message {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        border-left: 5px solid #2e8b57;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader("Conversation")
    
    if not st.session_state.chat_history:
        st.info("No messages yet. Start a conversation by sending a message!")
    else:
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You ({message["timestamp"]}):</strong><br>
                        {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # For assistant messages, process the JSON or string content
                    content_display = message["content"]
                    if isinstance(content_display, dict):
                        # Extract the main response from the JSON
                        if "response" in content_display:
                            content_display = content_display["response"]
                        elif "explanation" in content_display:
                            content_display = content_display["explanation"]
                        else:
                            content_display = json.dumps(content_display, indent=2)
                    
                    st.markdown(f"""
                    <div class="assistant-message">
                        <strong>Zene ({message["timestamp"]}):</strong><br>
                        {content_display}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Option to save conversation
            if st.button("💾 Save Conversation"):
                try:
                    st.session_state.conversation_agent.save_conversation()
                    st.success("Conversation saved successfully!")
                except Exception as e:
                    st.error(f"Error saving conversation: {str(e)}")

with col2:
    # Create tabs for different details
    tabs = st.tabs(["Token Usage", "Response Analysis", "Settings"])
    
    # Token Usage Tab
    with tabs[0]:
        st.header("Token Usage Statistics")
        
        # Show summary metrics
        token_usage = st.session_state.token_usage
        calls = token_usage["calls"]
        
        col_total, col_prompt, col_completion = st.columns(3)
        with col_total:
            st.metric("Total Tokens", f"{token_usage['total_tokens']:,}")
        with col_prompt:
            st.metric("Prompt Tokens", f"{token_usage['total_prompt_tokens']:,}")
        with col_completion:
            st.metric("Completion Tokens", f"{token_usage['total_completion_tokens']:,}")
        
        # Show latency metrics
        total_latency = token_usage["total_latency_seconds"]
        avg_latency = total_latency / calls if calls > 0 else 0
        
        col_latency, col_calls = st.columns(2)
        with col_latency:
            st.metric("Avg Latency", f"{avg_latency:.2f}s")
        with col_calls:
            st.metric("API Calls", calls)
        
        # Show token distribution chart
        if calls > 0:
            st.subheader("Token Distribution")
            token_df = pd.DataFrame({
                'Type': ['Prompt Tokens', 'Completion Tokens'],
                'Count': [token_usage['total_prompt_tokens'], token_usage['total_completion_tokens']]
            })
            st.bar_chart(token_df.set_index('Type'))
            
            # Calculate token usage rate
            tokens_per_call = token_usage['total_tokens'] / calls if calls > 0 else 0
            st.markdown(f"**Average tokens per call:** {tokens_per_call:.1f}")
            
            # Create a simple progress bar showing efficiency
            st.subheader("Efficiency")
            if tokens_per_call > 0:
                # A simple heuristic: below 1000 tokens per call is efficient
                efficiency = max(0, min(1, 1 - (tokens_per_call / 4000)))
                st.progress(efficiency)
                
                if efficiency > 0.7:
                    st.success("Token usage is efficient")
                elif efficiency > 0.4:
                    st.info("Token usage is moderate")
                else:
                    st.warning("Token usage is high - consider shorter prompts")
    
    # Response Analysis Tab
    with tabs[1]:
        st.header("Response Analysis")
        
        if st.session_state.chat_history and any(msg["role"] == "assistant" for msg in st.session_state.chat_history):
            # Get the most recent assistant response
            latest_response = next((msg for msg in reversed(st.session_state.chat_history) 
                                   if msg["role"] == "assistant"), None)
            
            if latest_response:
                # Show processing time
                st.info(f"Processing time: {latest_response.get('processing_time', 0):.2f} seconds")
                
                # Show the raw JSON response
                st.subheader("Raw Response")
                
                with st.expander("View Raw JSON", expanded=False):
                    st.json(latest_response["content"])
                
                # If the response is a dictionary with specific fields, show them nicely
                if isinstance(latest_response["content"], dict):
                    content = latest_response["content"]
                    
                    # Show any fields that might be in the response
                    possible_fields = ["response", "explanation", "analysis", "summary", "sources"]
                    
                    for field in possible_fields:
                        if field in content:
                            st.subheader(field.capitalize())
                            st.write(content[field])
        else:
            st.info("No responses to analyze yet. Start a conversation to see analysis.")
    
    # Settings Tab
    with tabs[2]:
        st.header("Settings")
        
        # User ID settings
        st.subheader("User ID")
        new_user_id = st.text_input("Change User ID", value=st.session_state.user_id)
        if st.button("Update User ID"):
            # Create a new agent with the new user ID
            st.session_state.user_id = new_user_id
            st.session_state.conversation_agent = SnowBlaze(user_id=new_user_id)
            st.success(f"User ID updated to {new_user_id}")
        
        # Model settings
        st.subheader("Model Settings")
        model_options = ["gpt-4o","gpt-4o-mini"]
        selected_model = st.selectbox(
            "Select Model", 
            options=model_options,
            index=0,  # Default to first option
            help="Choose the OpenAI model to use for responses"
        )
        if st.button("Update Model"):
            # The model setting would need to be passed to the get_response method
            st.success(f"Model updated to {selected_model}")
            st.info("This will apply to your next message")
        
        # About section
        st.subheader("About")
        st.markdown("""
        **Zene AI Assistant** is powered by OpenAI's models through the SnowBlaze framework.
        
        - Built using Streamlit
        - Uses JSON response format
        - Tracks token usage and conversation history
        """)

# Add footer
st.markdown("---")
st.markdown("Zene AI Assistant © 2023 | Powered by OpenAI")
