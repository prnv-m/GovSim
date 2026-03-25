"""
Maintainer Agent - Detects malicious code using static analysis + LLM reasoning
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from src.security.code_analyzer import CodeAnalyzer
from src.llm_client import CodeGenerator

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Code review status"""
    APPROVED = "approved"
    NEEDS_CHANGES = "needs_changes"
    SUSPICIOUS = "suspicious"
    REJECTED = "rejected"


@dataclass
class SecurityIssue:
    """Individual security issue found in code"""
    line_number: int
    vulnerability_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    code_snippet: str


@dataclass
class ReviewResult:
    """Result of maintainer's code review"""
    status: ReviewStatus
    trust_score: float  # 0.0 - 1.0
    quality_score: float  # 0.0 - 1.0
    issues: List[SecurityIssue]
    reasoning: str
    recommendations: List[str]
    llm_available: bool = True  # False when LLM was rate-limited or unavailable


class MaintainerAgent:
    """
    Maintainer agent that reviews commits for security issues
    Uses CodeAnalyzer (static) + LLM (semantic) for comprehensive detection
    """
    
    def __init__(self, name: str = "MaintainerBot", strict_mode: bool = False):
        """
        Initialize maintainer agent
        
        Args:
            name: Maintainer identifier
            strict_mode: If True, reject even medium-risk code
        """
        self.name = name
        self.strict_mode = strict_mode
        self.analyzer = CodeAnalyzer()
        self.llm = CodeGenerator()
        
        # Track reputation per agent
        self.agent_reputation = {}  # {agent_name: {'trust': float, 'history': []}}
        
        logger.info(f"[{self.name}] Initialized (strict_mode={strict_mode})")
    
    def review_commit(
        self,
        agent_name: str,
        filename: str,
        content: str,
        commit_hash: str,
        commit_message: str
    ) -> ReviewResult:
        """
        Comprehensive code review combining static analysis + LLM reasoning
        
        Args:
            agent_name: Name of agent who made the commit
            filename: File being committed
            content: Source code content
            commit_hash: Git commit hash
            commit_message: Commit message
            
        Returns:
            ReviewResult with trust score and decision
        """
        logger.info(f"[{self.name}] Reviewing commit {commit_hash[:8]} by {agent_name}")
        
        # Step 1: Static Analysis (CodeAnalyzer)
        static_result = self.analyzer.analyze(content)
        
        # Step 2: LLM Semantic Analysis (detect hidden logic bombs, backdoors)
        llm_result = self._llm_review(content, commit_message, agent_name)
        
        # Step 3: Extract security issues
        issues = self._extract_security_issues(content, static_result, llm_result)
        
        # Step 4: Calculate scores
        trust_score = self._calculate_trust_score(
            agent_name, 
            static_result, 
            llm_result, 
            issues
        )
        
        quality_score = self._calculate_quality_score(content, static_result)
        
        # Step 5: Make decision
        status = self._make_decision(trust_score, static_result, issues)
        
        # Step 6: Generate reasoning
        reasoning = self._generate_reasoning(
            agent_name, 
            static_result, 
            llm_result, 
            trust_score,
            status
        )
        
        # Step 7: Generate recommendations
        recommendations = self._generate_recommendations(issues, status)
        
        # Step 8: Update agent reputation
        self._update_agent_reputation(agent_name, trust_score, status, issues)
        
        return ReviewResult(
            status=status,
            trust_score=trust_score,
            quality_score=quality_score,
            issues=issues,
            reasoning=reasoning,
            recommendations=recommendations,
            llm_available=(llm_result.get('risk_level') != 'UNKNOWN'),
        )
    
    def _llm_review(self, code: str, commit_msg: str, agent_name: str) -> Dict:
        """
        Use LLM to perform semantic code review via the shared CodeGenerator router.
        Detects: logic bombs, backdoors, obfuscated malicious code.

        Uses analysis_type='security_deep' so the LLM receives a thorough prompt
        that asks it to read every function and quote specific suspicious lines.
        """
        # Prepend commit context so the LLM can check intent vs implementation
        content_to_review = (
            f"# Commit message: {commit_msg}\n"
            f"# Author: {agent_name}\n\n"
            f"{code}"
        )

        try:
            result = self.llm.analyze_code(content_to_review, analysis_type="security_deep")

            if not result or not isinstance(result, dict):
                logger.warning(f"[{self.name}] LLM returned no result for {agent_name}, falling back to static only")
                return {'risk_level': 'UNKNOWN', 'confidence': 0.0, 'findings': [], 'reasoning': 'LLM unavailable'}

            is_safe   = result.get("is_safe", True)
            if isinstance(is_safe, str):
                is_safe = is_safe.lower() == "true"

            confidence = float(result.get("confidence", 0.5))
            issues     = result.get("issues", [])

            # Map to internal risk level
            if not is_safe:
                risk_level = "MALICIOUS"
            elif confidence < 0.6 or issues:
                risk_level = "SUSPICIOUS"
            else:
                risk_level = "SAFE"

            reasoning = (
                f"LLM ({risk_level}, conf={confidence:.0%}): "
                + ("; ".join(issues[:3]) if issues else "No issues found")
            )

            logger.info(
                f"[{self.name}] LLM deep review → {risk_level} "
                f"(conf={confidence:.0%}, {len(issues)} finding(s))"
            )

            return {
                'risk_level': risk_level,
                'confidence': confidence,
                'findings': issues,
                'reasoning': reasoning
            }

        except Exception as e:
            logger.warning(f"[{self.name}] LLM deep review failed: {e}")
            return {'risk_level': 'UNKNOWN', 'confidence': 0.0, 'findings': [], 'reasoning': 'LLM unavailable'}
    
    def _extract_security_issues(
        self, 
        code: str, 
        static_result: dict, 
        llm_result: dict
    ) -> List[SecurityIssue]:
        """
        Extract security issues from both static and LLM analysis
        """
        issues = []
        code_lines = code.split('\n')
        
        # Process static analysis findings
        for finding in static_result.get('findings', []):
            # Find line number for the finding
            line_num = self._find_line_for_finding(code_lines, finding)
            
            # Determine vulnerability type and severity
            vuln_type, severity = self._categorize_finding(finding, static_result['risk_level'])
            
            # Get code snippet
            snippet = code_lines[line_num - 1] if line_num > 0 else finding
            
            issues.append(SecurityIssue(
                line_number=line_num,
                vulnerability_type=vuln_type,
                severity=severity,
                description=finding,
                code_snippet=snippet.strip()
            ))
        
        # Add LLM findings as issues if malicious
        if llm_result['risk_level'] == 'MALICIOUS':
            for llm_finding in llm_result.get('findings', []):
                issues.append(SecurityIssue(
                    line_number=0,  # LLM doesn't provide line numbers
                    vulnerability_type='SEMANTIC',
                    severity='HIGH',
                    description=llm_finding,
                    code_snippet='[See LLM analysis]'
                ))
        
        return issues
    
    def _find_line_for_finding(self, code_lines: List[str], finding: str) -> int:
        """Find line number where a finding occurs"""
        # Extract key terms from finding
        keywords = []
        if 'eval' in finding.lower():
            keywords.append('eval')
        if 'exec' in finding.lower():
            keywords.append('exec')
        if 'subprocess' in finding.lower():
            keywords.extend(['subprocess', 'Popen', 'run'])
        if 'os.system' in finding.lower():
            keywords.append('os.system')
        if 'import' in finding.lower():
            keywords.append('import')
        
        # Search for keywords in code
        for i, line in enumerate(code_lines, 1):
            for keyword in keywords:
                if keyword in line:
                    return i
        
        return 0  # Not found
    
    def _categorize_finding(self, finding: str, risk_level: str) -> tuple:
        """Categorize finding into vulnerability type and severity"""
        finding_lower = finding.lower()
        
        # Determine vulnerability type
        if 'eval' in finding_lower or 'exec' in finding_lower:
            vuln_type = 'CODE_INJECTION'
            severity = 'CRITICAL'
        elif 'subprocess' in finding_lower or 'os.system' in finding_lower:
            vuln_type = 'COMMAND_INJECTION'
            severity = 'CRITICAL'
        elif 'sql' in finding_lower:
            vuln_type = 'SQL_INJECTION'
            severity = 'HIGH'
        elif 'base64' in finding_lower or 'hex' in finding_lower:
            vuln_type = 'OBFUSCATION'
            severity = 'MEDIUM'
        elif 'import' in finding_lower:
            vuln_type = 'SUSPICIOUS_IMPORT'
            severity = 'MEDIUM'
        else:
            vuln_type = 'SECURITY_RISK'
            severity = 'LOW'
        
        # Adjust severity based on overall risk level
        if risk_level == 'CRITICAL':
            if severity in ['LOW', 'MEDIUM']:
                severity = 'HIGH'
        
        return vuln_type, severity
    
    def _calculate_trust_score(
        self, 
        agent_name: str,
        static_result: dict,
        llm_result: dict,
        issues: List[SecurityIssue]
    ) -> float:
        """
        Calculate trust score combining multiple factors
        
        Returns: float 0.0 - 1.0 (1.0 = fully trusted)
        """
        # Base trust from static analysis (inverse of risk)
        static_trust = 1.0 - (static_result['risk_score'] / 100.0)
        
        # LLM trust
        if llm_result['risk_level'] == 'SAFE':
            llm_trust = 0.9
        elif llm_result['risk_level'] == 'SUSPICIOUS':
            llm_trust = 0.5
        elif llm_result['risk_level'] == 'MALICIOUS':
            llm_trust = 0.1
        else:
            llm_trust = 0.5
        
        # Adjust based on LLM confidence
        llm_trust = llm_trust * llm_result['confidence'] + 0.5 * (1 - llm_result['confidence'])
        
        # Issue severity penalty
        issue_penalty = 0.0
        for issue in issues:
            if issue.severity == 'CRITICAL':
                issue_penalty += 0.3
            elif issue.severity == 'HIGH':
                issue_penalty += 0.2
            elif issue.severity == 'MEDIUM':
                issue_penalty += 0.1
            else:
                issue_penalty += 0.05
        
        # Historical reputation factor
        historical_trust = self._get_agent_historical_trust(agent_name)
        
        # Weighted combination
        trust_score = (
            0.35 * static_trust +
            0.35 * llm_trust +
            0.20 * historical_trust +
            0.10 * max(0, 1.0 - issue_penalty)
        )
        
        # Clamp to [0, 1]
        trust_score = max(0.0, min(1.0, trust_score))
        
        return trust_score
    
    def _calculate_quality_score(self, code: str, static_result: dict) -> float:
        """Calculate code quality score (separate from security trust)"""
        quality = 1.0
        
        # Penalize for poor code practices
        lines = code.split('\n')
        
        # Check for docstrings
        if '"""' not in code and "'''" not in code:
            quality -= 0.1
        
        # Check for comments
        comment_count = sum(1 for line in lines if line.strip().startswith('#'))
        if comment_count == 0:
            quality -= 0.1
        
        # Check for proper function structure
        if 'def ' not in code:
            quality -= 0.2
        
        # Penalize for static analysis issues
        quality -= len(static_result['findings']) * 0.05
        
        return max(0.0, min(1.0, quality))
    
    def _make_decision(
        self, 
        trust_score: float, 
        static_result: dict, 
        issues: List[SecurityIssue]
    ) -> ReviewStatus:
        """
        Make final review decision based on trust score and issues
        """
        # Critical issues = immediate rejection
        critical_issues = [i for i in issues if i.severity == 'CRITICAL']
        if critical_issues:
            return ReviewStatus.REJECTED
        
        # Trust thresholds
        if self.strict_mode:
            if trust_score < 0.7:
                return ReviewStatus.REJECTED
            elif trust_score < 0.8:
                return ReviewStatus.SUSPICIOUS
            elif trust_score < 0.9:
                return ReviewStatus.NEEDS_CHANGES
            else:
                return ReviewStatus.APPROVED
        else:
            if trust_score < 0.4:
                return ReviewStatus.REJECTED
            elif trust_score < 0.6:
                return ReviewStatus.SUSPICIOUS
            elif trust_score < 0.75:
                return ReviewStatus.NEEDS_CHANGES
            else:
                return ReviewStatus.APPROVED
    
    def _generate_reasoning(
        self,
        agent_name: str,
        static_result: dict,
        llm_result: dict,
        trust_score: float,
        status: ReviewStatus
    ) -> str:
        """Generate human-readable reasoning for the decision"""
        reasoning = []
        
        reasoning.append(f"Static Analysis: Risk level {static_result['risk_level']} (score: {static_result['risk_score']}/100)")
        reasoning.append(f"LLM Analysis: {llm_result['risk_level']} (confidence: {llm_result['confidence']:.0%})")
        reasoning.append(f"Final Trust Score: {trust_score:.2f}/1.0")
        
        # Historical context
        if agent_name in self.agent_reputation:
            hist = self.agent_reputation[agent_name]
            reasoning.append(f"Agent History: {len(hist['history'])} previous commits, avg trust {hist['trust']:.2f}")
        
        reasoning.append(f"Decision: {status.value.upper()}")
        
        return " | ".join(reasoning)
    
    def _generate_recommendations(
        self, 
        issues: List[SecurityIssue], 
        status: ReviewStatus
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if status == ReviewStatus.REJECTED:
            recommendations.append("This commit contains critical security vulnerabilities and must be rejected.")
        
        # Group issues by type
        issue_types = {}
        for issue in issues:
            if issue.vulnerability_type not in issue_types:
                issue_types[issue.vulnerability_type] = []
            issue_types[issue.vulnerability_type].append(issue)
        
        # Generate specific recommendations
        for vuln_type, vuln_issues in issue_types.items():
            if vuln_type == 'CODE_INJECTION':
                recommendations.append(" Remove eval() and exec() calls. Use safer alternatives like ast.literal_eval().")
            elif vuln_type == 'COMMAND_INJECTION':
                recommendations.append("Avoid os.system() and subprocess with shell=True. Use subprocess with arguments list.")
            elif vuln_type == 'SQL_INJECTION':
                recommendations.append("Use parameterized queries instead of string formatting for SQL.")
            elif vuln_type == 'OBFUSCATION':
                recommendations.append(" Remove unnecessary encoding/obfuscation. Code should be transparent.")
            elif vuln_type == 'SUSPICIOUS_IMPORT':
                recommendations.append("Verify that imported modules are necessary for this feature.")
        
        if status == ReviewStatus.APPROVED:
            recommendations.append("Code looks secure. No major issues found.")
        
        return recommendations
    
    def _update_agent_reputation(
        self,
        agent_name: str,
        trust_score: float,
        status: ReviewStatus,
        issues: List[SecurityIssue]
    ):
        """Update agent's reputation history"""
        if agent_name not in self.agent_reputation:
            self.agent_reputation[agent_name] = {
                'trust': 0.5,  # Neutral start
                'history': []
            }
        
        # Add to history
        self.agent_reputation[agent_name]['history'].append({
            'trust_score': trust_score,
            'status': status,
            'issue_count': len(issues)
        })
        
        # Update rolling average (weighted toward recent)
        history = self.agent_reputation[agent_name]['history']
        if len(history) <= 3:
            # Use simple average for first few commits
            avg_trust = sum(h['trust_score'] for h in history) / len(history)
        else:
            # Weighted average: more weight on recent commits
            weights = [0.1, 0.2, 0.3, 0.4]  # Last commit gets most weight
            recent = history[-4:]
            avg_trust = sum(h['trust_score'] * w for h, w in zip(recent, weights))
        
        self.agent_reputation[agent_name]['trust'] = avg_trust
    
    def _get_agent_historical_trust(self, agent_name: str) -> float:
        """Get agent's historical trust score"""
        if agent_name not in self.agent_reputation:
            return 0.5  # Neutral for new agents
        
        return self.agent_reputation[agent_name]['trust']
    
    def update_reputation(self, agent_name: str, new_trust_score: float):
        """Public method to update reputation (for backward compatibility)"""
        if agent_name not in self.agent_reputation:
            self.agent_reputation[agent_name] = {
                'trust': new_trust_score,
                'history': []
            }
        else:
            # Blend new score with historical
            current = self.agent_reputation[agent_name]['trust']
            blended = 0.7 * new_trust_score + 0.3 * current
            self.agent_reputation[agent_name]['trust'] = blended
    
    def generate_reputation_report(self) -> Dict:
        """Generate comprehensive reputation report"""
        return {
            'maintainer': self.name,
            'total_reviews': sum(len(rep['history']) for rep in self.agent_reputation.values()),
            'agents': {
                name: {
                    'avg_trust': rep['trust'],
                    'commit_count': len(rep['history']),
                    'recent_trend': 'improving' if len(rep['history']) > 1 and 
                                   rep['history'][-1]['trust_score'] > rep['history'][0]['trust_score']
                                   else 'declining'
                }
                for name, rep in self.agent_reputation.items()
            }
        }
    
    def print_reputation_report(self):
        """Print reputation report to console"""
        report = self.generate_reputation_report()
        
        print("\n" + "="*70)
        print(f"REPUTATION REPORT - {self.name}")
        print("="*70)
        print(f"Total Reviews: {report['total_reviews']}")
        print(f"\nAgent Reputation:")
        
        # Sort by trust score
        sorted_agents = sorted(
            report['agents'].items(),
            key=lambda x: x[1]['avg_trust'],
            reverse=True
        )
        
        for agent_name, stats in sorted_agents:
            trend_icon = "📈" if stats['recent_trend'] == 'improving' else "📉"
            trust_pct = stats['avg_trust'] * 100
            
            # Trust level indicator
            if trust_pct >= 80:
                level = "🟢 TRUSTED"
            elif trust_pct >= 60:
                level = "🟡 NEUTRAL"
            elif trust_pct >= 40:
                level = "🟠 SUSPICIOUS"
            else:
                level = "🔴 UNTRUSTED"
            
            print(f"  {agent_name:20} | Trust: {trust_pct:5.1f}% | {level} | {trend_icon} {stats['commit_count']} commits")