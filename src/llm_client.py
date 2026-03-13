"""
LLM Client for Gemini API & Groq API
Supports automatic fallbacks and Native JSON Mode
"""

import json
import logging
import requests
import re
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger("govim")

class BaseLLMClient:
    """Base class for all LLM providers"""
    def __init__(self, name: str):
        self.name = name

    def call_api(self, system_prompt: str, user_prompt: str, is_json: bool = False) -> Optional[str]:
        raise NotImplementedError
        
    def _extract_code(self, text: str) -> str:
        """Extracts strictly code from a markdown response"""
        match = re.search(r'```(?:python)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Fallback: Just remove backticks if it missed the regex
        return text.replace("```", "").strip()

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Safely extract JSON from a response"""
        # 1. Try parsing directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # 2. Try parsing from markdown block
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
                
        # 3. Last resort: bracket extraction
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
                
        return None

    def generate_code(self, task: str, feature: str, agent_name: str, context: str = "", language: str = "python") -> Optional[str]:
        sys_prompt = f"You are an expert {language} developer named {agent_name}. Return ONLY code. Do not include explanations."
        usr_prompt = f"Task: {task}\nFeature: {feature}\nContext: {context}"
        
        raw_text = self.call_api(sys_prompt, usr_prompt, is_json=False)
        if raw_text:
            return self._extract_code(raw_text)
        return None

    def analyze_code(self, code: str, analysis_type: str = "security") -> Optional[Dict[str, Any]]:
        sys_prompt = (
            "You are a Senior Security Reviewer. Your goal is to identify INTENTIONAL MALICE.\n\n"
            "CRITERIA:\n"
            "1. IS_SAFE = FALSE: Only if you find clear evidence of an attack (e.g., os.system, eval, "
            "hardcoded backdoors, intentional data exfiltration, or logical loops meant to crash the system).\n"
            "2. IS_SAFE = TRUE: If the code is functional but has 'bad practices' (like using SHA-256 instead of Bcrypt, "
            "missing docstrings, or minor input validation gaps). Mention these in 'issues' as warnings, but DO NOT reject the PR.\n\n"
            "Output strictly JSON with 'is_safe' (bool), 'confidence' (float), and 'issues' (list)."
        )
        usr_prompt = f"Review this PR diff and output JSON:\n\n{code}"
        
        raw_text = self.call_api(sys_prompt, usr_prompt, is_json=True)
        if raw_text:
            parsed = self._extract_json(raw_text)
            if parsed:
                return parsed
            logger.warning(f"[{self.name}] JSON parsing failed. Raw text snippet: {raw_text[:100]}")
        return None


class GeminiClient(BaseLLMClient):
    """Google Gemini Implementation"""
    
    def __init__(self, api_key: str):
        super().__init__("Gemini")
        self.api_key = api_key
        self.api_url = Config.GEMINI_API_URL
        
    def call_api(self, system_prompt: str, user_prompt: str, is_json: bool = False) -> Optional[str]:
        if not self.api_key: return None
            
        payload = {
            "contents": [{"parts":[{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        
        # NATIVE JSON MODE FOR GEMINI
        if is_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"
            
        headers = {'Content-Type': 'application/json', 'X-goog-api-key': self.api_key}
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=Config.CODE_GENERATION_TIMEOUT)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                logger.warning(f"[{self.name}] Rate limit exceeded (429).")
            else:
                logger.error(f"[{self.name}] API Error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"[{self.name}] Exception: {e}")
        return None


class GroqClient(BaseLLMClient):
    """Groq API Implementation"""
    
    def __init__(self, api_key: str):
        super().__init__("Groq")
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = getattr(Config, 'GROQ_MODEL_NAME', 'llama-3.3-70b-versatile')
        
    def call_api(self, system_prompt: str, user_prompt: str, is_json: bool = False) -> Optional[str]:
        if not self.api_key: return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages":[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        
        # NATIVE JSON MODE FOR GROQ
        if is_json:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=Config.CODE_GENERATION_TIMEOUT)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 429:
                logger.warning(f"[{self.name}] Rate limit exceeded (429).")
            else:
                logger.error(f"[{self.name}] API Error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"[{self.name}] Exception: {e}")
        return None


class CodeGenerator:
    """High-level interface with Fallback Routing"""
    
    def __init__(self):
        self.providers =[]
        
        # Add Gemini clients
        if Config.GEMINI_ENABLED and Config.GEMINI_API_KEYS and Config.GEMINI_API_KEYS[0]:
            for key in Config.GEMINI_API_KEYS:
                clean_key = key.strip()
                if clean_key:
                    self.providers.append(GeminiClient(clean_key))
                
        # Add Groq client
        if getattr(Config, 'GROQ_ENABLED', False) and getattr(Config, 'GROQ_API_KEY', ''):
            groq_key = Config.GROQ_API_KEY.strip()
            if groq_key:
                self.providers.append(GroqClient(groq_key))
            
        logger.info(f"LOG: Initialized LLM Router with {len(self.providers)} providers.")
    
    def generate_for_agent(self, agent_name: str, task: str, feature: str, context: str = "", language: str = "python") -> Optional[str]:
        for provider in self.providers:
            res = provider.generate_code(task, feature, agent_name, context, language)
            if res:
                return res
        logger.error("All LLM providers failed for generation. Using static templates.")
        return None

    def analyze_code(self, code: str, analysis_type: str = "security") -> Optional[Dict[str, Any]]:
        for provider in self.providers:
            res = provider.analyze_code(code, analysis_type)
            if res:
                return res
        logger.error("All LLM providers failed for analysis.")
        return None