import os
import requests
import json
from pdfminer.high_level import extract_text
import re
import unicodedata

INPUT_FOLDER = "entrada"
OUTPUT_FOLDER = "saida"

def extrair_texto_pdf(pdf_path):
    return extract_text(pdf_path)

def normalize_key(key):
    # Remove acentos, espaços, parênteses, aspas e deixa maiúsculo
    key = unicodedata.normalize('NFKD', key).encode('ASCII', 'ignore').decode('ASCII')
    key = key.replace(' ', '').replace('(', '').replace(')', '').replace('"', '').replace("'", '').replace('.', '').upper()
    return key

def normalize_json_keys(obj):
    if isinstance(obj, dict):
        return {normalize_key(k): v for k, v in obj.items()}
    return obj

def chamar_ia(texto):
    url = "http://localhost:11434/api/generate"
    prompt = (
        "Você é um extrator de dados de nota fiscal. Analise o texto e extraia APENAS os valores numéricos correspondentes a cada campo.\n"
        "Retorne APENAS um JSON válido com os campos encontrados:\n"
        "REGRAS IMPORTANTES:\n"
        "- Para TOTAL: procure por 'VALOR TOTAL' ou 'TOTAL' seguido de R$ e um valor\n"
        "- Para VALOR_DO_SERVICO: procure por 'VALOR DO SERVIÇO' ou 'VALOR SERVIÇO' seguido de valor\n"
        "- Para ISS: procure por 'ISS' ou 'ISSQN' ou 'VALOR DO ISS' seguido de valor\n"
        "- Para INSS: procure por 'INSS' seguido de valor\n"
        "- Para PIS: procure por 'PIS' seguido de valor\n"
        "- Para COFINS: procure por 'COFINS' seguido de valor\n"
        "- Para CSLL: procure por 'CSLL' seguido de valor\n"
        "- Para IRRF: procure por 'IRRF' seguido de valor\n"
        "- Para BASE_DE_CALCULO: procure por 'BASE DE CÁLCULO' seguido de valor\n"
        "- Para ALIQUOTA: procure por 'ALÍQUOTA' ou '%' seguido de número\n"
        "- Para TOTAL_RETENCOES: procure por 'TOTAL DAS RETENÇÕES' ou 'TOTAL RETENÇÕES' seguido de valor\n"
        "- Para VALOR_LIQUIDO: procure por 'VALOR LÍQUIDO' ou 'LÍQUIDO' seguido de valor\n"
        "- Para DEDUCAO: procure por 'DEDUÇÃO' seguido de valor\n"
        "- Para OUTRAS_DEDUCOES: procure por 'OUTRAS DEDUÇÕES' seguido de valor\n"
        "- Para QTD: procure por 'QTD' ou 'QUANTIDADE' seguido de número\n"
        "- Para DESCONTO: procure por 'DESCONTO' seguido de valor\n"
        "- Se não encontrar o campo, deixe vazio\n"
        "- Use apenas números no formato: 123.45 (sem R$, sem vírgulas para milhares)\n\n"
        "FORMATO DE RESPOSTA (apenas o JSON):\n"
        '{"TOTAL": "565365.03", "VALOR_DO_SERVICO": "565365.03", "ISS": "11307.30", "ALIQUOTA": "5.00", "BASE_DE_CALCULO": "565365.03", "INSS": "31095.07", "PIS": "3674.87", "COFINS": "16960.95", "CSLL": "6105.94", "IRRF": "6784.38", "TOTAL_RETENCOES": "64621.21", "VALOR_LIQUIDO": "500743.82", "DEDUCAO": "339219.01", "OUTRAS_DEDUCOES": "", "QTD": "1", "DESCONTO": ""}\n\n'
        f"TEXTO DA NOTA FISCAL:\n{texto}"
    )
    print(f"Enviando prompt para IA...")
    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(url, json=payload, timeout=240)
    if response.status_code != 200:
        raise Exception(f"Erro HTTP {response.status_code}: {response.text}")
    resposta = response.json()
    try:
        content = resposta['response']
        # Extrai o primeiro bloco JSON válido
        json_blocks = re.findall(r'\{[^{}]*\}', content)
        if not json_blocks:
            raise Exception(f"Nenhum JSON encontrado na resposta: {content}")
        
        for block in json_blocks:
            try:
                obj = json.loads(block)
                obj = normalize_json_keys(obj)
                return obj
            except Exception:
                continue
        
        raise Exception(f"Nenhum JSON válido extraído da resposta: {content}")
    except Exception as e:
        raise Exception(f"Erro ao processar resposta da IA: {str(e)}")

def filtrar_linhas_relevantes(texto):
    # Melhora o filtro para pegar apenas linhas com valores monetários
    palavras_chave = [
        "TOTAL", "ISS", "ISSQN", "INSS", "PIS", "COFINS", "CSLL", "IRRF",
        "VALOR", "BASE DE CÁLCULO", "ALÍQUOTA", "R$", "SERVIÇO", "RETENÇÕES",
        "LÍQUIDO", "DEDUÇÃO", "DEDUÇÕES", "QTD", "QUANTIDADE", "DESCONTO"
    ]
    linhas = texto.splitlines()
    relevantes = []
    
    for linha in linhas:
        linha_upper = linha.upper()
        # Pega linhas que contêm palavras-chave E valores monetários (R$ ou números com vírgula/ponto)
        if any(palavra in linha_upper for palavra in palavras_chave):
            if 'R$' in linha or re.search(r'\d+[.,]\d+', linha):
                relevantes.append(linha.strip())
    
    return "\n".join(relevantes)

def salvar_resultado(nome_arquivo, dados):
    # Cria pasta saida se não existir
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    
    # Nome do arquivo de saída
    nome_base = os.path.splitext(nome_arquivo)[0]
    arquivo_saida = os.path.join(OUTPUT_FOLDER, f"{nome_base}_extraido.json")
    
    # Salva o JSON
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    
    print(f"Resultado salvo em: {arquivo_saida}")

def main():
    arquivos = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(".pdf")]
    
    if not arquivos:
        print("Nenhum arquivo PDF encontrado na pasta 'entrada'")
        return
    
    for arquivo in arquivos:
        print(f"\nProcessando: {arquivo}")
        pdf_path = os.path.join(INPUT_FOLDER, arquivo)
        
        try:
            # Extrai texto do PDF
            texto = extrair_texto_pdf(pdf_path)
            print(f"Texto extraído com sucesso ({len(texto)} caracteres)")
            
            # Filtra linhas relevantes
            texto_filtrado = filtrar_linhas_relevantes(texto)
            print(f"Texto filtrado ({len(texto_filtrado)} caracteres)")
            
            # Chama IA para extrair dados
            campos = chamar_ia(texto_filtrado)
            print(f"Dados extraídos: {json.dumps(campos, ensure_ascii=False, indent=2)}")
            
            # Salva resultado
            salvar_resultado(arquivo, campos)
            
        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")

if __name__ == "__main__":
    main()
