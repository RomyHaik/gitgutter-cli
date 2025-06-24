# GitGutter CLI

A powerful command-line tool for searching code across GitHub repositories using the GitHub API. Results are automatically ordered by date (descending) for the most relevant and up-to-date code snippets.

## Features

- 🔍 **Interactive Search**: Search for code snippets across GitHub repositories
- 📅 **Date-Ordered Results**: Results are sorted by date (newest first)
- 🎨 **Colored Output**: Beautiful terminal output with syntax highlighting
- 🔐 **Optional Authentication**: Use GitHub Personal Access Token for higher rate limits
- 🌐 **Language Filtering**: Filter results by programming language
- 📊 **Rich Information**: File details, repository info, and code previews
- ⚡ **Rate Limit Monitoring**: Track API usage and limits
- 🔧 **File Extension Filtering**: Include or exclude specific file types
- 📋 **Configuration File Detection**: Automatically detect config files in repositories

## Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the script:
```bash
python github_code_search.py
```

The script will prompt you for:
1. **GitHub Personal Access Token** (optional but recommended)
2. **Search query** (e.g., "somecode", "function login", "class User")
3. **Language filter** (optional, e.g., "python", "javascript", "java")

### Example Search Queries

- `somecode` - Search for files containing "somecode"
- `function login` - Search for login functions
- `class User` - Search for User classes
- `import requests` - Search for Python files importing requests
- `console.log` - Search for JavaScript console.log statements

### Language Filters

You can filter results by programming language:
- `python` - Python files
- `javascript` - JavaScript files
- `java` - Java files
- `cpp` - C++ files
- `csharp` - C# files
- `go` - Go files
- `rust` - Rust files
- And many more...

## GitHub Personal Access Token (Recommended)

For better rate limits and access to private repositories, create a GitHub Personal Access Token:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `public_repo` scope
3. Copy the token and paste it when prompted by the script

**Without a token**: 60 requests per hour
**With a token**: 5,000 requests per hour

## Example Output

```
GitHub Code Search Tool
==================================================

Enter GitHub Personal Access Token (optional, press Enter to skip): 
⚠ No token provided - using unauthenticated requests (rate limited)

Enter your search query (or 'quit' to exit):
> somecode

Filter by language (optional, press Enter to skip): 
python

Searching for: 'somecode'
Language filter: python

Found 1,234 results
Showing 30 results (ordered by date, descending)

================================================================================
1. username/repo-name/src/main.py
   Language: Python | Size: 1024 bytes
   Updated: 2024-01-15 14:30:25
   URL: https://github.com/username/repo-name/blob/main/src/main.py
   Preview:
   def somecode():
       print("Hello, World!")
       return True
--------------------------------------------------------------------------------
```

## Advanced Usage

### Programmatic Usage

You can also use the `GitHubCodeSearch` class in your own Python scripts:

```python
from github_code_search import GitHubCodeSearch

# Initialize searcher
searcher = GitHubCodeSearch()

# Set token (optional)
searcher.set_token("your_github_token")

# Search for code
results = searcher.search_code(
    query="somecode",
    language="python",
    sort="indexed",  # Sort by date
    order="desc",    # Descending order
    per_page=30      # Results per page
)

# Display results
searcher.display_results(results)
```

### Search Parameters

- `query` (str): The search query
- `language` (str, optional): Programming language filter
- `sort` (str): `'indexed'` (by date) or `'best-match'`
- `order` (str): `'desc'` (descending) or `'asc'` (ascending)
- `per_page` (int): Number of results per page (max 100)
- `file_filter` (dict, optional): File extension filter
- `check_config_files` (bool): Whether to check for config files

### File Extension Filtering

You can include or exclude specific file extensions:

```python
# Include only Python and JavaScript files
file_filter = {
    'type': 'include',
    'extensions': ['.py', '.js']
}

# Exclude configuration files
file_filter = {
    'type': 'exclude',
    'extensions': ['.config', '.env', '.ini']
}
```

## Rate Limiting

GitHub API has rate limits:
- **Unauthenticated**: 60 requests per hour
- **Authenticated**: 5,000 requests per hour

The script displays your current rate limit status after each search.

## Error Handling

The script handles various error scenarios:
- Network connectivity issues
- Invalid search queries
- Rate limit exceeded
- API errors

## Requirements

- Python 3.6+
- requests
- python-dateutil
- colorama

## Troubleshooting

### Common Issues

1. **Rate limit exceeded**: Wait for the rate limit to reset or use a GitHub token
2. **No results found**: Try a different search query or remove language filters
3. **Network errors**: Check your internet connection

### Getting Help

If you encounter issues:
1. Check that all dependencies are installed
2. Verify your GitHub token is valid (if using one)
3. Try simpler search queries first

## License

This project is open source and available under the MIT License.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool! 