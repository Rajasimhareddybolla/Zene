import streamlit as st
import os
import dotenv
import openai
import json
import time
import logging
import traceback
from typing import List, Dict, Any, Optional
import uuid
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agentic-wars")

# Load environment variables
dotenv.load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Agent War: Conversational Battle",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/Rajasimhareddybolla/agent-war',
        'About': 'An AI agent conversation simulator from pinoxio'
    }
)

# Custom CSS for better UI
st.markdown("""
<style>
    .agent-box {
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .agent1-box {
        background-color: rgba(0, 121, 255, 0.1);
        border-left: 5px solid #0079FF;
    }
    .agent2-box {
        background-color: rgba(255, 99, 71, 0.1);
        border-left: 5px solid #FF6347;
    }
    .json-display {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        font-family: monospace;
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
    .big-button {
        font-size: 20px !important;
        height: 60px !important;
        padding: 15px 32px !important;
    }
    .chat-container {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        height: 600px;
        overflow-y: auto;
        background-color: #f9f9f9;
    }
    .chat-message {
        margin-bottom: 15px;
        padding: 10px 15px;
        border-radius: 10px;
        max-width: 80%;
    }
    .agent1-message {
        background-color: #0079FF;
        color: white;
        margin-right: auto;
    }
    .agent2-message {
        background-color: #FF6347;
        color: white;
        margin-left: auto;
    }
    .message-header {
        font-weight: bold;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Cache model options
@st.cache_data
def get_model_options():
    return ["gpt-4o-mini", "gpt-4o", "o3-mini"]

# Default JSON schema templates to help users
@st.cache_data
def mira_schema():
    return json.dumps({
  "name": "upsc_query_schema",
  "strict": True,
  "schema": {
    "type": "object",
    "properties": {
      "topics": {
        "type": "array",
        "description": "A list of the most relevant UPSC curriculum topics.",
        "items": {
          "type": "string"
        }
      },
      "sub-topics": {
        "type": "array",
        "description": "A list of the most relevant UPSC curriculum sub-topics.",
        "items": {
          "type": "string"
        }
      },
      "core_topic": {
        "type": "string",
        "description": "Core topic/focus/subject of the user query."
      },
      "user_intent": {
        "type": "string",
        "description": "Describes the user's query intent."
      },
      "is_ambiguous": {
        "type": "boolean",
        "description": "Indicates if the query is ambiguous."
      },
      "query_category": {
        "type": "string",
        "description": "One of the specified types related to the query.",
        "enum": [
          "chat",
          "question",
          "concept"
        ]
      },
      "target": {
        "type": "string",
        "description": "Identify the target of the user query.",
        "enum": [
          "agent",
          "exam",
          "curriculum",
          "user",
          "other"
        ]
      },
      "is_in_upsc_scope": {
        "type": "boolean",
        "description": "Indicates if the query is within the UPSC examination scope."
      },
      "next_agent": {
        "type": "string",
        "description": "Pick one of the specified agents.",
        "enum": [
          "Comet",
          "Thalia",
          "Milo"
        ]
      },
      "vector_database_retrieval_queries": {
        "type": "array",
        "description": "List of zero or more concise, effective and independent queries to retrieve all related content needed to address the user query.",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "topics",
      "sub-topics",
      "core_topic",
      "user_intent",
      "is_ambiguous",
      "query_category",
      "target",
      "is_in_upsc_scope",
      "next_agent",
      "vector_database_retrieval_queries"
    ],
    "additionalProperties": False
  }
})
@st.cache_data
def get_default_schema():
    return json.dumps({
        "response": "string",
        "thoughts": "string",
        "emotion": "string"
    }, indent=2)

class Agent:
    def __init__(self, name: str, system_prompt: str, model: str, response_schema: Optional[Dict] = None):
        self.name = name
        self.base_system_prompt = system_prompt
        self.model = model
        self.response_schema = response_schema
        self.messages_history = []
        self.id = str(uuid.uuid4())[:8]  # Generate a unique ID for the agent
        logger.info(f"Agent '{name}' (ID: {self.id}) initialized with model {model}")
        
    def get_system_prompt(self):
        """Combine base system prompt with response schema instructions if provided"""
        if self.response_schema:
            schema_str = json.dumps(self.response_schema, indent=2)
            return (f"{self.base_system_prompt}\n\n"
                   f"IMPORTANT: You must structure your responses as JSON following this exact schema:\n"
                   f"{schema_str}\n\n"
                   f"Make sure your response is valid JSON. Do not include any text outside the JSON object.")
        return self.base_system_prompt
        
    def initialize_chat(self):
        """Reset chat history and initialize with system prompt"""
        self.messages_history = [{"role": "system", "content": self.get_system_prompt()}]
        logger.info(f"Initialized chat for agent {self.name}")
        
    def add_message(self, role: str, content: str):
        """Add a message to the agent's conversation history"""
        self.messages_history.append({"role": role, "content": content})
        logger.debug(f"Added {role} message to {self.name}'s history")
        
    def get_message_for_display(self, message_content):
        """Format message for display based on whether it's JSON or not"""
        if self.response_schema:
            try:
                # Try to parse as JSON
                parsed = json.loads(message_content)
                return parsed
            except json.JSONDecodeError as e:
                # If not valid JSON, return as is
                logger.warning(f"Invalid JSON response from {self.name}: {e}")
                return {"error": "Invalid JSON response", "raw_content": message_content}
        return message_content
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError))
    )    
    def generate_response(self, client):
        """Generate a response from the agent using the OpenAI API with retry logic"""
        try:
            logger.info(f"Generating response for {self.name} using {self.model}")
            kwargs = {
                "model": self.model,
                "messages": self.messages_history,
                "temperature": 0.7,
                "timeout": 30,  # Add timeout to prevent hanging requests
            }
            
            # Add response format if schema is provided
            if self.response_schema:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = client.chat.completions.create(**kwargs)
            
            message = response.choices[0].message.content
            self.add_message("assistant", message)
            
            # Validate JSON if using schema
            if self.response_schema:
                try:
                    json.loads(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Model returned invalid JSON: {e}")
                    # Return a valid JSON error message
                    fallback_message = json.dumps({"error": "Model returned invalid JSON response", 
                                                  "response": "I'm sorry, I encountered an error in my formatting. Let me try again with a proper response."})
                    self.messages_history[-1]["content"] = fallback_message
                    return fallback_message
                    
            return message
        except openai.RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except openai.APITimeoutError as e:
            logger.error(f"API timeout: {e}")
            raise
        except openai.APIConnectionError as e:
            logger.error(f"API connection error: {e}")
            raise
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            # Return a valid error message in the expected format
            if self.response_schema:
                return json.dumps({"error": error_msg, "response": "I encountered an error. Please try again."})
            return error_msg

def validate_api_key(api_key):
    """Validate the OpenAI API key by making a simple request"""
    if not api_key or api_key.strip() == "":
        return False, "API key cannot be empty"
    
    try:
        client = openai.OpenAI(api_key=api_key)
        models = client.models.list()
        return True, "API key is valid"
    except Exception as e:
        logger.error(f"API key validation failed: {e}")
        return False, f"Invalid API key: {str(e)}"

def display_message(agent_name, message_content, agent_id, response_schema=None):
    """Display a message in the chat interface"""
    agent_class = "agent1-message" if agent_id == st.session_state.agent1.id else "agent2-message"
    
    if response_schema:
        try:
            message_obj = json.loads(message_content)
            
            with st.chat_message(agent_name, avatar=f"{'🔵' if agent_id == st.session_state.agent1.id else '🔴'}"):
                # Show error if present
                if "error" in message_obj:
                    st.error(message_obj["error"])
                
                # Display response fields
                for key, value in message_obj.items():
                    if key.lower() in ["response", "message", "content"]:
                        st.markdown(f"**{value}**")
                    elif key.lower() != "error":
                        st.markdown(f"*{key}*: {value}")
        except json.JSONDecodeError:
            with st.chat_message(agent_name, avatar=f"{'🔵' if agent_id == st.session_state.agent1.id else '🔴'}"):
                st.error("Invalid JSON response")
                st.text(message_content)
    else:
        with st.chat_message(agent_name, avatar=f"{'🔵' if agent_id == st.session_state.agent1.id else '🔴'}"):
            st.markdown(message_content)

def extract_main_content(message_content, response_schema):
    """Extract the main content/response from a JSON response"""
    if not response_schema:
        return message_content
    
    try:
        message_obj = json.loads(message_content)
        # Look for common response fields
        for key in ["response", "message", "content", "answer"]:
            if key in message_obj:
                return message_obj[key]
        # If no standard response field found, return the first value
        return next(iter(message_obj.values()))
    except (json.JSONDecodeError, StopIteration):
        logger.warning(f"Failed to extract main content from: {message_content[:100]}...")
        return message_content

def run_conversation(agent1, agent2, client, threshold):
    """Run the conversation between two agents"""
    conversation_log = []
    full_conversation_text = ""  # Track the full conversation as text
    
    # Initialize both agents
    agent1.initialize_chat()
    agent2.initialize_chat()
    
    try:
        # First message from agent1 to start the conversation
        with st.spinner(f"{agent1.name} is thinking..."):
            agent1_response = agent1.generate_response(client)
        
        conversation_log.append({"agent": agent1.name, "message": agent1_response, "agent_id": agent1.id})
        
        # Extract the main content if using schema
        main_content = extract_main_content(agent1_response, agent1.response_schema)
        
        # Update the full conversation text
        full_conversation_text += f"{agent1.name}: {main_content}\n\n"
        
        # Pass the full conversation to agent2 instead of just the last message
        agent2.add_message("user", full_conversation_text)
        
        # Display the message
        display_message(agent1.name, agent1_response, agent1.id, agent1.response_schema)
        
        # Run the conversation for the specified number of turns
        for i in range(threshold - 1):
            # Add progress indicator
            progress_text = f"Conversation progress: {i+1}/{threshold-1} rounds"
            progress_bar = st.progress(0)
            progress_bar.progress((i+1)/(threshold-1))
            st.text(progress_text)
            
            # Agent 2's turn
            with st.spinner(f"{agent2.name} is thinking..."):
                agent2_response = agent2.generate_response(client)
            
            conversation_log.append({"agent": agent2.name, "message": agent2_response, "agent_id": agent2.id})
            
            # Extract the main content if using schema
            main_content = extract_main_content(agent2_response, agent2.response_schema)
            
            # Update the full conversation text
            full_conversation_text += f"{agent2.name}: {main_content}\n\n"
            
            # Pass the full conversation to agent1
            agent1.add_message("user", full_conversation_text)
            
            # Display the message
            display_message(agent2.name, agent2_response, agent2.id, agent2.response_schema)
            
            # If this is the last turn, break after agent2's response
            if i == threshold - 2:
                break
            
            # Agent 1's turn
            with st.spinner(f"{agent1.name} is thinking..."):
                agent1_response = agent1.generate_response(client)
            
            conversation_log.append({"agent": agent1.name, "message": agent1_response, "agent_id": agent1.id})
            
            # Extract the main content if using schema
            main_content = extract_main_content(agent1_response, agent1.response_schema)
            
            # Update the full conversation text
            full_conversation_text += f"{agent1.name}: {main_content}\n\n"
            
            # Pass the full conversation to agent2
            agent2.add_message("user", full_conversation_text)
            
            # Display the message
            display_message(agent1.name, agent1_response, agent1.id, agent1.response_schema)
            
            # Update progress
            progress_bar.progress((i+2)/(threshold-1))
            
        # Clear progress bar when done
        st.empty()
        
    except Exception as e:
        logger.error(f"Error in conversation: {e}\n{traceback.format_exc()}")
        st.error(f"Error during conversation: {str(e)}")
    
    return conversation_log

def initialize_session_state():
    """Initialize session state variables"""
    if 'conversation_started' not in st.session_state:
        st.session_state.conversation_started = False
    
    if 'conversation_log' not in st.session_state:
        st.session_state.conversation_log = []
    
    if 'agent1' not in st.session_state:
        st.session_state.agent1 = None
    
    if 'agent2' not in st.session_state:
        st.session_state.agent2 = None
    
    if 'api_key_valid' not in st.session_state:
        st.session_state.api_key_valid = False

def main():
    try:
        initialize_session_state()
        
        # Header section
        st.title("🤖 Agent War: AI Conversational Battle")
        st.markdown("Create a conversation battle between two AI agents with custom personalities and see how they interact!")
        
        # Sidebar for API key
        with st.sidebar:
            st.header("🔑 API Configuration")
            
            # Get API key from env or let user input it
            api_key_source = st.radio("API Key Source", ["Environment Variable", "Manual Input"])
            
            if api_key_source == "Environment Variable":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    st.error("❌ OPENAI_API_KEY environment variable not found!")
                    st.stop()
                else:
                    is_valid, message = validate_api_key(api_key)
                    if is_valid:
                        st.success("✅ API key from environment is valid")
                        client = openai.OpenAI(api_key=api_key)
                        st.session_state.api_key_valid = True
                    else:
                        st.error(f"❌ {message}")
                        st.stop()
            else:
                api_key = st.text_input("OpenAI API Key", type="password")
                if st.button("Validate API Key"):
                    is_valid, message = validate_api_key(api_key)
                    if is_valid:
                        st.success("✅ API key is valid")
                        client = openai.OpenAI(api_key=api_key)
                        st.session_state.api_key_valid = True
                    else:
                        st.error(f"❌ {message}")
                        st.session_state.api_key_valid = False
                
                if not st.session_state.api_key_valid and api_key:
                    st.warning("Please validate your API key before proceeding")
                
                if not api_key:
                    st.warning("Please enter an API key")
                    st.session_state.api_key_valid = False
            
            if st.session_state.api_key_valid:
                client = openai.OpenAI(api_key=api_key)
                
                st.header("📊 Metrics")
                st.metric("Current User", "🧙‍♂️ SnowBlaze 🧙‍♂️")
                st.metric("Purpose", "Agentic War ⚠️")
                
                st.header("🔄 Reset")
                if st.button("Reset Conversation", use_container_width=True):
                    st.session_state.conversation_started = False
                    st.session_state.conversation_log = []
                    st.rerun()
        
        # Check if API key is valid before proceeding
        if not st.session_state.api_key_valid:
            st.warning("Please configure a valid API key in the sidebar to continue")
            st.stop()
        
        # Tabs for configuration and conversation
        tab1, tab2 = st.tabs(["⚙️ Agent Configuration", "💬 Conversation"])
        
        with tab1:
            st.header("Agent Configuration")
            
            # Split the screen for both agents
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="agent-box agent1-box">
                    <h3>Agent 1 Configuration</h3>
                </div>
                """, unsafe_allow_html=True)
                
                agent1_name = st.text_input("Agent 1 Name", "Agent Alpha")
                if not agent1_name.strip():
                    st.warning("Agent name cannot be empty")
                
                agent1_system_prompt = st.text_area("Agent 1 System Prompt", 
                                             """
                                                                
                    You are a simulation of a UPSC aspirant interacting with Mira, a query classification system. Your purpose is to test Mira's ability to classify queries and maintain engaging, natural conversation.

                    ## How to Test Mira:

                    1. Ask realistic UPSC-related questions across these categories:
                    - Concept explanations
                    - Practice questions 
                    - Study strategy queries 
                    - generic chat related to UPSC preparation

                    2. Focus on conversational follow-ups:
                    - "Can you please briefly summarize what I just asked about?"
                    - "How does this relate to what we discussed earlier?"
                    - "Could you explain that again but focus on [specific aspect]?"
                    - "I'm still confused about [topic from previous question], can you clarify?"
                    - "Based on my question about [previous topic], what should I study next?"

                    3. Maintain natural conversation flow:
                    - React to Mira's classifications and questions
                    - Build on previous topics rather than jumping randomly
                    - Express confusion or ask for clarification when appropriate
                    - Show appreciation when Mira correctly understands your queries
                    - Occasionally reference previous parts of the conversation

                    Your goal is to create a realistic testing environment that challenges Mira's ability to classify queries correctly while maintaining engaging conversation that feels natural to a UPSC aspirant's study journey.

                    Remember to vary your questions in complexity and subject matter across the UPSC syllabus (History, Geography, Polity, Economy, Science, Environment, Current Affairs, etc.).

                    you can include some generic messages to imitate like humans , while studying topics , like I am bored ,and all , you can do like a human. you have to follow the "The topic of this conversation "  which is mentioned as cholas and their administration .
                    only ask the questions dont ever never gave your explanations and all only the upsc candidate queries/ questions , even for the follow up .
                                             """
                                             )
                if not agent1_system_prompt.strip():
                    st.warning("System prompt cannot be empty")
                
                agent1_model = st.selectbox("Agent 1 Model", get_model_options(), index=0)
                
                # Add schema input for Agent 1
                use_schema1 = st.checkbox("Use JSON Response Schema for Agent 1", value=True, 
                                      help="Make Agent 1 structure responses according to a specific JSON schema")
                agent1_schema = None
                
                if use_schema1:
                    schema1_input = st.text_area("Agent 1 Response Schema (JSON)", 
                                                get_default_schema(), 
                                                height=150)
                    try:
                        if schema1_input.strip():
                            agent1_schema = json.loads(schema1_input)
                            st.success("✅ Valid JSON schema for Agent 1")
                        else:
                            st.warning("Schema cannot be empty if checkbox is enabled")
                            agent1_schema = None
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON schema for Agent 1: {str(e)}")
                        agent1_schema = None
            
            with col2:
                st.markdown("""
                <div class="agent-box agent2-box">
                    <h3>Agent 2 Configuration</h3>
                </div>
                """, unsafe_allow_html=True)
                
                agent2_name = st.text_input("Agent 2 Name", "Agent Zera")
                if not agent2_name.strip():
                    st.warning("Agent name cannot be empty")
                
                agent2_system_prompt = st.text_area("Agent 2 System Prompt", 
                                                                """{
                    ""role"": ""You are Zane, an user intent classifier agent. You profile the user query across Indian UPSC exam curriculum relevant topic, sub-topic and core theme of the query. You will pick the next agent from the below agents list to process the query as per your classification. You will also generate a detailed retrieval query for relevant content extraction from vector database for retrieval augmented generation with next agents.""
                    ""context"": ""Your user is an Indian UPSC exam aspirant. Your scope is limited to UPSC prelims, mains and interview curriculum and scope."",
                    ""instructions"":[
                        ""Do not provide any answers, solutions, or explanations to questions."", 
                        ""Classify according to the official UPSC syllabus curriculum and patterns."", 
                    ""Identify the optimal agent to handle this query.""
                        ""If a query spans multiple topics, list all relevant ones but prioritize the primary subject."", 
                    ""Use concise topic/sub-topic keywords for retrieval queries from vector database."",
                        ""Flag the ambiguous queries."", 
                        ""Flag if the content is within UPSC scope."", 
                        ""Always respond with a properly formatted JSON object that adheres to the schema."" 
                    ],
                    ""agents"":[
                    {
                    ""name"": ""Comet"",
                    ""role"": ""Friendly agent for casual chat and anything else the other agents cannot handle.""
                    },
                    {
                    ""name"": ""Thalia""
                    ""role"": ""Problem solver. Can ONLY solve questions and problems.""
                    },
                    {
                    ""name"":""Milo"",
                    ""role"": ""Topic explainer. Can ONLY explain any topic from the UPSC exam curriculum scope.""
                    }
                    ],
                    ""query_categories"": [ 
                        ""chat"", 
                        ""question"",  // only for UPSC curriculum related questions and problems
                        ""concept""  // only for concepts in UPSC curriculum 
                    ], 
                    ""target"": [
                    //identify the target of the user query across following
                    ""agent"", // Queries addressing the AI tutor itself, including feedback on its responses, correction requests, or discussions about its behavior, performance, or reliability
                    , ""exam"": //Queries focusing on exam logistics, strategies, preparation techniques, mock tests, scheduling revision sessions, exam day tips, and any content directly related to performing well on the exam.
                    , ""curriculum"": // Queries related to the subject matter of the exam syllabus—academic content, detailed concept explanations, historical events, factual knowledge, analyses, comparisons, and clarifications on topics.
                    , ""user"": //Queries that pertain to the user’s personal context or self-reflection, such as requests for personalized advice, self-assessment, or discussions about personal study habits and challenges not directly tied to exam logistics.
                    , ""other"": //All remaining queries that do not clearly fit into the above categories—casual conversation, general chit-chat, or any off-topic inquiries.
                    ]
                    }""" )
                if not agent2_system_prompt.strip():
                    st.warning("System prompt cannot be empty")
                
                agent2_model = st.selectbox("Agent 2 Model", get_model_options(), index=0)
                
                # Add schema input for Agent 2
                use_schema2 = st.checkbox("Use JSON Response Schema for Agent 2", value=True, 
                                      help="Make Agent 2 structure responses according to a specific JSON schema")
                agent2_schema = None
                
                if use_schema2:
                    schema2_input = st.text_area("Agent 2 Response Schema (JSON)", 
                                                mira_schema(), 
                                                height=150)
                    try:
                        if schema2_input.strip():
                            agent2_schema = json.loads(schema2_input)
                            st.success("✅ Valid JSON schema for Agent 2")
                        else:
                            st.warning("Schema cannot be empty if checkbox is enabled")
                            agent2_schema = None
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON schema for Agent 2: {str(e)}")
                        agent2_schema = None
            
            # Common configuration
            st.markdown("""
            <div class="agent-box" style="background-color: rgba(128, 128, 128, 0.1); border-left: 5px solid #808080;">
                <h3>Conversation Configuration</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Schema tips in the common area
            st.markdown("### Schema Tips")
            st.markdown("""
            - Include a `response` field for the main message
            - Add `thoughts` for reasoning
            - Consider `emotion` or `tone` fields
            - Add any other fields you want agents to include
            """)
            
            threshold_col1, threshold_col2 = st.columns([3, 1])
            
            with threshold_col1:
                threshold = st.slider("Conversation Turns", min_value=1, max_value=20, value=5, 
                                   help="Number of back-and-forth exchanges between agents")
            
            with threshold_col2:
                st.markdown(f"### Total Messages: {threshold * 2 - 1}")
                st.markdown(f"Agent 1 messages: {threshold}")
                st.markdown(f"Agent 2 messages: {threshold - 1}")
            
            # Initialize the agents
            init_disabled = False
            
            # Check for empty required fields
            if not agent1_name.strip() or not agent2_name.strip() or not agent1_system_prompt.strip() or not agent2_system_prompt.strip():
                init_disabled = True
                
            # Check for invalid schemas
            if (use_schema1 and agent1_schema is None) or (use_schema2 and agent2_schema is None):
                init_disabled = True
            
            if st.button("Initialize Agents", use_container_width=True, type="primary", 
                       help="Save agent configurations and prepare for conversation", 
                       disabled=init_disabled):
                
                try:
                    # Initialize with separate schemas
                    st.session_state.agent1 = Agent(agent1_name, agent1_system_prompt, agent1_model, 
                                                 agent1_schema if use_schema1 else None)
                    st.session_state.agent2 = Agent(agent2_name, agent2_system_prompt, agent2_model,
                                                 agent2_schema if use_schema2 else None)
                    
                    st.success(f"✅ Agents {agent1_name} and {agent2_name} are ready for conversation!")
                    st.session_state.threshold = threshold
                except Exception as e:
                    logger.error(f"Error initializing agents: {e}\n{traceback.format_exc()}")
                    st.error(f"Error initializing agents: {str(e)}")
        
        with tab2:
            st.header("Agent Conversation")
            
            # Check if agents are initialized
            if not st.session_state.agent1 or not st.session_state.agent2:
                st.warning("⚠️ Please initialize the agents in the Configuration tab first!")
                st.stop()
            
            # Display agent info
            agent_info_col1, agent_info_col2 = st.columns(2)
            
            with agent_info_col1:
                st.markdown(f"""
                <div class="agent-box agent1-box">
                    <h3>🔵 {st.session_state.agent1.name}</h3>
                    <p><strong>Model:</strong> {st.session_state.agent1.model}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with agent_info_col2:
                st.markdown(f"""
                <div class="agent-box agent2-box">
                    <h3>🔴 {st.session_state.agent2.name}</h3>
                    <p><strong>Model:</strong> {st.session_state.agent2.model}</p>
                </div>
                """, unsafe_allow_html=True)
            

            
            # Start conversation button
            start_button_col1, start_button_col2, start_button_col3 = st.columns([1, 2, 1])
            
            with start_button_col2:
                if not st.session_state.conversation_started:
                    if st.button("🚀 Start Conversation", use_container_width=True, type="primary", key="start_button", 
                               help="Begin the conversation between the two agents"):
                        try:
                            st.session_state.conversation_started = True
                            
                            # Start conversation with a topic if provided

                            # Run the conversation
                            with st.spinner("Starting conversation..."):
                                st.session_state.conversation_log = run_conversation(
                                    st.session_state.agent1,
                                    st.session_state.agent2,
                                    client,
                                    st.session_state.threshold
                                )
                            
                            # Display completion message
                            st.success("✅ Conversation completed!")
                        except Exception as e:
                            logger.error(f"Error in conversation: {e}\n{traceback.format_exc()}")
                            st.error(f"Error starting conversation: {str(e)}")
                            st.session_state.conversation_started = False
            
            # Display download button if conversation is complete
            if st.session_state.conversation_started and st.session_state.conversation_log:
                # Option to download the conversation
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    conversation_json = json.dumps(st.session_state.conversation_log, indent=2)
                    st.download_button(
                        label="📥 Download Conversation JSON",
                        data=conversation_json,
                        file_name="agent_conversation.json",
                        mime="application/json",
                        use_container_width=True
                    )
                    
                    # Also provide a text version
                    conversation_text = ""
                    for entry in st.session_state.conversation_log:
                        agent_name = entry["agent"]
                        message = entry["message"]
                        
                        # Try to extract the main content if it's JSON
                        try:
                            content = json.loads(message)
                            for key in ["response", "message", "content", "answer"]:
                                if key in content:
                                    message = content[key]
                                    break
                        except:
                            pass  # Use the raw message if we can't parse JSON
                        
                        conversation_text += f"{agent_name}: {message}\n\n"
                    
                    st.download_button(
                        label="📥 Download Conversation Text",
                        data=conversation_text,
                        file_name="agent_conversation.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            
            if not st.session_state.conversation_started:
                st.info("⏱️ The conversation will appear here once you start it.")
    
    except Exception as e:
        logger.critical(f"Application error: {e}\n{traceback.format_exc()}")
        st.error(f"An unexpected error occurred: {str(e)}")
        st.error("Please refresh the page and try again.")

if __name__ == "__main__":
    main()