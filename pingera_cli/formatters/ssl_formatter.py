
"""
SSL check result formatter
"""

from typing import Dict, Any
from .base_formatter import BaseFormatter


class SSLFormatter(BaseFormatter):
    """Formatter for SSL check results"""
    
    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is SSL metadata"""
        return 'ssl_grade' in metadata or ('checks' in metadata and 'certificate_info' in metadata.get('checks', {}))
    
    def format(self, metadata: Dict[str, Any]) -> str:
        """Format SSL check metadata"""
        info = "\n[bold cyan]SSL Check Results:[/bold cyan]"
        
        # SSL Grade and Score
        if 'ssl_grade' in metadata:
            grade_color = "green" if metadata['ssl_grade'] in ['A+', 'A'] else "yellow" if metadata['ssl_grade'] in ['B', 'C'] else "red"
            info += f"\n• SSL Grade: [{grade_color}]{metadata['ssl_grade']}[/{grade_color}]"
        
        if 'ssl_score' in metadata:
            score_color = "green" if metadata['ssl_score'] >= 80 else "yellow" if metadata['ssl_score'] >= 60 else "red"
            info += f"\n• SSL Score: [{score_color}]{metadata['ssl_score']}/100[/{score_color}]"
        
        # Certificate Information
        if 'checks' in metadata and 'certificate_info' in metadata['checks']:
            info += self._format_certificate_info(metadata['checks']['certificate_info'])
        
        # Protocol Support
        if 'checks' in metadata and 'protocol_support' in metadata['checks']:
            info += self._format_protocol_support(metadata['checks']['protocol_support'])
        
        # Vulnerabilities
        if 'checks' in metadata and 'vulnerabilities' in metadata['checks']:
            info += self._format_vulnerabilities(metadata['checks']['vulnerabilities'])
        
        # Assessment Summary
        if 'deduction_summary' in metadata:
            info += "\n\n[bold cyan]Assessment Summary:[/bold cyan]"
            for summary in metadata['deduction_summary']:
                info += f"\n• [dim]{summary}[/dim]"
        
        return info
    
    def _format_certificate_info(self, cert: Dict[str, Any]) -> str:
        """Format certificate information"""
        info = "\n\n[bold cyan]Certificate Details:[/bold cyan]"
        
        if 'subject' in cert:
            info += f"\n• Subject: [white]{cert['subject']}[/white]"
        if 'issuer' in cert:
            info += f"\n• Issuer: [white]{cert['issuer']}[/white]"
        if 'not_before' in cert and 'not_after' in cert:
            info += f"\n• Valid From: [white]{cert['not_before']}[/white]"
            info += f"\n• Valid Until: [white]{cert['not_after']}[/white]"
        if 'key_size' in cert:
            info += f"\n• Key Size: [white]{cert['key_size']} bits[/white]"
        if 'signature_algorithm' in cert:
            info += f"\n• Signature Algorithm: [white]{cert['signature_algorithm']}[/white]"
        
        # Certificate validation checks
        if 'cert_date_valid' in cert:
            status = "✅ Valid" if cert['cert_date_valid'] else "❌ Invalid"
            info += f"\n• Date Valid: {status}"
        if 'hostname_mismatch' in cert:
            status = "❌ Mismatch" if cert['hostname_mismatch'] else "✅ Match"
            info += f"\n• Hostname: {status}"
        if 'in_trust_store' in cert:
            status = "✅ Trusted" if cert['in_trust_store'] else "❌ Not Trusted"
            info += f"\n• Trust Store: {status}"
        
        return info
    
    def _format_protocol_support(self, protocols: Dict[str, Any]) -> str:
        """Format protocol support information"""
        info = "\n\n[bold cyan]Protocol Support:[/bold cyan]"
        
        for protocol, details in protocols.items():
            if details.get('supported'):
                cipher_count = len(details.get('ciphers', []))
                info += f"\n• {protocol.upper().replace('_', '.')}: [green]✅ Supported[/green] ({cipher_count} ciphers)"
            else:
                info += f"\n• {protocol.upper().replace('_', '.')}: [red]❌ Not Supported[/red]"
        
        return info
    
    def _format_vulnerabilities(self, vulns: Dict[str, Any]) -> str:
        """Format vulnerability information"""
        info = "\n\n[bold cyan]Security Vulnerabilities:[/bold cyan]"
        
        for vuln_name, vuln_data in vulns.items():
            if vuln_data.get('vulnerable'):
                info += f"\n• {vuln_name.replace('_', ' ').title()}: [red]❌ Vulnerable[/red]"
                if 'details' in vuln_data:
                    info += f"\n  [dim]{vuln_data['details']}[/dim]"
            else:
                info += f"\n• {vuln_name.replace('_', ' ').title()}: [green]✅ Not Vulnerable[/green]"
        
        return info
