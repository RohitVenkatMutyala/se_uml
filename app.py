import re
import requests
from flask import Flask, render_template, request, jsonify
import g4f
import os
import logging
from functools import wraps
import plantuml
import base64
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/diagrams'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize PlantUML with the correct image URL
plantuml_instance = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')
def get_plantuml_themes():
    """Return the fixed list of available PlantUML themes."""
    return [
        "amiga",
        "aws-orange",
        "black-knight",
        "bluegray",
        "blueprint",
        "carbon-gray",
        "cerulean-outline",
        "cerulean",
        "cloudscape-design",
        "crt-amber",
        "crt-green",
        "cyborg-outline",
        "cyborg",
        "hacker",
        "lightgray",
        "mars",
        "materia-outline",
        "materia",
        "metal",
        "mimeograph",
        "minty",
        "mono",
        "none",
        "plain",
        "reddress-darkblue",
        "reddress-darkgreen",
        "reddress-darkorange",
        "reddress-darkred",
        "reddress-lightblue",
        "reddress-lightgreen",
        "reddress-lightorange",
        "reddress-lightred",
        "sandstone",
        "silver",
        "sketchy-outline",
        "sketchy",
        "spacelab-white",
        "spacelab",
        "sunlust",
        "superhero-outline",
        "superhero",
        "toy",
        "united",
        "vibrant"
    ]

@app.route('/themes')
def get_themes():
    """Endpoint to fetch available PlantUML themes."""
    themes = get_plantuml_themes()
    return jsonify({'themes': themes})


def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except plantuml.PlantUMLHTTPError as e:
            logger.error(f"PlantUML HTTP Error: {str(e)}")
            return jsonify({'error': 'Failed to generate diagram: Server error'}), 500
        except plantuml.PlantUMLConnectionError as e:
            logger.error(f"PlantUML Connection Error: {str(e)}")
            return jsonify({'error': 'Failed to connect to PlantUML server'}), 500
        except plantuml.PlantUMLError as e:
            logger.error(f"PlantUML Error: {str(e)}")
            return jsonify({'error': 'Failed to process PlantUML syntax'}), 500
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return jsonify({'error': str(e)}), 500
    return decorated_function

def generate_ai_prompt(project_name, diagram_type, theme=None):
    """Generate a prompt for the AI based on project name, diagram type, and theme."""
    theme_directive = f"!theme {theme}\n" if theme else ""
    return f"""Create a PlantUML syntax for a {diagram_type} diagram for a project named {project_name}. 
    The diagram should be detailed and follow UML standards. 
    Provide only the PlantUML syntax without any additional text or explanations.
    Start with @startuml
    {theme_directive}"""

def generate_ai_prompt_from_description(description, diagram_type=None):
    """Generate a prompt for the AI based on natural language description."""
    diagram_type_info = f"for a {diagram_type} diagram" if diagram_type else ""
    
    return f"""Convert the following natural language description into proper PlantUML syntax {diagram_type_info}:
    
    "{description}"
    
    Provide only the PlantUML syntax without any additional text, explanations, or @startuml/@enduml tags.
    The syntax should follow UML standards and be detailed enough to represent all the entities and relationships described.
    """

