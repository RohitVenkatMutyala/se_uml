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

def extract_plantuml_syntax(text):
    """Extract and clean PlantUML syntax between @startuml and @enduml tags."""
    pattern = r'@startuml\s*(.*?)\s*@enduml'
    match = re.search(pattern, text, re.DOTALL)
    
    if not match:
        raise Exception("No valid PlantUML syntax found in AI response")
    
    content = match.group(1)
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    
    cleaned_content = '\n'.join(lines)
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
    if theme:
        plantuml_syntax = f"!theme {theme}\n{plantuml_syntax}"

    diagram_base64 = generate_diagram(plantuml_syntax)

    return jsonify({
        'diagram': diagram_base64,
        'syntax': plantuml_syntax
    })

if __name__ == '__main__':
    app.run(debug=True)
    
    
    
    
    
    