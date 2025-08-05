#!/usr/bin/env python3
"""
Teste rápido da nova implementação com pdfplumber e prompt melhorado
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append('.')

def test_extraction():
    """Testa a extração com a nova implementação"""
    from server import processar_pdf_com_pdfplumber
    
    pdf_path = 'entrada/2023_10_Holerite_3.pdf'
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo {pdf_path} não encontrado")
        return
    
    print("🧪 TESTE: Nova implementação com pdfplumber e prompt melhorado")
    print("=" * 70)
    
    try:
        resultado = processar_pdf_com_pdfplumber(pdf_path)
        
        print("\n✅ RESULTADO EXTRAÍDO:")
        print("=" * 50)
        
        # Mostrar dados pessoais
        print("📋 DADOS PESSOAIS:")
        for campo in ['NOME', 'MATRICULA', 'FUNCAO', 'PERIODO', 'EMPRESA']:
            valor = resultado.get(campo, '')
            if valor:
                print(f"  {campo}: {valor}")
        
        # Mostrar valores monetários
        print("\n💰 VALORES FINANCEIROS:")
        campos_financeiros = [
            'SALARIO', 'PTS', 'BOG', 'INSS', 'IRRF', 'ADIANTAMENTO',
            'VALE_REFEICAO', 'PLANO_SAUDE', 'PLANO_ODONTO', 'COMBUSTIVEL'
        ]
        
        for campo in campos_financeiros:
            col1 = resultado.get(f"{campo}_COL1", '')
            col2 = resultado.get(f"{campo}_COL2", '')
            if col1 or col2:
                print(f"  {campo}: COL1={col1} | COL2={col2}")
        
        # Mostrar totais
        print("\n📊 TOTAIS:")
        for campo in ['TOTAL_BRUTO', 'TOTAL_DESCONTOS', 'VALOR_LIQUIDO']:
            valor = resultado.get(campo, '')
            if valor:
                print(f"  {campo}: {valor}")
                
        print(f"\n🎯 Total de campos extraídos: {len([v for v in resultado.values() if v])}")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    test_extraction()
