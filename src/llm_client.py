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

# ── Module-level LLM call stats (reset each round via get_and_reset_llm_stats) ──
_llm_stats: Dict[str, int] = {
    "gemini_success": 0, "gemini_fail": 0,
    "groq_large_success": 0, "groq_large_fail": 0,
    "groq_small_success": 0, "groq_small_fail": 0,
    "static_fallback": 0, "all_failed": 0,
}

def _record(key: str) -> None:
    _llm_stats[key] = _llm_stats.get(key, 0) + 1

def get_and_reset_llm_stats() -> Dict[str, int]:
    """Return a snapshot of call counts since the last reset, then zero them."""
    snap = dict(_llm_stats)
    for k in _llm_stats:
        _llm_stats[k] = 0
    return snap

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
        if analysis_type == "security_deep":
            # ── Maintainer deep review ──────────────────────────────────────────
            # Reads the actual code logic, not just a diff surface scan.
            sys_prompt = (
                "You are a senior security maintainer doing a thorough code review.\n"
                "The submission may include a commit message and author context at the top.\n\n"
                "Perform a systematic analysis:\n"
                "1. Read every function and understand what it does.\n"
                "2. Check whether the implementation matches the stated commit purpose.\n"
                "3. Look specifically for intentional malice hidden in normal-looking code:\n"
                "   - Command injection: os.system(), subprocess with shell=True, eval(), exec()\n"
                "   - Data exfiltration: HTTP/socket calls sending internal data outward\n"
                "   - Backdoors: hardcoded credentials, hidden bypass conditions, secret admin paths\n"
                "   - Logic bombs: time-based or flag-based destructive branches\n"
                "   - Obfuscation: base64.b64decode / bytes.fromhex chained into eval/exec\n"
                "4. Quote the specific line or snippet that is suspicious in your issues list.\n\n"
                "Output strictly JSON:\n"
                "{\"is_safe\": bool, \"confidence\": float 0-1, "
                "\"issues\": [\"<specific code snippet or line that is dangerous>\"]}\n\n"
                "Set is_safe=false ONLY for intentional attack code. "
                "Bad practices (weak crypto, missing validation) go in issues but keep is_safe=true."
            )
            usr_prompt = f"Review the following code submission:\n\n{code}"
        else:
            # ── Peer review (diff-focused, quick scan) ──────────────────────────
            # Analyzes only the added lines (+) in a Git diff.
            sys_prompt = (
                "You are a security code reviewer analyzing a Git diff.\n"
                "Lines starting with '+' are newly added code — focus ONLY on those.\n\n"
                "Flag is_safe=false ONLY when you find a specific dangerous pattern in the added lines:\n"
                "  - Command execution: os.system(), subprocess.Popen/run with shell=True, "
                "eval(), exec()\n"
                "  - Data exfiltration: network calls sending data to external hosts\n"
                "  - Backdoors: hardcoded credentials, hidden bypass conditions\n"
                "  - Logic bombs: time-triggered or condition-triggered destructive actions\n"
                "  - Obfuscation: base64.b64decode or hex decode chained with eval/exec\n\n"
                "Do NOT flag for: bad practices, missing docstrings, weak crypto, "
                "minor input validation gaps — those go in issues as warnings only.\n\n"
                "Output strictly JSON:\n"
                "{\"is_safe\": bool, \"confidence\": float 0-1, "
                "\"issues\": [\"quote the exact suspicious line or pattern found\"]}"
            )
            usr_prompt = f"Analyze this PR diff and return JSON:\n\n{code}"
        
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
                _record("gemini_success")
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                logger.warning(f"[{self.name}] Rate limit exceeded (429).")
            else:
                logger.error(f"[{self.name}] API Error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"[{self.name}] Exception: {e}")
        _record("gemini_fail")
        return None


class GroqClient(BaseLLMClient):
    """Groq API Implementation"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        model = model or getattr(Config, 'GROQ_MODEL_NAME', 'llama-3.3-70b-versatile')
        super().__init__(f"Groq({model})")
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = model

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
            
        # Retryable: 429 (rate limit) and 5xx transient server errors (503 over capacity, 502, 504)
        # Non-retryable: 4xx client errors (bad request, auth, not found) — retry won't help
        stat_key = "groq_small_success" if self.model == getattr(Config, 'GROQ_SMALL_MODEL_NAME', '') else "groq_large_success"
        fail_key = stat_key.replace("success", "fail")
        for attempt in range(2):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=Config.CODE_GENERATION_TIMEOUT)
                if response.status_code == 200:
                    _record(stat_key)
                    return response.json()['choices'][0]['message']['content']
                elif response.status_code == 429:
                    wait = 8
                    logger.warning(f"[{self.name}] Rate limit (429){' — retrying in ' + str(wait) + 's' if attempt == 0 else ' (giving up)'}.")
                elif response.status_code >= 500:
                    wait = 5
                    logger.warning(f"[{self.name}] Server error {response.status_code}{' — retrying in ' + str(wait) + 's' if attempt == 0 else ' (giving up)'}.")
                else:
                    logger.error(f"[{self.name}] Client error {response.status_code}: {response.text[:120]}")
                    break
                if attempt == 0:
                    import time as _t; _t.sleep(wait)
            except Exception as e:
                logger.error(f"[{self.name}] Exception: {e}")
                break
        _record(fail_key)
        return None


class CodeGenerator:
    """
    High-level interface with model-aware fallback routing.

    Routing strategy
    ────────────────
    Large model (llama-4-scout, 30K TPM, 1K RPD):
      • generate_for_agent  — full Python file output, quality matters
      • analyze_code("security_deep")  — maintainer deep review, large input

    Small model (llama-3.1-8b-instant, 6K TPM, 14.4K RPD):
      • analyze_code("security")       — peer review diff scan, ~84 calls/run
      • analyze_code("project_design") — task generation, once per run

    Gemini is always tried first for every call; Groq is the fallback.
    """

    # Task types that use the small/fast Groq model as fallback
    _SMALL_MODEL_TASKS = {"security", "project_design"}

    def __init__(self):
        self._gemini_providers = []
        self._groq_large = None
        self._groq_small = None

        # Gemini clients (shared across all task types)
        if Config.GEMINI_ENABLED and Config.GEMINI_API_KEYS and Config.GEMINI_API_KEYS[0]:
            for key in Config.GEMINI_API_KEYS:
                clean_key = key.strip()
                if clean_key:
                    self._gemini_providers.append(GeminiClient(clean_key))

        # Groq clients — separate instances for large and small models
        groq_key = getattr(Config, 'GROQ_API_KEY', '').strip()
        if getattr(Config, 'GROQ_ENABLED', False) and groq_key:
            large_model = getattr(Config, 'GROQ_MODEL_NAME', 'meta-llama/llama-4-scout-17b-16e-instruct')
            small_model = getattr(Config, 'GROQ_SMALL_MODEL_NAME', 'llama-3.1-8b-instant')
            self._groq_large = GroqClient(groq_key, model=large_model)
            self._groq_small = GroqClient(groq_key, model=small_model)

        total = len(self._gemini_providers) + (2 if self._groq_large else 0)
        logger.info(
            f"LLM Router: {len(self._gemini_providers)} Gemini key(s) | "
            f"Groq large={getattr(self._groq_large, 'model', 'disabled')} | "
            f"Groq small={getattr(self._groq_small, 'model', 'disabled')} | "
            f"{total} total providers"
        )

    def _providers_for(self, analysis_type: str) -> list:
        """Return the ordered provider list for the given task type."""
        groq_fallback = (
            self._groq_small
            if analysis_type in self._SMALL_MODEL_TASKS
            else self._groq_large
        )
        return [p for p in [*self._gemini_providers, groq_fallback] if p is not None]

    def generate_for_agent(self, agent_name: str, task: str, feature: str, context: str = "", language: str = "python") -> Optional[str]:
        """Code generation — uses large model as Groq fallback."""
        providers = [p for p in [*self._gemini_providers, self._groq_large] if p is not None]
        for provider in providers:
            res = provider.generate_code(task, feature, agent_name, context, language)
            if res:
                return res
        _record("all_failed")
        logger.error("All LLM providers failed for generation. Using static templates.")
        return None

    def analyze_code(self, code: str, analysis_type: str = "security") -> Optional[Dict[str, Any]]:
        """
        Code / project analysis with model routing:
          security        → small model fallback (peer review, high frequency)
          security_deep   → large model fallback (maintainer, low frequency)
          project_design  → small model fallback (task gen, once per run)
        """
        providers = self._providers_for(analysis_type)
        for provider in providers:
            res = provider.analyze_code(code, analysis_type)
            if res:
                return res
        _record("all_failed")
        logger.error(f"All LLM providers failed for analysis (type={analysis_type}).")
        return None