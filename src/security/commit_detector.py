"""
Detect malicious commits in repository
"""

import logging
import subprocess
from typing import Dict
from pathlib import Path
from src.security.code_analyzer import CodeAnalyzer

logger = logging.getLogger(__name__)


class CommitDetector:
    """Detects malicious commits by analyzing code"""
    
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.analyzer = CodeAnalyzer()
    
    def analyze_all_commits(self) -> Dict[str, Dict]:
        """
        Analyze all commits in repository
        
        Returns:
            {
                'commit_hash': {
                    'author': 'agent_name',
                    'message': 'commit message',
                    'risk_level': 'CRITICAL',
                    'findings': [...]
                },
                ...
            }
        """
        results = {}
        
        try:
            # Get all commits
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H", "--reverse"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Git log failed: {result.stderr}")
                return results
            
            commits = [c.strip() for c in result.stdout.strip().split('\n') if c.strip()]
            
            logger.info(f"[INFO] Found {len(commits)} commits to analyze")
            
            for commit_hash in commits:
                try:
                    # Get commit details
                    details = self._get_commit_details(commit_hash)
                    
                    # Analyze code changes
                    analysis = self._analyze_commit_code(commit_hash)
                    
                    # Store results
                    results[commit_hash] = {
                        'author': details.get('author'),
                        'message': details.get('message'),
                        'risk_level': analysis['risk_level'],
                        'risk_score': analysis['risk_score'],
                        'findings': analysis['findings']
                    }
                
                except Exception as e:
                    logger.warning(f"Error analyzing commit {commit_hash}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error analyzing commits: {e}")
        
        return results
    
    def _get_commit_details(self, commit_hash: str) -> Dict:
        """Get commit author and message"""
        try:
            if not isinstance(commit_hash, str):
                commit_hash = str(commit_hash)
            
            result = subprocess.run(
                ["git", "show", "--pretty=format:%an|%s", "-s", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {'author': 'Unknown', 'message': 'Unknown'}
            
            output = result.stdout.strip()
            if '|' in output:
                parts = output.split('|', 1)  # Split on first | only
                if len(parts) >= 2:  # ← Add this safety check
                    return {
                        'author': parts.strip(),
                        'message': parts.strip()
                    }
            
            return {
                'author': 'Unknown',
                'message': output
            }
        except Exception as e:
            logger.warning(f"Error getting commit details for {commit_hash}: {e}")
            return {'author': 'Unknown', 'message': 'Unknown'}

    
    def _analyze_commit_code(self, commit_hash: str) -> Dict:
        """Analyze Python files in commit"""
        try:
            if not isinstance(commit_hash, str):
                commit_hash = str(commit_hash)
            
            # Get all Python files in commit
            result = subprocess.run(
                ["git", "show", "--name-only", "--pretty=", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    'risk_level': 'UNKNOWN',
                    'risk_score': 0,
                    'findings': ['Could not analyze commit files']
                }
            
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            python_files = [f for f in files if f.endswith('.py')]
            
            if not python_files:
                return {
                    'risk_level': 'LOW',
                    'risk_score': 0,
                    'findings': ['No Python files in commit']
                }
            
            # Analyze each file
            max_risk_score = 0
            all_findings = []
            
            for file in python_files:
                try:
                    # Get file content at this commit
                    show_result = subprocess.run(
                        ["git", "show", f"{commit_hash}:{file}"],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if show_result.returncode == 0:
                        analysis = self.analyzer.analyze(show_result.stdout)
                        max_risk_score = max(max_risk_score, analysis['risk_score'])
                        all_findings.extend(analysis['findings'])
                except Exception as e:
                    logger.warning(f"Could not analyze {file}: {e}")
                    continue
            
            # Determine overall risk level
            if max_risk_score >= 70:
                risk_level = 'CRITICAL'
            elif max_risk_score >= 50:
                risk_level = 'HIGH'
            elif max_risk_score >= 30:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'risk_level': risk_level,
                'risk_score': max_risk_score,
                'findings': all_findings
            }
        
        except Exception as e:
            logger.error(f"Error analyzing commit {commit_hash}: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'risk_score': 0,
                'findings': [f'Error: {str(e)}']
            }
    
    def generate_report(self, results: Dict) -> str:
        """Generate human-readable report"""
        report = "\n" + "="*70 + "\n"
        report += "MALICIOUS COMMIT DETECTION REPORT\n"
        report += "="*70 + "\n"
        
        critical_count = 0
        high_count = 0
        medium_count = 0
        
        for commit_hash, details in results.items():
            risk_level = details['risk_level']
            
            if risk_level == 'CRITICAL':
                critical_count += 1
            elif risk_level == 'HIGH':
                high_count += 1
            elif risk_level == 'MEDIUM':
                medium_count += 1
            
            if risk_level in ['CRITICAL', 'HIGH']:
                report += f"\n[{risk_level}] {commit_hash[:8]} by {details['author']}\n"
                report += f"  Message: {details['message']}\n"
                report += f"  Risk Score: {details['risk_score']}/100\n"
                report += f"  Findings:\n"
                for finding in details['findings']:
                    report += f"    - {finding}\n"
        
        report += "\n" + "="*70 + "\n"
        report += "SUMMARY\n"
        report += "="*70 + "\n"
        report += f"CRITICAL: {critical_count}\n"
        report += f"HIGH: {high_count}\n"
        report += f"MEDIUM: {medium_count}\n"
        report += f"Total Suspicious: {critical_count + high_count + medium_count}\n"
        
        return report
