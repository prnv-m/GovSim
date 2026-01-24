"""
LLM Client for Gemini API
Generates unique code for agents using Gemini AI
"""

import json
import logging
import requests
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Client for calling Gemini API
    Follows exact pattern from user specification
    """
    
    def __init__(self, api_key: str = None):
        """Initialize with API key"""
        if api_key is None:
            # Assumes Config.GEMINI_API_KEYS is a list; takes first entry
            api_key = Config.GEMINI_API_KEYS[0] if isinstance(Config.GEMINI_API_KEYS, list) else Config.GEMINI_API_KEYS
        
        self.api_key = api_key
        self.model_name = Config.GEMINI_MODEL_NAME
        self.api_url = Config.GEMINI_API_URL
        
        if not self.api_key:
            logger.error("Cannot initialize Gemini client: No API key provided")
    
    def call_gemini_api(self, messages: list) -> Optional[Dict[str, Any]]:
        """
        Calls Gemini REST API, cleans response, provides detailed logging
        
        STRICTLY FOLLOWS USER PATTERN:
        - messages = system_prompt
        - messages = user_prompt
        - Combine both into single prompt
        - Parse JSON response
        - Clean markdown wrappers
        """
        
        if not self.api_key:
            logger.error("Cannot call Gemini API: Key is missing.")
            return None
        
        try:
            # FIX: Accessing list elements by index
            system_prompt = messages[0]['content']
            user_prompt = messages[1]['content']
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Construct payload
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": combined_prompt}
                        ]
                    }
                ]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            
            logger.info("LOG: Sending request to Gemini REST API...")
            logger.debug(f"LOG: Prompt length: {len(combined_prompt)} chars")
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=Config.CODE_GENERATION_TIMEOUT
            )
            
            # Check response status
            if response.status_code == 200:
                response_data = response.json()
                
                # FIX: Correct nesting for Gemini API response
                try:
                    candidates = response_data.get('candidates', [])
                    if not candidates:
                        raise KeyError("No candidates found")
                    
                    generated_text = candidates[0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    logger.error(f"LOG: Gemini response malformed. Response: {response_data}")
                    return None
                
                logger.debug(f"LOG: Raw text from Gemini: '{generated_text[:200]}...'")
                
                # Clean markdown wrappers
                text_stripped = generated_text.strip()
                if text_stripped.startswith("```json"):
                    cleaned_text = text_stripped[7:-3].strip()
                elif text_stripped.startswith("```"):
                    cleaned_text = text_stripped[3:-3].strip()
                else:
                    cleaned_text = text_stripped
                
                logger.debug(f"LOG: Cleaned text length: {len(cleaned_text)} chars")
                
                # Parse JSON
                try:
                    parsed_json = json.loads(cleaned_text)
                    logger.debug(f"LOG: Successfully parsed JSON. Type: {type(parsed_json)}")
                    return parsed_json
                except json.JSONDecodeError:
                    # Fallback if the response is intended to be raw text/code
                    return cleaned_text
                    
            else:
                logger.error(f"LOG: Gemini API error. Status: {response.status_code}, Response: {response.text}")
                return None
                
        except requests.Timeout:
            logger.error(f"LOG: Gemini API request timed out.")
            return None
        except Exception as e:
            logger.error(f"LOG: Exception in call_gemini_api: {e}", exc_info=True)
            return None
    
    def generate_code(
        self,
        task: str,
        feature: str,
        agent_name: str,
        context: str = "",
        language: str = "python"
    ) -> Optional[str]:
        """Generate code for specific task/feature"""
        
        system_prompt = f"""You are an expert {language} developer. Your name is {agent_name}. 
Return ONLY the code wrapped in ```{language} ... ``` markers."""
        
        user_prompt = f"Task: {task}\nFeature: {feature}\nContext: {context if context else 'No constraints'}"
        
        messages = [
            {"role": "user", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info(f"LOG: Generating code for {agent_name} - {feature}")
        response = self.call_gemini_api(messages)
        
        if response and isinstance(response, dict) and 'code' in response:
            return response.get('code', '')
        elif response and isinstance(response, str):
            return response
        return None

    def analyze_code(self, code: str, analysis_type: str = "security") -> Optional[Dict[str, Any]]:
        """Analyze code for issues/patterns"""
        system_prompt = f"You are a {analysis_type} analyzer. Return JSON findings."
        user_prompt = f"Analyze this code for {analysis_type} issues:\n\n{code}"
        
        messages = [
            {"role": "user", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.call_gemini_api(messages)

class CodeGenerator:
    """High-level interface with load balancing"""
    
    def __init__(self):
        self.clients = [GeminiClient(key) for key in Config.GEMINI_API_KEYS]
        self.current_client_idx = 0
        logger.info(f"LOG: Initialized with {len(self.clients)} keys")
    
    def get_next_client(self) -> GeminiClient:
        client = self.clients[self.current_client_idx]
        self.current_client_idx = (self.current_client_idx + 1) % len(self.clients)
        return client
    
    def generate_for_agent(self, agent_name: str, task: str, feature: str, context: str = "", language: str = "python") -> Optional[str]:
        client = self.get_next_client()
        return client.generate_code(task, feature, agent_name, context, language)