def process_embedded_descriptions(syntax):
    """Process any natural language descriptions embedded within double quotes in the PlantUML syntax."""
    # Find all matches of text between double quotes that might be descriptions
    pattern = r'"([^"]{15,})"'  # Match text of at least 15 chars between quotes (to avoid normal short labels)
    
    # If no matches or syntax is too short, return original syntax
    if len(syntax) < 30 or not re.search(pattern, syntax):
        return syntax
    
    # Find all matches
    matches = re.finditer(pattern, syntax)
    modified_syntax = syntax
    
    for match in matches:
        description = match.group(1)
        # Check if this looks like a natural language description rather than a simple label
        words = description.split()
        if len(words) > 5:  # A heuristic to identify sentences vs. labels
            logger.info(f"Processing embedded description: {description[:50]}...")
            
            # Determine diagram type based on context if possible
            diagram_type = None
            if "class" in description.lower():
                diagram_type = "Class"
            elif "sequence" in description.lower() or "flow" in description.lower():
                diagram_type = "Sequence"
            elif "use case" in description.lower():
                diagram_type = "Use Case"
            elif "activity" in description.lower():
                diagram_type = "Activity"
            
            # Generate PlantUML code for this description
            prompt = generate_ai_prompt_from_description(description, diagram_type)
            
            try:
                # Get AI response for just this description
                replacement_syntax = get_ai_response(prompt)
                logger.info(f"Generated replacement syntax: {replacement_syntax[:50]}...")
                
                # Replace the description with the generated PlantUML syntax
                modified_syntax = modified_syntax.replace(match.group(0), replacement_syntax)
            except Exception as e:
                logger.error(f"Failed to process embedded description: {str(e)}")
                # If processing fails, keep the original text
                continue
    
    return modified_syntax

def extract_plantuml_syntax(text):
    """Extract and clean PlantUML syntax between @startuml and @enduml tags or from code blocks."""
    # First try to find syntax between @startuml and @enduml tags
    pattern = r'@startuml\s*(.*?)\s*@enduml'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        content = match.group(1)
    else:
        # If no @startuml tags, try to extract from code blocks
        code_block_pattern = r'```(?:plantuml)?\s*(.*?)```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        
        if match:
            content = match.group(1)
            # Check if content has @startuml and @enduml tags inside code block
            if '@startuml' in content and '@enduml' in content:
                inner_pattern = r'@startuml\s*(.*?)\s*@enduml'
                inner_match = re.search(inner_pattern, content, re.DOTALL)
                if inner_match:
                    content = inner_match.group(1)
        else:
            # If no code blocks, just use the entire text (maybe it's just the syntax)
            content = text
    
    # Clean up the content
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    
    # Remove empty lines at beginning and end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    
    cleaned_content = '\n'.join(lines)
    
    # If there are no @startuml tags in the final content, wrap it
    if '@startuml' not in cleaned_content:
        return cleaned_content
    else:
        # Extract only what's between @startuml and @enduml
        inner_pattern = r'@startuml\s*(.*?)\s*@enduml'
        inner_match = re.search(inner_pattern, cleaned_content, re.DOTALL)
        if inner_match:
            return inner_match.group(1).strip()
        else:
            return cleaned_content

def get_ai_response(prompt):
    """Get response from g4f AI API."""
    try:
        response = g4f.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_plantuml_syntax(response)
    except Exception as e:
        logger.error(f"AI API Error: {str(e)}")
        raise Exception("Failed to generate diagram syntax from AI")

def generate_diagram(plantuml_syntax):
    """Generate diagram image from PlantUML syntax."""
    try:
        # Make sure we have @startuml and @enduml tags
        if not plantuml_syntax.strip().startswith('@startuml'):
            plantuml_syntax = f"@startuml\n{plantuml_syntax}\n@enduml"
        
        png_data = plantuml_instance.processes(plantuml_syntax)
        return base64.b64encode(png_data).decode()
    except Exception as e:
        logger.error(f"PlantUML Processing Error: {str(e)}")
        raise

@app.route('/try')
def try_app():
    """Render the main page."""
    diagram_types = [
        "Sequence Diagram",
        "Use Case Diagram",
        "Class Diagram",
        "Object Diagram",
        "Activity Diagram",
        "Component Diagram",
        "Deployment Diagram",
        "State Diagram",
        "Timing Diagram"
    ]
    themes = get_plantuml_themes()
    return render_template('generate.html', diagram_types=diagram_types, themes=themes)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
