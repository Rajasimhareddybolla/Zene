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
    format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Mioo Upsc Tutor",
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
                    
                    # Store the full response in session state for display
                    if 'full_call_response' not in st.session_state:
                        st.session_state.full_call_response = {}
                    st.session_state.full_call_response = full_response
                    
                    # Get information about which agents were used
                    agents_used = []
                    
                    # Improved processing of agent responses
                    # First check if Zene was used (always the first agent in auto flow)
                    zene_history = st.session_state.conversation_agent.output_histories.get("zene", [])
                    if zene_history and len(zene_history) > 0 and zene_history[-1].get("query") == user_input:
                        agents_used.append("zene")
                        agent_output = zene_history[-1]
                        processing_time = agent_output.get("latency_seconds", 0)
                        
                        # Extract and process Zene's response
                        try:
                            if isinstance(agent_output["response"], str):
                                response_content = json.loads(agent_output["response"])
                            else:
                                response_content = agent_output["response"]
                            
                            # Add Zene's response to chat history
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "agent_type": "zene",
                                "content": response_content,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "usage": agent_output.get("usage", {}),
                                "processing_time": processing_time,
                                "raw_output": agent_output
                            })
                            
                            # Extract the next agent from Zene's response
                            next_agent = response_content.get("next_agent", "").lower()
                        except Exception as e:
                            logger.error(f"Error processing Zene response: {str(e)}")
                            next_agent = None
                    
                    # Now process Finn if queries were generated by Zene
                    finn_history = st.session_state.conversation_agent.output_histories.get("finn", [])
                    if finn_history and len(finn_history) > 0:
                        # Find Finn responses related to this user input (might be multiple)
                        recent_finn_responses = [item for item in finn_history if 
                                                item.get("timestamp", 0) > time.time() - 30]  # Within last 30 seconds
                        
                        if recent_finn_responses:
                            agents_used.append("finn")
                            
                            for finn_output in recent_finn_responses:
                                try:
                                    if isinstance(finn_output["response"], str):
                                        finn_content = json.loads(finn_output["response"])
                                    else:
                                        finn_content = finn_output["response"]
                                    
                                    # Add Finn's response to chat history
                                    st.session_state.chat_history.append({
                                        "role": "assistant",
                                        "agent_type": "finn",
                                        "content": finn_content,
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "usage": finn_output.get("usage", {}),
                                        "processing_time": finn_output.get("latency_seconds", 0),
                                        "raw_output": finn_output,
                                        "routed_from": "zene"
                                    })
                                except Exception as e:
                                    logger.error(f"Error processing Finn response: {str(e)}")
                    
                    # Check if Commet, Milo, or Thalia were used after Zene
                    for agent_type in ["commet", "milo", "thalia"]:
                        agent_history = st.session_state.conversation_agent.output_histories.get(agent_type, [])
                        if agent_history and len(agent_history) > 0 and agent_history[-1].get("query") and user_input in agent_history[-1].get("query"):
                            agents_used.append(agent_type)
                            agent_output = agent_history[-1]
                            processing_time = agent_output.get("latency_seconds", 0)
                            
                            # Extract response content for this agent
                            try:
                                if isinstance(agent_output["response"], str):
                                    response_content = json.loads(agent_output["response"])
                                else:
                                    response_content = agent_output["response"]
                                
                                # Add to chat history with clear indication it was routed from Zene
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "agent_type": agent_type,
                                    "content": response_content,
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "usage": agent_output.get("usage", {}),
                                    "processing_time": processing_time,
                                    "raw_output": agent_output,
                                    "routed_from": "zene"  # Mark as routed from Zene
                                })
                            except Exception as e:
                                logger.error(f"Error processing {agent_type} response: {str(e)}")
                    
                    # If no agents were used or something went wrong, add the raw response
                    if not agents_used:
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "agent_type": "unknown",
                            "content": {"response": str(full_response)},
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "usage": {},
                            "processing_time": time.time() - start_time,
                            "raw_output": full_response
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
    
    # Display chat history with improved styling
    st.markdown("""
    <style>
    .user-message {
        background-color: #e6f7ff;
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #1e90ff;
    }
    .assistant-message {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
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
    .agent-header {
        background-color: #f8f9fa;
        padding: 5px 10px;
        border-radius: 5px 5px 0 0;
        font-weight: bold;
        margin-bottom: -5px;
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
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You ({message["timestamp"]}):</strong><br>
                        {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # For assistant messages, display the content
                    content_display = message["content"]
                    
                    # Get the actual agent type that responded
                    agent_type = message.get("agent_type", "unknown")
                    agent_class = f"{agent_type}-message"
                    
                    # Prepare routing indicator if this was part of a flow
                    routing_note = ""
                    if "routed_from" in message:
                        routed_from = message["routed_from"]
                        routing_note = f"""
                        <div class="routing-indicator">
                            <strong>🔄 Flow:</strong> This response from {agent_type.capitalize()} was triggered by {routed_from.capitalize()}
                        </div>
                        """
                    
                    # Format the display based on agent type
                    if isinstance(content_display, dict):
                        # For JSON responses, extract the main content fields for display
                        main_content = ""
                        
                        # Show any routing info first if this is Zene (router agent)
                        if "next_agent" in content_display and agent_type == "zene":
                            main_content += f"<p><strong>Routing decision:</strong> Passing to {content_display['next_agent']} agent</p>"
                        
                        if agent_type == "zene":
                            if "user_intent" in content_display:
                                main_content += f"<p><strong>Intent:</strong> {content_display['user_intent']}</p>"
                            if "vector_database_retrieval_queries" in content_display:
                                main_content += f"<p><strong>Retrieval queries:</strong> {', '.join(content_display['vector_database_retrieval_queries'][:2])}...</p>"
                        
                        if agent_type == "finn":
                            if "section_250_word_report" in content_display:
                                main_content += f"<p><strong>Report:</strong> {content_display['section_250_word_report']}</p>"
                        
                        if agent_type in ["milo", "thalia", "commet"]:
                            if "response" in content_display:
                                main_content += f"<p><strong>Response:</strong> {content_display['response']}</p>"
                            
                        if "explanation" in content_display:
                            main_content += f"<p><strong>Explanation:</strong> {content_display['explanation']}</p>"
                        
                        # Fallback for any agent if response field exists
                        if main_content == "" and "response" in content_display:
                            main_content += f"<p>{content_display['response']}</p>"
                            
                        # If still no content extracted, show raw JSON
                        if main_content == "":
                            main_content = f"<pre>{json.dumps(content_display, indent=2)}</pre>"
                            
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
                    elif isinstance(content_display, str):
                        # For plain string responses, display directly
                        content_display = f"<p>{content_display}</p>"
                    
                    # Get token usage info
                    usage = message.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    processing_time = message.get("processing_time", 0)
                    
                    # Add token usage info
                    token_usage_info = f"""
                        <div class="token-usage">
                        Token usage: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total
                        (Processing time: {processing_time:.2f}s)
                        </div>
                    """
                    
                    # Create a more distinct header for each agent
                    agent_header = f"""
                    <div class="agent-header" style="background-color: {
                        '#e8f5e9' if agent_type == 'zene' else
                        '#f3e5f5' if agent_type == 'commet' else
                        '#fff3e0' if agent_type == 'finn' else
                        '#e3f2fd' if agent_type == 'milo' else
                        '#fce4ec' if agent_type == 'thalia' else
                        '#fff3cd'
                    }">
                        <span style="color: {
                            '#2e8b57' if agent_type == 'zene' else
                            '#9932cc' if agent_type == 'commet' else
                            '#ff4500' if agent_type == 'finn' else
                            '#1e90ff' if agent_type == 'milo' else
                            '#ff69b4' if agent_type == 'thalia' else
                            '#ff7f50'
                        };">
                        <strong>{agent_type.upper()}</strong>
                        </span> ({message["timestamp"]})
                    </div>
                    """
                    
                    st.markdown(f"""
                    {agent_header}
                    <div class="assistant-message {agent_class}">
                        {routing_note}
                        {content_display}
                        {token_usage_info}
                    </div>
                    """, unsafe_allow_html=True)

with col2:
    # Create tabs for different details
    tabs = st.tabs(["Token Usage", "Response Analysis", "Call Response", "Settings"])
    
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
    
    # Add Call Response Tab
    with tabs[2]:
        st.header("__call__ Method Response")
        
        if 'full_call_response' in st.session_state and st.session_state.full_call_response:
            st.subheader("Raw Response from __call__ Method")
            st.json(st.session_state.full_call_response)
            
            # Check if specific agent responses exist in the full response
            if isinstance(st.session_state.full_call_response, dict):
                for agent_type in ["finn", "milo", "thalia"]:
                    if agent_type in st.session_state.full_call_response:
                        st.subheader(f"{agent_type.capitalize()} Agent Response")
                        st.json(st.session_state.full_call_response[agent_type])
        else:
            st.info("No call response available yet. Start a conversation in auto mode to see the raw response.")
    
    # Settings Tab (now tab 3)
    with tabs[3]:
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
st.markdown("SnowBlaze AI Assistant © 2025 | Powered by Humans")

# Add debugging section at the bottom of the app
st.expander("Debug Information", expanded=False).write("""
This section shows debugging information about agent interactions.

### Common Issues:
1. If finn, milo, or thalia agents aren't working, check their output in the "Call Response" tab
2. Verify that the responses are proper JSON format
3. Check that the model being used is appropriate for each agent

For detailed logs, check the console where this Streamlit app is running.
""")