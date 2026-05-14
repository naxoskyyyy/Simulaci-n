import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import io

# 1. Configuración visual de la página web (Debe ser el primer comando de Streamlit)
st.set_page_config(page_title="Dulce Mamá - Herramientas", page_icon="🍰", layout="centered")

# 2. Configuración de la API (Preparado para la Nube y Local)
try:
    # Cuando lo subas a Streamlit Cloud, leerá la clave desde los ajustes de seguridad
    API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    # Si lo corres en tu PC y no tienes el archivo de secretos, usa esto (¡Bórralo antes de subir a GitHub!)
    API_KEY = "AIzaSyBmmy9FI7WrpITLm3Jrvo5H2mOsMwhk6gk" # Reemplaza con tu llave por ahora

client = genai.Client(api_key=API_KEY)

st.title("🍰 Sistema Administrativo Dulce Mamá")
st.subheader("Generador de Fichas Técnicas y Costos")

# 3. El "Cerebro" de la IA
instrucciones_sistema = """
Eres un ingeniero de alimentos y analista de costos para una pastelería en Chile.
Recibirás 4 datos: 1. Producto, 2. Porciones, 3. Ingredientes, 4. Tiempo de preparación.

Reglas matemáticas y normativas obligatorias:
- Costos Materia Prima: Estima en CLP usando precios de supermercados chilenos actuales.
- Costo Mano de Obra: La hora base es $5.000 CLP. Calcula el valor proporcional según los minutos.
- Precio Venta: (Costo Materia Prima + Costo Mano de Obra) * 1.35 (Margen del 35%).
- Nutrición: Suma el peso de todos los ingredientes. Calcula los nutrientes "Por 100g" y divídelo por las porciones.
- Sellos RSA: Aplica la Ley 20.606 y el Reglamento Sanitario de los Alimentos de Chile.

REGLA ESTRICTA DE FORMATO:
En el campo "explicacion_didactica", debes proporcionar un ARRAY DE STRINGS. Cada string debe explicar la operación matemática exacta que realizaste. NO des respuestas genéricas, muestra la fórmula.

Debes devolver ÚNICAMENTE un JSON válido con esta estructura exacta:
{
  "producto": "nombre",
  "finanzas": {
    "costo_materia_prima": 0,
    "costo_mano_obra": 0,
    "costo_total": 0,
    "precio_venta_sugerido": 0,
    "precio_por_porcion": 0
  },
  "ingredientes_costos": [
    {"ingrediente": "nombre", "cantidad": "valor", "costo_clp": 0}
  ],
  "tabla_nutricional": [
    {"nutriente": "Energía (kcal)", "por_100g": 0, "por_porcion": 0},
    {"nutriente": "Proteínas (g)", "por_100g": 0, "por_porcion": 0},
    {"nutriente": "Grasas Totales (g)", "por_100g": 0, "por_porcion": 0},
    {"nutriente": "Hidratos de Carbono (g)", "por_100g": 0, "por_porcion": 0},
    {"nutriente": "Azúcares Totales (g)", "por_100g": 0, "por_porcion": 0},
    {"nutriente": "Sodio (mg)", "por_100g": 0, "por_porcion": 0}
  ],
  "sellos_rsa": ["Alto en Calorías", "Alto en Azúcares"],
  "explicacion_didactica": [
    "Paso 1: ...",
    "Paso 2: ..."
  ]
}
"""

# 4. Formulario Web
with st.form("formulario_receta"):
    nombre_producto = st.text_input("1. Nombre del Producto (ej. Torta de Hojarasca)")
    
    col1, col2 = st.columns(2)
    with col1:
        porciones = st.number_input("2. ¿Cuántas porciones rinde?", min_value=1, step=1)
    with col2:
        tiempo_minutos = st.number_input("3. Minutos de preparación", min_value=1, step=5)
        
    ingredientes = st.text_area("4. Ingredientes detallados", placeholder="Ej: 2 tazas de harina, 500g manjar, 3 huevos...")
    
    submit_button = st.form_submit_button(label="Generar Cotización y Ficha")

# 5. Lógica de Ejecución al presionar el botón
if submit_button:
    if not nombre_producto or not ingredientes:
        st.error("Por favor, llena el nombre del producto y los ingredientes antes de continuar.")
    else:
        with st.spinner('Procesando cálculos, separando utilidades y armando Excel...'):
            prompt_usuario = f"Producto: {nombre_producto}\nPorciones: {porciones}\nIngredientes: {ingredientes}\nTiempo: {tiempo_minutos} minutos."
            
            try:
                respuesta = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_usuario,
                    config=types.GenerateContentConfig(
                        system_instruction=instrucciones_sistema,
                        response_mime_type="application/json",
                    )
                )
                
                texto_limpio = respuesta.text.replace("\\n", " ").replace("\\", "")
                datos = json.loads(texto_limpio)

                # --- NUEVA LÓGICA FINANCIERA ---
                costo_materia_prima = datos['finanzas']['costo_materia_prima']
                costo_total = datos['finanzas']['costo_total']
                precio_venta = datos['finanzas']['precio_venta_sugerido']
                ganancia_neta = precio_venta - costo_total

                df_resumen = pd.DataFrame([{
                    "Producto": datos["producto"],
                    "Porciones": porciones,
                    "Minutos Prep.": tiempo_minutos,
                    "Costo Materia Prima": f"${costo_materia_prima}",
                    "Costo Mano de Obra": f"${datos['finanzas']['costo_mano_obra']}",
                    "Costo Total (Inversión)": f"${costo_total}",
                    "Precio Venta Sugerido": f"${precio_venta}",
                    "Precio por Porción": f"${datos['finanzas']['precio_por_porcion']}",
                    "----------------------": "----------------------",
                    "DINERO A SEPARAR PARA REPONER INSUMOS": f"${costo_materia_prima}",
                    "GANANCIA NETA (Bolsillo/Negocio)": f"${ganancia_neta}",
                    "---------------------- ": "----------------------",
                    "Sellos (RSA)": ", ".join(datos["sellos_rsa"]) if datos["sellos_rsa"] else "Sin sellos"
                }])
                
                df_ingredientes = pd.DataFrame(datos["ingredientes_costos"])
                df_nutricion = pd.DataFrame(datos["tabla_nutricional"])

                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
                    df_nutricion.to_excel(writer, sheet_name="Nutricional", index=False)
                    df_ingredientes.to_excel(writer, sheet_name="Costos", index=False)
                
                texto_reporte = f"=== REPORTE TÉCNICO: {datos['producto'].upper()} ===\n\n"
                for parrafo in datos["explicacion_didactica"]:
                    texto_reporte += f"{parrafo}\n\n"

                st.success("¡Ficha técnica generada con éxito!")

                st.subheader("Descarga tus documentos:")
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    st.download_button(
                        label="📊 Descargar Excel",
                        data=excel_buffer.getvalue(),
                        file_name=f"Ficha_{nombre_producto.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                with col_btn2:
                    st.download_button(
                        label="📄 Descargar Explicación",
                        data=texto_reporte,
                        file_name=f"Explicacion_{nombre_producto.replace(' ', '_')}.txt",
                        mime="text/plain"
                    )

            except Exception as e:
                st.error(f"Ocurrió un error en el procesamiento. Detalles: {e}")