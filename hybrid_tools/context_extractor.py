"""
Context extraction tool from your project.
Extracts rich context from HTML pages.
"""

from langchain_core.tools import tool
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import requests
from typing import Dict, Any

@tool
def extract_context(html: str, base_url: str = "") -> str:
    """
    Extract rich context from HTML including URLs, APIs, JavaScript, and forms.
    
    This tool analyzes HTML to find:
    - Submit URLs and API endpoints
    - JavaScript code and logic
    - Form actions and methods
    - Sample API data
    
    Parameters
    ----------
    html : str
        HTML content to analyze
    base_url : str
        Base URL for resolving relative links
    
    Returns
    -------
    str
        JSON string with extracted context information
    """
    print(f"\n[CONTEXT] Extracting context from HTML ({len(html)} chars)")
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        context = {}
        
        # Extract submit URLs
        submit_urls = []
        
        # Check forms
        for form in soup.find_all('form'):
            action = form.get('action', '')
            if action:
                full_url = urljoin(base_url, action) if base_url else action
                submit_urls.append(full_url)
        
        # Check for submit URLs in text
        text = soup.get_text()
        submit_patterns = [
            r'submit.*?to[:\s]+([^\s<]+)',
            r'POST.*?to[:\s]+([^\s<]+)',
            r'endpoint[:\s]+([^\s<]+)',
        ]
        
        for pattern in submit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.startswith('http'):
                    submit_urls.append(match)
                elif base_url:
                    submit_urls.append(urljoin(base_url, match))
        
        context['submit_urls'] = list(set(submit_urls))
        
        # Extract API URLs
        api_urls = []
        
        # From links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'api' in href.lower() or href.endswith('.json'):
                full_url = urljoin(base_url, href) if base_url else href
                api_urls.append(full_url)
        
        # From scripts
        for script in soup.find_all('script'):
            script_text = script.string or ''
            urls_in_script = re.findall(r'["\']https?://[^"\']+["\']', script_text)
            for url in urls_in_script:
                clean_url = url.strip('"\'')
                if 'api' in clean_url.lower() or clean_url.endswith('.json'):
                    api_urls.append(clean_url)
        
        context['api_urls'] = list(set(api_urls))
        
        # Extract JavaScript code
        scripts = []
        for script in soup.find_all('script'):
            if script.string:
                scripts.append(script.string)
        
        context['javascript_count'] = len(scripts)
        if scripts:
            # Include first script as sample
            context['sample_javascript'] = scripts[0][:500]
        
        # Sample API endpoints
        api_samples = {}
        for api_url in api_urls[:3]:  # Sample first 3 APIs
            try:
                resp = requests.get(api_url, timeout=5)
                if resp.status_code == 200:
                    try:
                        api_samples[api_url] = resp.json()
                    except:
                        api_samples[api_url] = resp.text[:200]
            except:
                pass
        
        context['api_samples'] = api_samples
        
        # Extract forms
        forms = []
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET').upper(),
                'inputs': []
            }
            
            for input_tag in form.find_all('input'):
                form_data['inputs'].append({
                    'name': input_tag.get('name', ''),
                    'type': input_tag.get('type', 'text'),
                })
            
            forms.append(form_data)
        
        context['forms'] = forms
        
        # Summary
        print(f"[CONTEXT] ✓ Extracted:")
        print(f"[CONTEXT]   - {len(submit_urls)} submit URLs")
        print(f"[CONTEXT]   - {len(api_urls)} API URLs")
        print(f"[CONTEXT]   - {len(scripts)} JavaScript blocks")
        print(f"[CONTEXT]   - {len(forms)} forms")
        print(f"[CONTEXT]   - {len(api_samples)} API samples")
        
        import json
        return json.dumps(context, indent=2)
        
    except Exception as e:
        error_msg = f"Error extracting context: {str(e)}"
        print(f"[CONTEXT] ✗ {error_msg}")
        return error_msg
