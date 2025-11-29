"""
Enhanced web scraper with context extraction.
Combines someonesproject2's clean implementation with context awareness.
"""

from langchain_core.tools import tool
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, Any

@tool
def get_rendered_html(url: str) -> str:
    """
    Fetch and return the fully rendered HTML of a webpage with enhanced context extraction.

    This function uses Playwright to load a webpage in a headless Chromium browser,
    allowing all JavaScript on the page to execute. It also extracts useful context
    like links, forms, and scripts.

    IMPORTANT RESTRICTIONS:
    - ONLY use this for actual HTML webpages (articles, documentation, dashboards).
    - DO NOT use this for direct file links (URLs ending in .csv, .pdf, .zip, .png).
      Playwright cannot render these and will crash. Use the 'download_file' tool instead.

    Parameters
    ----------
    url : str
        The URL of the webpage to retrieve and render.

    Returns
    -------
    str
        The fully rendered HTML content with metadata about links and forms.
    """
    print(f"\n[WEB_SCRAPER] Fetching and rendering: {url}")
    print(f"[WEB_SCRAPER] Launching Playwright browser...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            print(f"[WEB_SCRAPER] Browser launched, navigating to URL...")

            # Load the page (let JS execute)
            print(f"[WEB_SCRAPER] Waiting for page to load (networkidle)...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            print(f"[WEB_SCRAPER] Page loaded, waiting 2s for dynamic content...")
            page.wait_for_timeout(2000)  # Extra wait for dynamic content

            # Extract rendered HTML
            content = page.content()
            
            # Extract additional context
            links = []
            for link in page.query_selector_all("a"):
                href = link.get_attribute("href")
                text = link.inner_text()
                if href:
                    absolute_url = urljoin(url, href)
                    links.append({"url": absolute_url, "text": text})
            
            # Extract forms
            forms = []
            for form in page.query_selector_all("form"):
                action = form.get_attribute("action")
                method = form.get_attribute("method") or "GET"
                if action:
                    forms.append({
                        "action": urljoin(url, action),
                        "method": method.upper()
                    })

            browser.close()
            
            # Parse HTML for additional context
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract API URLs from scripts and links
            api_urls = []
            for script in soup.find_all('script'):
                script_text = script.string or ''
                # Look for API endpoints
                import re
                urls_in_script = re.findall(r'["\']https?://[^"\']+["\']', script_text)
                for found_url in urls_in_script:
                    clean_url = found_url.strip('"\'')
                    if 'api' in clean_url.lower() or clean_url.endswith('.json'):
                        api_urls.append(clean_url)
            
            # Build context metadata
            context_info = f"\n\n<!-- CONTEXT_METADATA\n"
            context_info += f"Links found: {len(links)}\n"
            if links[:5]:  # Show first 5 links
                context_info += "Top links:\n"
                for link in links[:5]:
                    context_info += f"  - {link['text']}: {link['url']}\n"
            
            if forms:
                context_info += f"\nForms found: {len(forms)}\n"
                for form in forms:
                    context_info += f"  - {form['method']} {form['action']}\n"
            
            if api_urls:
                context_info += f"\nAPI URLs found: {len(api_urls)}\n"
                for api_url in api_urls[:3]:
                    context_info += f"  - {api_url}\n"
            
            context_info += "-->\n"
            
            print(f"[WEB_SCRAPER] ✓ Page loaded successfully")
            print(f"[WEB_SCRAPER] Found {len(links)} links, {len(forms)} forms, {len(api_urls)} API URLs")
            
            return content + context_info

    except Exception as e:
        error_msg = f"Error fetching/rendering page: {str(e)}"
        print(f"[WEB_SCRAPER] ✗ {error_msg}")
        return error_msg
