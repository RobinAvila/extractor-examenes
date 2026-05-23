import streamlit as st
import pdfplumber
from google import genai
import os

# Configuración de la página de Streamlit
st.set_page_config(page_title="Extractor de Exámenes de Laboratorio", page_icon="🩺", layout="centered")

st.title("🩺 Extractor de Exámenes de Laboratorio")
st.write("Sube un PDF del cualquier laboratorio clínico para obtener los resultados en un formato estructurado listo para copiar.")

# --- CONFIGURACIÓN DE LA API KEY (AHORA VISIBLE DE INMEDIATO) ---
api_key = st.text_input(
    "Introduce tu Clave de API aquí:", 
    type="password", 
    help="Tu clave personal empieza con 'AIzaSy...'. Se requiere para activar la IA."
)

# --- SECCIÓN DE AYUDA (AHORA ABAJO COMO SOPORTE) ---
with st.expander("ℹ️ ¿No tienes una Clave de API o no sabes cómo usar la herramienta?", expanded=False):
    st.markdown("""
    Para que este extractor funcione, necesitas una **API Key** gratuita de Google. Esto asegura que los datos se procesen localmente de forma rápida y segura. Sigue estos pasos para obtener la tuya:
    
    1. **Entra a la plataforma:** Ingresa a [Google AI Studio](https://aistudio.google.com/) con cualquier cuenta de Gmail común.
    2. **Genera el código:** Haz clic en el botón de arriba a la izquierda que dice **"Crear clave de API"**. Se desplegará una ventana donde podrás dar un nombre a la clave y elegir proyecto. Selecciona **+ Crear proyecto.** Dale un nombre y luego selecciona **Crear clave.**
    3. **Copia y pega:** Copia esa cadena larga de letras y números, pégala en la casilla visible de arriba y da ENTER.
    4. **Carga o arrastra** el documento en PDF y el procesamiento se hará automáticamente.
    """)

# Definición del Prompt Maestro Optimizado
PROMPT_MAESTRO = """
Eres un asistente de extracción de datos clínicos de la más alta precisión. Tu tarea es extraer resultados de exámenes desde el texto de un PDF y formatearlos estrictamente bajo las siguientes reglas:

1. Identifica la Fecha del examen de forma clara.
2. Reporta los resultados en el orden exacto indicado abajo, usando solo las abreviaturas y omitiendo los títulos de las secciones.

REGLA CRÍTICA DE ASTERISCOS (*):
- Examina con extremo cuidado el texto crudo. Si un número o parámetro tiene un asterisco (*) antes, después o cerca (incluso si quedó en la línea de arriba o en una columna adyacente debido al formato del PDF), DEBES conservar ese asterisco pegado al número en el reporte final (Ejemplo: * 11.5 o *37). Esto es vital para identificar valores fuera de rango.

Estructura estricta del reporte principal:
- Fecha: [Fecha]
- Hba1c: [Valor]
- Glic: [Valor]
- P. lipídico: CT [Valor], cHDL [Valor], cLDL [Valor], Tg [Valor] (mantener asteriscos si corresponden)
- Crea: [Valor], VFGe: [Valor] (incluir el método de cálculo que aparezca indexado, ej: MDRD o CKD-EPI)
- RAC: [Valor]
- BUN: [Valor], Urea: [Valor]
- ELP: Na+ [X] mEq/L / K+ [Y] mEq/L / Cl- [Z] mEq/L
- Ác. Úrico: [Valor]
- P. Hepático: GOT/AST: [valor], GPT/ALT: [Valor], GGT: [Valor], B. Total: [Valor], B. Directa: [Valor], B. Indirecta: [Valor]
- Albúmina:[Valor]
- INR: [Valor]
- Hemograma: Hto: [X]%, Hb: [Y] g/dL, VCM: [Z] fL, HCM: [W] pg, GB: [Valor transformado] /mm3, Plaq: [Valor transformado] /mm3
- Orina: SO: Leuco [Valor], Hematíes [Valor], y reportar el químico solo si hay alteraciones (ej: Glucosa, Nitritos o Cuerpos cetónicos positivos). Si todo el sedimento/químico es normal o negativo, pon "Orina completa normal".
- TSH: [Valor], T4L: [Valor]

Reglas críticas de transformación para el Hemograma:
- Para GB y Plaq multiplica el valor base por 10^3 para mostrar el número completo y termínalo en /mm3 (Ej: si dice 7.01 con unidad x10^3, pon 7.010 /mm3; si dice 305, pon 305.000 /mm3). Si el valor original llevaba asterisco, mantlo (Ej: * 7.010 /mm3).

REDE DE SEGURIDAD PARA EXÁMENES ADICIONALES:
- Es OBLIGATORIO que revises si existen más exámenes en el texto que NO estén incluidos en la lista de arriba (por ejemplo: Frotis, Fórmula leucocitaria detallada, parámetros específicos de orina alterados, PCR, Troponinas, Vitaminas, Cinética de hierro, Otroas Pruebas de coagulación como TP/% Actividad de Protrombina, etc.).
- Si encuentras cualquiera de estos datos adicionales, agrégalos todos al final del reporte en una sección llamada "Otros exámenes:" detallando sus nombres, valores y unidades correspondientes, manteniendo también sus asteriscos si los tienen. Si no hay nada adicional, omite esta sección.

Responde únicamente con el texto formateado, sin introducciones ni comentarios adicionales.
"""

st.write("---")

# Componente para subir el archivo PDF
uploaded_file = st.file_uploader("Arrastra o selecciona el archivo PDF del examen a procesar", type=["pdf"])

if uploaded_file is not None:
    if not api_key:
        st.error("⚠️ Por favor, introduce tu Clave de API de Google en la casilla superior para comenzar el procesamiento.")
    else:
        with st.spinner("Procesando documento clínico..."):
            try:
                # 1. Extraer el texto del PDF usando pdfplumber
                texto_crudo = ""
                with pdfplumber.open(uploaded_file) as pdf:
                    for pagina in pdf.pages:
                        texto_pag = pagina.extract_text()
                        if texto_pag:
                            texto_crudo += f"\n{texto_pag}"

                if not texto_crudo.strip():
                    st.error("No se detectó texto en el PDF. Asegúrate de que no sea una imagen escaneada sin reconocimiento de caracteres.")
                else:
                    # 2. Llamada a la API de Gemini
                    client = genai.Client(api_key=api_key)
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[PROMPT_MAESTRO, f"Texto del examen:\n{texto_crudo}"]
                    )
                    
                    # 3. Despliegue del resultado final
                    st.success("¡Extracción completada!")
                    st.text_area("Resultado listo para copiar:", value=response.text, height=400)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar el archivo: {e}")
