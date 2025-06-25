import os
import requests
import json
from pdfminer.high_level import extract_text
import re

INPUT_FOLDER = "entrada"
OUTPUT_FOLDER = "saida"

def extrair_texto_pdf(pdf_path):
    return extract_text(pdf_path)

def chamar_ia(texto):
    url = "http://localhost:11434/api/generate"
    prompt = (
        "Extraia todos os valores monetários do texto de uma nota fiscal abaixo. "
        "Responda APENAS com um JSON, usando as seguintes chaves: "
        "TOTAL, VALOR DO ISS, ALIQUOTA(%), BASE DE CÁLCULO(R$), DEDUÇÃO, DESCONTO, QTD., VALOR DO SERVIÇO, "
        "INSS, PIS, COFINS, CSLL, IRRF. "
        "Se algum campo não existir, retorne vazio. "
        "Exemplo de resposta:\n"
        '{"TOTAL": "1000.00", "VALOR DO ISS": "50.00", "ALIQUOTA(%)": "5", "BASE DE CÁLCULO(R$)": "1000.00", '
        '"DEDUÇÃO": "", "DESCONTO": "", "QTD.": "", "VALOR DO SERVIÇO": "1000.00", '
        '"INSS": "", "PIS": "", "COFINS": "", "CSLL": "", "IRRF": ""}\n'
        "Agora, extraia do texto a seguir e retorne os valores em JSON APENAS EM JSON:\n"
        f"{texto}"
    )
    print(f"Prompt enviado ao modelo:\n{prompt}\n{'='*40}")
    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(url, json=payload, timeout=270)
    if response.status_code != 200:
        raise Exception(f"Erro HTTP {response.status_code}: {response.text}")
    resposta = response.json()
    try:
        content = resposta['response']
        # Extrai todos os blocos JSON válidos, mesmo dentro de ```json ... ```
        json_blocks = re.findall(r'\{[\s\S]*?\}', content)
        if not json_blocks:
            raise Exception(f"Nenhum JSON encontrado na resposta: {content}")
        json_objs = []
        for block in json_blocks:
            try:
                json_objs.append(json.loads(block.replace('\n', '').replace('\r', '')))
            except Exception:
                continue
        if not json_objs:
            raise Exception(f"Nenhum JSON válido extraído da resposta: {content}")
        # Se só houver um JSON, retorna ele; se houver vários, retorna a lista
        return json_objs if len(json_objs) > 1 else json_objs[0]
    except Exception as e:
        raise Exception(f"Resposta inesperada da IA: {resposta}")

def filtrar_linhas_relevantes(texto):
    palavras_chave = [
        "TOTAL", "ISS", "INSS", "PIS", "COFINS", "CSLL", "IRRF",
        "VALOR", "BASE DE CÁLCULO", "DEDUÇÃO", "DESCONTO", "QTD.", "ALIQUOTA"
    ]
    linhas = texto.splitlines()
    relevantes = [linha for linha in linhas if any(palavra in linha.upper() for palavra in palavras_chave)]
    return "\n".join(relevantes)

def main():
    arquivos = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(".pdf")]
    for arquivo in arquivos:
        pdf_path = os.path.join(INPUT_FOLDER, arquivo)
        texto = extrair_texto_pdf(pdf_path)
        print(f"Texto extraído de {arquivo}:\n{texto}\n{'-'*40}")
        texto_filtrado = filtrar_linhas_relevantes(texto)
        print(f"Texto filtrado de {arquivo}:\n{texto_filtrado}\n{'='*40}")
        try:
            campos = chamar_ia(texto_filtrado)
            print(f"JSON extraído de {arquivo}:\n{json.dumps(campos, ensure_ascii=False, indent=2)}\n{'#'*40}")
        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")

if __name__ == "__main__":
    main()