import streamlit as st
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as ET
import io

def create_ofx(df, col_fecha, col_concepto, col_importe):
    ofx_header = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?OFX OFXHEADER="200" VERSION="211" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
<OFX>
    <BANKMSGSRSV1><STMTTRNRS><STMTRS>
        <CURDEF>EUR</CURDEF>
        <BANKTRANLIST>"""
    ofx_footer = """</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""

    transactions = ""
    for _, row in df.iterrows():
        try:
            # Procesar fecha
            f = row[col_fecha]
            dt = pd.to_datetime(f, dayfirst=True) if isinstance(f, str) else f
            date_str = dt.strftime('%Y%m%d')
            
            # Importe
            amt = row[col_importe]
            if isinstance(amt, str):
                amt = float(amt.replace('.', '').replace(',', '.'))
            
            memo = str(row[col_concepto])
            fitid = f"{date_str}{str(amt).replace('.','')}{memo[:3]}".replace(" ", "")
            
            transactions += f"""
                <STMTTRN>
                    <TRNTYPE>{'CREDIT' if amt > 0 else 'DEBIT'}</TRNTYPE>
                    <DTPOSTED>{date_str}</DTPOSTED>
                    <TRNAMT>{amt}</TRNAMT>
                    <FITID>{fitid}</FITID>
                    <MEMO>{memo}</MEMO>
                </STMTTRN>"""
        except: continue
    return ofx_header + transactions + ofx_footer

st.title("🏦 Conversor Universal a OFX")

banco = st.radio("Origen de datos:", ["BBVA", "Santander", "Inversis (XML)"], horizontal=True)

# Ajustar tipos de archivo permitidos
file_types = ["xlsx"] if banco != "Inversis (XML)" else ["xml"]
uploaded_file = st.file_uploader(f"Sube tu archivo de {banco}", type=file_types)

if uploaded_file:
    try:
        if banco == "BBVA":
            df = pd.read_excel(uploaded_file, skiprows=4).dropna(axis=1, how='all')
            c_fecha, c_concepto, c_importe = 'Fecha', 'Concepto', 'Importe'
        
        elif banco == "Santander":
            df = pd.read_excel(uploaded_file, skiprows=7)
            c_fecha, c_concepto, c_importe = 'Fecha Valor', 'Concepto', 'Importe'
            
        elif banco == "Inversis (XML)":
            # --- Lógica específica para XML de Inversis ---
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            
            data = []
            # Inversis suele estructurar por <movimiento> o similar
            # Buscamos de forma genérica etiquetas que suelen contener los datos
            for mov in root.iter():
                if 'movimiento' in mov.tag.lower() or 'item' in mov.tag.lower():
                    row = {}
                    for child in mov:
                        row[child.tag] = child.text
                    if row: data.append(row)
            
            df = pd.DataFrame(data)
            # Mapeo de columnas típicas de su XML
            c_fecha = next((c for c in df.columns if 'fecha' in c.lower()), None)
            c_concepto = next((c for c in df.columns if 'descripcion' in c.lower() or 'concepto' in c.lower()), None)
            c_importe = next((c for c in df.columns if 'importe' in c.lower()), None)

        df.columns = df.columns.str.strip()
        st.write("### Previsualización:")
        st.dataframe(df[[c_fecha, c_concepto, c_importe]].head())

        ofx_result = create_ofx(df, c_fecha, c_concepto, c_importe)
        st.download_button("💾 Descargar OFX", ofx_result, f"banco_{banco}.ofx")

    except Exception as e:
        st.error(f"Error: {e}")
