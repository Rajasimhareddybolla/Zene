import json
import logging
import os
import time
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Tuple, Union, cast
from datetime import datetime
from contextlib import contextmanager

import openai
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool

# Local imports
from prompts import Zene, summary, user_knowledge, Commet, Finn, Milo, Thalia
from talia import generate

# CONSTANTS
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.0
TOKEN_LIMIT = 10  # Keep last N conversation messages
DATABASE_DIR = "data"
CONVERSATION_DIR = "conversations"
DEBUG_DIR = "debugs"

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure required directories exist
for directory in [DATABASE_DIR, CONVERSATION_DIR, DEBUG_DIR]:
    os.makedirs(directory, exist_ok=True)

# Database setup
Base = declarative_base()


class ConversationData(Base):
    """Database model for storing conversation history."""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), index=True, nullable=False)
    agent_type = Column(String(64), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    conversation_data = Column(JSON)
    output_history = Column(JSON)


class DatabaseManager:
    """Handles database connections and operations."""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize databae connection.
        
        Args:
            db_url: Database connection URL (defaults to SQLite if None)
        """
        if db_url is None:
            db_url = f"sqlite:///{os.path.join(DATABASE_DIR, 'mioo.db')}"
        
        self.engine = create_engine(
            db_url, 
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600
        )
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.Session = scoped_session(sessionmaker(bind=self.engine))
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            session.close()
    
    def load_conversation(self, user_id: str, agent_type: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Load conversation history from database for a specific agent type.
        
        Args:
            user_id: The user identifier
            agent_type: Type of agent conversation to load
            
        Returns:
            Tuple containing (conversation_messages, output_history)
        """
        try:
            with self.session_scope() as session:
                conversation_record = session.query(ConversationData).filter_by(
                    user_id=user_id,
                    agent_type=agent_type
                ).order_by(ConversationData.updated_at.desc()).first()
                
                if conversation_record:
                    logger.info(f"Loaded existing {agent_type} conversation for user {user_id}")
                    return (
                        conversation_record.conversation_data or [],
                        conversation_record.output_history or []
                    )
                else:
                    logger.info(f"No existing {agent_type} conversation found for user {user_id}")
                    return [], []
        except Exception as e:
            logger.error(f"Error loading {agent_type} conversation: {e}", exc_info=True)
            return [], []
    
    def save_conversation(self, user_id: str, agent_type: str, 
                          conversation_data: List[Dict[str, Any]], 
                          output_history: List[Dict[str, Any]]) -> bool:
        """
        Save current conversation state to the database for a specific agent type.
        
        Args:
            user_id: The user identifier
            agent_type: Type of agent conversation to save
            conversation_data: List of conversation messages
            output_history: List of output history records
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            with self.session_scope() as session:
                # Check if record exists
                existing = session.query(ConversationData).filter_by(
                    user_id=user_id,
                    agent_type=agent_type
                ).first()
                
                if existing:
                    # Update existing record
                    existing.conversation_data = conversation_data
                    existing.output_history = output_history
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new record
                    new_record = ConversationData(
                        user_id=user_id,
                        agent_type=agent_type,
                        conversation_data=conversation_data,
                        output_history=output_history
                    )
                    session.add(new_record)
                
                logger.info(f"Saved {agent_type} conversation for user {user_id} to database")
                return True
        except Exception as e:
            logger.error(f"Error saving {agent_type} to database: {e}", exc_info=True)
            return False
    
    def delete_conversation(self, user_id: str, agent_type: Optional[str] = None) -> bool:
        """
        Delete conversation(s) from the database.
        
        Args:
            user_id: The user identifier
            agent_type: Type of agent conversation to delete (None for all types)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            with self.session_scope() as session:
                if agent_type is None:
                    session.query(ConversationData).filter_by(user_id=user_id).delete()
                    logger.info(f"Deleted all conversations for user {user_id} from database")
                else:
                    session.query(ConversationData).filter_by(
                        user_id=user_id, 
                        agent_type=agent_type
                    ).delete()
                    logger.info(f"Deleted {agent_type} conversation for user {user_id} from database")
                return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}", exc_info=True)
            return False


