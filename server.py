from flask import Flask, render_template_string, request, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
import json
import requests
import re
import pdfplumber

# Configurações
UPLOAD_FOLDER = 'entrada'
OUTPUT_FOLDER = 'saida'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def processar_pdf_com_pdfplumber(pdf_path):
    """Processa PDF usando pdfplumber para extração estruturada"""
    print(f"🚀 Processando: {pdf_path}")
    
    # 1. Extrair texto e tabelas com pdfplumber
    print("📋 Extraindo texto e tabelas com pdfplumber...")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]  # Primeira página
            
            # Extrair texto principal
            text = page.extract_text()
            
            # Extrair tabelas
            tables = page.extract_tables()
            
            # Montar texto estruturado
            structured_text = f"=== CABEÇALHO DO HOLERITE ===\n{text}\n\n"
            
            if tables:
                structured_text += "=== TABELAS DE VALORES ===\n"
                for i, table in enumerate(tables):
                    structured_text += f"\nTabela {i+1}:\n"
                    for row_idx, row in enumerate(table):
                        if row and any(cell for cell in row if cell):  # Linha não vazia
                            # Formatar linha de forma estruturada
                            cells = [str(cell).strip() if cell else "" for cell in row]
                            structured_text += f"Linha {row_idx+1}: {' | '.join(cells)}\n"
            
            print(f"✅ Texto estruturado extraído ({len(structured_text)} caracteres)")
            print(f"📊 Encontradas {len(tables)} tabelas")
            
    except Exception as e:
        raise Exception(f"Erro ao extrair PDF com pdfplumber: {str(e)}")
    
    # 2. Configurar prompt otimizado para texto estruturado
    prompt = f"""
    Analise este holerite/folha de pagamento extraído de forma estruturada e extraia TODOS os dados em JSON.

    DADOS DO HOLERITE:
    {structured_text}

    INSTRUÇÕES ESPECÍFICAS:
    1. No cabeçalho, encontre: NOME, MATRÍCULA, FUNÇÃO, PERÍODO, EMPRESA
    
    2. Nas tabelas, IGNORE os códigos numéricos (101, 171, 314, 401, 405, 410, 422, 424, 461, 564, 574, etc.) 
       que são apenas identificadores. Procure pelos VALORES MONETÁRIOS que vêm após as descrições:
       
       - SALARIO + valores monetários
       - PTS + valores monetários  
       - BOG + valores monetários
       - INSS + valores monetários
       - IMPOSTO DE RENDA/IRRF + valores monetários
       - ADIANT/ADIANTAMENTO + valores monetários
       - VALE REFEICAO/DESC VALE REFEICAO + valores monetários
       - ODONTO/PL ODONTO + valores monetários
       - PLANO SAUDE/COPART PLANO SAUDE + valores monetários
       - COMBUSTIVEL/DESC COMBUSTIVEL + valores monetários
       
    3. Procure por TOTAL BRUTO, TOTAL DESCONTOS, LÍQUIDO A RECEBER
    
    4. Para cada item que tem múltiplos valores numéricos, extraia:
       - COL1: primeiro valor (geralmente quantidade/horas)
       - COL2: segundo valor (geralmente valor monetário)
       
    5. IMPORTANTE: Números como 101, 171, 314, 401, 405, 410, 422, 424, 461, 564, 574 são CÓDIGOS,
       NÃO valores monetários. Ignore-os completamente.
       
    6. Use formato decimal: 1234.56 (converter vírgulas para pontos)
    7. Se não encontrar, deixe vazio ""
    
    EXEMPLO de como interpretar:
    "101 SALARIO 30.00 5.113,34" → SALARIO_COL1="30.00", SALARIO_COL2="5113.34"
    "171 PTS(1) 1.73 50,00" → PTS_COL1="1.73", PTS_COL2="50.00"
    "401 INSS 0.00 620,36" → INSS_COL1="0.00", INSS_COL2="620.36"
    
    RETORNE APENAS ESTE JSON (sem explicações):
    {{
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
    }}
    """
    
    # 3. Processar com Mistral via Ollama
    print("🤖 Processando com Mistral...")
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2000,
            "stop": ["}"]
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=300)  # 5 min
        
        if response.status_code != 200:
            raise Exception(f"Erro HTTP {response.status_code}: {response.text}")
        
        # 4. Extrair e processar resultado
        resposta = response.json()
        content = resposta['response']
        
        # Garantir que o JSON termine com }
        if not content.strip().endswith('}'):
            content += "}"
        
        print(f"📦 Resposta do Mistral: {content[:200]}...")
        
        # 5. Extrair JSON da resposta
        json_blocks = re.findall(r'\{[\s\S]*?\}', content, re.DOTALL)
        if not json_blocks:
            raise Exception(f"Nenhum JSON encontrado na resposta: {content}")
        
        # 6. Tentar cada bloco JSON encontrado
        for block in json_blocks:
            try:
                obj = json.loads(block)
                print(f"✅ Mistral extraiu {len(obj)} campos!")
                return obj
            except json.JSONDecodeError as e:
                print(f"⚠️ Erro ao parsear JSON: {e}")
                continue
                
        raise Exception("Não foi possível extrair JSON válido da resposta")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro na comunicação com Ollama: {str(e)}")

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
            
            # Processa o PDF com pdfplumber (extração estruturada)
            try:
                json_data = processar_pdf_com_pdfplumber(pdf_path)
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
            <h2>Leitor Inteligente de Holerite PDF (com PDFPlumber + Mistral)</h2>
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