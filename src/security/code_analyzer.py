"""
Enhanced Code Analyzer - More Aggressive Detection
"""

import ast
import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class EnhancedCodeAnalyzer:
    """
    Analyzes Python code for suspicious patterns
    Enhanced version with more aggressive detection
    """
    
    def __init__(self):
        self.suspicious_patterns = {
            # Command execution
            'subprocess': ['Popen', 'run', 'call', 'check_output'],
            'os_system': ['os.system', 'os.popen', 'os.exec'],
            'eval': ['eval', 'exec', 'compile'],
            
            # File operations
            'file_access': ['open', 'write', 'read', 'remove', 'unlink'],
            
            # Network operations
            'network': ['socket', 'urllib', 'requests', 'http.client'],
            
            # Hidden strings
            'string_encoding': ['base64', 'hex', 'encode', 'decode'],
            
            # Dangerous imports
            'dangerous_imports': ['pickle', 'shelve', 'marshal'],
        }
        
        # Patterns that are ALWAYS malicious
        self.critical_patterns = [
            'eval(',
            'exec(',
            'os.system(',
            '__import__',
            'subprocess.Popen',
            'subprocess.call',
            'subprocess.run',
        ]
        
        # Patterns for hardcoded secrets
        self.secret_patterns = [
            r'PASSWORD\s*=\s*["\']',
            r'API_KEY\s*=\s*["\']',
            r'SECRET\s*=\s*["\']',
            r'TOKEN\s*=\s*["\']',
            r'admin123',
            r'password123',
            r'sk_live_',
            r'sk_test_',
        ]
        
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
        
        # Check for critical patterns FIRST (don't even need to parse)
        self._check_critical_patterns(code)
        
        # Check for hardcoded secrets
        self._check_hardcoded_secrets(code)
        
        try:
            # Parse code
            tree = ast.parse(code)
        except SyntaxError as e:
            # Syntax errors are suspicious
            self.findings.append(f'Syntax error (possibly obfuscated): {e}')
            self.risk_score += 20
            return self._generate_result()
        
        # Check for suspicious imports
        self._check_imports(tree)
        
        # Check for suspicious function calls
        self._check_function_calls(tree)
        
        # Check for suspicious string operations
        self._check_string_operations(tree, code)
        
        # Check for SQL injection patterns
        self._check_sql_injection(tree, code)
        
        return self._generate_result()
    
    def _check_critical_patterns(self, code: str):
        """Check for patterns that are ALWAYS malicious"""
        for pattern in self.critical_patterns:
            if pattern in code:
                self.findings.append(f"CRITICAL: Found dangerous pattern '{pattern}'")
                self.risk_score += 30  # Heavy penalty
    
    def _check_hardcoded_secrets(self, code: str):
        """Check for hardcoded passwords/API keys"""
        for pattern in self.secret_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                self.findings.append(f"Hardcoded credential detected: {pattern}")
                self.risk_score += 25
    
    def _check_imports(self, tree):
        """Check for suspicious imports"""
        dangerous_modules = {
            'subprocess': 20,
            'os': 15,
            'socket': 20,
            'urllib': 15,
            'requests': 10,
            'pickle': 25,  # Pickle is dangerous
            'marshal': 20,
            'eval': 30,
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for module, score in dangerous_modules.items():
                        if module in alias.name:
                            self.findings.append(f"Suspicious import: {alias.name}")
                            self.risk_score += score
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for module, score in dangerous_modules.items():
                        if module in node.module:
                            self.findings.append(f"Suspicious import: from {node.module}")
                            self.risk_score += score
    
    def _check_function_calls(self, tree):
        """Check for suspicious function calls"""
        dangerous_calls = {
            'eval': 30,
            'exec': 30,
            'compile': 20,
            '__import__': 25,
            'open': 10,  # File access
            'system': 25,
            'popen': 25,
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Direct function calls
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_calls:
                        self.findings.append(f"Dangerous function: {node.func.id}()")
                        self.risk_score += dangerous_calls[node.func.id]
                
                # Attribute calls like os.system()
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    if func_name in dangerous_calls:
                        self.findings.append(f"Dangerous function: .{func_name}()")
                        self.risk_score += dangerous_calls[func_name]
    
    def _check_string_operations(self, tree, code: str):
        """Check for suspicious string operations"""
        # Base64 encoding (often used to hide malicious code)
        if 'base64' in code or 'b64decode' in code or 'b64encode' in code:
            self.findings.append("Base64 encoding detected (may hide malicious code)")
            self.risk_score += 15
        
        # Hex encoding
        if '\\x' in code or 'hex' in code.lower():
            self.findings.append("Hex encoding detected")
            self.risk_score += 10
        
        # Obfuscated strings
        if code.count('\\x') > 5:  # Multiple hex chars
            self.findings.append("Heavily obfuscated strings detected")
            self.risk_score += 20
    
    def _check_sql_injection(self, tree, code: str):
        """Check for SQL injection patterns"""
        # Look for string formatting in SQL-like strings
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE']
        
        for node in ast.walk(tree):
            # Check for f-strings or .format() with SQL
            if isinstance(node, ast.JoinedStr):  # f-string
                # Get the string content (simplified check)
                if any(keyword in code for keyword in sql_keywords):
                    # Check if there are variables in the f-string
                    if node.values:
                        self.findings.append("Potential SQL injection: f-string with SQL keywords")
                        self.risk_score += 25
            
            # Check for % formatting or .format()
            elif isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Mod):  # % operator
                    # Simplified check for SQL in string operations
                    pass  # Would need more complex AST analysis
        
        # Regex check for obvious SQL injection patterns
        sql_injection_patterns = [
            r'SELECT.*FROM.*WHERE.*=.*["\'].*\{',
            r'f["\'].*SELECT.*\{',
            r'["\'].*SELECT.*["\'].*%',
        ]
        
        for pattern in sql_injection_patterns:
            if re.search(pattern, code, re.IGNORECASE | re.DOTALL):
                self.findings.append("SQL injection vulnerability detected")
                self.risk_score += 25
    
    def _generate_result(self) -> Dict:
        """Generate final result"""
        # Determine risk level with more aggressive thresholds
        if self.risk_score >= 60:  # Lowered from 70
            risk_level = 'CRITICAL'
        elif self.risk_score >= 40:  # Lowered from 50
            risk_level = 'HIGH'
        elif self.risk_score >= 20:  # Lowered from 30
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_level': risk_level,
            'risk_score': min(100, self.risk_score),  # Cap at 100
            'findings': self.findings,
            'is_malicious': risk_level in ['HIGH', 'CRITICAL']
        }


# Backward compatibility - replace CodeAnalyzer with EnhancedCodeAnalyzer
CodeAnalyzer = EnhancedCodeAnalyzer