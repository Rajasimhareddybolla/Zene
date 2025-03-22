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
    page_title="SnowBlaze AI Assistant",
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
if 'current_agent_type' not in st.session_state:
    st.session_state.current_agent_type = "zene"
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gpt-4o"

# App title and description
st.title("🧠 SnowBlaze AI Assistant")
st.markdown("Have a conversation with multiple AI agents, powered by OpenAI's language models")

# User ID selection at the top of the app
st.sidebar.header("User Identification")
if st.sidebar.checkbox("Use custom User ID", False):
    custom_user_id = st.sidebar.text_input("Enter Custom User ID", value=st.session_state.user_id)
    if custom_user_id != st.session_state.user_id:
        st.session_state.user_id = custom_user_id
        st.session_state.conversation_agent = SnowBlaze(user_id=custom_user_id)
        st.sidebar.success(f"User ID set to: {custom_user_id}")

# Display current user ID
st.sidebar.info(f"Current User ID: {st.session_state.user_id}")

# Agent selector - Updated to include all agent types
st.sidebar.header("Agent Selection")
agent_options = ["zene", "commet", "finn", "milo", "thalia", "auto"]
selected_agent = st.sidebar.selectbox(
    "Select Agent", 
    options=agent_options,
    index=agent_options.index(st.session_state.current_agent_type) if st.session_state.current_agent_type in agent_options else 0,
    help="Choose which agent to converse with"
)

