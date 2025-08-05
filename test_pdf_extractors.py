#!/usr/bin/env python3
"""
Teste de diferentes bibliotecas para extração de PDF
Comparando a qualidade da extração estruturada
"""

import os
import pdfplumber
import pymupdf4llm
import fitz  # PyMuPDF
import tabula
import camelot
import pdfquery

def test_pymupdf4llm(pdf_path):
    """Teste com pymupdf4llm (atual)"""
    print("\n🔍 TESTE 1: pymupdf4llm")
    print("=" * 50)
    try:
        text = pymupdf4llm.to_markdown(pdf_path)
        print(f"Caracteres extraídos: {len(text)}")
        print("Amostra:")
        print(text[:800])
        return text
    except Exception as e:
        print(f"Erro: {e}")
        return None

def test_pdfplumber(pdf_path):
    """Teste com pdfplumber - ótimo para tabelas"""
    print("\n🔍 TESTE 2: pdfplumber")
    print("=" * 50)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            
            # Extração de texto simples
            text = page.extract_text()
            print(f"Texto simples - Caracteres: {len(text)}")
            
            # Tentativa de extrair tabelas
            tables = page.extract_tables()
            print(f"Tabelas encontradas: {len(tables)}")
            
            result = f"TEXTO:\n{text}\n\n"
            
            if tables:
                result += "TABELAS:\n"
                for i, table in enumerate(tables):
                    result += f"\nTabela {i+1}:\n"
                    for row in table:
                        if row:
                            result += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
            
            print("Amostra:")
            print(result[:800])
            return result
            
    except Exception as e:
        print(f"Erro: {e}")
        return None

def test_tabula(pdf_path):
    """Teste com tabula-py - especializado em tabelas"""
    print("\n🔍 TESTE 3: tabula-py")
    print("=" * 50)
    try:
        # Tentar extrair todas as tabelas
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        print(f"Tabelas encontradas: {len(tables)}")
        
        result = ""
        for i, df in enumerate(tables):
            result += f"\nTabela {i+1}:\n"
            result += df.to_string() + "\n"
        
        print("Amostra:")
        print(result[:800])
        return result
        
    except Exception as e:
        print(f"Erro: {e}")
        return None

def test_camelot(pdf_path):
    """Teste com camelot - detecção avançada de tabelas"""
    print("\n🔍 TESTE 4: camelot")
    print("=" * 50)
    try:
        tables = camelot.read_pdf(pdf_path, pages='1')
        print(f"Tabelas encontradas: {len(tables)}")
        
        result = ""
        for i, table in enumerate(tables):
            result += f"\nTabela {i+1} (confiança: {table.parsing_report['accuracy']:.2f}):\n"
            result += table.df.to_string() + "\n"
        
        print("Amostra:")
        print(result[:800])
        return result
        
    except Exception as e:
        print(f"Erro: {e}")
        return None

def test_pymupdf_raw(pdf_path):
    """Teste com PyMuPDF direto - controle total"""
    print("\n🔍 TESTE 5: PyMuPDF (raw)")
    print("=" * 50)
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        
        # Extração de texto com layout preservado
        text = page.get_text("text")
        print(f"Texto simples - Caracteres: {len(text)}")
        
        # Extração com informações de layout
        blocks = page.get_text("dict")
        
        result = f"TEXTO SIMPLES:\n{text}\n\n"
        result += "ESTRUTURA DE BLOCOS:\n"
        
        for block in blocks["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    if line_text.strip():
                        result += f"Linha: {line_text.strip()}\n"
        
        doc.close()
        
        print("Amostra:")
        print(result[:800])
        return result
        
    except Exception as e:
        print(f"Erro: {e}")
        return None

def main():
    pdf_path = "entrada/2023_10_Holerite_3.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo {pdf_path} não encontrado!")
        return
    
    print(f"🎯 Testando extração de: {pdf_path}")
    
    # Executar todos os testes
    results = {}
    
    results['pymupdf4llm'] = test_pymupdf4llm(pdf_path)
    results['pdfplumber'] = test_pdfplumber(pdf_path)
    results['tabula'] = test_tabula(pdf_path)
    results['camelot'] = test_camelot(pdf_path)
    results['pymupdf_raw'] = test_pymupdf_raw(pdf_path)
    
    # Resumo
    print("\n" + "="*80)
    print("📊 RESUMO DOS TESTES")
    print("="*80)
    
    for method, result in results.items():
        if result:
            print(f"✅ {method}: {len(result)} caracteres extraídos")
        else:
            print(f"❌ {method}: Falhou")

if __name__ == "__main__":
    main()
