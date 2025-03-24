import streamlit as st
import json
import time
import pandas as pd
import altair as alt
import os
from main_gemini import Mioo as SnowBlaze
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SnowBlaze AI Assistant",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1E3A8A;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .agent-tag {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        color: white;
        font-weight: 600;
        font-size: 0.8rem;
        margin-right: 0.5rem;
    }
    .zene-tag {
        background-color: #2563EB;
    }
    .commet-tag {
        background-color: #7C3AED;
    }
    .finn-tag {
        background-color: #10B981;
    }
    .milo-tag {
        background-color: #F59E0B;
    }
    .thalia-tag {
        background-color: #EC4899;
    }
    .user-tag {
        background-color: #6B7280;
    }
    .chat-message {
        margin-bottom: 1rem;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .user-message {
        background-color: #F3F4F6;
    }
    .assistant-message {
        background-color: #EFF6FF;
        border-left: 3px solid #2563EB;
    }
    .metrics-container {
        background-color: #F9FAFB;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
    .token-metrics {
        display: flex;
        justify-content: space-between;
        margin-top: 0.5rem;
    }
    .flow-message {
        margin-bottom: 0.5rem;
        padding: 0.5rem;
        border-radius: 0.3rem;
        border-left: 3px solid #6B7280;
    }
    .stProgress > div > div {
        background-color: #2563EB;
    }
    /* Hide hamburger menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conversation_flow' not in st.session_state:
    st.session_state.conversation_flow = []
if 'token_usage' not in st.session_state:
    st.session_state.token_usage = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0,
        'history': []
    }
if 'snowblaze' not in st.session_state:
    # Initialize with a UUID if you want to persist conversation between sessions
    user_id = f"user_{int(time.time())}"
    st.session_state.snowblaze = SnowBlaze(user_id=user_id)
if 'show_details_panel' not in st.session_state:
    st.session_state.show_details_panel = True

# Create a details panel toggle button
if st.button("Toggle Details Panel", key="toggle_details"):
    st.session_state.show_details_panel = not st.session_state.show_details_panel

# Sidebar
with st.sidebar:
    st.markdown("<div class='main-header'>SnowBlaze AI</div>", unsafe_allow_html=True)
    st.markdown("An advanced AI assistant powered by OpenAI and Gemini.")
    
    
    st.markdown("<div class='sub-header'>Agents</div>", unsafe_allow_html=True)
    st.markdown("""
    <div><span class='agent-tag zene-tag'>Zene</span> - Primary router agent</div>
    <div><span class='agent-tag commet-tag'>Commet</span> - Complex inquiry handler</div>
    <div><span class='agent-tag finn-tag'>Finn</span> - Knowledge retrieval agent</div>
    <div><span class='agent-tag milo-tag'>Milo</span> - Content generation agent</div>
    <div><span class='agent-tag thalia-tag'>Thalia</span> - Creative assistant</div>
    """, unsafe_allow_html=True)
    
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.conversation_flow = []
        st.session_state.token_usage['history'] = []
        for agent_type in ['zene', 'commet', 'finn', 'milo', 'thalia']:
            st.session_state.snowblaze.delete_conversation(agent_type)
        st.experimental_rerun()

# Main layout - split into two columns if details panel is shown
if st.session_state.show_details_panel:
    main_col, details_col = st.columns([3, 2])
else:
    main_col = st.container()

# Main chat area
with main_col:
    st.markdown("<div class='main-header'>SnowBlaze AI Assistant</div>", unsafe_allow_html=True)
    
    # Chat messages display
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                # Try to parse JSON if it's in JSON format
                try:
                    content = json.loads(message["content"])
                    if "response" in content:
                        st.markdown(content["response"])
                    else:
                        st.json(content)
                except:
                    st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Display typing indicator while processing
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                message_placeholder = st.empty()
                
                # Process with SnowBlaze
                start_time = time.time()
                response, conversation_flow = st.session_state.snowblaze(prompt)
                processing_time = time.time() - start_time
                
                # Update conversation flow
                st.session_state.conversation_flow = conversation_flow
                
                # Calculate token usage from the conversation flow
                tokens_used = {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'query': prompt,
                    'latency': processing_time
                }
                
                # Process conversation flow to extract token usage for each agent
                for step in conversation_flow:
                    if step.get('role') in ['zene', 'commet', 'finn', 'milo', 'thalia']:
                        try:
                            if isinstance(step['content'], str):
                                content = json.loads(step['content'])
                            else:
                                content = step['content']
                                
                            # Extract usage from output_histories
                            agent_type = step.get('role')
                            if agent_type in st.session_state.snowblaze.output_histories:
                                histories = st.session_state.snowblaze.output_histories[agent_type]
                                if histories and isinstance(histories[-1], dict):
                                    usage_data = histories[-1].get('usage', {})
                                    tokens_used['prompt_tokens'] += usage_data.get('prompt_tokens', 0)
                                    tokens_used['completion_tokens'] += usage_data.get('completion_tokens', 0)
                                    tokens_used['total_tokens'] += usage_data.get('total_tokens', 0)
                        except Exception as e:
                            st.error(f"Error processing token usage: {e}")
                
                # Update total token usage
                st.session_state.token_usage['prompt_tokens'] += tokens_used['prompt_tokens']
                st.session_state.token_usage['completion_tokens'] += tokens_used['completion_tokens']
                st.session_state.token_usage['total_tokens'] += tokens_used['total_tokens']
                st.session_state.token_usage['history'].append(tokens_used)
                
                # Display the response
                if isinstance(response, dict):
                    formatted_response = json.dumps(response, indent=2)
                    message_placeholder.json(response)
                else:
                    formatted_response = str(response)
                    message_placeholder.markdown(formatted_response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": formatted_response})

# Details panel (right side) - only shown if show_details_panel is True
if st.session_state.show_details_panel:
    with details_col:
        # Create tabs for different details
        tabs = st.tabs(["Token Usage", "Agent Flow", "Conversation Analysis"])
        
        # Token Usage Tab
        with tabs[0]:
            st.subheader("Token Usage Statistics")
            
            # Current interaction metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tokens", f"{st.session_state.token_usage['total_tokens']:,}")
            with col2:
                st.metric("Prompt Tokens", f"{st.session_state.token_usage['prompt_tokens']:,}")
            with col3:
                st.metric("Completion Tokens", f"{st.session_state.token_usage['completion_tokens']:,}")
            
            # Agent usage breakdown
            if st.session_state.snowblaze:
                st.subheader("Agent Usage")
                
                for agent_type in ["zene", "commet", "finn", "milo", "thalia"]:
                    if agent_type in st.session_state.snowblaze.output_histories:
                        interactions = len(st.session_state.snowblaze.output_histories[agent_type])
                        if interactions > 0:
                            st.write(f"**{agent_type.capitalize()}**: {interactions} interactions")
            
            # Token usage history chart
            if st.session_state.token_usage['history']:
                st.subheader("Token Usage History")
                
                # Create a DataFrame from token usage history
                token_df = pd.DataFrame(st.session_state.token_usage['history'])
                if not token_df.empty and len(token_df) > 1:
                    # Create a line chart
                    chart = alt.Chart(token_df).mark_line().encode(
                        x=alt.X('timestamp:O', title='Time'),
                        y=alt.Y('total_tokens:Q', title='Tokens'),
                        tooltip=['timestamp', 'query', 'total_tokens', 'prompt_tokens', 'completion_tokens', 'latency']
                    ).properties(
                        height=200
                    )
                    st.altair_chart(chart, use_container_width=True)
        
        # Agent Flow Tab
        with tabs[1]:
            st.subheader("Agent Conversation Flow")
            
            if st.session_state.conversation_flow:
                # Display flow path
                flow_path = " → ".join([step.get("role", "unknown").upper() for step in st.session_state.conversation_flow])
                st.success(f"Flow path: {flow_path}")
                
                # Show detailed flow
                for i, step in enumerate(st.session_state.conversation_flow):
                    role = step.get('role', 'unknown')
                    
                    # Determine tag class based on role
                    tag_class = f"{role}-tag" if role in ['zene', 'commet', 'finn', 'milo', 'thalia', 'user'] else "user-tag"
                    
                    with st.expander(f"{i+1}. {role.upper()} Step", expanded=i==0):
                        st.markdown(f"<span class='agent-tag {tag_class}'>{role.upper()}</span>", unsafe_allow_html=True)
                        
                        if role == 'user':
                            st.markdown(step.get('content', ''))
                        else:
                            try:
                                # Try to parse as JSON for better display
                                content = step.get('content', '')
                                json_content = json.loads(content) if isinstance(content, str) else content
                                st.json(json_content)
                            except:
                                st.markdown(step.get('content', ''))
            else:
                st.info("No agent flow data available. Start a conversation to see the flow.")
        
        # Conversation Analysis Tab
        with tabs[2]:
            st.subheader("Response Analysis")
            
            if st.session_state.conversation_flow:
                # Get the final agent that provided the response
                final_steps = [step for step in st.session_state.conversation_flow 
                              if step.get('role') in ['zene', 'commet', 'finn', 'milo', 'thalia']]
                
                if final_steps:
                    final_agent = final_steps[-1].get('role', 'unknown')
                    st.info(f"The final response was provided by the **{final_agent.upper()}** agent")
                    
                    # Latency information if available
                    if st.session_state.token_usage['history']:
                        latest_interaction = st.session_state.token_usage['history'][-1]
                        if 'latency' in latest_interaction:
                            st.metric("Response Time", f"{latest_interaction['latency']:.2f} seconds")
                    
                    # Show raw content of the response if requested
                    with st.expander("View Response Details", expanded=False):
                        try:
                            content = final_steps[-1].get('content', '')
                            if isinstance(content, str):
                                st.json(json.loads(content))
                            else:
                                st.json(content)
                        except:
                            st.write(final_steps[-1].get('content', ''))
            else:
                st.info("No responses to analyze yet. Start a conversation to see analysis.")

# Footer
st.markdown("---")
st.markdown("SnowBlaze AI Assistant © 2024 - Powered by OpenAI and Gemini")
