import json
import logging
import os
import time
from typing import Dict, Any, List, Optional
from prompts import Zene, summary, user_knowledge, Commet ,Finn , Milo , Thalia
import openai
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from talia import generate
import datetime
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()

class ConversationData(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), index=True, nullable=False)
    agent_type = Column(String(64), index=True, nullable=False)  # New field to track agent type
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    conversation_data = Column(JSON)
    output_history = Column(JSON)

class SnowBlaze:
    """
    A conversational agent that supports multiple agent types like Zene and Commet.
    """
    def __init__(self, user_id: str , db_url: Optional[str] = None):
        """
        Initialize the SnowBlaze with user ID and OpenAI client.
        
        Args:
            user_id: User ID for conversation tracking
            db_url: Database connection URL (defaults to SQLite if None)
        """
        print("gemini")
        load_dotenv()
        self.user_id = user_id
        self.client = openai.OpenAI()
        self.gemini_client = openai.OpenAI(
            api_key= os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )  
        # Initialize conversations for different agent types
        self.conversations = {
            "zene": [],
            "commet": [],
            "finn": [],
            "milo": [],
            "thalia": []
        }
        self.output_histories = {
            "zene": [],
            "commet": [],
            "finn": [],
            "milo": [],
            "thalia": []
        }
        
        # Agent configurations
        self.summary = summary
        self.zene = Zene
        self.commet = Commet
        self.finn = Finn
        self.milo = Milo
        self.thalia = Thalia
        
        
        # Set up database connection
        if db_url is None:
            # Default to SQLite database in a data directory
            os.makedirs("data", exist_ok=True)
            db_url = f"sqlite:///data/snowblaze.db"
        
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
        
        # Load existing conversations for all agent types
        self._load_all_conversations()
    
    @contextmanager
    def _session_scope(self):
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
    
    def _load_all_conversations(self):
        """Load all agent conversations for this user from the database."""
        for agent_type in self.conversations.keys():
            self._load_conversation(agent_type)
    
    def _load_conversation(self, agent_type="zene"):
        """Load conversation history from database for a specific agent type."""
        try:
            with self._session_scope() as session:
                conversation_record = session.query(ConversationData).filter_by(
                    user_id=self.user_id,
                    agent_type=agent_type
                ).order_by(ConversationData.updated_at.desc()).first()
                
                if conversation_record:
                    logger.info(f"Loaded existing {agent_type} conversation for user {self.user_id}")
                    self.conversations[agent_type] = conversation_record.conversation_data
                    self.output_histories[agent_type] = conversation_record.output_history
                    return True
                else:
                    logger.info(f"No existing {agent_type} conversation found for user {self.user_id}")
                    return False
        except Exception as e:
            logger.error(f"Error loading {agent_type} conversation: {e}", exc_info=True)
            return False
    
    def _save_to_database(self, agent_type="zene"):
        """Save current conversation state to the database for a specific agent type."""
        try:
            with self._session_scope() as session:
                # Check if record exists
                existing = session.query(ConversationData).filter_by(
                    user_id=self.user_id,
                    agent_type=agent_type
                ).first()
                
                if existing:
                    # Update existing record
                    existing.conversation_data = self.conversations[agent_type]
                    existing.output_history = self.output_histories[agent_type]
                    existing.updated_at = datetime.datetime.now()
                else:
                    # Create new record
                    new_record = ConversationData(
                        user_id=self.user_id,
                        agent_type=agent_type,
                        conversation_data=self.conversations[agent_type],
                        output_history=self.output_histories[agent_type]
                    )
                    session.add(new_record)
                
                logger.info(f"Saved {agent_type} conversation for user {self.user_id} to database")
                return True
        except Exception as e:
            logger.error(f"Error saving {agent_type} to database: {e}", exc_info=True)
            return False

    def __reset_conversation(self, agent_type="zene") -> str:
        """
        Reset the conversation history for a specific agent, generating a summary of previous interactions.
        
        Args:
            agent_type: Type of agent conversation to reset
            
        Returns:
            str: Summary of the previous conversation or error message
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
            
            # Track performance metrics
            start_time = time.time()
            
            # Generate summary
            model_name = "gpt-4o"
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.0,
                max_tokens=1000  # Limit summary length
            )
            
            # Calculate performance metrics
            end_time = time.time()
            latency = end_time - start_time
            content = response.choices[0].message.content
            
            # Log usage statistics
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "latency_seconds": latency
            }
            logger.info(f"{agent_type} summary generation - Token usage: {usage}")
            
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

    def reset_and_summarize_conversation(self, agent_type="zene") -> str:
        """
        Public method to reset the conversation and return a summary.
        
        Args:
            agent_type: Type of agent conversation to reset
            
        Returns:
            str: Summary of the previous conversation
        """
        return self.__reset_conversation(agent_type)

    def get_agent_response(self, agent_type: str, prompt: str, user_intent: str = None, model_name: str = "gpt-4o") -> str:
        """
        Get a response from a specific agent based on the given prompt.
        
        Args:
            agent_type: Type of agent to use ("zene" or "commet")
            prompt: User input prompt
            user_intent: User intent determined by previous agent (optional)
            model_name: Name of the OpenAI model to use
            
        Returns:
            Response content as a string
        """
        try:
            # Select the appropriate agent configuration
            if agent_type.lower() == "zene":
                agent_config = self.zene
            elif agent_type.lower() == "commet":
                agent_config = self.commet
            elif agent_type.lower() == "finn":
                agent_config = self.finn
            elif agent_type.lower() == "milo":
                agent_config = self.milo
            elif agent_type.lower() == "thalia":
                agent_config = self.thalia
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            sys_prompt = agent_config["system_prompt"]
            response_format = agent_config["response_schema"]
            
            messages = [
                {"role": "system", "content": sys_prompt}
            ]
            
            # Add conversation history if available
            if agent_type.lower() in  ["zene" , "commet"]:
                messages.extend(self.conversations[agent_type.lower()])
            
            # Add user intent if provided (for subsequent agents)
            if user_intent:
                messages.append({"role": "system", "content": f"User intent: {user_intent}"})
                prompt += "user intent" + user_intent
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            if  "gemini" in model_name:
                    return generate(sys_prompt , prompt)
            # For debugging
            os.makedirs("debugs", exist_ok=True)
            logger.debug(f"Debugging messages for {agent_type}: {messages}")
            debug_file = f"debugs/message_input_{agent_type.lower()}.json"
            with open(debug_file, "w") as f:
                json.dump(messages, f, indent=2)
            
            start_time = time.time()

            if model_name == "o3-mini":
                response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                reasoning_effort="high",
                response_format={
                    "type": "json_schema",
                    "json_schema": response_format
                },
            )
            else:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.0,
                    response_format={
                        "type": "json_schema",
                        "json_schema": response_format
                    },
                )
                
            end_time = time.time()
            latency = end_time - start_time
            
            content = response.choices[0].message.content

            # Calculate usage statistics
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "latency_seconds": latency
            }
            
            logger.info(f"{agent_type} token usage: {usage}")
            logger.info(f"{agent_type} latency: {latency:.2f} seconds")
            
            # Record the output for history
            self.output_histories[agent_type.lower()].append({
                "query": prompt,
                "response": content,
                "usage": usage,
                "latency_seconds": latency
            })
            
            # Update conversation history for this agent
            self.conversations[agent_type.lower()].append({
                "role": "user",
                "content": prompt,
            })
            self.conversations[agent_type.lower()].append({
                "role": "assistant",
                "content": content,
            })
            
            # Keep conversation history manageable
            if len(self.conversations[agent_type.lower()]) > 10:
                self.conversations[agent_type.lower()] = self.conversations[agent_type.lower()][-10:]
            
            # Save conversation to database
            self._save_to_database(agent_type.lower())
            
            return content
            
        except Exception as e:
            logger.error(f"Error for {agent_type} prompt: {prompt}\n{e}")
            return f"Error: {str(e)}"

    def get_response(self, prompt: str, model_name: str = "gpt-4o") -> str:
        """
        Get a response from OpenAI based on the given prompt.
        
        Args:
            prompt: User input prompt
            model_name: Name of the OpenAI model to use
            
        Returns:
            Response content as a string
        """
        # This is now a wrapper around get_agent_response for backward compatibility
        return self.get_agent_response("zene", prompt, model_name=model_name)
    
    def __call__(self, message: str) -> Dict[str, Any]:
        """
        Process a conversational message through the agent workforce.
        
        Args:
            message: User message
            
        Returns:
            Parsed JSON response from the final agent in the chain
        """
        logger.info(f"Processing message from gemini : {message}")
        
        # First, get response from Zene
        zene_response_str = self.get_agent_response("zene", message)
        
        try:
            zene_response = json.loads(zene_response_str)
            
            # Check if we need to route to another agent
            if "next_agent" in zene_response and zene_response["next_agent"].lower() == "commet":
                logger.info(f"Routing to Commet agent based on Zene response")
                
                # Extract user intent if available
                user_intent = zene_response.get("user_intent", "")
                
                # Get response from Commet agent
                commet_response_str = self.get_agent_response(
                    "commet", 
                    message, 
                    user_intent=user_intent
                )
                
                try:
                    commet_response = json.loads(commet_response_str)
                    return commet_response
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Commet response: {e}")
                    return {"error": f"Failed to parse Commet response: {str(e)}"}
            rag_responses = []
            if "vector_database_retrieval_queries" in zene_response:
                quiries = zene_response["vector_database_retrieval_queries"]
                
                for query in quiries[:1]:
                    # Perform vector database retrieval here
                    res = self.get_agent_response("finn",query )
                    try:
                        res = json.loads(res)
                        if "section_250_word_report" in res:
                            rag_responses.append(res["section_250_word_report"])
                        else:
                            rag_responses.append(res)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Finn response: {e}")
                        return {"error": f"Failed to parse Finn response: {str(e)}"}
            
            if "next_agent" in zene_response and zene_response["next_agent"].lower() == "milo":
                logger.info(f"Routing to Milo agent based on Zene response")
                
                # Extract user intent if available
                user_intent = zene_response.get("user_intent", "")
                
                # Create augmented message with Finn's content
                augmented_message = f"{message}\nFinn's content -> {str(rag_responses)}"
                
                # Get response from Milo agent
                milo_response_str = self.get_agent_response(
                    "milo", 
                    augmented_message,
                    user_intent=user_intent
                )
                
                try:
                    milo_response = json.loads(milo_response_str)
                    return milo_response
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Milo response: {e}")
                    return {"error": f"Failed to parse Milo response: {str(e)}"}
            
            if "next_agent" in zene_response and zene_response["next_agent"].lower() == "thalia":
                logger.info(f"Routing to Thalia agent based on Zene response")
                
                # Extract user intent if available
                user_intent = zene_response.get("user_intent", "")
                
                # Create augmented message with Finn's content
                augmented_message = f"{message}\nFinn's content -> {str(rag_responses)}"
                
                # Get response from Thalia agent
                thalia_response_str = self.get_agent_response(
                    "thalia", 
                    augmented_message,
                    user_intent=user_intent,
                    model_name= "gemini-2.0-flash"
                )
                
                try:
                    thalia_response = json.loads(thalia_response_str)
                    return thalia_response
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Thalia response: {e}")
                    return {"error": f"Failed to parse Thalia response: {str(e)}"}
        ## obj1 = Snowblaze(user_id="user123")
        ## res = obj1("user_query")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Zene response: {e}")
            return {"error": f"Failed to parse response: {str(e)}"}
    
    def save_conversation(self, agent_type="all", filename: str = None) -> None:
        """
        Save the current conversation to a file and database.
        
        Args:
            agent_type: Type of agent conversation to save ("all", "zene", "commet")
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
            
            os.makedirs("conversations", exist_ok=True)
            filepath = os.path.join("conversations", agent_filename)
            
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
                logger.error(f"Failed to save {agent} conversation: {e}")
            
    def delete_conversation(self, agent_type="all"):
        """
        Delete conversation(s) from the database.
        
        Args:
            agent_type: Type of agent conversation to delete ("all", "zene", "commet")
        """
        try:
            with self._session_scope() as session:
                if agent_type == "all":
                    session.query(ConversationData).filter_by(user_id=self.user_id).delete()
                    # Reset all in-memory conversations
                    for agent in self.conversations:
                        self.conversations[agent] = []
                        self.output_histories[agent] = []
                    logger.info(f"Deleted all conversations for user {self.user_id} from database")
                elif agent_type.lower() in self.conversations:
                    agent_type = agent_type.lower()
                    session.query(ConversationData).filter_by(
                        user_id=self.user_id, 
                        agent_type=agent_type
                    ).delete()
                    # Reset in-memory conversation for this agent
                    self.conversations[agent_type] = []
                    self.output_histories[agent_type] = []
                    logger.info(f"Deleted {agent_type} conversation for user {self.user_id} from database")
                else:
                    logger.error(f"Unknown agent type: {agent_type}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}", exc_info=True)
            return False

# Example usage
if __name__ == "__main__":
    # You can specify a database URL or let it default to SQLite
    # Example: db_url = "postgresql://user:password@localhost/snowblaze"
    zene_agent = SnowBlaze(user_id="user123")
    
    # If this is a returning user, their conversation history is already loaded
    response = zene_agent("Hello, how can you help me today?")
    print(json.dumps(response, indent=2))
    
    # Conversation is automatically saved to database after each interaction
    # You can also manually save to file
    zene_agent.save_conversation()
    
    
    
    