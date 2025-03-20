import json
import logging
import os
import time
from typing import Dict, Any, List
from prompts import Zene , summary , user_knowledge
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SnowBlaze:
    """
    A simplified conversational agent that uses Zene for interactions.
    """
    def __reset_conversation(self) -> str:
        """
        Reset the conversation history, generating a summary of previous interactions.
        
        Returns:
            str: Summary of the previous conversation or error message
        """
        logger.info("Resetting conversation history")
        try:
            # Skip processing if conversation is empty
            if not self.conversations:
                logger.info("No conversation history to reset")
                return "No conversation history to summarize"
                
            # Prepare message for summary generation
            messages = [
                {"role": "system", "content": self.summary},
                {"role": "user", "content": "Summarize the following conversation: " + 
                 json.dumps([conv for conv in self.conversations if conv.get("content")])}
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
            logger.info(f"Summary generation - Token usage: {usage}")
            logger.info(f"Summary generation - Latency: {latency:.2f} seconds")
            
            # Reset conversation but keep summary as context
            self.conversations = []
            self.conversations.append({
                "role": "system",
                "content": f"Previous conversation summary: {content}"
            })
            
            # Record summary in history
            self.output_history.append({
                "action": "conversation_reset",
                "summary": content,
                "usage": usage,
                "timestamp": time.time()
            })
            
            logger.info("Conversation history reset with summary")
            return content
            
        except Exception as e:
            logger.error(f"Failed to reset conversation: {str(e)}", exc_info=True)
            return f"Error resetting conversation: {str(e)}"

    def reset_and_summarize_conversation(self) -> str:
        """
        Public method to reset the conversation and return a summary.
        
        Returns:
            str: Summary of the previous conversation
        """
        return self.__reset_conversation()

    def __init__(self, user_id: str):
        """
        Initialize the SnowBlaze with user ID and OpenAI client.
        
        Args:
            user_id: User ID for conversation tracking
        """
        load_dotenv()
        self.user_id = user_id
        self.client = openai.OpenAI()
        self.conversations = []
        self.output_history = []
        self.summary = summary
        self.zene = Zene
        
    def get_response(self, prompt: str, model_name: str = "gpt-4o") -> str:
        """
        Get a response from OpenAI based on the given prompt.
        
        Args:
            prompt: User input prompt
            model_name: Name of the OpenAI model to use
            
        Returns:
            Response content as a string
        """
        try:
            sys_prompt = self.zene["system_prompt"]
            response_format = self.zene["response_schema"]
            
            messages = [
                {"role": "system", "content": sys_prompt}
            ]
            
            # Add conversation history if available
            messages.extend(self.conversations)
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            start_time = time.time()
            
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
            
            logger.info(f"Token usage: {usage}")
            logger.info(f"Latency: {latency:.2f} seconds")
            
            # Record the output for history
            self.output_history.append({
                "query": prompt,
                "response": content,
                "usage": usage,
                "latency_seconds": latency
            })
            
            return content
            
        except Exception as e:
            logger.error(f"Error for prompt: {prompt}\n{e}")
            return f"Error: {str(e)}"
    
    def __call__(self, message: str) -> Dict[str, Any]:
        """
        Process a conversational message through Zene.
        
        Args:
            message: User message
            
        Returns:
            Parsed JSON response
        """
        logger.info(f"Processing message: {message}")
        
        response = self.get_response(prompt=message)
        
        try:
            response_json = json.loads(response)
            
            # Update conversation history
            self.conversations.append({
                "role": "user",
                "content": message,
            })
            self.conversations.append({
                "role": "assistant",
                "content": response,
            })
            
            # Keep conversation history manageable
            if len(self.conversations) > 10:
                self.conversations = self.conversations[-10:]
                
            return response_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}")
            return {"error": f"Failed to parse response: {str(e)}"}
            
    def save_conversation(self, filename: str = None) -> None:
        """
        Save the current conversation to a file.
        
        Args:
            filename: Optional filename to save to
        """
        if not filename:
            filename = f"conversation_{self.user_id}_{int(time.time())}.json"
        
        os.makedirs("conversations", exist_ok=True)
        filepath = os.path.join("conversations", filename)
        
        try:
            with open(filepath, "w") as f:
                json.dump({
                    "user_id": self.user_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "conversation": self.conversations,
                    "usage_stats": self.output_history
                }, f, indent=2)
            logger.info(f"Conversation saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")

# Example usage
if __name__ == "__main__":
    zene_agent = SnowBlaze(user_id="user123")
    response = zene_agent.converse("Hello, how can you help me today?")
    print(json.dumps(response, indent=2))
    zene_agent.save_conversation()