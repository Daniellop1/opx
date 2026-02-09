import streamlit as st
import pandas as pd
from datetime import datetime
import io

def smart_read(file, skiprows=0):
    """Intenta leer el archivo como Excel, si falla como CSV, y si falla como HTML."""
    # 1. Intentar como Excel real
    try:
        return pd.read_excel(file, skiprows=skiprows)
    except:
        pass
    
    # 2. Intentar como CSV (Muy común en BBVA aunque diga .xlsx)
    try:
        file.seek(0)
        return pd.read_csv(file, skiprows=skiprows, sep=None, engine='python')
    except:
        pass

    # 3. Intentar como HTML (Común en Inversis/Santander .xls antiguos)
    try:
        file.seek(0)
        tables = pd.read_html(file)
        if tables:
            df = tables[0]
            if skiprows > 0:
                df = df.iloc[skiprows:].reset_index(drop=True)
            return df
    except:
        pass
    
    raise ValueError("No se ha podido determinar el formato del archivo. ¿Seguro que es un extracto bancario?")

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
            # Limpiar fecha
            f_val = row[col_fecha]
            dt = pd.to_datetime(f_val, dayfirst=True) if isinstance(f_val, str) else f_val
            if pd.isna(dt): continue
            date_str = dt.strftime('%Y%m%d')
            
            # Limpiar importe
            amt = row[col_importe]
            if isinstance(amt, str):
                amt = float(amt.replace('.', '').replace(',', '.'))
            if pd.isna(amt): continue
            
            memo = str(row[col_concepto])
            fitid = f"{date_str}{str(abs(amt)).replace('.','')}{memo[:3]}".replace(" ", "")
            
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

# --- Interfaz ---
st.set_page_config(page_title="Convertidor Bancario PRO", page_icon="🏦")
st.title("🏦 Convertidor Bancario Inteligente")
st.write("Soporta archivos de BBVA, Santander e Inversis (incluso si la extensión es engañosa).")

banco = st.selectbox("Selecciona tu banco:", ["BBVA", "Santander", "Inversis"])
uploaded_file = st.file_uploader("Sube tu archivo", type=["xlsx", "xls", "csv"])

if uploaded_file:
    try:
        # Configuración por banco
        if banco == "BBVA":
            df = smart_read(uploaded_file, skiprows=4)
            # BBVA suele tener una col 0 vacía en sus CSVs
            df = df.dropna(axis=1, how='all')
            c_fecha, c_concepto, c_importe = 'Fecha', 'Concepto', 'Importe'
        
        elif banco == "Santander":
            df = smart_read(uploaded_file, skiprows=7)
            c_fecha, c_concepto, c_importe = 'Fecha Valor', 'Concepto', 'Importe'
            
        elif banco == "Inversis":
            df = smart_read(uploaded_file, skiprows=0)
            df.columns = df.columns.astype(str).str.strip()
            # Búsqueda automática de columnas para Inversis
            c_fecha = next((c for c in df.columns if 'fecha' in c.lower()), df.columns[0])
            c_concepto = next((c for c in df.columns if 'desc' in c.lower() or 'concep' in c.lower()), df.columns[1])
            c_importe = next((c for c in df.columns if 'importe' in c.lower()), df.columns[2])

        # Limpieza final
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=[c_fecha, c_importe])

        st.success("¡Archivo analizado con éxito!")
        st.dataframe(df[[c_fecha, c_concepto, c_importe]].head())

        ofx_data = create_ofx(df, c_fecha, c_concepto, c_importe)
        st.download_button("💾 Descargar .OFX", ofx_data, f"{banco.lower()}.ofx")

    except Exception as e:
        st.error(f"Error: {e}")