@handle_errors
def generate():
    """Handle diagram generation request."""
    project_name = request.form.get('project_name')
    diagram_type = request.form.get('diagram_type')
    theme = request.form.get('theme')

    if not project_name or not diagram_type:
        return jsonify({'error': 'Missing required fields'}), 400

    prompt = generate_ai_prompt(project_name, diagram_type, theme)
    plantuml_syntax = get_ai_response(prompt)
    
    # If theme is selected, add theme directive at the beginning
    if theme and "!theme" not in plantuml_syntax:
        plantuml_syntax = f"!theme {theme}\n{plantuml_syntax}"

    diagram_base64 = generate_diagram(plantuml_syntax)

    return jsonify({
        'diagram': diagram_base64,
        'syntax': plantuml_syntax
    })

@app.route('/process_description', methods=['POST'])
@handle_errors
def process_description():
    """Process a natural language description directly."""
    data = request.get_json()
    
    if not data or 'description' not in data:
        return jsonify({'error': 'Missing required description field'}), 400
    
    description = data['description']
    diagram_type = data.get('diagram_type')
    theme = data.get('theme')
    
    # Generate PlantUML syntax from the description
    prompt = generate_ai_prompt_from_description(description, diagram_type)
    plantuml_syntax = get_ai_response(prompt)
    
    # If theme is selected, add theme directive at the beginning
    if theme and "!theme" not in plantuml_syntax:
        plantuml_syntax = f"!theme {theme}\n{plantuml_syntax}"
    
    # Generate diagram
    diagram_base64 = generate_diagram(plantuml_syntax)
    
    return jsonify({
        'diagram': diagram_base64,
        'syntax': plantuml_syntax
    })

@app.route('/debug_syntax', methods=['POST'])
@handle_errors
def debug_syntax():
    """Handle debugging and correction of PlantUML syntax."""
    data = request.get_json()
    
    if not data or 'syntax' not in data:
        return jsonify({'error': 'Missing required syntax field'}), 400
    
    syntax = data['syntax']
    
    # Check if this is just a description without any PlantUML syntax
    if syntax.strip().startswith('"') and syntax.strip().endswith('"'):
        # This is likely just a description in quotes, treat it as such
        description = syntax.strip('"')
        return process_description(jsonify({'description': description}))
    
    # First, process any embedded descriptions in the syntax
    logger.info("Processing embedded descriptions in syntax")
    processed_syntax = process_embedded_descriptions(syntax)
    
    # If the syntax was changed, generate diagram with the processed syntax
    if processed_syntax != syntax:
        logger.info("Descriptions were processed, generating diagram with processed syntax")
        try:
            # Make sure we have theme info if provided
            theme = data.get('theme')
            if theme and "!theme" not in processed_syntax:
                processed_syntax = f"!theme {theme}\n{processed_syntax}"
                
            # Generate diagram with processed syntax
            diagram_base64 = generate_diagram(processed_syntax)
            
            return jsonify({
                'diagram': diagram_base64,
                'syntax': processed_syntax,
                'message': 'Natural language descriptions were converted to PlantUML syntax'
            })
        except Exception as e:
            logger.warning(f"Error with processed syntax: {str(e)}. Falling back to debug.")
            pass
    
    # If no descriptions were found or processing failed, debug the syntax
    logger.info("No descriptions found or processing failed, debugging syntax")
    # Generate AI prompt for debugging
    prompt = f"""Debug and correct the following PlantUML syntax to ensure it works properly.
    If there are any errors, fix them. If the syntax is valid, optimize it for better readability.
    Return only the corrected PlantUML syntax without any additional text or explanations.
    
    ```
    {syntax}
    ```"""
    
    try:
        # Get AI response
        corrected_syntax = get_ai_response(prompt)
        
        # Apply theme if provided
        theme = data.get('theme')
        if theme and "!theme" not in corrected_syntax:
            corrected_syntax = f"!theme {theme}\n{corrected_syntax}"
        
        # Generate diagram with corrected syntax
        diagram_base64 = generate_diagram(corrected_syntax)
        
        return jsonify({
            'diagram': diagram_base64,
            'syntax': corrected_syntax
        })
    except Exception as e:
        logger.error(f"Debug Syntax Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)