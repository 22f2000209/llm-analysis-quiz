"""
Image analysis tool using Gemini Vision API.
For vision tasks: analyzing images, charts, diagrams, etc.
"""

from langchain_core.tools import tool
import os
import base64
from typing import Optional

@tool
def analyze_image(image_url: str, question: str = "Describe this image in detail") -> str:
    """
    Analyze an image using Gemini Vision API.
    
    Use this for:
    - Reading text from images (OCR)
    - Analyzing charts and graphs
    - Describing visual content
    - Extracting data from diagrams
    - Answering questions about images
    
    Parameters
    ----------
    image_url : str
        URL to the image file or local path
    question : str
        Question to ask about the image or task to perform
        Examples:
        - "What text is in this image?"
        - "What are the values in this chart?"
        - "Describe what you see"
        - "Extract the data from this table"
    
    Returns
    -------
    str
        Answer or description based on the image
    """
    print(f"\n[IMAGE_ANALYZER] Analyzing image: {image_url}")
    print(f"[IMAGE_ANALYZER] Question: {question}")
    
    try:
        import mimetypes
        from openai import OpenAI
        
        # Use Gemini via OpenAI-compatible API (same as llm_client.py)
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Error: GOOGLE_API_KEY not found in environment"
        
        print(f"[IMAGE_ANALYZER] Using Gemini Vision via OpenAI-compatible API")
        
        # Download image if it's a URL
        if image_url.startswith('http'):
            from hybrid_tools.download_file import download_file
            local_path = download_file.invoke({"url": image_url})
            
            if "Error" in local_path:
                return f"Failed to download image: {local_path}"
            
            image_path = local_path
        else:
            image_path = image_url
        
        print(f"[IMAGE_ANALYZER] Using image: {image_path}")
        
        # Determine mime type
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            mime_type = "image/jpeg"
        
        print(f"[IMAGE_ANALYZER] Image mime type: {mime_type}")
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        print(f"[IMAGE_ANALYZER] Image size: {len(image_data)} bytes (base64)")
        
        # Use OpenAI client with Gemini base URL
        client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        # Use same model as in .env (gemini-2.5-flash)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        print(f"[IMAGE_ANALYZER] Calling Gemini Vision API with model: {model}")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_data}"}
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        answer = response.choices[0].message.content
        
        print(f"[IMAGE_ANALYZER] ✓ Analysis complete")
        print(f"[IMAGE_ANALYZER] Answer: {answer[:200] if answer else 'EMPTY'}...")
        
        return answer if answer else "No response from vision API"

        
    except ImportError:
        # Fallback to OpenAI Vision if Gemini not available
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Download image if URL
            if image_url.startswith('http'):
                from hybrid_tools.download_file import download_file
                local_path = download_file.invoke({"url": image_url})
                image_path = local_path
            else:
                image_path = image_url
            
            # Encode image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Determine image type
            ext = image_path.split('.')[-1].lower()
            mime_type = f"image/{ext}" if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else "image/png"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            print(f"[IMAGE_ANALYZER] ✓ Analysis complete (OpenAI fallback)")
            return answer
            
        except Exception as e:
            error_msg = f"Error analyzing image: {str(e)}"
            print(f"[IMAGE_ANALYZER] ✗ {error_msg}")
            return error_msg
    
    except Exception as e:
        error_msg = f"Error analyzing image: {str(e)}"
        print(f"[IMAGE_ANALYZER] ✗ {error_msg}")
        return error_msg
