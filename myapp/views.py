from django.shortcuts import render
from groq import Groq
from tika import parser
import json
import re
import requests
import os
from passwordmanager import settings
from .forms import UploadFileForm
from django.core.files.storage import FileSystemStorage

# Create your views here.

from django.http import HttpResponse
from django.template import loader

def display_start(request):
    return render(request, 'start_page.html')


# Step 1: Extract Text from PDF
def extract_text_from_pdf(pdf_path):
    raw = parser.from_file(pdf_path)  # Parse the PDF file
    return raw['content']

# Step 2: Send the parsed text to OpenAI API for processing
def send_to_openai(parsed_text):

    client = Groq(
        # This is the default and can be omitted
        api_key=settings.GROQ_API_KEY,
    )


    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"From the following text, create 25 hard flashcard-style exam questions and answers. It should test full coverage of the content, and include details such as any method and software definitions. Each flashcard should have a question and an answer in a json format: {parsed_text}",
            }
        ],
        model="llama3-8b-8192",
    )

    return chat_completion.choices[0].message.content

def get_in_json_form(summary, deck_name):

    pattern = r'\{.*?\}'
    matches = re.findall(pattern, summary, re.DOTALL)
    # Combine into a single JSON array string
    combined_json = '[' + ','.join(matches) + ']'

    # Parse the combined JSON string
    flashcards = json.loads(combined_json)
    
    for card in flashcards:
        answer = card.get("answer", "no answer found")
        question = card.get("question", "no question found")

        add_note_to_anki(deck_name, question, answer)
    



def add_note_to_anki(deck_name, front, back):
    # AnkiConnect API endpoint
    url = 'http://localhost:8765'
    
    # Prepare the payload for the API request
    payload = {
        'action': 'addNote',
        'version': 6,
        'params': {
            'note': {
                'deckName': deck_name,
                'modelName': 'Basic',
                'fields': {
                    'Front': front,
                    'Back': back
                },
                'tags': 'Week 3',
                'options': {
                    'allowDuplicate': True
                }
            }
        }
    }

    # Send the request to AnkiConnect
    response = requests.post(url, data=json.dumps(payload))
    return response.json()

def full_workflow(request):
    try:
        if request.method == 'POST':

            uploaded_file = request.FILES.get('pdf_file')
            deck_name = request.POST.get('set_name')

            fs = FileSystemStorage()

            file_path = None
            for i in range(2):
                file_path = fs.save(uploaded_file.name, uploaded_file)
                file_url = fs.url(file_path)
                print(file_path)

            # Absolute path where the file is saved
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
            
            # Process the file (e.g., extract text from the PDF)
            text = extract_text_from_pdf(file_path)

            if text:
                summary = send_to_openai(text)

                get_in_json_form(summary, deck_name)

                print("It should all be successful")
                os.remove(file_path)
                return render(request, 'success.html')
            
    except Exception:       
        return render(request, 'success.html')
    
    return render(request, 'error.html')

def save_uploaded_file(uploaded_file):
    # Define the path where the file will be saved
    file_path = f'media/uploads/{uploaded_file.name}'
    
    # Save the file to the specified path
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    return file_path

def success(request):
    return render(request, 'success.html')

def error(request):
    return render(request, 'error.html')

        