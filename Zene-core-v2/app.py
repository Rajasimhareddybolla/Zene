import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import time
import logging
from main import Mioo
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

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
            
            # Collect token usage data from conversation agent
            if st.session_state.conversation_agent:
                
                # Extract token usage data from all agents
                all_token_data = []
                current_chat_data = []
                total_tokens_used = 0
                total_prompt_tokens = 0
                total_completion_tokens = 0
                
                # Track current chat token usage
                current_chat_tokens = 0
                current_chat_prompt_tokens = 0
                current_chat_completion_tokens = 0
                
                for agent_type in ["zene", "commet", "finn", "milo", "thalia", "mara", "inka"]:
                    if agent_type in st.session_state.conversation_agent.output_histories:
                        history = st.session_state.conversation_agent.output_histories[agent_type]
                        
                        # Track if we've found items for the current chat
                        current_chat_found = False
                        
                        # Process each history item with token usage
                        for item in history:
                            if "usage" in item and isinstance(item["usage"], dict):
                                usage = item["usage"]
                                # Extract timestamp or use current time if not available
                                timestamp = item.get("timestamp", time.time())
                                if isinstance(timestamp, (int, float)):
                                    timestamp = datetime.fromtimestamp(timestamp)
                                else:
                                    timestamp = datetime.now()
                                    
                                # Format timestamp
                                formatted_time = timestamp.strftime("%H:%M:%S")
                                
                                # Extract token counts
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                completion_tokens = usage.get("completion_tokens", 0)
                                total_item_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                                model = usage.get("model", "unknown")
                                
                                # Check if this is from the current chat (most recent item for each agent)
                                # We identify the current chat as the most recent interactions across all agents
                                time_threshold = time.time() - 300  # Items in the last 5 minutes are considered current chat
                                if timestamp.timestamp() > time_threshold:
                                    current_chat_tokens += total_item_tokens
                                    current_chat_prompt_tokens += prompt_tokens
                                    current_chat_completion_tokens += completion_tokens
                                    current_chat_found = True
                                    
                                    # Add to current chat dataset
                                    current_chat_data.append({
                                        "agent": agent_type,
                                        "timestamp": formatted_time,
                                        "prompt_tokens": prompt_tokens,
                                        "completion_tokens": completion_tokens,
                                        "total_tokens": total_item_tokens,
                                        "model": model
                                    })
                                
                                # Update totals for all time
                                total_tokens_used += total_item_tokens
                                total_prompt_tokens += prompt_tokens
                                total_completion_tokens += completion_tokens
                                
                                # Add to all data dataset
                                all_token_data.append({
                                    "agent": agent_type,
                                    "timestamp": formatted_time,
                                    "prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens,
                                    "total_tokens": total_item_tokens,
                                    "model": model
                                })
                
                
                
                # 1. DISPLAY CURRENT CHAT STATISTICS FIRST
                st.markdown("### Current Chat Token Usage")
                if current_chat_data:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Tokens", f"{current_chat_tokens:,}")
                    with col2:
                        st.metric("Input Tokens", f"{current_chat_prompt_tokens:,}")
                    with col3:
                        st.metric("Output Tokens", f"{current_chat_completion_tokens:,}")
                    
                    # Show current chat agent breakdown
                    if len(current_chat_data) > 0:
                        current_df = pd.DataFrame(current_chat_data)
                        
                        # Group by agent for the current chat
                        current_agent_usage = current_df.groupby("agent").agg({
                            "prompt_tokens": "sum", 
                            "completion_tokens": "sum",
                            "total_tokens": "sum"
                        }).reset_index()
                        
                        # Plot token usage by agent for current chat
                        fig = px.bar(
                            current_agent_usage, 
                            x="agent", 
                            y=["prompt_tokens", "completion_tokens"],
                            title="Current Chat: Token Usage by Agent",
                            labels={"value": "Tokens", "agent": "Agent", "variable": "Token Type"},
                            color_discrete_map={"prompt_tokens": "#2ca02c", "completion_tokens": "#d62728"}
                        )
                        fig.update_layout(legend_title_text="Token Type")
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Show detailed table for current chat
                        with st.expander("Current Chat Details", expanded=False):
                            st.dataframe(
                                current_df.sort_values("timestamp", ascending=False),
                                use_container_width=True,
                                hide_index=True
                            )
                else:
                    st.info("No token data available for the current chat.")
                
                # 2. HISTORICAL DATA VISUALIZATIONS
                if all_token_data:
                    st.markdown("---")
                    st.markdown("### Historical Token Usage")
                    
                    df = pd.DataFrame(all_token_data)
                    st.markdown("---")
                    st.markdown("### Total Token Usage (All Time)")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Tokens Used", f"{total_tokens_used:,}")
                    with col2:
                        st.metric("Total Input Tokens", f"{total_prompt_tokens:,}")
                    with col3:
                        st.metric("Total Output Tokens", f"{total_completion_tokens:,}")
                    # Token usage by agent
                    agent_usage = df.groupby("agent").agg({
                        "prompt_tokens": "sum", 
                        "completion_tokens": "sum", 
                        "total_tokens": "sum"
                    }).reset_index()
                    
                    # Plot token usage by agent using Plotly
                    fig = px.bar(
                        agent_usage, 
                        x="agent", 
                        y=["prompt_tokens", "completion_tokens"],
                        title="Token Usage by Agent (All Time)",
                        labels={"value": "Tokens", "agent": "Agent", "variable": "Token Type"},
                        color_discrete_map={"prompt_tokens": "#1f77b4", "completion_tokens": "#ff7f0e"}
                    )
                    fig.update_layout(legend_title_text="Token Type")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Token usage by model if multiple models exist
                    if len(df["model"].unique()) > 1:
                        model_usage = df.groupby("model").agg({
                            "prompt_tokens": "sum", 
                            "completion_tokens": "sum", 
                            "total_tokens": "sum"
                        }).reset_index()
                        
                        fig = px.pie(
                            model_usage, 
                            values="total_tokens", 
                            names="model",
                            title="Token Distribution by Model (All Time)",
                            hole=0.3
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Timeline of token usage (for recent interactions)
                    last_n = min(10, len(df))  # Show at most last 10 interactions
                    recent_data = df.iloc[-last_n:].copy()
                    
                    st.subheader(f"Recent Token Usage Timeline (Last {last_n} interactions)")
                    fig = px.line(
                        recent_data,
                        x="timestamp", 
                        y="total_tokens",
                        color="agent",
                        markers=True,
                        title="Token Usage Over Time"
                    )
                    fig.update_layout(xaxis_title="Time", yaxis_title="Total Tokens")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show detailed token usage data in an expandable table
                    with st.expander("Detailed Token Usage Data (All Time)", expanded=False):
                        st.dataframe(
                            df.sort_values("timestamp", ascending=False),
                            use_container_width=True,
                            hide_index=True
                        )
                
                # 3. DISPLAY TOTAL STATISTICS AT THE BOTTOM

                
                # Display agent usage stats
                st.markdown("---")
                st.subheader("Agent Interaction Count")
                
                agent_counts = {}
                for agent_type in ["zene", "commet", "finn", "milo", "thalia", "mara", "inka"]:
                    if agent_type in st.session_state.conversation_agent.output_histories:
                        count = len(st.session_state.conversation_agent.output_histories[agent_type])
                        agent_counts[agent_type] = count
                
                if agent_counts:
                    # Create a horizontal bar chart for agent usage count
                    fig = go.Figure(go.Bar(
                        y=list(agent_counts.keys()),
                        x=list(agent_counts.values()),
                        orientation='h',
                        marker=dict(
                            color=['rgba(25, 125, 225, 0.6)' if x != max(agent_counts.values()) 
                                  else 'rgba(225, 50, 50, 0.6)' for x in agent_counts.values()]
                        )
                    ))
                    fig.update_layout(
                        title="Number of Interactions by Agent",
                        xaxis_title="Interaction Count",
                        yaxis_title="Agent"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No agent interaction data available yet.")
            else:
                st.info("No token usage data available yet. Start a conversation to see token usage statistics.")

# Footer
st.markdown("---")
st.markdown("Mioo UPSC Assistant © 2024 | Powered by OpenAI and Google Gemini")