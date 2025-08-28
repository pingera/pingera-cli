"""
Synthetic/Browser check result formatter
"""

from typing import Dict, Any, List
from .base_formatter import BaseFormatter


class SyntheticFormatter(BaseFormatter):
    """Formatter for synthetic/browser check results"""

    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is synthetic metadata"""
        return 'execution_time' in metadata and 'pages' in metadata

    def format(self, metadata: Dict[str, Any]) -> str:
        """Format synthetic check metadata"""
        info = "\n[bold cyan]Synthetic Check Results:[/bold cyan]"

        # Execution time
        if 'execution_time' in metadata:
            info += f"\n• Total Execution Time: [yellow]{metadata['execution_time']}ms[/yellow]"

        # Test Summary
        if 'test_summary' in metadata:
            info += self._format_test_summary(metadata['test_summary'])

        # Test Results
        if 'test_results' in metadata:
            info += self._format_test_results(metadata['test_results'])

        # Logs
        if 'logs' in metadata and metadata['logs']:
            info += self._format_logs(metadata['logs'])

        # Page Performance
        if 'pages' in metadata and metadata['pages']:
            info += self._format_page_performance(metadata['pages'][0])

        return info

    def _format_test_summary(self, summary: Dict[str, Any]) -> str:
        """Format test summary"""
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        return f"\n• Tests: [green]{passed} passed[/green], [red]{failed} failed[/red], [white]{total} total[/white]"

    def _format_test_results(self, test_results: List[Dict[str, Any]]) -> str:
        """Format test results"""
        info = "\n\n[bold cyan]Test Results:[/bold cyan]"

        for test in test_results:
            status_color = "green" if test.get('status') == 'passed' else "red"
            status_icon = "✅" if test.get('status') == 'passed' else "❌"
            info += f"\n• {test.get('name', 'Unnamed Test')}: [{status_color}]{status_icon} {test.get('status', 'unknown')}[/{status_color}]"

            if test.get('duration'):
                info += f" ([yellow]{test['duration']}ms[/yellow])"
            if test.get('error'):
                info += f"\n  [red]Error: {test['error']}[/red]"

            # Browser Screenshots/Videos
            if 'browser_metadata' in test:
                info += self._format_browser_metadata(test['browser_metadata'])

        return info

    def _format_browser_metadata(self, browser_meta: Dict[str, Any]) -> str:
        """Format browser metadata (screenshots, videos)"""
        info = ""

        if browser_meta.get('screenshots'):
            info += f"\n• Screenshots: [blue]{len(browser_meta['screenshots'])} available[/blue]"
            screenshot_limit = None if self.verbose else 3
            for screenshot in browser_meta['screenshots'][:screenshot_limit]:
                name = screenshot.get('name', 'screenshot')
                # Add download link if available
                if 'url' in screenshot:
                    info += f"\n  - [dim]{name}[/dim] - [blue]{screenshot['url']}[/blue]"
                elif 'download_url' in screenshot:
                    info += f"\n  - [dim]{name}[/dim] - [blue]{screenshot['download_url']}[/blue]"
                else:
                    info += f"\n  - [dim]{name}[/dim]"
            if not self.verbose and len(browser_meta['screenshots']) > 3:
                info += f"\n  - [dim]... and {len(browser_meta['screenshots']) - 3} more (use --verbose to see all)[/dim]"

        if browser_meta.get('videos'):
            info += f"\n• Videos: [blue]{len(browser_meta['videos'])} available[/blue]"
            if self.verbose:
                for video in browser_meta['videos']:
                    name = video.get('name', 'video')
                    if 'url' in video:
                        info += f"\n  - [dim]{name}[/dim] - [blue]{video['url']}[/blue]"
                    elif 'download_url' in video:
                        info += f"\n  - [dim]{name}[/dim] - [blue]{video['download_url']}[/blue]"
                    else:
                        info += f"\n  - [dim]{name}[/dim]"

        return info

    def _format_logs(self, logs: List[Dict[str, Any]]) -> str:
        """Format execution logs"""
        info = "\n\n[bold cyan]Execution Logs:[/bold cyan]"
        log_limit = None if self.verbose else 5

        for i, log in enumerate(logs[:log_limit]):
            level = log.get('level', 'info')
            level_color = {"error": "red", "warn": "yellow", "info": "blue", "log": "white"}.get(level, "white")
            timestamp = log.get('timestamp', 'Unknown time')
            message = log.get('message', 'No message')
            info += f"\n• [{level_color}]{level.upper()}[/{level_color}] [{timestamp}]: {message}"

        if not self.verbose and len(logs) > 5:
            info += f"\n• [dim]... and {len(logs) - 5} more logs (use --verbose to see all)[/dim]"

        return info

    def _format_page_performance(self, page: Dict[str, Any]) -> str:
        """Format page performance data"""
        info = "\n\n[bold cyan]Page Performance:[/bold cyan]"

        if 'duration' in page:
            info += f"\n• Page Load Duration: [yellow]{page['duration']:.2f}ms[/yellow]"

        # Web Vitals
        if 'webVitals' in page:
            info += self._format_web_vitals(page['webVitals'])

        # Network requests
        if 'network' in page:
            info += self._format_network_requests(page['network'])

        # Document request details
        if 'documentRequest' in page:
            info += self._format_document_request(page['documentRequest'])

        return info

    def _format_web_vitals(self, vitals: Dict[str, Any]) -> str:
        """Format Web Vitals data"""
        info = "\n• Web Vitals:"
        if 'FCP' in vitals:
            info += f"\n  - First Contentful Paint: [yellow]{vitals['FCP']}ms[/yellow]"
        if 'LCP' in vitals:
            info += f"\n  - Largest Contentful Paint: [yellow]{vitals['LCP']}ms[/yellow]"
        if 'TTFB' in vitals:
            info += f"\n  - Time to First Byte: [yellow]{vitals['TTFB']}ms[/yellow]"
        if self.verbose and 'CLS' in vitals:
            info += f"\n  - Cumulative Layout Shift: [yellow]{vitals['CLS']}[/yellow]"
        if self.verbose and 'FID' in vitals:
            info += f"\n  - First Input Delay: [yellow]{vitals['FID']}ms[/yellow]"
        return info

    def _format_network_requests(self, network: List[Dict[str, Any]]) -> str:
        """Format network requests"""
        info = f"\n• Network Requests: [white]{len(network)} total[/white]"

        # Summarize by resource type
        resource_types = {}
        for req in network:
            res_type = req.get('resourceType', 'unknown')
            resource_types[res_type] = resource_types.get(res_type, 0) + 1

        for res_type, count in resource_types.items():
            info += f"\n  - {res_type}: [blue]{count}[/blue]"

        # Show detailed network requests in verbose mode
        if self.verbose:
            info += self._format_detailed_network_requests(network)

        return info

    def _format_detailed_network_requests(self, network: List[Dict[str, Any]]) -> str:
        """Format detailed network requests (verbose mode)"""
        info = "\n\n[bold cyan]Detailed Network Requests:[/bold cyan]"

        # In verbose mode, show ALL requests, not just first 20
        limit = len(network) if self.verbose else 20

        for i, req in enumerate(network[:limit]):
            url = req.get('url', 'Unknown URL')
            method = req.get('method', 'GET')

            # Extract status from response field with better logic
            status = self._extract_status(req)
            size = self._extract_size(req)
            duration = self._extract_duration(req)
            res_type = req.get('resourceType', 'unknown')

            # Color code status
            status_display = self._format_status_code(status)
            size_display = self._format_size(size)
            duration_display = self._format_duration(duration)

            info += f"\n• [{method}] {status_display} [{res_type}] {size_display} {duration_display}"
            info += self._format_url_with_breaks(url)

        # Only show truncation message if NOT in verbose mode
        if not self.verbose and len(network) > 20:
            info += f"\n• [dim]... and {len(network) - 20} more requests (use --verbose to see all)[/dim]"

        return info

    def _extract_status(self, req: Dict[str, Any]) -> Any:
        """Extract status code from request with improved logic"""
        # Try multiple possible locations for status code
        if 'response' in req and req['response'] and isinstance(req['response'], dict):
            response = req['response']
            if 'status' in response:
                return response['status']
            if 'statusCode' in response:
                return response['statusCode']

        # Try direct status field
        if 'status' in req:
            return req['status']
        if 'statusCode' in req:
            return req['statusCode']

        # Try nested in other common locations
        if 'networkResponse' in req and req['networkResponse']:
            net_resp = req['networkResponse']
            if 'status' in net_resp:
                return net_resp['status']

        # For failed requests, they might not have a response
        if req.get('failed') or req.get('errorText'):
            return 'Failed'

        return 'Unknown'

    def _extract_size(self, req: Dict[str, Any]) -> int:
        """Extract size from request with improved logic"""
        # Try multiple possible locations for size data
        if 'response' in req and req['response'] and isinstance(req['response'], dict):
            response_data = req['response']

            # Try different size fields in order of preference
            for size_field in ['encodedDataLength', 'transferSize', 'decodedBodyLength', 'contentLength']:
                if size_field in response_data and response_data[size_field] is not None:
                    return int(response_data[size_field])

        # Try direct size fields
        for size_field in ['encodedDataLength', 'transferSize', 'size', 'contentLength']:
            if size_field in req and req[size_field] is not None:
                return int(req[size_field])

        return 0

    def _extract_duration(self, req: Dict[str, Any]) -> float:
        """Extract duration from request with improved logic"""
        # Try direct duration field first
        if 'duration' in req and req['duration'] is not None and req['duration'] > 0:
            return float(req['duration'])

        # Calculate from timing if available
        if 'timing' in req and req['timing']:
            timing = req['timing']
            if 'responseEnd' in timing and 'requestStart' in timing:
                duration = timing['responseEnd'] - timing['requestStart']
                if duration > 0:
                    return duration

        # Try other common duration fields
        for duration_field in ['responseTime', 'loadTime', 'totalTime']:
            if duration_field in req and req[duration_field] is not None:
                return float(req[duration_field])

        return 0

    def _format_status_code(self, status: Any) -> str:
        """Format status code with appropriate color"""
        if isinstance(status, int):
            if 200 <= status < 300:
                return f"[green]{status}[/green]"
            elif 400 <= status < 500:
                return f"[yellow]{status}[/yellow]"
            elif status >= 500:
                return f"[red]{status}[/red]"
            else:
                return f"[white]{status}[/white]"
        elif str(status).lower() == 'failed':
            return f"[red]Failed[/red]"
        else:
            return f"[white]{status}[/white]"

    def _format_url_with_breaks(self, url: str) -> str:
        """Format URL with line breaks for readability"""
        if len(url) <= 90:
            return f"\n  [dim]{url}[/dim]"

        # Find a good break point
        break_points = ['/', '?', '&', '=']
        best_break = 80
        for bp in break_points:
            pos = url.rfind(bp, 50, 85)
            if pos > 0:
                best_break = pos + 1
                break

        return f"\n  [dim]{url[:best_break]}[/dim]\n  [dim]{url[best_break:]}[/dim]"

    def _format_document_request(self, doc_req: Dict[str, Any]) -> str:
        """Format main document request details"""
        info = "\n\n[bold cyan]Main Document Request:[/bold cyan]"

        if 'url' in doc_req:
            info += f"\n• URL: [white]{doc_req['url']}[/white]"
        if 'method' in doc_req:
            info += f"\n• Method: [white]{doc_req['method']}[/white]"
        if 'statusCode' in doc_req:
            status_code = doc_req['statusCode']
            if 200 <= status_code < 300:
                info += f"\n• Status: [green]{status_code}[/green]"
            elif 400 <= status_code < 500:
                info += f"\n• Status: [yellow]{status_code}[/yellow]"
            else:
                info += f"\n• Status: [red]{status_code}[/red]"

        if self.verbose and 'responseHeaders' in doc_req:
            info += self._format_response_headers(doc_req['responseHeaders'])

        return info

    def _format_response_headers(self, headers: Dict[str, Any]) -> str:
        """Format response headers"""
        info = "\n• Response Headers:"

        if self.verbose:
            # In verbose mode, show ALL headers
            for header, value in headers.items():
                info += f"\n  - {header}: [dim]{value}[/dim]"
        else:
            # In non-verbose mode, show important headers only
            important_headers = [
                'content-type', 'content-length', 'server', 'cache-control',
                'x-frame-options', 'strict-transport-security'
            ]

            for header in important_headers:
                if header in headers:
                    value = self._truncate_text(headers[header])
                    info += f"\n  - {header}: [dim]{value}[/dim]"

            other_count = len(headers) - len([h for h in important_headers if h in headers])
            if other_count > 0:
                info += f"\n  - [dim]... and {other_count} more headers[/dim]"

        return info