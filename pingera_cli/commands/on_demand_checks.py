
"""
On-demand checks commands for PingeraCLI
"""

import os
from typing import Optional

import typer
from rich.table import Table
from rich.panel import Panel

from .base import BaseCommand
from ..utils.config import get_api_key

# Supported check types for on-demand execution
SUPPORTED_CHECK_TYPES = ["web", "api", "tcp", "ssl", "dns", "icmp", "portscan", "synthetic", "multistep"]


class OnDemandChecksCommand(BaseCommand):
    """
    Commands for managing on-demand monitoring checks
    """
    
    def __init__(self, output_format: Optional[str] = None, verbose: bool = False):
        super().__init__(output_format)
        self.verbose = verbose
    
    def _parse_check_file(self, file_path: str) -> dict:
        """Parse check configuration from JSON or YAML file (local or URL)"""
        from ..utils.file_utils import load_check_file, is_url
        
        try:
            if is_url(file_path):
                self.display_info(f"Downloading check configuration from: {file_path}")
            
            return load_check_file(file_path)
            
        except Exception as e:
            self.display_error(str(e))
            raise typer.Exit(1)
        
    def get_client(self):
        """Get Pingera SDK client with authentication for on-demand checks"""
        api_key = get_api_key()
        if not api_key:
            self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
            raise typer.Exit(1)
        
        try:
            from pingera import ApiClient, Configuration
            from pingera.api import OnDemandChecksApi
            from ..utils.config import get_config
            
            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key
            
            # Create API client
            api_client = ApiClient(configuration)
            return OnDemandChecksApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def execute_custom_check(self, url: Optional[str] = None, check_type: str = "web", host: Optional[str] = None, port: Optional[int] = None, timeout: Optional[int] = None, name: str = "On-demand check", regions: Optional[str] = None, parameters: Optional[str] = None, pw_script_file: Optional[str] = None, from_file: Optional[str] = None, wait_for_result: bool = True, ports: Optional[str] = None):
        """Execute custom on-demand check"""
        try:
            import json
            import os
            checks_api = self.get_client()
            
            # Import the SDK models
            from pingera.models import ExecuteCustomCheckRequest
            
            # If creating from file, parse file and merge with command line options
            if from_file:
                file_data = self._parse_check_file(from_file)
                
                # Filter only SDK-recognized fields from file data
                # This ignores marketplace-specific fields and other extensions
                sdk_fields = ["name", "type", "url", "host", "port", "timeout", "parameters", "secrets"]
                filtered_file_data = {k: v for k, v in file_data.items() if k in sdk_fields}
                
                # Command line options take precedence over file data
                check_data = {
                    "name": filtered_file_data.get("name", name),
                    "type": filtered_file_data.get("type", check_type)
                }
                
                # Handle timeout - only set if explicitly provided or in file
                if timeout is not None:
                    check_data["timeout"] = timeout
                elif "timeout" in filtered_file_data:
                    check_data["timeout"] = filtered_file_data["timeout"]
                
                # Override with command line values if provided
                if name != "On-demand check":  # Only override if name was explicitly provided
                    check_data["name"] = name
                if check_type != "web":  # Only override if type was explicitly provided
                    check_data["type"] = check_type
                if timeout != 30:  # Only override if timeout was explicitly provided
                    check_data["timeout"] = timeout
                
                # Handle URL from file
                if url is None and filtered_file_data.get("url"):
                    url = filtered_file_data["url"]
                elif url is not None:
                    # Command line URL takes precedence
                    pass
                
                # Handle host/port from file
                if host is None and filtered_file_data.get("host"):
                    host = filtered_file_data["host"]
                elif host is not None:
                    # Command line host takes precedence
                    pass
                    
                if port is None and filtered_file_data.get("port"):
                    port = filtered_file_data["port"]
                elif port is not None:
                    # Command line port takes precedence
                    pass
                
                # Handle parameters from file
                file_parameters = filtered_file_data.get("parameters")
                if file_parameters and parameters is None:
                    # Use file parameters if no command line parameters
                    parameters = json.dumps(file_parameters) if isinstance(file_parameters, dict) else file_parameters
                
                # Handle secrets from file
                if filtered_file_data.get("secrets"):
                    check_data["secrets"] = filtered_file_data["secrets"]
                
                # Handle pw_script_file from file (this is CLI-specific, not sent to SDK)
                if pw_script_file is None and file_data.get("pw_script_file"):
                    pw_script_file = file_data["pw_script_file"]
                
                # Show info about ignored fields if any
                ignored_fields = [k for k in file_data.keys() if k not in sdk_fields and k != "pw_script_file"]
                if ignored_fields:
                    self.display_info(f"Ignoring non-SDK fields from file: {', '.join(ignored_fields)}")
                
                self.display_info(f"Creating on-demand check from file: {from_file}")
            else:
                # Build check data normally
                check_data = {
                    "name": name,
                    "type": check_type
                }
                
                # Only set timeout if explicitly provided by user
                if timeout is not None:
                    check_data["timeout"] = timeout
            
            # Add URL if provided (required for web, api, ssl checks)
            if url is not None:
                check_data["url"] = url
            
            # Add host/port for TCP/SSL checks
            if host is not None:
                check_data["host"] = host
            if port is not None:
                check_data["port"] = port
            
            # Handle pw_script_file option
            params_dict = {}
            if pw_script_file is not None:
                if not os.path.exists(pw_script_file):
                    self.display_error(f"Playwright script file not found: {pw_script_file}")
                    raise typer.Exit(1)
                
                try:
                    with open(pw_script_file, 'r', encoding='utf-8') as f:
                        pw_script_content = f.read().strip()
                    
                    if not pw_script_content:
                        self.display_error(f"Playwright script file is empty: {pw_script_file}")
                        raise typer.Exit(1)
                    
                    params_dict["pw_script"] = pw_script_content
                    self.display_info(f"Loaded Playwright script from: {pw_script_file}")
                    
                except IOError as e:
                    self.display_error(f"Failed to read Playwright script file: {str(e)}")
                    raise typer.Exit(1)
            
            # Handle regions parameter - add to params_dict if provided and not in parameters
            if regions is not None and parameters is None:
                # Parse comma-separated regions into a list
                regions_list = [r.strip() for r in regions.split(',') if r.strip()]
                if regions_list:
                    params_dict["regions"] = regions_list
            
            # Handle ports parameter - add to params_dict if provided and not in parameters
            if ports is not None and parameters is None:
                params_dict["ports"] = ports
            
            # Parse parameters JSON if provided (this takes precedence over --regions and --ports)
            if parameters is not None:
                try:
                    parsed_params = json.loads(parameters)
                    # Merge with pw_script from file if both are provided
                    params_dict.update(parsed_params)
                except json.JSONDecodeError as e:
                    self.display_error(f"Invalid JSON in --parameters: {str(e)}")
                    self.display_info("Example: --parameters '{\"pw_script\": \"const { test } = require('@playwright/test'); test('example', async ({ page }) => { await page.goto('https://example.com'); });\", \"regions\": [\"US\", \"EU\"]}'")
                    raise typer.Exit(1)
            
            # Add parameters to check_data if we have any
            if params_dict:
                check_data["parameters"] = params_dict
            
            # Validation based on check type - use the actual type from check_data
            actual_check_type = check_data.get("type", check_type)
            
            # Validate check type is supported
            if actual_check_type not in SUPPORTED_CHECK_TYPES:
                self.display_error(f"Invalid check type: {actual_check_type}. Supported types: {', '.join(SUPPORTED_CHECK_TYPES)}")
                raise typer.Exit(1)
            
            if actual_check_type in ['web', 'api'] and not url:
                self.display_error(f"URL is required for {actual_check_type} checks")
                raise typer.Exit(1)
            
            if actual_check_type in ['tcp', 'portscan', 'dns', 'icmp'] and not host:
                self.display_error(f"Host is required for {actual_check_type} checks")
                raise typer.Exit(1)
            
            if actual_check_type in ['ssl'] and not (url or host):
                self.display_error(f"Either URL or host is required for {actual_check_type} checks")
                raise typer.Exit(1)
            
            if actual_check_type in ['synthetic', 'multistep'] and not params_dict.get('pw_script'):
                self.display_error(f"Playwright script is required for {actual_check_type} checks. Use --pw-script-file or --parameters with pw_script")
                raise typer.Exit(1)
            
            # Create the request
            check_request = ExecuteCustomCheckRequest(**check_data)
            
            # Execute the check
            response = checks_api.v1_checks_execute_post(check_request)
            job_id = response.job_id
            
            # Build success message - use the actual type from check_data
            actual_check_type = check_data.get("type", check_type)
            success_details = [f"Job ID: {job_id}", f"Type: {actual_check_type}"]
            if url:
                success_details.append(f"URL: {url}")
            if host:
                success_details.append(f"Host: {host}")
            if port:
                success_details.append(f"Port: {port}")
            if pw_script_file:
                success_details.append(f"Script: loaded from {pw_script_file}")
            
            if wait_for_result:
                # Wait for the job to complete and show the result
                self._wait_and_show_result(job_id, success_details)
            else:
                if self.output_format in ['json', 'yaml']:
                    actual_check_type = check_data.get("type", check_type)
                    actual_name = check_data.get("name", name)
                    self.output_data({
                        "job_id": job_id,
                        "check_type": actual_check_type,
                        "url": url,
                        "host": host,
                        "port": port,
                        "name": actual_name,
                        "status": "queued"
                    })
                else:
                    self.display_success(
                        f"On-demand check queued successfully!\n" + "\n".join(success_details) + f"\n\nUse 'pngr checks jobs status {job_id}' to check job status.\n\n💡 Tip: Remove --no-wait to see results immediately.",
                        "✅ Check Queued"
                    )
            
        except Exception as e:
            self.display_error(f"Failed to execute custom check: {str(e)}")
            raise typer.Exit(1)

    def execute_existing_check(self, check_id: str, wait_for_result: bool = True):
        """Execute existing check on demand"""
        try:
            checks_api = self.get_client()
            
            # Execute existing check
            response = checks_api.v1_checks_check_id_execute_post(check_id=check_id)
            job_id = response.job_id
            
            if wait_for_result:
                # Wait for the job to complete and show the result
                success_details = [f"Job ID: {job_id}", f"Check ID: {check_id}"]
                self._wait_and_show_result(job_id, success_details)
            else:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({
                        "job_id": job_id,
                        "check_id": check_id,
                        "status": "queued"
                    })
                else:
                    self.display_success(
                        f"Existing check executed successfully!\nJob ID: {job_id}\nCheck ID: {check_id}\n\nUse 'pngr checks jobs status {job_id}' to check job status.\n\n💡 Tip: Remove --no-wait to see results immediately.",
                        "✅ Check Executed"
                    )
            
        except Exception as e:
            self.display_error(f"Failed to execute existing check: {str(e)}")
            raise typer.Exit(1)


    def list_jobs(self, page: int = 1, page_size: int = 20):
        """List check jobs"""
        try:
            checks_api = self.get_client()
            
            # List check jobs
            response = checks_api.v1_checks_jobs_get(
                page=page,
                per_page=page_size
            )
            
            if not hasattr(response, 'jobs') or not response.jobs:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"jobs": [], "total": 0, "message": "No jobs found"})
                else:
                    self.display_info("No jobs found.")
                return
            
            if self.output_format in ['json', 'yaml']:
                jobs_data = []
                for job in response.jobs:
                    # Extract name and type from check_parameters
                    name = None
                    check_type = None
                    host = None
                    url = None
                    
                    if hasattr(job, 'check_parameters') and job.check_parameters:
                        params = job.check_parameters
                        name = params.get('name')
                        check_type = params.get('type')
                        host = params.get('host')
                        # For web checks, construct URL from host/url
                        if check_type == 'web' and 'url' in params:
                            url = params['url']
                        elif host:
                            url = host
                    
                    job_dict = {
                        "job_id": str(job.id) if job.id else None,
                        "name": name,
                        "type": check_type,
                        "url": url,
                        "host": host,
                        "status": job.status if hasattr(job, 'status') else None,
                        "job_type": job.job_type if hasattr(job, 'job_type') else None,
                        "check_id": job.check_id if hasattr(job, 'check_id') else None,
                        "created_at": job.created_at.isoformat() if hasattr(job, 'created_at') and job.created_at else None,
                        "started_at": job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if hasattr(job, 'completed_at') and job.completed_at else None,
                        "error_message": job.error_message if hasattr(job, 'error_message') else None
                    }
                    jobs_data.append(job_dict)
                
                # Include pagination info from response
                pagination_info = {}
                if hasattr(response, 'pagination') and response.pagination:
                    pagination_info = {
                        "page": response.pagination.get('page', page),
                        "per_page": response.pagination.get('per_page', page_size),
                        "total": response.pagination.get('total', len(jobs_data)),
                        "pages": response.pagination.get('pages', 1),
                        "has_next": response.pagination.get('has_next', False),
                        "has_prev": response.pagination.get('has_prev', False)
                    }
                
                self.output_data({
                    "jobs": jobs_data,
                    "pagination": pagination_info if pagination_info else {"page": page, "per_page": page_size, "total": len(jobs_data)}
                })
            else:
                table = Table(title="Check Jobs")
                table.add_column("Job ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Type", style="blue")
                table.add_column("Target", style="yellow")
                table.add_column("Status", style="magenta")
                table.add_column("Job Type", style="dim")
                table.add_column("Created", style="dim")
                
                for job in response.jobs:
                    # Extract details from check_parameters
                    name = "Unknown"
                    check_type = "Unknown"
                    target = "Unknown"
                    
                    if hasattr(job, 'check_parameters') and job.check_parameters:
                        params = job.check_parameters
                        name = params.get('name', 'Unknown')
                        check_type = params.get('type', 'Unknown')
                        
                        # Determine target based on check type
                        if check_type == 'web' and 'url' in params:
                            target = params['url']
                        elif 'host' in params:
                            port = params.get('port')
                            target = f"{params['host']}" + (f":{port}" if port else "")
                        else:
                            target = params.get('url', params.get('host', 'Unknown'))
                    
                    # Status with color coding
                    status_color = "green" if hasattr(job, 'status') and job.status == 'completed' else "yellow" if hasattr(job, 'status') and job.status in ['running', 'pending'] else "red"
                    status_display = f"[{status_color}]{job.status}[/{status_color}]" if hasattr(job, 'status') and job.status else "-"
                    
                    table.add_row(
                        str(job.id) if job.id else "-",
                        name,
                        check_type,
                        target,
                        status_display,
                        job.job_type if hasattr(job, 'job_type') and job.job_type else "-",
                        job.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(job, 'created_at') and job.created_at else "Unknown"
                    )
                
                self.console.print(table)
                
                # Show pagination info
                if hasattr(response, 'pagination') and response.pagination:
                    pagination = response.pagination
                    total_items = pagination.get('total', len(response.jobs))
                    total_pages = pagination.get('pages', 1)
                    current_page = pagination.get('page', page)
                    per_page = pagination.get('per_page', page_size)
                    
                    self.console.print(f"\n[dim]Showing {len(response.jobs)} jobs • Page {current_page} of {total_pages} • {total_items} total items • {per_page} per page[/dim]")
                else:
                    self.console.print(f"\n[dim]Found {len(response.jobs)} jobs[/dim]")
                
                # Add helpful tip about getting job details
                self.console.print(f"\n[dim]💡 For detailed job information, use: [white]pngr checks jobs status <job_id>[/white][/dim]")
                self.console.print(f"[dim]💡 For detailed result information, use: [white]pngr checks results --result-id <result_id>[/white][/dim]")
            
        except Exception as e:
            self.display_error(f"Failed to list jobs: {str(e)}")
            raise typer.Exit(1)

    def get_job_status(self, job_id: str):
        """Get job status"""
        try:
            checks_api = self.get_client()
            
            # Get job status
            job_status = checks_api.v1_checks_jobs_job_id_get(job_id=job_id)
            
            if self.output_format in ['json', 'yaml']:
                # Include full job data for JSON/YAML output
                job_data = {
                    "job_id": job_id,
                    "status": job_status.status if hasattr(job_status, 'status') else None,
                    "job_type": job_status.job_type if hasattr(job_status, 'job_type') else None,
                    "check_id": job_status.check_id if hasattr(job_status, 'check_id') else None,
                    "created_at": job_status.created_at.isoformat() if hasattr(job_status, 'created_at') and job_status.created_at else None,
                    "started_at": job_status.started_at.isoformat() if hasattr(job_status, 'started_at') and job_status.started_at else None,
                    "completed_at": job_status.completed_at.isoformat() if hasattr(job_status, 'completed_at') and job_status.completed_at else None,
                    "error_message": job_status.error_message if hasattr(job_status, 'error_message') else None,
                    "check_parameters": job_status.check_parameters if hasattr(job_status, 'check_parameters') else None,
                    "result": job_status.result if hasattr(job_status, 'result') else None
                }
                self.output_data(job_data)
            else:
                # Rich formatted detailed view - fetch and display with results
                self._fetch_and_display_job_result(job_id, job_status, verbose=self.verbose)
            
        except Exception as e:
            self.display_error(f"Failed to get job status: {str(e)}")
            raise typer.Exit(1)

    def _fetch_and_display_job_result(self, job_id: str, job_status, verbose: bool = False):
        """Fetch detailed results from the new results endpoint and display them"""
        import time
        
        try:
            # Extract result_id(s) from job response
            result_ids = []
            is_multi_region = False
            
            if hasattr(job_status, 'result') and job_status.result:
                result = job_status.result
                
                # Debug: Print the raw result to see what we're getting (only in verbose mode)
                if verbose and self.output_format not in ['json', 'yaml']:
                    import json
                    self.console.print(f"[dim]DEBUG: Raw result from job status:[/dim]")
                    self.console.print(f"[dim]{json.dumps(result, indent=2, default=str)}[/dim]")
                
                # Check if this is a multi-region result
                if isinstance(result, dict):
                    if 'regional_summary' in result and result['regional_summary']:
                        # Multi-region execution
                        is_multi_region = True
                        regional_summary = result['regional_summary']
                        
                        # Debug: Show what we found (only in verbose mode)
                        if verbose and self.output_format not in ['json', 'yaml']:
                            self.console.print(f"[dim]DEBUG: Found {len(regional_summary)} regions in regional_summary[/dim]")
                        
                        for regional_result in regional_summary:
                            if 'result_id' in regional_result:
                                result_ids.append(regional_result['result_id'])
                        
                        # Check if we might be missing results (race condition detection)
                        total_regions = result.get('total_regions', len(regional_summary))
                        completed_regions = result.get('completed_regions', len(regional_summary))
                        
                        if verbose and self.output_format not in ['json', 'yaml']:
                            self.console.print(f"[dim]DEBUG: total_regions={total_regions}, completed_regions={completed_regions}, found result_ids={len(result_ids)}[/dim]")
                        
                        # If we're missing results, wait a bit and refetch
                        if len(result_ids) < total_regions:
                            if self.output_format not in ['json', 'yaml']:
                                self.console.print(f"[yellow]⚠ Race condition detected: {len(result_ids)}/{total_regions} results ready. Waiting 2s and retrying...[/yellow]")
                            time.sleep(2)
                            
                            # Refetch job status
                            checks_api = self.get_client()
                            job_status = checks_api.v1_checks_jobs_job_id_get(job_id=job_id)
                            
                            # Re-extract result_ids
                            result_ids = []
                            if hasattr(job_status, 'result') and job_status.result:
                                result = job_status.result
                                if isinstance(result, dict) and 'regional_summary' in result:
                                    for regional_result in result['regional_summary']:
                                        if 'result_id' in regional_result:
                                            result_ids.append(regional_result['result_id'])
                                    
                                    if verbose and self.output_format not in ['json', 'yaml']:
                                        self.console.print(f"[dim]DEBUG: After retry, found {len(result_ids)} result_ids[/dim]")
                    
                    elif 'result_id' in result:
                        # Single-region execution
                        result_ids.append(result['result_id'])
            
            if not result_ids:
                # No result IDs found, display job status only
                self._display_detailed_job_status(job_status, job_id)
                return
            
            # Get client for fetching results
            api_key = get_api_key()
            if not api_key:
                self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
                raise typer.Exit(1)
            
            from pingera import ApiClient, Configuration
            from pingera.api import ChecksUnifiedResultsApi
            from ..utils.config import get_config
            
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key
            api_client = ApiClient(configuration)
            checks_api = ChecksUnifiedResultsApi(api_client)
            
            # Fetch detailed results for each result_id
            if is_multi_region:
                # For multi-region, show aggregated view
                self._display_multi_region_results(job_status, job_id, result_ids, checks_api)
            else:
                # For single-region, fetch and display the single result
                result_id = result_ids[0]
                response = checks_api.v1_checks_all_results_get(result_id=result_id)
                
                if hasattr(response, 'results') and response.results and len(response.results) > 0:
                    detailed_result = response.results[0]
                    self._display_detailed_result_with_job_info(job_status, job_id, detailed_result)
                else:
                    # Fallback to job status display
                    self._display_detailed_job_status(job_status, job_id)
                    
        except Exception as e:
            # Fallback to job status display on error
            self.display_warning(f"Could not fetch detailed results: {str(e)}")
            self._display_detailed_job_status(job_status, job_id)
    
    def _display_multi_region_results(self, job_status, job_id: str, result_ids: list, checks_api):
        """Display aggregated multi-region results"""
        from rich.table import Table
        
        if self.output_format in ['json', 'yaml']:
            # For JSON/YAML, include full job data with regional summary
            job_data = {
                "job_id": job_id,
                "status": job_status.status if hasattr(job_status, 'status') else None,
                "multi_region": True,
                "regions_count": len(result_ids),
                "result_ids": result_ids
            }
            
            # Extract regional summary if available
            if hasattr(job_status, 'result') and isinstance(job_status.result, dict):
                result = job_status.result
                if 'regional_summary' in result:
                    job_data['regional_summary'] = result['regional_summary']
            
            self.output_data(job_data)
            return
        
        # Display job basic info first
        status_emoji = "✅" if hasattr(job_status, 'status') and job_status.status == 'completed' else "❌"
        status_color = "green" if hasattr(job_status, 'status') and job_status.status == 'completed' else "red"
        
        self.console.print(f"\n[bold cyan]Multi-Region Execution Result[/bold cyan]")
        self.console.print(f"• Job ID: [white]{job_id}[/white]")
        self.console.print(f"• Status: [{status_color}]{status_emoji} {job_status.status}[/{status_color}]")
        
        # Extract and display aggregated statistics
        if hasattr(job_status, 'result') and isinstance(job_status.result, dict):
            result = job_status.result
            regional_summary = result.get('regional_summary', [])
            
            # Display region count from actual regional_summary
            self.console.print(f"• Regions: [white]{len(regional_summary)}[/white]")
            
            if regional_summary:
                # Calculate aggregated statistics
                response_times = []
                completed_count = 0
                failed_count = 0
                
                for region_result in regional_summary:
                    if region_result.get('status') == 'ok':
                        completed_count += 1
                    else:
                        failed_count += 1
                    
                    if 'response_time' in region_result and region_result['response_time']:
                        response_times.append(region_result['response_time'])
                
                # Display aggregated stats
                self.console.print(f"\n[bold cyan]Aggregated Statistics:[/bold cyan]")
                self.console.print(f"• Completed: [green]{completed_count}[/green] / Failed: [red]{failed_count}[/red]")
                
                if response_times:
                    avg_response = sum(response_times) / len(response_times)
                    min_response = min(response_times)
                    max_response = max(response_times)
                    self.console.print(f"• Response Time: [yellow]Avg: {avg_response:.0f}ms[/yellow], [green]Min: {min_response}ms[/green], [red]Max: {max_response}ms[/red]")
                
                # Create regional results table
                table = Table(title="Regional Results")
                table.add_column("Region", style="cyan")
                table.add_column("Status", style="magenta")
                table.add_column("Response Time", style="yellow")
                table.add_column("Result ID", style="dim")
                
                for region_result in regional_summary:
                    region = region_result.get('region', 'Unknown')
                    status = region_result.get('status', 'unknown')
                    response_time = region_result.get('response_time')
                    result_id = region_result.get('result_id', 'N/A')
                    
                    # Format status with color
                    status_color = "green" if status == 'ok' else "red"
                    status_display = f"[{status_color}]{status}[/{status_color}]"
                    
                    # Format response time
                    response_display = f"{response_time}ms" if response_time else "N/A"
                    
                    table.add_row(region, status_display, response_display, result_id)
                
                self.console.print("\n")
                self.console.print(table)
                
                # Add guidance for detailed results
                self.console.print(f"\n[dim]💡 To see detailed results for a specific region, use:[/dim]")
                self.console.print(f"[dim]   pngr checks results --result-id <result_id>[/dim]")
            else:
                # Fallback if no regional_summary
                self._display_detailed_job_status(job_status, job_id)
        else:
            # Fallback to basic job status
            self._display_detailed_job_status(job_status, job_id)
    
    def _display_detailed_result_with_job_info(self, job_status, job_id: str, detailed_result):
        """Display detailed result information combined with job info"""
        from rich.panel import Panel
        from ..formatters.registry import FormatterRegistry
        
        # Determine status color and emoji
        status_emoji = "✅" if hasattr(detailed_result, 'status') and detailed_result.status == 'ok' else "❌"
        status_color = "green" if hasattr(detailed_result, 'status') and detailed_result.status == 'ok' else "red"
        
        # Basic information
        basic_info = f"""[bold cyan]Basic Information:[/bold cyan]
• Result ID: [white]{detailed_result.id if hasattr(detailed_result, 'id') else 'Unknown'}[/white]
• Check ID: [white]{detailed_result.check_id if hasattr(detailed_result, 'check_id') and detailed_result.check_id else 'None'}[/white]
• Status: [{status_color}]{status_emoji} {detailed_result.status if hasattr(detailed_result, 'status') else 'Unknown'}[/{status_color}]
• Timestamp: [white]{detailed_result.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(detailed_result, 'created_at') and detailed_result.created_at else 'Unknown'}[/white]"""
        
        if hasattr(detailed_result, 'response_time') and detailed_result.response_time:
            basic_info += f"\n• Response Time: [yellow]{detailed_result.response_time}ms[/yellow]"
        
        # Server information
        if hasattr(detailed_result, 'check_server') and detailed_result.check_server:
            server = detailed_result.check_server
            server_info = f"""• Check Server: [white]{server.id if hasattr(server, 'id') else 'Unknown'}[/white]
• Server IP: [white]{server.ip_address if hasattr(server, 'ip_address') else 'Unknown'}[/white]
• Server Country: [white]{server.country if hasattr(server, 'country') else 'Unknown'}[/white]
• Server Region: [white]{server.region if hasattr(server, 'region') else 'Unknown'}[/white]"""
            basic_info += f"\n{server_info}"
        
        # Error information
        error_info = ""
        if hasattr(detailed_result, 'error_message') and detailed_result.error_message:
            error_info = f"""
[bold red]Error Information:[/bold red]
• Error: [red]{detailed_result.error_message}[/red]"""
        
        # Metadata analysis using formatters
        metadata_info = ""
        if hasattr(detailed_result, 'check_metadata') and detailed_result.check_metadata:
            metadata = detailed_result.check_metadata
            
            if isinstance(metadata, dict):
                # Add result_id to metadata for formatters to use in truncation notice
                metadata_with_id = metadata.copy()
                if hasattr(detailed_result, 'id'):
                    metadata_with_id['result_id'] = detailed_result.id
                
                registry = FormatterRegistry(verbose=self.verbose)
                metadata_info = registry.format_metadata(metadata_with_id)
        
        # Combine all sections
        full_info = basic_info
        if error_info:
            full_info += error_info
        if metadata_info:
            full_info += metadata_info
        
        panel = Panel(
            full_info,
            title=f"🔍 Result Details: {detailed_result.id if hasattr(detailed_result, 'id') else 'Unknown'}",
            border_style="blue",
            padding=(1, 2),
        )
        
        self.console.print(panel)
    
    def _display_detailed_job_status(self, job_status, job_id: str):
        """Display detailed job status information in a rich format"""
        
        # Determine status color and emoji
        status_emoji = "✅" if hasattr(job_status, 'status') and job_status.status == 'completed' else "🏃" if hasattr(job_status, 'status') and job_status.status in ['running', 'pending'] else "❌"
        status_color = "green" if hasattr(job_status, 'status') and job_status.status == 'completed' else "yellow" if hasattr(job_status, 'status') and job_status.status in ['running', 'pending'] else "red"
        
        # Basic job information
        basic_info = f"""[bold cyan]Job Information:[/bold cyan]
• Job ID: [white]{job_id}[/white]
• Status: [{status_color}]{status_emoji} {job_status.status if hasattr(job_status, 'status') else 'Unknown'}[/{status_color}]
• Job Type: [blue]{job_status.job_type if hasattr(job_status, 'job_type') else 'Unknown'}[/blue]
• Check ID: [white]{job_status.check_id if hasattr(job_status, 'check_id') else 'None (custom check)'}[/white]
• Created: [white]{job_status.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(job_status, 'created_at') and job_status.created_at else 'Unknown'}[/white]
• Started: [white]{job_status.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(job_status, 'started_at') and job_status.started_at else 'Not started'}[/white]
• Completed: [white]{job_status.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(job_status, 'completed_at') and job_status.completed_at else 'Not completed'}[/white]"""

        # Check parameters section
        params_info = ""
        if hasattr(job_status, 'check_parameters') and job_status.check_parameters:
            params = job_status.check_parameters
            params_info = f"""
[bold cyan]Check Parameters:[/bold cyan]
• Name: [white]{params.get('name', 'Unknown')}[/white]
• Type: [blue]{params.get('type', 'Unknown')}[/blue]"""
            
            # Add type-specific parameters
            if params.get('type') == 'web':
                if 'url' in params:
                    params_info += f"\n• URL: [yellow]{params['url']}[/yellow]"
            elif params.get('type') == 'tcp':
                if 'host' in params:
                    params_info += f"\n• Host: [yellow]{params['host']}[/yellow]"
                if 'port' in params:
                    params_info += f"\n• Port: [white]{params['port']}[/white]"
            elif params.get('type') in ['multistep', 'synthetic']:
                if 'parameters' in params and 'pw_script' in params['parameters']:
                    script_preview = params['parameters']['pw_script']
                    if len(script_preview) > 100:
                        script_preview = script_preview[:100] + "..."
                    params_info += f"\n• Script: [dim]{script_preview}[/dim]"
            
            if 'timeout' in params:
                params_info += f"\n• Timeout: [white]{params['timeout']}s[/white]"
            
            # Show regions if available
            if 'parameters' in params and isinstance(params['parameters'], dict) and 'regions' in params['parameters']:
                regions = params['parameters']['regions']
                params_info += f"\n• Regions: [white]{', '.join(regions)}[/white]"

        # Error information
        error_info = ""
        if hasattr(job_status, 'error_message') and job_status.error_message:
            error_info = f"""
[bold red]Error Information:[/bold red]
• Error: [red]{job_status.error_message}[/red]"""

        # Result analysis
        result_info = ""
        if hasattr(job_status, 'result') and job_status.result:
            result = job_status.result
            
            # Basic result info
            result_status = result.get('status', 'Unknown') if isinstance(result, dict) else 'Unknown'
            result_status_color = "green" if result_status == 'ok' else "red" if result_status == 'failed' else "yellow"
            
            result_info = f"""
[bold cyan]Result Summary:[/bold cyan]
• Result Status: [{result_status_color}]{result_status}[/{result_status_color}]"""
            
            if isinstance(result, dict):
                # Response time
                if 'response_time' in result and result['response_time']:
                    result_info += f"\n• Response Time: [yellow]{result['response_time']}ms[/yellow]"
                
                # Check server info
                if 'check_server' in result and result['check_server']:
                    server = result['check_server']
                    result_info += f"\n• Server: [magenta]{server.get('region', 'Unknown')} ({server.get('ip_address', 'Unknown IP')})[/magenta]"
                
                # Error message from result
                if 'error_message' in result and result['error_message']:
                    result_info += f"\n• Result Error: [red]{result['error_message']}[/red]"
                
                # Format check metadata using existing formatters
                if 'check_metadata' in result and result['check_metadata']:
                    metadata = result['check_metadata']
                    
                    # Use the same metadata formatting as check results
                    try:
                        from ..formatters.registry import FormatterRegistry
                        registry = FormatterRegistry(verbose=False)  # Default to non-verbose for job status
                        metadata_formatted = registry.format_metadata(metadata)
                        
                        if metadata_formatted.strip():
                            result_info += f"\n{metadata_formatted}"
                    except Exception:
                        # Fallback to basic metadata display
                        if 'logs' in metadata and metadata['logs']:
                            logs = metadata['logs']
                            result_info += f"\n• Logs: [dim]{len(logs)} log entries[/dim]"
                            # Show first log entry if available
                            if logs and len(logs) > 0:
                                first_log = logs[0]
                                log_level = first_log.get('level', 'info')
                                log_message = first_log.get('message', 'No message')
                                log_color = "red" if log_level == 'error' else "yellow" if log_level == 'warn' else "white"
                                result_info += f"\n  - [{log_color}]{log_level.upper()}: {log_message}[/{log_color}]"
                        
                        if 'execution_time' in metadata:
                            result_info += f"\n• Execution Time: [white]{metadata['execution_time']}ms[/white]"
                        
                        if 'test_summary' in metadata:
                            summary = metadata['test_summary']
                            total_tests = summary.get('total', 0)
                            passed_tests = summary.get('passed', 0)
                            failed_tests = summary.get('failed', 0)
                            result_info += f"\n• Test Results: [green]{passed_tests} passed[/green], [red]{failed_tests} failed[/red], [white]{total_tests} total[/white]"

        # Combine all sections
        full_info = basic_info
        if params_info:
            full_info += params_info
        if error_info:
            full_info += error_info
        if result_info:
            full_info += result_info

        panel = Panel(
            full_info,
            title=f"📋 Job Status: {job_id}",
            border_style="blue",
            padding=(1, 2),
        )
        
        self.console.print(panel)

    def _wait_and_show_result(self, job_id: str, initial_details: list):
        """Wait for job completion and display the result"""
        import time
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        if self.output_format not in ['json', 'yaml']:
            # Show initial success message
            self.display_success(
                f"On-demand check queued successfully!\n" + "\n".join(initial_details) + f"\n\nWaiting for result...",
                "✅ Check Queued"
            )
        
        # Polling logic with progress indicator
        max_wait_time = 300  # 5 minutes maximum wait
        poll_interval = 2    # Poll every 2 seconds
        elapsed_time = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            if self.output_format not in ['json', 'yaml']:
                task = progress.add_task("⏳ Waiting for job completion...", total=None)
            
            while elapsed_time < max_wait_time:
                try:
                    checks_api = self.get_client()
                    job_status = checks_api.v1_checks_jobs_job_id_get(job_id=job_id)
                    
                    if hasattr(job_status, 'status'):
                        if job_status.status in ['completed', 'failed', 'error']:
                            # Job is finished, fetch and show the result
                            if self.output_format not in ['json', 'yaml']:
                                progress.update(task, description=f"✅ Job {job_status.status}!")
                                time.sleep(0.5)  # Brief pause to show completion
                            
                            # Fetch and display the actual result
                            self._fetch_and_display_job_result(job_id, job_status, verbose=self.verbose)
                            return
                        
                        elif job_status.status == 'running':
                            if self.output_format not in ['json', 'yaml']:
                                progress.update(task, description=f"🏃 Job running... ({elapsed_time}s elapsed)")
                        
                        else:  # pending, queued, etc.
                            if self.output_format not in ['json', 'yaml']:
                                progress.update(task, description=f"⏳ Job {job_status.status}... ({elapsed_time}s elapsed)")
                    
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    
                except Exception as e:
                    if self.output_format in ['json', 'yaml']:
                        self.output_data({
                            "error": f"Failed to poll job status: {str(e)}",
                            "job_id": job_id,
                            "elapsed_time": elapsed_time
                        })
                    else:
                        self.display_error(f"Error polling job status: {str(e)}")
                        self.display_info(f"You can manually check status with: pngr checks jobs status {job_id}")
                    return
            
            # Timeout reached
            if self.output_format in ['json', 'yaml']:
                self.output_data({
                    "timeout": True,
                    "message": f"Job did not complete within {max_wait_time} seconds",
                    "job_id": job_id,
                    "elapsed_time": elapsed_time
                })
            else:
                self.display_warning(
                    f"Job did not complete within {max_wait_time} seconds.\n"
                    f"The job may still be running. Use 'pngr checks jobs status {job_id}' to check status manually."
                )


