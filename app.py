import streamlit as st
import pandas as pd
from datetime import datetime
import io

def create_ofx(df, col_fecha, col_concepto, col_importe):
    """Genera el contenido OFX estándar."""
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
            fecha_val = row[col_fecha]
            if isinstance(fecha_val, str):
                dt = pd.to_datetime(fecha_val, dayfirst=True)
            else:
                dt = fecha_val
            date_str = dt.strftime('%Y%m%d')
            
            # Procesar importe
            amount = row[col_importe]
            if isinstance(amount, str):
                # Limpiar formatos como 1.250,50
                amount = float(amount.replace('.', '').replace(',', '.'))
            
            memo = str(row[col_concepto])
            # Generar ID único para evitar duplicados en apps de finanzas
            fitid = f"{date_str}{str(amount).replace('.','')}{memo[:3]}".replace(" ", "")
            
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

# --- Configuración de la App ---
st.set_page_config(page_title="Convertidor Bancario", page_icon="📈")
st.title("🏦 Convertidor de Extractos a OFX")
st.markdown("Convierte tus archivos de **BBVA, Santander o Inversis** para usarlos en aplicaciones de finanzas.")

banco = st.selectbox("Selecciona tu banco:", ["BBVA", "Santander", "Inversis"])
# Inversis suele ser .xls, BBVA/Santander suelen ser .xlsx
uploaded_file = st.file_uploader("Sube el archivo descargado de tu banco", type=["xlsx", "xls"])

if uploaded_file:
    try:
        if banco == "BBVA":
            # Ajustado según el archivo real que subiste (salta 4 filas, limpia vacíos)
            df = pd.read_excel(uploaded_file, skiprows=4)
            df = df.dropna(axis=1, how='all') # Elimina columnas vacías iniciales
            c_fecha, c_concepto, c_importe = 'Fecha', 'Concepto', 'Importe'
        
        elif banco == "Santander":
            df = pd.read_excel(uploaded_file, skiprows=7)
            c_fecha, c_concepto, c_importe = 'Fecha Valor', 'Concepto', 'Importe'
            
        elif banco == "Inversis":
            # Inversis .xls: suele tener cabeceras simples
            df = pd.read_excel(uploaded_file) 
            # Intentamos detectar columnas si no son fijas
            df.columns = df.columns.str.strip()
            c_fecha = next((c for c in df.columns if 'fecha' in c.lower()), df.columns[0])
            c_concepto = next((c for c in df.columns if 'desc' in c.lower() or 'concep' in c.lower()), df.columns[1])
            c_importe = next((c for c in df.columns if 'importe' in c.lower() or 'valor' in c.lower()), df.columns[2])

        # Limpiar espacios en nombres de columnas
        df.columns = df.columns.str.strip()
        # Eliminar filas donde la fecha sea nula (finales de página, etc)
        df = df.dropna(subset=[c_fecha])

        st.success(f"Archivo de {banco} cargado con éxito.")
        st.write("### Vista previa de movimientos:")
        st.dataframe(df[[c_fecha, c_concepto, c_importe]].head())

        # Botón de descarga
        ofx_data = create_ofx(df, c_fecha, c_concepto, c_importe)
        st.download_button(
            label="💾 Descargar archivo .OFX",
            data=ofx_data,
            file_name=f"movimientos_{banco.lower()}.ofx",
            mime="application/x-ofx"
        )
        
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        st.info("Nota: Si es un .xls de Inversis, asegúrate de tener instalada la librería 'xlrd'.")
