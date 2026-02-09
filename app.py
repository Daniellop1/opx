import streamlit as st
import pandas as pd
from datetime import datetime
import io

def create_ofx(df, col_fecha, col_concepto, col_importe):
    """Genera el contenido OFX."""
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
            fecha_obj = row[col_fecha]
            if isinstance(fecha_obj, str):
                fecha_obj = pd.to_datetime(fecha_obj, dayfirst=True)
            date_str = fecha_obj.strftime('%Y%m%d')
            
            # Procesar importe
            amount = row[col_importe]
            if isinstance(amount, str):
                amount = float(amount.replace('.', '').replace(',', '.'))
            
            memo = str(row[col_concepto])
            fitid = f"{date_str}{amount}{memo[:5]}"
            
            transactions += f"""
                <STMTTRN>
                    <TRNTYPE>{'CREDIT' if amount > 0 else 'DEBIT'}</TRNTYPE>
                    <DTPOSTED>{date_str}</DTPOSTED>
                    <TRNAMT>{amount}</TRNAMT>
                    <FITID>{fitid}</FITID>
                    <MEMO>{memo}</MEMO>
                </STMTTRN>"""
        except:
            continue
    
    return ofx_header + transactions + ofx_footer

# --- Interfaz ---
st.set_page_config(page_title="Convertidor Bancario", page_icon="💰")
st.title("🏦 Convertidor Universal a OFX")

banco = st.selectbox("Selecciona el formato de origen", ["BBVA", "Santander", "Inversis"])
uploaded_file = st.file_uploader("Sube tu archivo Excel o CSV", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # Lógica de lectura según el banco
        if banco == "BBVA":
            # Según tu muestra, BBVA tiene 4 filas vacías/título y la col 0 está vacía
            df = pd.read_excel(uploaded_file, skiprows=4)
            # Si el archivo tiene una columna vacía al principio, la eliminamos
            df = df.dropna(axis=1, how='all') 
            c_fecha, c_concepto, c_importe = 'Fecha', 'Concepto', 'Importe'
        
        elif banco == "Santander":
            df = pd.read_excel(uploaded_file, skiprows=7)
            c_fecha, c_concepto, c_importe = 'Fecha Valor', 'Concepto', 'Importe'
            
        elif banco == "Inversis":
            # Inversis suele usar 'Fecha Operación' y 'Descripción'
            df = pd.read_excel(uploaded_file, skiprows=3) # Ajustar según tu Excel real
            c_fecha = 'Fecha Operación' if 'Fecha Operación' in df.columns else 'Fecha'
            c_concepto = 'Descripción' if 'Descripción' in df.columns else 'Concepto'
            c_importe = 'Importe'

        # Limpieza de datos
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=[c_fecha, c_importe])
        
        st.write("### Vista previa de los datos detectados:")
        st.dataframe(df[[c_fecha, c_concepto, c_importe]].head())

        # Botón de descarga
        ofx_output = create_ofx(df, c_fecha, c_concepto, c_importe)
        st.download_button(
            label=f"Descargar OFX para {banco}",
            data=ofx_output,
            file_name=f"export_{banco.lower()}.ofx",
            mime="application/x-ofx"
        )
        
    except Exception as e:
        st.error(f"Error al procesar: {e}. Revisa que las columnas coincidan.")
