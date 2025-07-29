from flask import Flask, render_template_string, request, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
import json
import requests
import re
import base64
import fitz  # PyMuPDF

# Configurações
UPLOAD_FOLDER = 'entrada'
OUTPUT_FOLDER = 'saida'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def processar_pdf_com_visao(pdf_path):
    """Processa PDF usando apenas visão computacional"""
    print(f"🚀 Processando: {pdf_path}")
    
    # 1. Converter PDF para imagem
    print("🖼️ Convertendo PDF para imagem...")
    doc = fitz.open(pdf_path)
    page = doc[0]  # Primeira página
    mat = fitz.Matrix(2.0, 2.0)  # 200% zoom para melhor qualidade
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    doc.close()
    
    # 2. Codificar imagem em base64
    img_base64 = base64.b64encode(img_data).decode()
    print(f"✅ Imagem convertida ({len(img_base64)} caracteres)")
    
    # 3. Configurar prompt
    prompt = """
    Analise este holerite/folha de pagamento e extraia TODOS os dados em JSON estruturado.

    INSTRUÇÕES:
    1. Encontre cada campo pelo nome (SALARIO, PTS, BOG, INSS, etc.)
    2. Para campos com duas colunas de valores, extraia ambas
    3. Use formato decimal: 1234.56 (ponto para decimal)
    4. Se não encontrar, deixe vazio
    
    RETORNE APENAS ESTE JSON:
    {
      "NOME": "",
      "MATRICULA": "",
      "FUNCAO": "",
      "PERIODO": "",
      "EMPRESA": "",
      "SALARIO_COL1": "",
      "SALARIO_COL2": "",
      "PTS_COL1": "",
      "PTS_COL2": "",
      "BOG_COL1": "",
      "BOG_COL2": "",
      "INSS_COL1": "",
      "INSS_COL2": "",
      "IRRF_COL1": "",
      "IRRF_COL2": "",
      "ADIANTAMENTO_COL1": "",
      "ADIANTAMENTO_COL2": "",
      "VALE_REFEICAO_COL1": "",
      "VALE_REFEICAO_COL2": "",
      "PLANO_SAUDE_COL1": "",
      "PLANO_SAUDE_COL2": "",
      "PLANO_ODONTO_COL1": "",
      "PLANO_ODONTO_COL2": "",
      "COMBUSTIVEL_COL1": "",
      "COMBUSTIVEL_COL2": "",
      "TOTAL_BRUTO": "",
      "TOTAL_DESCONTOS": "",
      "VALOR_LIQUIDO": ""
    }
    """
    
    # 4. Processar com modelo de visão
    print("🤖 Processando com LLaVA 13B...")
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": "llava:13b",
        "prompt": prompt,
        "images": [img_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1500,
            "stop": ["}"]
        }
    }
    
    response = requests.post(url, json=payload, timeout=1800)  # 30 min
    
    if response.status_code != 200:
        raise Exception(f"Erro HTTP {response.status_code}: {response.text}")
    
    # 5. Extrair e processar resultado
    resposta = response.json()
    content = resposta['response'] + "}"  # Adiciona } caso tenha sido cortado
    
    # 6. Extrair JSON da resposta
    json_blocks = re.findall(r'\{[\s\S]*?\}', content, re.DOTALL)
    if not json_blocks:
        raise Exception(f"Nenhum JSON encontrado na resposta")
    
    # 7. Tentar cada bloco JSON encontrado
    for block in json_blocks:
        try:
            obj = json.loads(block)
            print(f"✅ LLaVA extraiu {len(obj)} campos!")
            return obj
        except:
            continue
            
    raise Exception("Não foi possível extrair JSON válido")

def salvar_resultado(nome_arquivo, dados):
    """Salva os resultados em JSON"""
    nome_base = os.path.splitext(nome_arquivo)[0]
    arquivo_saida = os.path.join(OUTPUT_FOLDER, f"{nome_base}_extraido.json")
    
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Resultado salvo em: {arquivo_saida}")
    return arquivo_saida

# Rotas da aplicação web
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    pdf_url = None
    json_data = None
    
    if request.method == 'POST':
        file = request.files.get('file')
        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)
            pdf_url = url_for('uploaded_file', filename=filename)
            
            # Processa o PDF com visão computacional
            try:
                json_data = processar_pdf_com_visao(pdf_path)
                salvar_resultado(filename, json_data)
            except Exception as e:
                json_data = {"Erro": f"Erro ao processar o PDF: {str(e)}"}
        else:
            json_data = {"Erro": "Arquivo inválido. Envie um PDF."}
    
    return render_template_string(HTML, pdf_url=pdf_url, json_data=json_data)

@app.route('/entrada/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Template HTML (manter seu HTML existente)
HTML = """
<!doctype html>
<html>
<head>
    <title>Leitor de Holerite PDF</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .upload-section { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .data-section { display: flex; gap: 20px; }
        .pdf-viewer { flex: 1; }
        .json-display { flex: 1; }
        .category { background: #fff; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 15px; }
        .category-header { background: #007bff; color: white; padding: 10px; border-radius: 8px 8px 0 0; font-weight: bold; }
        .category-content { padding: 15px; }
        .field-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee; }
        .field-name { font-weight: bold; color: #333; }
        .field-value { color: #666; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; }
        embed { border: 1px solid #ddd; border-radius: 4px; }
        .processing { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="upload-section">
            <h2>Leitor Inteligente de Holerite PDF</h2>
            <form method=post enctype=multipart/form-data>
                <input type=file name=file accept="application/pdf" style="margin-right: 10px;">
                <input type=submit value="Enviar e Processar" style="background: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
            </form>
        </div>

        {% if pdf_url or json_data %}
        <div class="data-section">
            {% if pdf_url %}
            <div class="pdf-viewer">
                <h3>📋 Documento Enviado</h3>
                <embed src="{{ pdf_url }}" width="100%" height="600" type="application/pdf">
            </div>
            {% endif %}

            {% if json_data %}
            <div class="json-display">
                <h3>📊 Dados Extraídos</h3>
                {% if json_data.get('Erro') %}
                    <div class="error">{{ json_data.Erro }}</div>
                {% else %}
                    {% for category, fields in json_data.items() %}
                        {% if fields is mapping %}
                        <div class="category">
                            <div class="category-header">{{ category.replace('_', ' ').title() }}</div>
                            <div class="category-content">
                                {% for field, value in fields.items() %}
                                    {% if value %}
                                    <div class="field-row">
                                        <span class="field-name">{{ field.replace('_', ' ').title() }}:</span>
                                        <span class="field-value">{{ value }}</span>
                                    </div>
                                    {% endif %}
                                {% endfor %}
                            </div>
                        </div>
                        {% else %}
                        <div class="category">
                            <div class="category-content">
                                <div class="field-row">
                                    <span class="field-name">{{ category.replace('_', ' ').title() }}:</span>
                                    <span class="field-value">{{ fields }}</span>
                                </div>
                            </div>
                        </div>
                        {% endif %}
                    {% endfor %}
                {% endif %}
            </div>
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)