"""
File downloader tool from someonesproject2.
"""

from langchain_core.tools import tool
import requests
import os

@tool
def download_file(url: str, filename: str = None) -> str:
    """
    Download a file from a URL and save it locally.
    
    Use this for direct file downloads (PDFs, CSVs, images, etc.).
    DO NOT use get_rendered_html for file URLs - it will fail.
    
    Parameters
    ----------
    url : str
        Direct URL to the file
    filename : str, optional
        Name to save the file as. If not provided, extracts from URL.
    
    Returns
    -------
    str
        Path to the downloaded file, or error message
    """
    print(f"\n[DOWNLOADER] Downloading: {url}")
    
    try:
        # Create download directory
        download_dir = "hybrid_llm_files"
        os.makedirs(download_dir, exist_ok=True)
        
        # Determine filename
        if not filename:
            filename = url.split('/')[-1].split('?')[0]
            if not filename:
                filename = "downloaded_file"
        
        filepath = os.path.join(download_dir, filename)
        
        # Download file
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        file_size = len(response.content)
        print(f"[DOWNLOADER] ✓ Downloaded {file_size} bytes to {filepath}")
        
        return filepath
        
    except Exception as e:
        error_msg = f"Error downloading file: {str(e)}"
        print(f"[DOWNLOADER] ✗ {error_msg}")
        return error_msg