if selected_agent != st.session_state.current_agent_type:
    st.session_state.current_agent_type = selected_agent
    st.sidebar.success(f"Switched to {selected_agent} agent")

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
        agent_type = st.session_state.current_agent_type
        if agent_type == "auto":
            st.session_state.conversation_agent.delete_conversation("all")
        else:
            st.session_state.conversation_agent.delete_conversation(agent_type)
        st.session_state.chat_history = []
        st.success(f"Conversation cleared for {agent_type}!")
    
    # Process the query when submitted
    if submit_button and user_input:
        with st.spinner('Processing your message...'):
            try:
                # Process the message
                start_time = time.time()
                
                # Determine which agent to use and store this for display
                active_agent_type = st.session_state.current_agent_type
                
                if active_agent_type == "auto":
                    # Add user message to chat history
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_input,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    
                    # Use the __call__ method to handle the entire agent workflow
                    full_response = st.session_state.conversation_agent(user_input)
                    
                    # Get information about which agents were used
                    agents_used = []
                    
                    # Check output histories to see which agents were used
                    for agent_type in ["zene", "commet", "finn", "milo", "thalia"]:
                        history = st.session_state.conversation_agent.output_histories[agent_type]
                        if history and history[-1].get("query") == user_input:
                            agents_used.append(agent_type)
                            agent_output = history[-1]
                            processing_time = agent_output.get("latency_seconds", 0)
                            
                            # Extract response content for this agent
                            response_content = None
                            try:
                                if "response" in agent_output:
                                    response_content = json.loads(agent_output["response"])
                                else:
                                    response_content = agent_output.get("response", {})
                            except:
                                response_content = agent_output.get("response", "")
                            
                            # Add to chat history
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "agent_type": agent_type,
                                "content": response_content,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "usage": agent_output.get("usage", {}),
                                "processing_time": processing_time,
                                "raw_output": agent_output,
                                "routed_from": "auto_flow"  # Mark as part of auto flow
                            })
                    
                    # If no agents were tracked (unlikely), add the final response
                    if not agents_used:
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "agent_type": "unknown",
                            "content": full_response,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "usage": {},
                            "processing_time": time.time() - start_time,
                            "raw_output": {}
                        })
                    
                else:
                    # Use a specific agent
                    response_str = st.session_state.conversation_agent.get_agent_response(
                        active_agent_type, 
                        user_input,
                        model_name="o3-mini" if active_agent_type == "thalia" else st.session_state.selected_model
                    )
                    
                    # Parse the response
                    try:
                        response_json = json.loads(response_str)
                    except json.JSONDecodeError:
                        response_json = {"response": response_str}
                    
                    # The actual agent is the one we specified
                    actual_agent_type = active_agent_type
                    
                    # Get the latest output for this agent
                    latest_output = {}
                    if st.session_state.conversation_agent.output_histories[active_agent_type]:
                        latest_output = st.session_state.conversation_agent.output_histories[active_agent_type][-1]
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    # Get usage directly from the output history for the correct agent
                    latest_usage = latest_output.get("usage", {})
                    
                    # Add to chat history with the correct agent type
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_input,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "agent_type": actual_agent_type,  # Use the actual agent that responded
                        "content": response_json,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "usage": latest_usage,
                        "processing_time": processing_time,
                        "raw_output": latest_output  # Store the full raw output for reference
                    })
                
            except Exception as e:
                st.error(f"Error processing message: {str(e)}")
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
    
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
    }
    .zene-message {
        border-left: 5px solid #2e8b57;
    }
    .commet-message {
        border-left: 5px solid #9932cc;
    }
    .finn-message {
        border-left: 5px solid #ff4500;
    }
    .milo-message {
        border-left: 5px solid #1e90ff;
    }
    .thalia-message {
        border-left: 5px solid #ff69b4;
    }
    .unknown-message {
        border-left: 5px solid #ff7f50;
    }
    .routing-indicator {
        background-color: #ffffe0;
        padding: 5px;
        border-radius: 5px;
        margin: 5px 0;
        font-size: 0.8em;
        border-left: 5px solid #ffa500;
    }
    .token-usage {
        font-size: 0.8em;
        color: #666;
        margin-top: 5px;
        padding-top: 5px;
        border-top: 1px dashed #ccc;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader("Conversation")
    
    if not st.session_state.chat_history:
        st.info("No messages yet. Start a conversation by sending a message!")
    else:
        chat_container = st.container()
        with chat_container:
            # Track when to show routing indicators
            show_routing = False
            routed_from = None
            
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You ({message["timestamp"]}):</strong><br>
                        {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                    # Reset routing indicators for new user message
                    show_routing = False
                    routed_from = None
                else:
                    # For assistant messages, display the content
                    content_display = message["content"]
                    
                    # Get the actual agent type that responded
                    agent_type = message.get("agent_type", "unknown")
                    agent_class = f"{agent_type}-message"
                    
                    # Check if this message was routed from another agent
                    if "routed_from" in message:
                        show_routing = True
                        routed_from = message["routed_from"]
                    
                    # Show routing indicator if needed
                    if show_routing and routed_from and routed_from == agent_type:
                        routing_to = ""
                        if isinstance(content_display, dict) and "next_agent" in content_display:
                            routing_to = content_display["next_agent"]
                            st.markdown(f"""
                            <div class="routing-indicator">
                                <strong>🔄 Routing:</strong> {agent_type.capitalize()} determined this request should be handled by {routing_to.capitalize()}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Get token usage for this message
                    usage = message.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    latency = usage.get("latency_seconds", 0)
                    
                    # Format the display
                    if isinstance(content_display, dict):
                        # For JSON responses, extract the main content fields for display
                        main_content = ""
                        
                        # Show any routing info first if this is the router agent
                        if "next_agent" in content_display:
                            if agent_type == "zene":
                                main_content += f"<p><strong>Routing decision:</strong> Passing to {content_display['next_agent']} agent</p>"
                        
                        if "response" in content_display:
                            main_content += f"<p><strong>Response:</strong> {content_display['response']}</p>"
                        
                        # Include agent-specific information
                        if agent_type == "zene":
                            if "user_intent" in content_display:
                                main_content += f"<p><strong>Intent:</strong> {content_display['user_intent']}</p>"
                            if "vector_database_retrieval_queries" in content_display:
                                main_content += f"<p><strong>Retrieval queries:</strong> {', '.join(content_display['vector_database_retrieval_queries'][:2])}...</p>"
                        
                        if agent_type == "finn":
                            if "section_250_word_report" in content_display:
                                main_content += f"<p><strong>Report:</strong> {content_display['section_250_word_report']}</p>"
                        
                        if agent_type == "milo" or agent_type == "thalia":
                            if "response" in content_display:
                                main_content += f"<p><strong>Response:</strong> {content_display['response']}</p>"
                            
                        if "explanation" in content_display:
                            main_content += f"<p><strong>Explanation:</strong> {content_display['explanation']}</p>"
                            
                        # Add expand/collapse for full JSON
                        full_json = f"```json\n{json.dumps(content_display, indent=2)}\n```"
                        
                        # Use the extracted content instead of raw JSON by default
                        content_display = main_content
                        
                        # Add expand/collapse for full JSON
                        content_display += f"""
                        <details>
                            <summary>View full response</summary>
                            {full_json}
                        </details>
                        """
                    
                    # Add token usage info
                    token_usage_info = f"""
                        <div class="token-usage">
                        Token usage {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total (Latency: {latency:.2f}s)
                        </div>
                    """
                    
                    # Show a note if this was a response from being routed
                    routed_note = ""
                    if "routed_from" in message:
                        if message["routed_from"] == "auto_flow":
                            routed_note = f"<span style='color: #ff6600;'>(Auto Flow)</span> "
                        else:
                            routed_note = f"<span style='color: #ff6600;'>(Routed from {message['routed_from'].capitalize()})</span> "
                    
                    st.markdown(f"""
                    <div class="assistant-message {agent_class}">
                        <strong>{agent_type.capitalize()} {routed_note}({message["timestamp"]}):</strong><br>
                        {content_display}
                        {token_usage_info}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Option to save conversation
            if st.button("💾 Save Conversation"):
                try:
                    st.session_state.conversation_agent.save_conversation(
                        agent_type="all"  # Save all agent conversations
                    )
                    st.success(f"Conversation saved successfully for all agents!")
                except Exception as e:
                    st.error(f"Error saving conversation: {str(e)}")

with col2:
    # Create tabs for different details
    tabs = st.tabs(["Token Usage", "Response Analysis", "Settings"])
    
    # Token Usage Tab
    with tabs[0]:
        st.header("Token Usage Statistics")
        
        # Get token usage by agent
        if st.session_state.conversation_agent:
            # Show usage breakdown by agent
            st.subheader("Usage by Agent")
            
            # Create a tab for each agent
            agent_tabs = st.tabs(["Zene", "Commet", "Finn", "Milo", "Thalia", "Combined"])
            
            # Prepare data for each agent
            agent_data = {}
            for agent_type in ["zene", "commet", "finn", "milo", "thalia"]:
                agent_totals = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "latency_seconds": 0,
                    "calls": 0
                }
                
                # Get the latest message for this agent
                latest_output = None
                output_history = st.session_state.conversation_agent.output_histories.get(agent_type, [])
                
                if output_history:
                    latest_output = output_history[-1]
                    # Calculate totals
                    for item in output_history:
                        usage = item.get("usage", {})
                        agent_totals["prompt_tokens"] += usage.get("prompt_tokens", 0)
                        agent_totals["completion_tokens"] += usage.get("completion_tokens", 0)
                        agent_totals["total_tokens"] += usage.get("total_tokens", 0)
                        agent_totals["latency_seconds"] += usage.get("latency_seconds", 0)
                        agent_totals["calls"] += 1
                
                agent_data[agent_type] = {
                    "totals": agent_totals,
                    "latest": latest_output
                }
            
            # Individual agent tabs
            for i, agent_type in enumerate(["zene", "commet", "finn", "milo", "thalia"]):
                with agent_tabs[i]:
                    agent_info = agent_data[agent_type]
                    totals = agent_info["totals"]
                    latest = agent_info["latest"]
                    
                    if latest:
                        st.subheader(f"Latest {agent_type.capitalize()} Message")
                        latest_usage = latest.get("usage", {})
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Prompt Tokens", f"{latest_usage.get('prompt_tokens', 0):,}")
                        with col2:
                            st.metric("Completion Tokens", f"{latest_usage.get('completion_tokens', 0):,}")
                        with col3:
                            st.metric("Total Tokens", f"{latest_usage.get('total_tokens', 0):,}")
                        
                        st.metric("Latency", f"{latest_usage.get('latency_seconds', 0):.2f}s")
                        
                        # Show the query that generated this response
                        if "query" in latest:
                            with st.expander("Last Query"):
                                st.write(latest["query"])
                    
                    st.subheader(f"{agent_type.capitalize()} Cumulative Stats")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Tokens", f"{totals['total_tokens']:,}")
                    with col2:
                        st.metric("API Calls", totals['calls'])
                    with col3:
                        avg_latency = totals['latency_seconds'] / totals['calls'] if totals['calls'] > 0 else 0
                        st.metric("Avg Latency", f"{avg_latency:.2f}s")
            
            # Combined Tab
            with agent_tabs[5]:
                # Calculate combined totals
                combined_totals = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "calls": 0,
                    "latency_seconds": 0
                }
                
                for agent_type in agent_data:
                    agent_totals = agent_data[agent_type]["totals"]
                    combined_totals["prompt_tokens"] += agent_totals["prompt_tokens"]
                    combined_totals["completion_tokens"] += agent_totals["completion_tokens"] 
                    combined_totals["total_tokens"] += agent_totals["total_tokens"]
                    combined_totals["calls"] += agent_totals["calls"]
                    combined_totals["latency_seconds"] += agent_totals["latency_seconds"]
                
                st.subheader("Combined Statistics")
                col_total, col_prompt, col_completion = st.columns(3)
                with col_total:
                    st.metric("Total Tokens", f"{combined_totals['total_tokens']:,}")
                with col_prompt:
                    st.metric("Prompt Tokens", f"{combined_totals['prompt_tokens']:,}")
                with col_completion:
                    st.metric("Completion Tokens", f"{combined_totals['completion_tokens']:,}")
                
                # Show latency metrics
                avg_latency = combined_totals["latency_seconds"] / combined_totals["calls"] if combined_totals["calls"] > 0 else 0
                
                col_latency, col_calls = st.columns(2)
                with col_latency:
                    st.metric("Avg Latency", f"{avg_latency:.2f}s")
                with col_calls:
                    st.metric("API Calls", combined_totals["calls"])
                
                # Show token distribution chart
                if combined_totals["calls"] > 0:
                    # Agent comparison chart
                    st.subheader("Token Usage by Agent")
                    agent_comparison = pd.DataFrame({
                        'Agent': ['Zene', 'Commet', 'Finn', 'Milo', 'Thalia'],
                        'Tokens': [
                            agent_data["zene"]["totals"]["total_tokens"],
                            agent_data["commet"]["totals"]["total_tokens"],
                            agent_data["finn"]["totals"]["total_tokens"],
                            agent_data["milo"]["totals"]["total_tokens"],
                            agent_data["thalia"]["totals"]["total_tokens"]
                        ]
                    })
                    st.bar_chart(agent_comparison.set_index('Agent'))
                    
                    # Token type distribution
                    st.subheader("Token Distribution")
                    token_df = pd.DataFrame({
                        'Type': ['Prompt Tokens', 'Completion Tokens'],
                        'Count': [combined_totals['prompt_tokens'], combined_totals['completion_tokens']]
                    })
                    st.bar_chart(token_df.set_index('Type'))
        else:
            st.info("No usage data available yet.")
    
    # Response Analysis Tab
    with tabs[1]:
        st.header("Response Analysis")
        
        if st.session_state.chat_history and any(msg["role"] == "assistant" for msg in st.session_state.chat_history):
            # Get all assistant responses for the most recent user query
            latest_user_msg_idx = max([i for i, msg in enumerate(st.session_state.chat_history) if msg["role"] == "user"])
            latest_responses = [msg for i, msg in enumerate(st.session_state.chat_history) 
                               if i > latest_user_msg_idx and msg["role"] == "assistant"]
            
            if latest_responses:
                st.subheader("Latest Conversation Flow")
                
                # Show information about each agent in the flow
                for i, response in enumerate(latest_responses):
                    agent_type = response.get("agent_type", "unknown")
                    
                    # Show a divider between agents
                    if i > 0:
                        st.markdown("⬇️ **Next in flow** ⬇️")
                    
                    # Create a colored box for each agent
                    agent_colors = {
                        "zene": "#2e8b57",
                        "commet": "#9932cc",
                        "finn": "#ff4500",
                        "milo": "#1e90ff",
                        "thalia": "#ff69b4",
                        "unknown": "#ff7f50"
                    }
                    agent_color = agent_colors.get(agent_type, "#ff7f50")
                    
                    st.markdown(f"""
                    <div style="background-color: {agent_color}20; padding: 10px; border-radius: 5px; border-left: 5px solid {agent_color};">
                        <h3 style="color: {agent_color};">{agent_type.capitalize()} Agent</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show processing time
                    st.info(f"Processing time: {response.get('processing_time', 0):.2f} seconds")
                    
                    # Show token usage
                    usage = response.get("usage", {})
                    st.write(f"**Token Usage:** {usage.get('prompt_tokens', 0):,} prompt + {usage.get('completion_tokens', 0):,} completion = {usage.get('total_tokens', 0):,} total")
                    
                    # Extract key details
                    content = response["content"] if isinstance(response["content"], dict) else {}
                    
                    if agent_type == "zene":
                        if "user_intent" in content:
                            st.success(f"Detected intent: {content['user_intent']}")
                        if "next_agent" in content:
                            st.warning(f"Routing decision: Send to {content['next_agent']} agent")
                        if "vector_database_retrieval_queries" in content:
                            st.info("Vector database queries:")
                            for q in content["vector_database_retrieval_queries"][:3]:
                                st.markdown(f"- {q}")
                    
                    if agent_type == "finn":
                        if "section_250_word_report" in content:
                            st.subheader("Knowledge Report")
                            st.write(content["section_250_word_report"])
                    
                    if agent_type in ["milo", "thalia"]:
                        if "response" in content:
                            st.subheader("Response")
                            st.write(content["response"])
                    
                    if "explanation" in content:
                        st.subheader("Analysis")
                        st.write(content["explanation"])
                    
                    # Show raw JSON if needed
                    with st.expander("View Raw JSON", expanded=False):
                        st.json(content)
            else:
                st.info("No responses to analyze yet. Start a conversation to see analysis.")
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
        
        # Agent settings
        st.subheader("Agent Settings")
        agent_type = st.session_state.current_agent_type
        
        if st.button("Reset Conversation"):
            if agent_type == "auto":
                # In auto mode, prompt for which agent to reset
                reset_all = st.checkbox("Reset all agents?", value=True)
                if reset_all:
                    for agent in ["zene", "commet", "finn", "milo", "thalia"]:
                        st.session_state.conversation_agent.reset_and_summarize_conversation(agent)
                    st.success("Reset and summarized all agent conversations")
                else:
                    agent_to_reset = st.selectbox("Which agent to reset?", ["zene", "commet", "finn", "milo", "thalia"])
                    summary = st.session_state.conversation_agent.reset_and_summarize_conversation(agent_to_reset)
                    st.success(f"Reset and summarized {agent_to_reset} conversation")
                    st.info(f"Summary: {summary}")
            else:
                # Reset specific agent
                summary = st.session_state.conversation_agent.reset_and_summarize_conversation(agent_type)
                st.success(f"Reset and summarized {agent_type} conversation")
                st.info(f"Summary: {summary}")
        
        # Add option to display raw JSON in conversation
        st.subheader("Display Settings")
        if 'show_raw_json' not in st.session_state:
            st.session_state.show_raw_json = True
        st.session_state.show_raw_json = st.checkbox(
            "Show raw JSON responses", 
            value=st.session_state.show_raw_json,
            help="Display the complete JSON response in the conversation"
        )
        
        # Model settings - updated to include o3-mini
        st.subheader("Model Settings")
        model_options = ["gpt-4o", "gpt-4o-mini", "o3-mini"]
        selected_model = st.selectbox(
            "Select Model", 
            options=model_options,
            index=model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0,
            help="Choose the OpenAI model to use for responses (Note: Thalia always uses o3-mini)"
        )
        if st.button("Update Model"):
            st.session_state.selected_model = selected_model
            st.success(f"Model updated to {selected_model}")
            st.info("This will apply to your next message")
        
        # Database operations
        st.subheader("Database Operations")
        if st.button("Delete All Conversations"):
            # Confirm dangerous operation
            confirm = st.checkbox("Confirm deletion of all conversations?")
            if confirm:
                st.session_state.conversation_agent.delete_conversation("all")
                st.session_state.chat_history = []
                st.success("All conversations deleted from database")
                st.experimental_rerun()
        
        # About section
        st.subheader("About")
        st.markdown("""
        **SnowBlaze AI Assistant** is powered by OpenAI's models through the SnowBlaze framework.
        
        - Built using Streamlit
        - Supports multiple agent types:
          - Zene: Main router agent
          - Commet: Complex messaging agent
          - Finn: Knowledge retrieval agent
          - Milo: Content generation agent
          - Thalia: Lightweight response agent (uses o3-mini model)
        - Uses JSON response format
        - Tracks token usage and conversation history
        """)

# Add footer
st.markdown("---")
st.markdown("SnowBlaze AI Assistant © 2023 | Powered by OpenAI")
