# CHROMEX
A web application for generating UML diagrams for software engineering projects.

### 📝 Description
This application allows users to create and generate various types of UML (Unified Modeling Language) diagrams for software engineering projects. UML diagrams help visualize, document, and design software systems by providing standardized notation.

### 📁 File Structure
```
├── har_and_cookies/         # Directory for storing diagram data
├── templates/               # HTML templates
│   ├── generate.html        # Template for generating UML diagrams
│   └── index.html           # Main application interface
├── .gitattributes           # Git attributes file
├── .gitignore               # Git ignore file
├── README.md                # This file
├── app.py                   # Main application file
├── d.sh                     # Shell script (possibly for deployment)
├── logo.jpeg                # Application logo
└── requirements.txt         # Python dependencies
```

### 🚀 Installation
Clone the repository:
```bash
git clone https://github.com/RohitVenkatMutyala/se_uml.git
cd se_uml
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

Run the application:
```bash
python app.py
```

Open your web browser and navigate to http://localhost:5000 

### 🔧 Dependencies
The application requires the following Python packages:
- Flask: Web framework for building the application
- g4f: Library for data formatting and handling
- plantuml: For generating UML diagrams
- python-dotenv: For loading environment variables
- requests: For making HTTP requests
- Werkzeug: WSGI web application library used by Flask

### 🖱️ Usage
1. Navigate to the dummy page and then click open then you will open the uml generator
2. In that there was a text field asks about the project description give about our project details and some description
3. Then you have a chance to select which type of Diagram Type there are 9 diagram types such as:
   - Class diagrams
   - Sequence diagrams
   - Use case diagrams
   - Activity diagrams
   - State diagrams
   - etc.
4. Then you have chance to select which type of Theme
5. Click the generate button
6. It will start generating the uml diagram
7. If you get any errors then please try to run it again this because of an internal server error due large crowd on the server
8. When your UML Diagram appears, if you are not satisfied with that then you start editing it in the code editor below it
9. There's no need of checking and writing the code without any errors it debug the code and it show the debugging history in the comments in the code
10. When you're satisfied with the output you can share these with our teammates who are on the github by just clicking the download button it create two files one is uml diagram and another is Plantuml code
