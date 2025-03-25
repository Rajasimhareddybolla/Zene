import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import time
import logging
from main import Mioo
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
    page_title="Mioo UPSC Tutor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Hide hamburger menu and footer
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

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
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response_str,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "agent_type": active_agent_type
                    })
                
            except Exception as e:
                st.error(f"Error processing message: {str(e)}")
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
    
    # Display chat history using standard Streamlit components
    if not st.session_state.chat_history:
        st.info("No messages yet. Start by asking a question about UPSC preparation!")
    else:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                agent_type = message.get("agent_type", "assistant")
                # Fix: Remove custom emoji avatar and add agent name in the message instead
                with st.chat_message("assistant"):
                    # Add agent name at the top of the message
                    if agent_type and agent_type != "assistant":
                        st.caption(f"Agent: {agent_type.upper()}")
                    
                    # Try to parse JSON if the response is in JSON format
                    try:
                        if isinstance(message["content"], str):
                            content_json = json.loads(message["content"])
                            if "response" in content_json:
                                st.write(content_json["response"])
                            elif "section_250_word_report" in content_json:
                                st.write(content_json["section_250_word_report"])
                            else:
                                st.write(message["content"])
                        else:
                            st.write(message["content"])
                    except:
                        # If not JSON or parsing fails, display as is
                        st.write(message["content"])

# Only show details if sidebar is shown
if st.session_state.show_sidebar:
    with details_col:
        # Create tabs for different details
        tabs = st.tabs(["Response Analysis", "Agent Flow", "Token Usage"])
        
        # Response Analysis Tab
        with tabs[0]:
            st.subheader("Response Analysis")
            
            if st.session_state.chat_history and any(msg["role"] == "assistant" for msg in st.session_state.chat_history):
                # Get the last assistant response
                latest_responses = [msg for msg in st.session_state.chat_history 
                                  if msg["role"] == "assistant"]
                
                if latest_responses:
                    latest_response = latest_responses[-1]
                    agent_type = latest_response.get("agent_type", "unknown")
                    
                    # Display which agent provided the final response
                    st.info(f"The final response was provided by the **{agent_type.upper()}** agent")
                    
                    # Show raw content of the response if requested
                    with st.expander("View Response Details", expanded=False):
                        st.write(latest_response["content"])
            else:
                st.info("No responses to analyze yet. Start a conversation to see analysis.")
            
        # Agent Flow Tab
        with tabs[1]:
            st.subheader("Agent Conversation Flow")
            
            if 'conversation_flow' in st.session_state and st.session_state.conversation_flow:
                # Create a visual flow of the agents used
                flow = st.session_state.conversation_flow
                
                # Display flow path
                flow_path = " → ".join([step.get("role", "unknown").upper() for step in flow])
                st.success(f"Flow path: {flow_path}")
                
                # Show detailed flow
                for i, step in enumerate(flow):
                    role = step.get("role", "unknown")
                    
                    with st.expander(f"{i+1}. {role.upper()} Step", expanded=i==0):
                        if role == "user":
                            st.write(step.get("content", ""))
                        else:
                            st.write(step.get("content", ""))
            else:
                st.info("No agent flow data available. Start a conversation using 'auto' mode to see the flow.")
        
        # Token Usage Tab 
        with tabs[2]:
            st.subheader("Token Usage Statistics")
            
            # Collect token usage data - simplified for direct Mioo integration
            st.info("Token usage tracking is available in automatic mode")
            
            if st.session_state.conversation_agent:
                usage_data = []
                
                # Display agent usage stats
                st.subheader("Agent Usage")
                
                for agent_type in ["zene", "commet", "finn", "milo", "thalia"]:
                    if st.session_state.conversation_agent.output_histories.get(agent_type):
                        st.write(f"**{agent_type.capitalize()}**: {len(st.session_state.conversation_agent.output_histories[agent_type])} interactions")
            else:
                st.info("No token usage data available yet.")

# Footer
st.markdown("---")
st.markdown("Mioo UPSC Assistant © 2024 | Powered by OpenAI and Google Gemini")
