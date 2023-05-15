from flask import Flask, render_template, request, jsonify
import spacy
import fitz
import re
import json
import os

app = Flask(__name__)

nlp = spacy.load('en_core_web_sm')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # Get the uploaded file from the request
    file = request.files['resume']
    
    # Open the PDF file in binary mode
    with fitz.open(stream=file.read(), filetype='pdf') as pdf_file:
        # Extracting the text from each page of the PDF file
        text = ''
        for page in pdf_file:
            text += page.get_text()

        # Cleaning up the text
        text = ' '.join(text.split())

        # Using Spacy to parse the text and extract relevant information
        doc = nlp(text)
        data = {}

        # Extracting the name of the individual 
        name = ''
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                name = ent.text
                break
        data['name'] = name if name else None

        # Extract age
        age = ''
        age_re = re.compile(r'\b\d{1,2}\b\s*(years old|yo|Y\.O\.|yrs|years)')
        match = age_re.search(text)
        if match:
            age = match.group(0)
        data['age'] = age if age else None

        # Extracting contact information
        contact = {}
        email_re = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        phone_re = re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')
        address_re = re.compile(r'\b\d+\s+([A-Za-z]+\s+){1,3}(St\.|Ave\.|Rd\.|Blvd\.|Ln\.)\b')
        for token in doc:
            if token.like_email:
                match = email_re.search(token.text)
                if match:
                    contact['email'] = match.group(0)
            elif phone_re.search(token.text):
                match = phone_re.search(token.text)
                if match:
                    contact['phone'] = match.group(0)
            elif token.is_stop and token.nbor().is_title:
                match = address_re.search(f'{token.text} {token.nbor().text}')
                if match:
                    contact['address'] = match.group(0)
        data['contact'] = contact if contact else None

        # Extracting skills if available 
        programming_languages = []
        frontend_technologies = []
        backend_technologies = []
        operating_systems = []
        databases = []
        other_skills = []
        for sent in doc.sents:
            if 'Programming Languages:' in sent.text:
                programming_languages.extend([skill.strip() for skill in sent.text.replace('Programming Languages:', '').split(',')])
            elif 'Frontend Technologies:' in sent.text:
                frontend_technologies.extend([skill.strip() for skill in sent.text.replace('Frontend Technologies:', '').split(',')])
            elif 'Backend Technologies:' in sent.text:
                backend_technologies.extend([skill.strip() for skill in sent.text.replace('Backend Technologies:', '').split(',')])
            elif 'Operating Systems:' in sent.text:
                operating_systems.extend([skill.strip() for skill in sent.text.replace('Operating Systems:', '').split(',')])
            elif 'Databases:' in sent.text:
                databases.extend([skill.strip() for skill in sent.text.replace('Databases:', '').split(',')])
            elif 'Other:' in sent.text:
                other_skills.extend([skill.strip() for skill in sent.text.replace('Other:', '').split(',')])
        data['programming_languages'] = programming_languages if programming_languages else None
        data['frontend_technologies'] = frontend_technologies if frontend_technologies else None
        data['backend_technologies'] = backend_technologies if backend_technologies else None
        data['operating_systems'] = operating_systems if operating_systems else None
        data['databases'] = databases if databases else None
        data['other_skills'] = other_skills if other_skills else None

        # Extracting honors and awards if available
        honors_and_awards = []
        honors_re = re.compile(r'\b\d{4}\b(.+)')
        matches = honors_re.findall(text)
        for match in matches:
            honors_and_awards.append(match.strip())
        data['honors_and_awards'] = honors_and_awards if honors_and_awards else None

        # Extracting extracurricular activities if available
        extracurricular_activities = []
        activities_re = re.compile(r'Contributor in (.+?)\s(.+?)\s(.+?)\s·\sRésumé the extraction of this in the skills')
        matches = activities_re.findall(text)
        for match in matches:
            activity = {
                'name': match[0].strip(),
                'location': match[1].strip(),
                'year': match[2].strip()
            }
            extracurricular_activities.append(activity)
        data['extracurricular_activities'] = extracurricular_activities if extracurricular_activities else None

        # Passing the extracted information to a JSON file
        with open('resume_info.json', 'w') as json_file:
            json.dump(data, json_file, indent=8, sort_keys=True)

        # Return the extracted information as a JSON response
        return jsonify(data=sorted(data.items()))


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
