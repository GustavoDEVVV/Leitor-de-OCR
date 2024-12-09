from flask import Flask, request, render_template
import pytesseract
import PyPDF2
from werkzeug.utils import secure_filename
import os
import re
from pdf2image import convert_from_path  # Adicionada para OCR em PDFs

# Inicializando a aplicação Flask
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Rota para a página principal que exibe o formulário
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ajuda')
def ajuda():
    return render_template('Tela_de_ajuda.html')

# Função para ler imagens com Tesseract
def read_image(file_path):
    return pytesseract.image_to_string(file_path)

# Função para ler PDFs com PyPDF2 ou OCR
def read_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()

        # Se o texto extraído estiver vazio, aplicar OCR no PDF
        if not text.strip():
            pages = convert_from_path(file_path)
            for page in pages:
                text += pytesseract.image_to_string(page)

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
    results = []

    # Normalizando o texto
    extracted_text = extracted_text.lower()

    # Definição de padrões para capturar os campos específicos
    fields = {
        "valor": r"valor:\s*r\$\s?(\d+,\d{2})",
        "nome do pagante": r"nome do pagante:\s*(.*)",
        "nome de quem recebeu": r"nome de quem recebeu:\s*(.*)",
        "cidade": r"cidade:\s*(.*)",
        "data": r"data:\s*(\d{2}/\d{2}/\d{4})",
        "instituição": r"instituição:\s*(.*)",
        "descrição": r"descrição:\s*(.*)",
        "chave pix": r"chave pix:\s*(.*)",
        "tipo de transação": r"tipo de transação:\s*(.*)",
        "número da transação": r"número da transação:\s*(\d+)",
        "conta do recebedor": r"conta do recebedor:\s*(.*)",
        "cpf do pagante": r"cpf do pagante:\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})",
        "cpf do recebedor": r"cpf do recebedor:\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})",
        "código de autenticação": r"código de autenticação:\s*(.*)",
        "horário da transação": r"horário da transação:\s*(.*)"
    }

    # Verifica qual campo o usuário solicitou e busca no texto
    for field, pattern in fields.items():
        if field in query.lower():
            match = re.search(pattern, extracted_text, re.IGNORECASE)
            if match:
                results.append(f"{field.capitalize()}: {match.group(1).strip()}")

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
