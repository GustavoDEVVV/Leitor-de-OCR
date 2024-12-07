from flask import Flask, request, render_template
import pytesseract
import PyPDF2
from werkzeug.utils import secure_filename
import os
import re
import spacy

# Inicializando a aplicação Flask
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Carregando o modelo de linguagem da spaCy
nlp = spacy.load("pt_core_news_sm")

# Rota para a página principal que exibe o formulário
@app.route('/')
def home():
    return render_template('index.html')

# Função para ler imagens com Tesseract
def read_image(file_path):
    return pytesseract.image_to_string(file_path)

# Função para ler PDFs com PyPDF2
def read_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
        return text

# Função principal para processar arquivos
def process_file(file_path):
    if file_path.endswith(('.png', '.jpg', '.jpeg')):
        return read_image(file_path)
    elif file_path.endswith('.pdf'):
        return read_pdf(file_path)
    else:
        return "Formato de arquivo não suportado."

# Função para buscar informações no texto extraído
def search_information(extracted_text, query):
    results = []  # Lista para armazenar todas as informações encontradas

    # Normalizando o texto para facilitar a busca
    extracted_text = extracted_text.lower()

    # Busca por informações do pagador ou recebedor com base na consulta
    if "pagador" in query.lower() or "quem pagou" in query.lower():
        name_payer = re.findall(r'nome:\s*(.*)', extracted_text)
        if name_payer:
            results.append(f"Nome do Pagador: {name_payer[0].strip()}")  # Primeiro nome encontrado
    elif "recebedor" in query.lower() or "quem recebeu" in query.lower():
        name_receiver = re.findall(r'nome:\s*(.*)', extracted_text)
        if name_receiver:
            results.append(f"Nome do Recebedor: {name_receiver[-1].strip()}")  # Último nome encontrado
    elif "nome" in query.lower():  # Se o usuário pedir apenas "nome"
        names = re.findall(r'nome:\s*(.*)', extracted_text)
        if names:
            # Caso o usuário não especifique, retorna tanto o pagador quanto o recebedor
            results.append(f"Nome do Pagador: {names[0].strip()}")
            results.append(f"Nome do Recebedor: {names[-1].strip()}")

    # Outras buscas como CPF, valor, etc.
    if "cpf" in query.lower() or "cnpj" in query.lower():
        cpf_match = re.findall(r'cpf/cnpj:\s*(\S+)', extracted_text)
        if cpf_match:
            results.extend([f"CPF/CNPJ: {cpf}" for cpf in cpf_match])

    if "valor" in query.lower():
        value = re.findall(r'valor:\s*r\$\s?(\d+,\d{2})', extracted_text)
        if value:
            results.append(f"Valor: R$ {value[0]}")

    if "instituição" in query.lower():
        institution_matches = re.findall(r'instituição:\s*(.*)', extracted_text)
        if institution_matches:
            results.append(f"Instituições: {', '.join(institution_matches)}")

    if "data" in query.lower():
        date_time = re.findall(r'data e hora:\s*(\d{2}/\d{2}/\d{4}\s*-\s*\d{2}:\d{2}:\d{2})', extracted_text)
        if date_time:
            results.append(f"Data e Hora: {date_time[0]}")

    if "identificador" in query.lower():
        identifier = re.findall(r'identificador:\s*(\S+)', extracted_text)
        if identifier:
            results.append(f"Identificador: {identifier[0]}")

    if "chave vinculada" in query.lower():
        linked_key = re.findall(r'chave vinculada:\s*(\S+)', extracted_text)
        if linked_key:
            results.append(f"Chave Vinculada: {linked_key[0]}")

    # Retornar as informações encontradas
    if not results:
        return "Não foi possível encontrar as informações solicitadas."

    return ", ".join(results)

# Rota de upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'message' not in request.form:
        return 'Nenhum arquivo ou mensagem fornecido.', 400

    file = request.files['file']
    message = request.form['message']

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Realizar OCR no arquivo
        extracted_text = process_file(file_path)

        # Filtrar a informação baseada na mensagem do usuário
        requested_info = search_information(extracted_text, message)

        # Exibir o resultado em outra página HTML
        return render_template('result.html', result=requested_info)

if __name__ == '__main__':
    app.run(debug=True)
