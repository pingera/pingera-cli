
"""
Multistep check result formatter
"""

from typing import Dict, Any, List
from .base_formatter import BaseFormatter


class MultistepFormatter(BaseFormatter):
    """Formatter for multistep check results"""
    
    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is multistep metadata"""
        return 'test_results' in metadata and 'test_summary' in metadata
    
    def format(self, metadata: Dict[str, Any]) -> str:
        """Format multistep check metadata"""
        info = "\n[bold cyan]Multistep Check Results:[/bold cyan]"
        
        # Execution time
        if 'execution_time' in metadata:
            info += f"\n• Total Execution Time: [yellow]{metadata['execution_time']}ms[/yellow]"
        
        # Test Summary
        if 'test_summary' in metadata:
            info += self._format_test_summary(metadata['test_summary'])
        
        # Test Results
        if 'test_results' in metadata and metadata['test_results']:
            info += self._format_test_results(metadata['test_results'])
        
        # Location info
        if 'region' in metadata:
            info += f"\n• Region: [white]{metadata['region']}[/white]"
        if 'provider' in metadata:
            info += f"\n• Provider: [white]{metadata['provider']}[/white]"
        
        # Logs
        if 'logs' in metadata and metadata['logs']:
            info += self._format_logs(metadata['logs'])
        
        return info
    
    def _format_test_summary(self, summary: Dict[str, Any]) -> str:
        """Format test summary"""
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        duration = summary.get('duration', 0)
        
        info = f"\n\n[bold cyan]Test Summary:[/bold cyan]"
        info += f"\n• Tests: [green]{passed} passed[/green], [red]{failed} failed[/red], [white]{total} total[/white]"
        info += f"\n• Duration: [yellow]{duration}ms[/yellow]"
        
        return info
    
    def _format_test_results(self, test_results: List[Dict[str, Any]]) -> str:
        """Format test results"""
        info = "\n\n[bold cyan]Test Results:[/bold cyan]"
        
        for i, test in enumerate(test_results, 1):
            status_color = "green" if test.get('status') == 'passed' else "red"
            status_icon = "✅" if test.get('status') == 'passed' else "❌"
            test_name = test.get('name', f'Test {i}')
            duration = test.get('duration', 0)
            
            info += f"\n• {test_name}: [{status_color}]{status_icon} {test.get('status', 'unknown')}[/{status_color}]"
            info += f" ([yellow]{duration}ms[/yellow])"
            
            # Soft assertion errors
            if test.get('softAssertionErrors', 0) > 0:
                info += f" [yellow]⚠️ {test['softAssertionErrors']} soft assertion errors[/yellow]"
            
            # Error details
            if test.get('error'):
                error_text = self._truncate_text(test['error'], 80) if not self.verbose else test['error']
                info += f"\n  [red]Error: {error_text}[/red]"
            
            # Steps
            if 'steps' in test and test['steps']:
                info += self._format_test_steps(test['steps'])
        
        return info
    
    def _format_test_steps(self, steps: List[Dict[str, Any]]) -> str:
        """Format test steps"""
        info = f"\n  [bold dim]Steps:[/bold dim]"
        
        for i, step in enumerate(steps, 1):
            status_color = "green" if step.get('status') == 'passed' else "red"
            status_icon = "✓" if step.get('status') == 'passed' else "✗"
            step_name = step.get('name', f'Step {i}')
            duration = step.get('duration', 0)
            
            info += f"\n    {i}. {step_name}: [{status_color}]{status_icon}[/{status_color}] ([dim]{duration}ms[/dim])"
            
            # Step error
            if step.get('error') and (self.verbose or step.get('status') == 'failed'):
                error_text = self._truncate_text(step['error'], 60) if not self.verbose else step['error']
                info += f"\n       [red]Error: {error_text}[/red]"
        
        return info
    
    def _format_logs(self, logs: List[Dict[str, Any]]) -> str:
        """Format execution logs"""
        info = "\n\n[bold cyan]Execution Logs:[/bold cyan]"
        
        if not self.verbose:
            info += f"\n• [dim]Found {len(logs)} log entries (use --verbose to see all)[/dim]"
            # Show only first few logs in non-verbose mode
            for log in logs[:3]:
                level = log.get('level', 'log')
                message = self._truncate_text(log.get('message', ''), 60)
                timestamp = log.get('timestamp', '')
                
                level_color = self._get_log_level_color(level)
                info += f"\n• [{level_color}]{level.upper()}[/{level_color}]: [dim]{message}[/dim]"
        else:
            # Show all logs in verbose mode
            for i, log in enumerate(logs, 1):
                level = log.get('level', 'log')
                message = log.get('message', '')
                timestamp = log.get('timestamp', '')
                
                level_color = self._get_log_level_color(level)
                info += f"\n• [{level_color}]{level.upper()}[/{level_color}] [{timestamp}]: {message}"
        
        return info
    
    def _get_log_level_color(self, level: str) -> str:
        """Get color for log level"""
        colors = {
            'error': 'red',
            'warn': 'yellow',
            'warning': 'yellow',
            'info': 'blue',
            'log': 'white',
            'debug': 'dim'
        }
        return colors.get(level.lower(), 'white')
