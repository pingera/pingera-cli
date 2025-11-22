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
        
        # Track if we need to show truncation notice
        has_truncation = False
        result_id = metadata.get('result_id')

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
            protocol_info, truncated = self._format_protocol_support(metadata['checks']['protocol_support'])
            info += protocol_info
            if truncated:
                has_truncation = True

        # Vulnerabilities
        if 'checks' in metadata and 'vulnerabilities' in metadata['checks']:
            vuln_info, truncated = self._format_vulnerabilities(metadata['checks']['vulnerabilities'])
            info += vuln_info
            if truncated:
                has_truncation = True

        # Assessment Summary
        if 'deduction_summary' in metadata:
            info += "\n\n[bold cyan]Assessment Summary:[/bold cyan]"
            for summary in metadata['deduction_summary']:
                info += f"\n• [dim]{summary}[/dim]"
        
        # Show truncation notice once at the bottom if needed
        if has_truncation and not self.verbose:
            info += "\n" + self._get_truncation_notice(result_id)

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

    def _format_protocol_support(self, protocols: Dict[str, Any]) -> tuple:
        """Format protocol support information. Returns (info, has_truncation)"""
        info = "\n\n[bold cyan]Protocol Support:[/bold cyan]"
        has_truncation = False

        for protocol, details in protocols.items():
            if details.get('supported'):
                cipher_count = len(details.get('ciphers', []))
                info += f"\n• {protocol.upper().replace('_', '.')}: [green]✅ Supported[/green] ({cipher_count} ciphers)"
                
                # Show cipher details
                cipher_details = details.get('cipher_details', [])
                if cipher_details:
                    if self.verbose:
                        # Show all ciphers in verbose mode
                        for cipher in cipher_details:
                            cipher_name = cipher.get('openssl_name', cipher.get('name', 'Unknown'))
                            key_size = cipher.get('key_size', 'N/A')
                            info += f"\n  - [dim]{cipher_name} ({key_size}-bit)[/dim]"
                    else:
                        # Show first 3 ciphers in non-verbose mode
                        display_count = min(3, len(cipher_details))
                        for cipher in cipher_details[:display_count]:
                            cipher_name = cipher.get('openssl_name', cipher.get('name', 'Unknown'))
                            key_size = cipher.get('key_size', 'N/A')
                            info += f"\n  - [dim]{cipher_name} ({key_size}-bit)[/dim]"
                        
                        if len(cipher_details) > display_count:
                            remaining = len(cipher_details) - display_count
                            info += f"\n  [dim]... and {remaining} more cipher(s)[/dim]"
                            has_truncation = True
            else:
                info += f"\n• {protocol.upper().replace('_', '.')}: [red]❌ Not Supported[/red]"

        return info, has_truncation

    def _format_vulnerabilities(self, vulns: Dict[str, Any]) -> tuple:
        """Format vulnerability information. Returns (info, has_truncation)"""
        info = "\n\n[bold cyan]Security Vulnerabilities:[/bold cyan]"
        has_truncation = False

        for vuln_name, vuln_data in vulns.items():
            if vuln_data.get('vulnerable'):
                info += f"\n• {vuln_name.replace('_', ' ').title()}: [red]❌ Vulnerable[/red]"
                if 'details' in vuln_data:
                    details = vuln_data['details']
                    if isinstance(details, list):
                        # Show first 3 items, then indicate there are more
                        display_items = details[:3]
                        for item in display_items:
                            info += f"\n  [dim]{item}[/dim]"
                        if len(details) > 3:
                            remaining = len(details) - 3
                            info += f"\n  [dim]... and {remaining} more item(s)[/dim]"
                            has_truncation = True
                    else:
                        info += f"\n  [dim]{details}[/dim]"
            else:
                info += f"\n• {vuln_name.replace('_', ' ').title()}: [green]✅ Not Vulnerable[/green]"

        return info, has_truncation

    