class VoiceService:
    """Handles integration with voice service for text-to-speech."""
    
    VOICE_SERVICE_URL = "http://127.0.0.1:4000"
    
    @staticmethod
    def prep_text_for_voice(markdown_content: str) -> str:
        """
        Prepare markdown content for voice synthesis by extracting text
        and formatting it appropriately.
        
        Args:
            markdown_content: Content in markdown format
            
        Returns:
            Cleaned text suitable for TTS
        """
        # Strip markdown formatting for better speech synthesis
        lines = []
        for line in markdown_content.split('\n'):
            # Remove markdown headers
            cleaned_line = line.strip()
            if cleaned_line.startswith('#'):
                cleaned_line = cleaned_line.lstrip('#').strip()
            
            # Remove other markdown formatting
            cleaned_line = cleaned_line.replace('**', '').replace('*', '')
            cleaned_line = cleaned_line.replace('`', '')
            
            if cleaned_line:
                lines.append(cleaned_line)
        
        return '\n'.join(lines)
    
    @staticmethod
    async def check_available() -> bool:
        """
        Check if the voice service is available.
        
        Returns:
            True if voice service is available, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{VoiceService.VOICE_SERVICE_URL}/health",
                    timeout=2.0  # Quick timeout for health check
                )
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Voice service unavailable: {e}")
            return False
    
    @staticmethod
    async def send_to_voice_service(text_content: str) -> bool:
        """
        Send text content to the voice service for TTS conversion and streaming.
        
        Args:
            text_content: The text to be converted to speech
            
        Returns:
            True if successfully sent to voice service, False otherwise
        """
        try:
            # Format the content for the voice service
            # The API expects a list of dicts with elements
            formatted_data = [
                {
                    "elements": [
                        {"type": "text", "content": paragraph.strip()}
                    ]
                }
                for paragraph in text_content.split('\n') if paragraph.strip()
            ]
            
            # Call the voice service API
            async with httpx.AsyncClient() as client:
                try:
                    # Set a reasonable timeout for the initial connection
                    response = await client.post(
                        f"{VoiceService.VOICE_SERVICE_URL}/sse-text-to-speech/",
                        json=formatted_data,
                        timeout=10.0
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Voice service error: {response.text}")
                        return False
                    
                    # The voice service is now streaming the audio
                    logger.info("Voice streaming started successfully")
                    return True
                except httpx.ConnectError as e:
                    logger.warning(f"Voice service unavailable: {e}")
                    logger.info("Continuing without voice synthesis")
                    return False
                except httpx.TimeoutException:
                    logger.warning("Voice service connection timed out")
                    logger.info("Continuing without voice synthesis")
                    return False
                
        except Exception as e:
            logger.error(f"Error sending content to voice service: {e}", exc_info=True)
            return False


class AIClient:
    """Handles AI model integrations for different providers."""
    
    def __init__(self):
        """Initialize AI clients for different providers."""
        load_dotenv()
        self.openai_client = openai.OpenAI()
        
        # Initialize Gemini client if API key exists
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            self.gemini_client = openai.OpenAI(
                api_key=gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        else:
            self.gemini_client = None
            logger.warning("GEMINI_API_KEY not found in environment variables")
    
    def get_completion(self, 
                       messages: List[Dict[str, str]], 
                       model_name: str = DEFAULT_MODEL,
                       temperature: float = DEFAULT_TEMPERATURE,
                       response_format: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any], float]:
        """
        Get a completion from an AI model.
        
        Args:
            messages: List of message dictionaries with role and content
            model_name: Name of the model to use
            temperature: Sampling temperature
            response_format: Optional format specification for the response
            
        Returns:
            Tuple of (content, usage_stats, latency)
        """
        start_time = time.time()
        
        try:
            # Determine which client to use based on model name
            client = self.gemini_client if model_name.startswith("gemini") else self.openai_client
            
            if not client:
                raise ValueError(f"No client available for model {model_name}")
            
            # Prepare arguments based on model
            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature
            }
            
            # Add model-specific parameters
            if model_name == "o3-mini":
                kwargs["reasoning_effort"] = "high"
                if response_format:
                    kwargs["response_format"] = response_format
            elif response_format:
                kwargs["response_format"] = response_format
            
            # Call the API
            response = client.chat.completions.create(**kwargs)
            
            end_time = time.time()
            latency = end_time - start_time
            
            # Extract content and usage statistics
            content = response.choices[0].message.content
            
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "latency_seconds": latency,
                "model": model_name
            }
            
            logger.info(f"Model {model_name} response - Token usage: {usage}")
            
            return content, usage, latency
            
        except Exception as e:
            end_time = time.time()
            latency = end_time - start_time
            logger.error(f"Error getting completion from {model_name}: {e}", exc_info=True)
            
            # Return error information
            return f"Error: {str(e)}", {
                "error": str(e),
                "latency_seconds": latency,
                "model": model_name
            }, latency


class Mioo:
    """
    A conversational agent system that coordinates multiple specialized agents.
    """
    def __init__(self, user_id: str, db_url: Optional[str] = None):
        """
        Initialize the Mioo with user ID and required components.
        
        Args:
            user_id: User ID for conversation tracking
            db_url: Database connection URL (defaults to SQLite if None)
        """
        self.user_id = user_id
        
        # Initialize component services
        self.db_manager = DatabaseManager(db_url)
        self.ai_client = AIClient()
        
        # Initialize conversations for different agent types
        self.agent_types = ["zene", "commet", "finn", "milo", "thalia"]
        self.conversations = {agent_type: [] for agent_type in self.agent_types}
        self.output_histories = {agent_type: [] for agent_type in self.agent_types}
        self.conversation_flow = []
        
        # Agent configurations
        self.agent_configs = {
            "zene": Zene,
            "commet": Commet,
            "finn": Finn,
            "milo": Milo,
            "thalia": Thalia
        }
        self.summary = summary
        
        # Load existing conversations
        self._load_all_conversations()
        
        logger.info(f"Initialized Mioo for user {user_id}")
    
    def _load_all_conversations(self) -> None:
        """Load all agent conversations for this user from the database."""
        for agent_type in self.conversations.keys():
            self._load_conversation(agent_type)
    
    def _load_conversation(self, agent_type: str) -> bool:
        """
        Load conversation history from database for a specific agent type.
        
        Args:
            agent_type: Type of agent conversation to load
            
        Returns:
            True if loaded successfully, False otherwise
        """
        conversation, history = self.db_manager.load_conversation(self.user_id, agent_type)
        if conversation or history:
            self.conversations[agent_type] = conversation
            self.output_histories[agent_type] = history
            return True
        return False
    
    def _save_to_database(self, agent_type: str) -> bool:
        """
        Save current conversation state to the database for a specific agent type.
        
        Args:
            agent_type: Type of agent conversation to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        return self.db_manager.save_conversation(
            self.user_id, 
            agent_type, 
            self.conversations[agent_type], 
            self.output_histories[agent_type]
        )

    def reset_and_summarize_conversation(self, agent_type: str = "zene") -> str:
        """
        Reset the conversation and return a summary.
        
        Args:
            agent_type: Type of agent conversation to reset
            
        Returns:
            str: Summary of the previous conversation
        """
        logger.info(f"Resetting {agent_type} conversation history")
        try:
            # Skip processing if conversation is empty
            if not self.conversations[agent_type]:
                logger.info(f"No {agent_type} conversation history to reset")
                return f"No {agent_type} conversation history to summarize"
                
            # Prepare message for summary generation
            messages = [
                {"role": "system", "content": self.summary},
                {"role": "user", "content": "Summarize the following conversation: " + 
                 json.dumps([conv for conv in self.conversations[agent_type] if conv.get("content")])}
            ]
            
            # Generate summary
            content, usage, _ = self.ai_client.get_completion(
                messages=messages,
                model_name=DEFAULT_MODEL,
                temperature=0.0
            )
            
            # Reset conversation but keep summary as context
            self.conversations[agent_type] = []
            self.conversations[agent_type].append({
                "role": "system",
                "content": f"Previous conversation summary: {content}"
            })
            
            # Record summary in history
            self.output_histories[agent_type].append({
                "action": "conversation_reset",
                "summary": content,
                "usage": usage,
                "timestamp": time.time()
            })
            
            # Save changes to database
            self._save_to_database(agent_type)
            
            logger.info(f"{agent_type} conversation history reset with summary")
            return content
            
        except Exception as e:
            logger.error(f"Failed to reset {agent_type} conversation: {str(e)}", exc_info=True)
            return f"Error resetting {agent_type} conversation: {str(e)}"

    def get_agent_response(self, 
                           agent_type: str, 
                           prompt: str, 
                           user_intent: Optional[str] = None, 
                           model_name: str = DEFAULT_MODEL) -> str:
        """
        Get a response from a specific agent based on the given prompt.
        
        Args:
            agent_type: Type of agent to use (e.g., "zene", "commet")
            prompt: User input prompt
            user_intent: User intent determined by previous agent (optional)
            model_name: Name of the model to use
            
        Returns:
            Response content as a string
        """
        try:
            # Validate agent type
            agent_type = agent_type.lower()
            if agent_type not in self.agent_configs:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # Handle special case for Thalia
            if agent_type == "thalia":
                return generate(self.agent_configs[agent_type]["system_prompt"], prompt)
            
            # Get agent configuration
            agent_config = self.agent_configs[agent_type]
            sys_prompt = agent_config["system_prompt"]
            response_format = agent_config["response_schema"]
            
            # Build messages list
            messages = [
                {"role": "system", "content": sys_prompt}
            ]
            
            # Add conversation history for Zene and Commet
            if agent_type in ["zene", "commet"]:
                messages.extend(self.conversations[agent_type])
            
            # Add user intent if provided
            if user_intent:
                messages.append({"role": "system", "content": f"User intent: {user_intent}"})
                prompt += f"\nUser intent: {user_intent}"
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Save debug information
            debug_file = os.path.join(DEBUG_DIR, f"message_input_{agent_type}.json")
            with open(debug_file, "w") as f:
                json.dump(messages, f, indent=2)
            
            # Get model response
            content, usage, latency = self.ai_client.get_completion(
                messages=messages,
                model_name=model_name,
                temperature=DEFAULT_TEMPERATURE,
                response_format={"type": "json_schema", "json_schema": response_format}
            )
            
            # Record the output for history
            self.output_histories[agent_type].append({
                "query": prompt,
                "response": content,
                "usage": usage,
                "latency_seconds": latency,
                "timestamp": time.time()
            })
            
            # Update conversation history for this agent
            self.conversations[agent_type].append({
                "role": "user",
                "content": prompt,
            })
            self.conversations[agent_type].append({
                "role": "assistant",
                "content": content,
            })
            
            # Keep conversation history manageable
            if len(self.conversations[agent_type]) > TOKEN_LIMIT:
                # Keep first message (usually system) and last TOKEN_LIMIT-1 messages
                self.conversations[agent_type] = [self.conversations[agent_type][0]] + \
                                               self.conversations[agent_type][-(TOKEN_LIMIT-1):]
            
            # Save conversation to database
            self._save_to_database(agent_type)
            
            return content
            
        except Exception as e:
            logger.error(f"Error for {agent_type} prompt: {prompt}\n{e}", exc_info=True)
            return json.dumps({
                "error": str(e),
                "status": "error",
                "message": f"Error processing request with {agent_type} agent"
            })

    def get_response(self, prompt: str, model_name: str = DEFAULT_MODEL) -> str:
        """
        Get a response from the default agent (zene).
        
        Args:
            prompt: User input prompt
            model_name: Name of the model to use
            
        Returns:
            Response content as a string
        """
        # This is a wrapper around get_agent_response for backward compatibility
        return self.get_agent_response("zene", prompt, model_name=model_name)

    def json_to_markdown_milo(self, milo_res: Dict[str, Any]) -> str:
        """
        Convert Milo's JSON response to formatted markdown.
        
        Args:
            milo_res: Milo agent response as JSON
            
        Returns:
            Formatted markdown string
        """
        md_content = ""
        # Add summary section first
        md_content += f"# Summary\n\n{milo_res['summary']}\n\n"

        # Process each section
        for section in milo_res["sections"]:
            # Add section heading with section number
            md_content += f"## {section['title']}\n\n"
            
            # Add content items with proper formatting
            for content in section['content']:
                md_content += f"### {content['text']}\n"
                
                # Add tags as bullet points if available
                if content.get('tags'):
                    md_content += "\n**Tags:** "
                    md_content += ", ".join([f"`{tag}`" for tag in content['tags']])
                    md_content += "\n"
                
                # Add references if available
                if content.get('references') and len(content['references']) > 0:
                    md_content += "\n**References:**\n"
                    for ref in content['references']:
                        md_content += f"- {ref['current_tag']} → {ref['other_content_sequential_id']} ({', '.join(ref['other_content_tags'])})\n"
                
                md_content += "\n"
            
            # Add slide layout information
            md_content += f"**Slide Layout:** {section['slide_layout']}\n\n"
            
            # Add assessment questions
            if section.get('assessment_questions'):
                md_content += "**Assessment Questions:**\n"
                for question in section['assessment_questions']:
                    md_content += f"- {question['question_sequential_id']}: {question['concept_to_be_assessed']}\n"
                md_content += "\n"

        return md_content

    async def process_with_voice(self, message: str) -> Tuple[Union[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process user message and send output to voice service.
        
        Args:
            message: User input message
            
        Returns:
            Tuple of (response_content, conversation_flow)
        """
        # Process the message first
        text_response, flow = self(message)
        
        # Check if voice service is available
        voice_service_available = await VoiceService.check_available()
        
        if voice_service_available:
            # Prepare content for TTS (only send first portion for efficiency)
            # Get text content whether response is string or dict
            text_content = text_response if isinstance(text_response, str) else json.dumps(text_response)
            
            # Get first portion (100 chars) for voice synthesis
            voice_text = VoiceService.prep_text_for_voice(text_content[:1000])
            
            # Send to voice service
            await VoiceService.send_to_voice_service(voice_text)
        else:
            logger.info("Voice service unavailable, continuing with text-only response")
        
        return text_response, flow

    def _process_zene_response(self, message: str) -> Tuple[Dict[str, Any], bool]:
        """
        Process the initial Zene agent response.
        
        Args:
            message: User input message
            
        Returns:
            Tuple of (parsed_response, success_flag)
        """
        try:
            # Get response from Zene agent
            zene_response_str = self.get_agent_response("zene", message)
            
            # Parse the JSON response
            zene_response = json.loads(zene_response_str)
            
            # Add to conversation flow
            self.conversation_flow.append({
                "role": "zene",
                "content": zene_response_str
            })
            
            return zene_response, True
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Zene response: {e}")
            return {"error": f"Failed to parse Zene response: {str(e)}"}, False
        except Exception as e:
            logger.error(f"Error processing Zene response: {e}", exc_info=True)
            return {"error": f"Error processing Zene response: {str(e)}"}, False

    def _process_rag_queries(self, queries: List[str]) -> List[Any]:
        """
        Process RAG queries using the Finn agent.
        
        Args:
            queries: List of vector database retrieval queries
            
        Returns:
            List of RAG responses
        """
        rag_responses = []
        
        # Process only the first query for efficiency
        if not queries:
            return rag_responses
            
        try:
            # Get Finn's response for vector DB search
            query = queries[0]
            finn_response_str = self.get_agent_response("finn", query)
            
            finn_response = json.loads(finn_response_str)
            if "section_250_word_report" in finn_response:
                rag_responses.append(finn_response["section_250_word_report"])
            else:
                rag_responses.append(finn_response)
                
            self.conversation_flow.append({
                "role": "finn",
                "content": finn_response
            })
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Finn response: {e}")
        except Exception as e:
            logger.error(f"Error getting RAG response: {e}", exc_info=True)
            
        return rag_responses

    def _route_to_agent(self, 
                        next_agent: str, 
                        message: str, 
                        rag_responses: List[Any], 
                        user_intent: str) -> Tuple[Union[str, Dict[str, Any]], bool]:
        """
        Route the conversation to the appropriate agent.
        
        Args:
            next_agent: Name of the next agent to use
            message: Original user message
            rag_responses: List of RAG responses from Finn
            user_intent: User intent from Zene
            
        Returns:
            Tuple of (agent_response, success_flag)
        """
        next_agent = next_agent.lower()
        logger.info(f"Routing to {next_agent} agent")
        
        # Create augmented message with RAG content if available
        augmented_message = message
        if rag_responses:
            augmented_message = f"{message}\nAdditional context: {json.dumps(rag_responses)}"
        
        # Set model based on agent
        model_name = "gemini-2.0-flash" if next_agent == "thalia" else DEFAULT_MODEL
        
        try:
            # Get response from next agent
            agent_response_str = self.get_agent_response(
                next_agent, 
                augmented_message,
                user_intent=user_intent,
                model_name=model_name
            )
            
            # Parse the response
            if next_agent == "commet":
                agent_response = json.loads(agent_response_str)
                self.conversation_flow.append({
                    "role": next_agent,
                    "content": agent_response_str
                })
                return f'#### {agent_response["response"]}', True
                
            elif next_agent == "milo":
                agent_response = json.loads(agent_response_str)
                self.conversation_flow.append({
                    "role": next_agent,
                    "content": agent_response
                })
                # Convert to markdown format
                return self.json_to_markdown_milo(agent_response), True
                
            elif next_agent == "thalia":
                agent_response = json.loads(agent_response_str)
                self.conversation_flow.append({
                    "role": next_agent,
                    "content": agent_response
                })
                return agent_response, True
            
            return agent_response_str, True
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {next_agent} response: {e}")
            return {"error": f"Failed to parse {next_agent} response: {str(e)}"}, False
        except Exception as e:
            logger.error(f"Error routing to {next_agent}: {e}", exc_info=True)
            return {"error": f"Error routing to {next_agent}: {str(e)}"}, False

    def __call__(self, message: str) -> Tuple[Union[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process a conversational message through the agent workforce.
        
        Args:
            message: User message
            
        Returns:
            Tuple of (response_content, conversation_flow)
        """
        # Reset and initialize conversation flow
        self.conversation_flow = []
        self.conversation_flow.append({
            "role": "user",
            "content": message
        })
        logger.info(f"Processing user message: {message[:50]}...")
        
        try:
            # Step 1: Process with Zene agent
            zene_response, success = self._process_zene_response(message)
            if not success:
                return zene_response, self.conversation_flow
            
            # Step 2: Process RAG queries if present
            rag_responses = []
            if "vector_database_retrieval_queries" in zene_response:
                rag_responses = self._process_rag_queries(
                    zene_response["vector_database_retrieval_queries"]
                )
            
            # Step 3: Route to appropriate agent if specified
            if "next_agent" in zene_response:
                user_intent = zene_response.get("user_intent", "")
                response, success = self._route_to_agent(
                    zene_response["next_agent"],
                    message,
                    rag_responses,
                    user_intent
                )
                
                if success:
                    return response, self.conversation_flow
            
            # Default: Return Zene's response if no routing or if routing failed
            return zene_response, self.conversation_flow
                
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            return {"error": f"Unexpected error: {str(e)}"}, self.conversation_flow

    def save_conversation(self, agent_type: str = "all", filename: Optional[str] = None) -> None:
        """
        Save the current conversation to file and database.
        
        Args:
            agent_type: Type of agent conversation to save ("all" or specific agent)
            filename: Optional filename to save to
        """
        # Determine which agent types to save
        if agent_type == "all":
            agent_types = list(self.conversations.keys())
        elif agent_type.lower() in self.conversations:
            agent_types = [agent_type.lower()]
        else:
            logger.error(f"Unknown agent type: {agent_type}")
            return
        
        # Save each agent type conversation
        for agent in agent_types:
            # Save to database
            self._save_to_database(agent)
            
            # Also save to file if requested
            if filename:
                file_base = os.path.splitext(filename)[0]
                file_ext = os.path.splitext(filename)[1] or ".json"
                agent_filename = f"{file_base}_{agent}{file_ext}"
            else:
                agent_filename = f"conversation_{self.user_id}_{agent}_{int(time.time())}.json"
            
            filepath = os.path.join(CONVERSATION_DIR, agent_filename)
            
            try:
                with open(filepath, "w") as f:
                    json.dump({
                        "user_id": self.user_id,
                        "agent_type": agent,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "conversation": self.conversations[agent],
                        "usage_stats": self.output_histories[agent]
                    }, f, indent=2)
                logger.info(f"{agent} conversation saved to {filepath}")
            except Exception as e:
                logger.error(f"Failed to save {agent} conversation to file: {e}")
            
    def delete_conversation(self, agent_type: str = "all") -> bool:
        """
        Delete conversation(s) from the database and memory.
        
        Args:
            agent_type: Type of agent conversation to delete ("all" or specific agent)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            if agent_type == "all":
                # Delete all conversations from database
                result = self.db_manager.delete_conversation(self.user_id)
                
                # Reset all in-memory conversations
                for agent in self.conversations:
                    self.conversations[agent] = []
                    self.output_histories[agent] = []
                    
                return result
            elif agent_type.lower() in self.conversations:
                agent_type = agent_type.lower()
                
                # Delete from database
                result = self.db_manager.delete_conversation(self.user_id, agent_type)
                
                # Reset in-memory conversation
                self.conversations[agent_type] = []
                self.output_histories[agent_type] = []
                
                return result
            else:
                logger.error(f"Unknown agent type: {agent_type}")
                return False
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}", exc_info=True)
            return False


# Example usage with better error handling
if __name__ == "__main__":
    try:
        # Create agent with user ID
        zene_agent = Mioo(user_id="user123")
        
        # For asynchronous usage with voice
        async def main():
            try:
                response, flow = await zene_agent.process_with_voice("Can you explain about the Chola dynasty?")
                print(json.dumps(response, indent=2) if isinstance(response, dict) else response)
            except Exception as e:
                logger.error(f"Error in main async function: {e}", exc_info=True)
                print(f"Error: {e}")
        
        # Run the async main function
        asyncio.run(main())
        
        # Save conversation history
        zene_agent.save_conversation()
        
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        print(f"A critical error occurred: {e}")
