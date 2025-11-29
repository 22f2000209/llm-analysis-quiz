"""
Data visualization tool for generating charts and graphs.
Supports matplotlib, seaborn, and returns base64-encoded images.
"""

from langchain_core.tools import tool
import os
import base64
from typing import Optional

@tool
def create_visualization(data_description: str, chart_type: str = "auto", title: str = "") -> str:
    """
    Generate a data visualization chart and return it as base64-encoded image.
    
    This tool generates Python code to create visualizations using matplotlib/seaborn,
    executes it, and returns the chart as a base64 string that can be submitted.
    
    Use this for:
    - Creating bar charts, line charts, scatter plots
    - Generating statistical visualizations
    - Creating heatmaps, histograms
    - Any data visualization task
    
    Parameters
    ----------
    data_description : str
        Description of the data and what to visualize.
        Should include data source (API, file, etc.) and what to plot.
        Example: "Fetch data from /api/sales and create a bar chart of sales by month"
    
    chart_type : str
        Type of chart to create. Options:
        - "auto": Let the system decide
        - "bar": Bar chart
        - "line": Line chart
        - "scatter": Scatter plot
        - "pie": Pie chart
        - "histogram": Histogram
        - "heatmap": Heatmap
        - "box": Box plot
    
    title : str
        Title for the chart
    
    Returns
    -------
    str
        Base64-encoded PNG image of the chart, or error message
    """
    print(f"\n[VISUALIZER] Creating {chart_type} visualization")
    print(f"[VISUALIZER] Data: {data_description[:100]}...")
    
    try:
        # Generate visualization code
        viz_code = f"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import base64
from io import BytesIO

# Set style
sns.set_style("whitegrid")
plt.figure(figsize=(10, 6))

# Data preparation and visualization
{data_description}

# Add title if provided
{"plt.title('" + title + "')" if title else ""}

# Save to base64
buffer = BytesIO()
plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
buffer.seek(0)
image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
plt.close()

# Print the base64 string
print(image_base64)
"""
        
        print(f"[VISUALIZER] Executing visualization code...")
        
        # Execute the code
        from hybrid_tools.code_executor import run_code
        result = run_code.invoke({"code": viz_code})
        
        if result["return_code"] == 0 and result["stdout"]:
            # Extract base64 from output
            output = result["stdout"].strip()
            
            # The last line should be the base64 string
            lines = output.split('\n')
            base64_str = lines[-1] if lines else output
            
            print(f"[VISUALIZER] ✓ Visualization created ({len(base64_str)} chars)")
            return base64_str
        else:
            error_msg = result.get("stderr", "Unknown error")
            print(f"[VISUALIZER] ✗ Failed: {error_msg}")
            return f"Error creating visualization: {error_msg}"
    
    except Exception as e:
        error_msg = str(e)
        print(f"[VISUALIZER] ✗ Exception: {error_msg}")
        return f"Error: {error_msg}"


@tool
def create_chart_from_data(data_code: str, chart_config: str) -> str:
    """
    Create a chart from data using custom Python code.
    
    Returns the base64-encoded image that can be submitted as the answer.
    """
    print(f"\n[VISUALIZER] Creating custom chart")
    
    try:
        full_code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import base64
from io import BytesIO
import httpx

# Data preparation
{data_code}

# Create figure
plt.figure(figsize=(10, 6))
sns.set_style("whitegrid")

# Chart configuration
{chart_config}

# Save to base64
buffer = BytesIO()
plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
buffer.seek(0)
answer = base64.b64encode(buffer.read()).decode('utf-8')
plt.close()

print(answer)
"""
        
        from hybrid_tools.code_executor import run_code
        result = run_code.invoke({"code": full_code})
        
        if result["return_code"] == 0 and result.get("answer"):
            print(f"[VISUALIZER] ✓ Chart created")
            # Return the base64 - LLM needs it to submit
            return result["answer"]
        else:
            error_msg = result.get("stderr", "Unknown error")
            print(f"[VISUALIZER] ✗ Failed: {error_msg}")
            return f"Error: {error_msg}"
    
    except Exception as e:
        error_msg = str(e)
        print(f"[VISUALIZER] ✗ Exception: {error_msg}")
        return f"Error: {error_msg}"