# Create Typer app for on-demand checks commands
app = typer.Typer(name="on-demand", help="⚡ On-demand checks execution")
run_app = typer.Typer(name="run", help="🚀 Execute checks on demand")
jobs_app = typer.Typer(name="jobs", help="📋 Manage check jobs")

# Register sub-apps
app.add_typer(run_app)
app.add_typer(jobs_app)


def get_output_format():
    """Get output format from config"""
    from ..utils.config import get_config
    return get_config().get('output_format', 'table')


def get_verbose_mode():
    """Get verbose mode from config"""
    from ..utils.config import get_verbose_mode as _get_verbose_mode
    return _get_verbose_mode()


@run_app.command("custom")
def run_custom_check(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL to monitor (required for web, api, ssl checks)"),
    check_type: str = typer.Option("web", "--type", "-t", help=f"Check type: {', '.join(SUPPORTED_CHECK_TYPES)}"),
    host: Optional[str] = typer.Option(None, "--host", help="Hostname/IP for TCP/SSL/portscan/DNS/ICMP checks (max 255 characters)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port number for TCP/SSL checks (1-65535)"),
    ports: Optional[str] = typer.Option(None, "--ports", help="Ports to scan for portscan checks (e.g., '80,443' or '1-1024'). Overridden by --parameters if both are specified."),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Timeout in seconds (optional - backend will use defaults if not specified)"),
    name: str = typer.Option("On-demand check", "--name", "-n", help="Check name"),
    regions: Optional[str] = typer.Option(None, "--regions", "-r", help="Comma-separated list of regions (e.g., 'ru-central1,eu-west1'). Overridden by --parameters if both are specified."),
    parameters: Optional[str] = typer.Option(None, "--parameters", help="JSON string with check parameters (e.g., '{\"regions\": [\"US\", \"EU\"]}')"),
    pw_script_file: Optional[str] = typer.Option(None, "--pw-script-file", help="Path to file containing Playwright script for synthetic/multistep checks"),
    from_file: Optional[str] = typer.Option(None, "--from-file", "-f", help="Path to JSON or YAML file containing check configuration"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for job completion, just queue the check and return job ID"),
):
    """Execute custom on-demand check. Can be executed from command line options or from a JSON/YAML file.
    
    By default, waits for job completion and shows result immediately (max 5 minutes).
    Use --no-wait to just queue the check and return the job ID.
    
    When using --from-file:
    - Command line options override file values
    - File should contain check configuration in JSON or YAML format
    
    Parameters vary by check type:
    - web/api: --url required
    - tcp: --host required, --port optional  
    - ssl: --url or --host required, --port optional
    - portscan: --host required, --ports optional
    - synthetic/multistep: --pw-script-file or --parameters with pw_script required
    
    Timeout is optional - if not specified, backend will use appropriate defaults for each check type."""
    on_demand_cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    on_demand_cmd.execute_custom_check(url, check_type, host, port, timeout, name, regions, parameters, pw_script_file, from_file, not no_wait, ports)


@run_app.command("existing")
def run_existing_check(
    check_id: str = typer.Argument(..., help="Existing check ID to execute"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for job completion, just queue the check and return job ID"),
):
    """Execute existing check on demand. By default, waits for job completion and shows result immediately (max 5 minutes). Use --no-wait to just queue the check."""
    on_demand_cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    on_demand_cmd.execute_existing_check(check_id, not no_wait)


@jobs_app.command("list")
def list_jobs(
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page"),
):
    """List check jobs"""
    on_demand_cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    on_demand_cmd.list_jobs(page, page_size)


@jobs_app.command("status")
def get_job_status(
    job_id: str = typer.Argument(..., help="Job ID to get status for"),
):
    """Get job status and results. For multi-region executions, shows aggregated statistics and regional summary."""
    on_demand_cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    on_demand_cmd.get_job_status(job_id)
