#!/usr/bin/env python3
"""
GitHub Code Search Tool
An interactive Python script to search for code on GitHub using their API.
Results are ordered by date (descending).
"""

import requests
import json
import time
from datetime import datetime, timedelta
from dateutil import parser
import sys
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

class GitHubCodeSearch:
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GitHub-Code-Search-Tool/1.0',
            'Accept': 'application/vnd.github.v3.text-match+json'
        })
        
    def set_token(self, token):
        """Set GitHub personal access token for authenticated requests"""
        if token:
            self.session.headers.update({'Authorization': f'token {token}'})
            print(f"{Fore.GREEN}✓ GitHub token set successfully{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ No token provided - using unauthenticated requests (rate limited){Style.RESET_ALL}")
    
    def search_code(self, query, language=None, sort='best-match', order='desc', per_page=30, file_filter=None, check_config_files=False):
        """
        Search for code on GitHub
        
        Args:
            query (str): Search query
            language (str, optional): Filter by programming language
            sort (str): Sort order ('best-match', 'indexed')
            order (str): Sort direction ('desc', 'asc')
            per_page (int): Number of results per page (max 100)
            file_filter (dict, optional): File extension filter
                {
                    'type': 'include' or 'exclude',
                    'extensions': ['list', 'of', 'extensions']
                }
            check_config_files (bool): Whether to check for config files in repositories
        """
        # Build search query
        search_query = query
        
        if language:
            search_query += f" language:{language}"
        
        # Add file extension filters to the query
        if file_filter and file_filter.get('extensions'):
            extensions = file_filter['extensions']
            filter_type = file_filter['type']
            
            if filter_type == 'include':
                # Include only specific file extensions
                extension_filters = []
                for ext in extensions:
                    if ext.startswith('.'):
                        extension_filters.append(f'extension:{ext[1:]}')
                    else:
                        extension_filters.append(f'extension:{ext}')
                search_query += f" {' '.join(extension_filters)}"
            
            elif filter_type == 'exclude':
                # Exclude specific file extensions
                extension_filters = []
                for ext in extensions:
                    if ext.startswith('.'):
                        extension_filters.append(f'-extension:{ext[1:]}')
                    else:
                        extension_filters.append(f'-extension:{ext}')
                search_query += f" {' '.join(extension_filters)}"
        
        # Build URL
        url = f"{self.base_url}/search/code"
        params = {
            'q': search_query,
            'sort': sort,
            'order': order,
            'per_page': min(per_page, 100)
        }
        
        print(f"{Fore.BLUE}Searching for: {search_query}{Style.RESET_ALL}")
        
        # Make request
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            results = response.json()
            
            # If sorting by date, enrich results with commit dates
            if sort == 'indexed':
                print(f"{Fore.YELLOW}Enriching results with commit dates...{Style.RESET_ALL}")
                results['items'] = self._enrich_items_with_dates(results['items'])
                
                # Sort by the fetched dates (descending by default)
                results['items'].sort(key=lambda x: x.get('_fetched_date', ''), reverse=True)
                print(f"{Fore.GREEN}Results sorted by commit date (newest first){Style.RESET_ALL}")
            
            # Check for config files if enabled
            if check_config_files:
                print(f"{Fore.YELLOW}Checking for configuration files in repositories...{Style.RESET_ALL}")
                results['items'] = self._enrich_items_with_config_files(results['items'])
            
            return results
        else:
            print(f"{Fore.RED}Search failed with status code: {response.status_code}{Style.RESET_ALL}")
            if response.status_code == 403:
                print(f"{Fore.RED}Rate limit exceeded. Please wait or use authentication.{Style.RESET_ALL}")
            return None
    
    def _enrich_items_with_dates(self, items):
        """Fetch additional file information to get proper last modified dates using the commits API"""
        enriched_items = []
        for item in items:
            try:
                repo_name = item['repository']['full_name']
                file_path = item['path']
                # Get the latest commit for this file
                commits_url = f"{self.base_url}/repos/{repo_name}/commits?path={file_path}&per_page=1"
                commit_response = self.session.get(commits_url)
                if commit_response.status_code == 200:
                    commits_data = commit_response.json()
                    if commits_data:
                        latest_commit = commits_data[0]
                        commit_date = latest_commit.get('commit', {}).get('author', {}).get('date', '')
                        item['_fetched_date'] = commit_date
                        item['updated_at'] = commit_date
                    else:
                        item['_fetched_date'] = ''
                        item['updated_at'] = ''
                else:
                    item['_fetched_date'] = ''
                    item['updated_at'] = ''
                enriched_items.append(item)
                time.sleep(0.1)  # avoid rate limiting
            except Exception as e:
                print(f"{Fore.YELLOW}Warning: Could not fetch date for {item.get('path', 'unknown')}: {e}{Style.RESET_ALL}")
                item['_fetched_date'] = ''
                item['updated_at'] = ''
                enriched_items.append(item)
        return enriched_items
    
    def _enrich_items_with_config_files(self, items):
        """Check for environment and configuration files in each repository"""
        enriched_items = []
        
        # Track repositories we've already checked to avoid duplicate API calls
        checked_repos = {}
        
        for item in items:
            repo_name = item['repository']['full_name']
            
            # Check if we've already examined this repository
            if repo_name in checked_repos:
                item['config_files'] = checked_repos[repo_name]
            else:
                config_files = self._find_config_files_in_repo(repo_name)
                item['config_files'] = config_files
                checked_repos[repo_name] = config_files
            
            enriched_items.append(item)
        
        return enriched_items
    
    def _find_config_files_in_repo(self, repo_name):
        """Find environment and configuration files in a repository"""
        config_files = {
            'env_files': [],
            'config_files': []
        }
        
        # Define file patterns to search for
        env_patterns = [
            '.env', '.env.local', '.env.development', '.env.production', 
            '.env.test', '.env.staging', 'environment', 'env'
        ]
        
        config_patterns = [
            '.config', '.cfg', '.conf', '.ini', '.yaml', '.yml', '.toml', 
            '.json', '.xml', 'config', 'configuration', 'settings'
        ]
        
        try:
            # Search for environment files
            for pattern in env_patterns:
                env_results = self._search_files_in_repo(repo_name, pattern)
                if env_results:
                    config_files['env_files'].extend(env_results)
                time.sleep(0.1)  # Rate limiting
            
            # Search for configuration files
            for pattern in config_patterns:
                config_results = self._search_files_in_repo(repo_name, pattern)
                if config_results:
                    config_files['config_files'].extend(config_results)
                time.sleep(0.1)  # Rate limiting
            
            # Remove duplicates
            config_files['env_files'] = list(set(config_files['env_files']))
            config_files['config_files'] = list(set(config_files['config_files']))
            
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not check config files for {repo_name}: {e}{Style.RESET_ALL}")
        
        return config_files
    
    def _search_files_in_repo(self, repo_name, filename):
        """Search for specific files in a repository"""
        try:
            url = f"{self.base_url}/search/code"
            params = {
                'q': f'repo:{repo_name} filename:{filename}',
                'per_page': 10
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                results = response.json()
                return [item['path'] for item in results.get('items', [])]
            else:
                return []
                
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Error searching for {filename} in {repo_name}: {e}{Style.RESET_ALL}")
            return []
    
    def format_result(self, item, index):
        """Format a single search result for display"""
        repo_name = item['repository']['full_name']
        file_path = item['path']
        file_url = item['html_url']
        
        # Extract file name from path
        file_name = file_path.split('/')[-1] if '/' in file_path else file_path
        
        # Show original values from API
        size = item.get('size', 'Unknown')
        language = item.get('language', 'Unknown')
        updated_at = item.get('updated_at', 'Unknown')
        
        # Check if result is older than 1 month (use UTC for both)
        is_old = False
        if updated_at and updated_at != 'Unknown':
            try:
                update_date = parser.parse(updated_at)
                now_utc = datetime.utcnow().replace(tzinfo=update_date.tzinfo)
                one_month_ago = now_utc - timedelta(days=30)
                is_old = update_date < one_month_ago
            except Exception as e:
                pass
        
        # Get code snippet with context
        code_snippet = self._get_code_snippet_with_context(item)
        
        # Format the result
        result = f"{Fore.CYAN}{index + 1}.{Style.RESET_ALL} "
        
        # Add red indicator for old results
        if is_old:
            result += f"{Fore.RED}[OLD]{Style.RESET_ALL} "
        
        result += f"{Fore.GREEN}{repo_name}/{file_path}{Style.RESET_ALL}\n"
        result += f"   {Fore.YELLOW}Repository:{Style.RESET_ALL} {repo_name}\n"
        result += f"   {Fore.YELLOW}File:{Style.RESET_ALL} {file_name}\n"
        result += f"   {Fore.YELLOW}Language:{Style.RESET_ALL} {language} | {Fore.YELLOW}Size:{Style.RESET_ALL} {size}\n"
        
        # Color the date red if old
        date_color = Fore.RED if is_old else Fore.YELLOW
        result += f"   {date_color}Updated:{Style.RESET_ALL} {updated_at}\n"
        result += f"   {Fore.YELLOW}URL:{Style.RESET_ALL} {file_url}\n"
        
        # Add config file indicators if available
        config_files = item.get('config_files', {})
        if config_files:
            env_files = config_files.get('env_files', [])
            config_files_list = config_files.get('config_files', [])
            
            if env_files:
                result += f"   {Fore.MAGENTA}🔧 Env Files:{Style.RESET_ALL} {', '.join(env_files[:3])}"
                if len(env_files) > 3:
                    result += f" (+{len(env_files) - 3} more)"
                result += "\n"
            
            if config_files_list:
                result += f"   {Fore.MAGENTA}⚙️  Config Files:{Style.RESET_ALL} {', '.join(config_files_list[:3])}"
                if len(config_files_list) > 3:
                    result += f" (+{len(config_files_list) - 3} more)"
                result += "\n"
        
        if code_snippet:
            result += f"   {Fore.YELLOW}Code Snippet:{Style.RESET_ALL}\n{Fore.WHITE}{code_snippet}{Style.RESET_ALL}\n"
        
        return result
    
    def display_results(self, results):
        """Display search results in a formatted way"""
        if not results or 'items' not in results:
            print(f"{Fore.RED}No results found or error occurred{Style.RESET_ALL}")
            return
        
        total_count = results.get('total_count', 0)
        items = results.get('items', [])
        
        print(f"\n{Fore.GREEN}Found {total_count} results{Style.RESET_ALL}")
        print(f"{Fore.BLUE}Showing {len(items)} results (ordered by date, descending){Style.RESET_ALL}\n")
        print("=" * 80)
        
        for i, item in enumerate(items):
            print(self.format_result(item, i))
            print("-" * 80)
    
    def interactive_search(self):
        """Run interactive search loop"""
        print(f"{Fore.CYAN}GitHub Code Search Tool{Style.RESET_ALL}")
        print("=" * 50)
        
        # Get GitHub token (optional)
        token = input(f"{Fore.YELLOW}Enter GitHub Personal Access Token (optional, press Enter to skip):{Style.RESET_ALL} ").strip()
        self.set_token(token)
        
        while True:
            print(f"\n{Fore.CYAN}Enter your search query (or 'quit' to exit):{Style.RESET_ALL}")
            query = input("> ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
                break
            
            if not query:
                print(f"{Fore.RED}Please enter a search query{Style.RESET_ALL}")
                continue
            
            # Optional language filter
            language = input(f"{Fore.YELLOW}Filter by language (optional, press Enter to skip):{Style.RESET_ALL} ").strip()
            if not language:
                language = None
            
            # Sort option
            print(f"{Fore.YELLOW}Sort by:")
            print(f"1. Best match (faster)")
            print(f"2. Date (slower, requires additional API calls)")
            sort_choice = input(f"Choose 1 or 2 (default: 1):{Style.RESET_ALL} ").strip()
            
            if sort_choice == "2":
                sort = "indexed"
                print(f"{Fore.BLUE}Using date sorting (this will take longer)...{Style.RESET_ALL}")
            else:
                sort = "best-match"
                print(f"{Fore.BLUE}Using best match sorting...{Style.RESET_ALL}")
            
            print(f"\n{Fore.BLUE}Searching for: '{query}'{Style.RESET_ALL}")
            if language:
                print(f"{Fore.BLUE}Language filter: {language}{Style.RESET_ALL}")
            
            # Perform search
            results = self.search_code(query, language=language, sort=sort)
            
            if results:
                self.display_results(results)
                
                # Allow user to select a result for detailed view
                self._handle_result_selection(results)
            else:
                print(f"{Fore.RED}Search failed. Please try again.{Style.RESET_ALL}")
            
            # Rate limiting info
            remaining = self.session.headers.get('X-RateLimit-Remaining', 'Unknown')
            reset_time = self.session.headers.get('X-RateLimit-Reset', 'Unknown')
            
            if reset_time != 'Unknown':
                reset_time = datetime.fromtimestamp(int(reset_time)).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\n{Fore.YELLOW}Rate limit info: {remaining} requests remaining, resets at {reset_time}{Style.RESET_ALL}")
    
    def _handle_result_selection(self, results):
        """Handle user selection of a search result for detailed view"""
        items = results.get('items', [])
        if not items:
            return
        
        print(f"\n{Fore.CYAN}Enter a result number (1-{len(items)}) to view commit history, or press Enter to continue:{Style.RESET_ALL}")
        try:
            selection = input("> ").strip()
            if not selection:
                return
            
            result_index = int(selection) - 1
            if 0 <= result_index < len(items):
                selected_item = items[result_index]
                repo_name = selected_item['repository']['full_name']
                file_path = selected_item['path']
                
                print(f"\n{Fore.GREEN}Selected: {repo_name}/{file_path}{Style.RESET_ALL}")
                
                # Ask for number of commits to show
                max_commits_input = input(f"{Fore.YELLOW}Number of commits to show (default 10):{Style.RESET_ALL} ").strip()
                max_commits = 10
                if max_commits_input:
                    try:
                        max_commits = int(max_commits_input)
                        max_commits = min(max_commits, 100)  # Limit to 100
                    except ValueError:
                        pass
                
                # Show commit history
                self.get_file_commit_history(repo_name, file_path, max_commits)
                
                # Ask if user wants to continue
                input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Invalid result number. Please enter a number between 1 and {len(items)}{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Selection cancelled{Style.RESET_ALL}")
    
    def _get_code_snippet_with_context(self, item):
        """Get code snippet with 2 lines before and after the matched text, always highlighting the match"""
        text_matches = item.get('text_matches', [])
        if not text_matches:
            return ""
        
        # Use the first text match
        match = text_matches[0]
        fragment = match.get('fragment', '')
        matched_text = match.get('text', '')
        
        if not fragment or not matched_text:
            return fragment or ""
        
        # Find all lines containing the matched text
        lines = fragment.split('\n')
        match_indices = [i for i, line in enumerate(lines) if matched_text in line]
        if not match_indices:
            # fallback: highlight all occurrences in the fragment
            highlighted = fragment.replace(matched_text, f"{Fore.RED}{matched_text}{Style.RESET_ALL}")
            return highlighted
        
        # For each match, show 2 lines before and after (but only the first match for now)
        idx = match_indices[0]
        start_line = max(0, idx - 2)
        end_line = min(len(lines), idx + 3)
        context_lines = lines[start_line:end_line]
        
        result_lines = []
        for i, line in enumerate(context_lines):
            line_num = start_line + i + 1
            if start_line + i == idx:
                # Highlight all occurrences of the matched text in the line
                highlighted_line = line.replace(matched_text, f"{Fore.RED}{matched_text}{Style.RESET_ALL}")
                result_lines.append(f"   >> {line_num:3d}: {highlighted_line}")
            else:
                result_lines.append(f"      {line_num:3d}: {line}")
        return '\n'.join(result_lines)

    def get_file_commit_history(self, repo_name, file_path, max_commits=10):
        """Get the full commit history for a specific file"""
        commits_url = f"{self.base_url}/repos/{repo_name}/commits?path={file_path}&per_page={max_commits}"
        
        try:
            print(f"{Fore.BLUE}Fetching commit history for {repo_name}/{file_path}...{Style.RESET_ALL}")
            response = self.session.get(commits_url)
            
            if response.status_code == 200:
                commits = response.json()
                if not commits:
                    print(f"{Fore.YELLOW}No commits found for this file{Style.RESET_ALL}")
                    return
                
                print(f"\n{Fore.GREEN}Found {len(commits)} commits for {repo_name}/{file_path}{Style.RESET_ALL}")
                print("=" * 80)
                
                for i, commit in enumerate(commits):
                    commit_sha = commit.get('sha', '')[:8]  # Short SHA
                    commit_date = commit.get('commit', {}).get('author', {}).get('date', '')
                    commit_message = commit.get('commit', {}).get('message', '').strip()
                    author_name = commit.get('commit', {}).get('author', {}).get('name', 'Unknown')
                    
                    # Parse and format the date
                    try:
                        parsed_date = parser.parse(commit_date)
                        formatted_date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_date = commit_date
                    
                    print(f"\n{Fore.CYAN}Commit {i+1}:{Style.RESET_ALL}")
                    print(f"   {Fore.YELLOW}SHA:{Style.RESET_ALL} {commit_sha}")
                    print(f"   {Fore.YELLOW}Date:{Style.RESET_ALL} {formatted_date}")
                    print(f"   {Fore.YELLOW}Author:{Style.RESET_ALL} {author_name}")
                    print(f"   {Fore.YELLOW}Message:{Style.RESET_ALL} {commit_message}")
                    
                    # Get the file content for this commit
                    try:
                        file_content = self._get_file_content_at_commit(repo_name, file_path, commit_sha)
                        if file_content:
                            print(f"   {Fore.YELLOW}File Content:{Style.RESET_ALL}")
                            # Show first 10 lines of the file
                            lines = file_content.split('\n')[:10]
                            for j, line in enumerate(lines, 1):
                                print(f"      {j:3d}: {line}")
                            if len(file_content.split('\n')) > 10:
                                remaining_lines = len(file_content.split('\n')) - 10
                                print(f"      ... ({remaining_lines} more lines)")
                    except Exception as e:
                        print(f"   {Fore.RED}Could not fetch file content: {e}{Style.RESET_ALL}")
                    
                    print("-" * 80)
                    
            else:
                print(f"{Fore.RED}Error fetching commit history: {response.status_code}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Response: {response.text}{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    
    def _get_file_content_at_commit(self, repo_name, file_path, commit_sha):
        """Get the file content at a specific commit"""
        try:
            # Get the file content at the specific commit
            file_url = f"{self.base_url}/repos/{repo_name}/contents/{file_path}?ref={commit_sha}"
            response = self.session.get(file_url)
            
            if response.status_code == 200:
                file_data = response.json()
                if file_data.get('type') == 'file':
                    # Decode the content (it's base64 encoded)
                    import base64
                    content = base64.b64decode(file_data.get('content', '')).decode('utf-8', errors='ignore')
                    return content
            
            return None
            
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not fetch file content at commit {commit_sha}: {e}{Style.RESET_ALL}")
            return None

def main():
    """Main function"""
    try:
        searcher = GitHubCodeSearch()
        searcher.interactive_search()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Search interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main() 