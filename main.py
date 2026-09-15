import re
import pandas as pd
from difflib import SequenceMatcher
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import chromadb
from fastapi.staticfiles import StaticFiles  

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# --- CONFIGURACIÓN CHROMADB (En Memoria) ---
chroma_client = chromadb.Client()
coleccion_productos = chroma_client.get_or_create_collection(
    name="catalogo_productos")

ARCHIVO_EXCEL = "productos.xlsx"
STOPWORDS = {
    'cuanto', 'cuesta', 'el', 'la', 'los', 'las', 'un', 'una',
    'de', 'precio', 'tienen', 'valen', 'vale', 'detalles', 'stock',
    'buscando', 'necesito', 'quisiera', 'saber', 'que', 'por', 'favor'
}


def normalizar_texto(texto: str) -> str:
    texto = str(texto).lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def calcular_similitud(texto1: str, texto2: str) -> float:
    return SequenceMatcher(None, texto1, texto2).ratio()


# --- CARGA E INDIZACIÓN EN CHROMADB ---
try:
    df_productos = pd.read_excel(ARCHIVO_EXCEL)

    # 1. Normalizar nombres de columnas (quita espacios y tildes en los encabezados)
    df_productos.columns = df_productos.columns.str.strip().str.lower()
    
    # Si la columna se llama 'categoría' con tilde, la renombras
    if 'categoría' in df_productos.columns:
        df_productos.rename(columns={'categoría': 'categoria'}, inplace=True)

    # 2. Asegurar que existan las columnas mínimas necesarias
    columnas_esperadas = {'nombre': '', 'precio': 0.0, 'cantidad': 0, 'desc': '', 'categoria': 'general'}
    for col, val_defecto in columnas_esperadas.items():
        if col not in df_productos.columns:
            df_productos[col] = val_defecto

    # 3. Limpiar valores nulos para evitar errores de JSON
    df_productos = df_productos.fillna({
        'nombre': 'Sin nombre',
        'precio': 0.0,
        'cantidad': 0,
        'desc': 'Sin descripción',
        'categoria': 'general'
    })

    # 4. Crear columnas auxiliares de búsqueda
    df_productos['nombre_busqueda'] = df_productos['nombre'].astype(str).apply(normalizar_texto)
    df_productos['categoria'] = df_productos['categoria'].astype(str).apply(normalizar_texto)

    # 5. Convertir a diccionario seguro de Python
    productos = []
    for row in df_productos.to_dict(orient="records"):
        productos.append({
            "nombre": str(row.get('nombre', '')),
            "nombre_busqueda": str(row.get('nombre_busqueda', '')),
            "precio": float(row.get('precio', 0.0)),
            "cantidad": int(row.get('cantidad', 0)),
            "desc": str(row.get('desc', '')),
            "categoria": str(row.get('categoria', 'general'))
        })

    print(f"Base de datos cargada correctamente. {len(productos)} productos indexados.")

except FileNotFoundError:
    productos = []
    print(f"Advertencia: No se encontró {ARCHIVO_EXCEL}.")


class Consulta(BaseModel):
    texto: str


def buscar_producto_similar(entrada_limpia: str):
    tokens_entrada = entrada_limpia.split()
    tokens_clave = [t for t in tokens_entrada if t not in STOPWORDS] or tokens_entrada

    # 1. BÚSQUEDA EN CONTEXTO (ChromaDB)
    resultados_chroma = coleccion_productos.query(
        query_texts=[" ".join(tokens_clave)],
        n_results=min(10, len(productos)) if productos else 1
    )
    candidatos = resultados_chroma['metadatas'][0] if resultados_chroma['metadatas'] else []

    # Helper para evaluar un grupo de productos
    def evaluar_candidatos(lista_productos):
        mejor_prod = None
        max_puntaje = 0.0
        for prod in lista_productos:
            nombre_prod = prod['nombre_busqueda']
            tokens_prod = nombre_prod.split()

            # Coincidencia Exacta
            if re.search(r'\b' + re.escape(nombre_prod) + r'\b', entrada_limpia):
                return prod, 1.0

            # Evaluación de Similitud por tokens
            puntajes = [
                max([calcular_similitud(tp, tu) for tu in tokens_clave] or [0])
                for tp in tokens_prod
            ]
            puntaje_promedio = sum(puntajes) / len(puntajes)

            if puntaje_promedio > max_puntaje:
                max_puntaje = puntaje_promedio
                mejor_prod = prod
        return mejor_prod, max_puntaje

    # Evaluar primero los candidatos devueltos por el contexto de ChromaDB
    producto_encontrado, puntaje = evaluar_candidatos(candidatos)

    # 2. FALLBACK AL JSON PRINCIPAL:
    # Si el contexto de ChromaDB no superó el umbral de 0.85, evaluamos el catálogo completo (JSON)
    if puntaje < 0.85:
        producto_encontrado, puntaje = evaluar_candidatos(productos)

    # Validación final del umbral de coincidencia
    if puntaje >= 0.85 and producto_encontrado:
        contexto_relacionados = [
            p for p in productos 
            if p['categoria'] == producto_encontrado['categoria'] or any(t in p['nombre_busqueda'] for t in tokens_clave)
        ]
        return producto_encontrado, contexto_relacionados

    return None, []


@app.get("/")
async def chat_interface(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


def buscar_listado_productos(entrada_limpia: str):
    tokens_entrada = entrada_limpia.split()
    
    INTENCION_LISTAR = {'que', 'cuales', 'muestra', 'muestrame', 'ver', 'dame', 'listado', 'lista', 'hay', 'todos', 'tienen', 'catalogo'}
    INTENCION_STOCK_GENERAL = {'stock', 'inventario', 'disponibles', 'productos', 'existencias'}

    # 1. SI LA CONSULTA PIDE STOCK GENERAL O TODO EL CATALOGO
    if any(p in tokens_entrada for p in INTENCION_STOCK_GENERAL) and not any(t in entrada_limpia for t in ['monitor', 'teclado', 'laptop', 'mouse']):
        return [dict(p) for p in productos]

    # 2. VERIFICAR INTENCIÓN EXPLÍCITA DE LISTAR
    tiene_intencion = any(p in tokens_entrada for p in INTENCION_LISTAR)

    # Limpiamos stopwords e intenciones
    tokens_clave = [t for t in tokens_entrada if t not in INTENCION_LISTAR and t not in STOPWORDS]
    if not tokens_clave:
        tokens_clave = tokens_entrada

    # 3. BUSQUEDA ESPECÍFICA MULTI-TÉRMINO (Ej: "Mouse logic", "teklado logy")
    if not tiene_intencion and len(tokens_clave) > 1:
        coincidencias_especificas = []
        for prod in productos:
            nombre_prod = prod['nombre_busqueda']
            tokens_prod = nombre_prod.split()
            
            coincide_todo = True
            for token_u in tokens_clave:
                raiz_token = re.sub(r'(es|s)$', '', token_u)
                if len(raiz_token) < 3:
                    raiz_token = token_u

                # Comprueba si el token o su raíz coinciden por subcadena O por similitud >= 0.60
                match_token = any(
                    raiz_token in tp or 
                    tp in raiz_token or
                    token_u in tp or 
                    tp in token_u or
                    calcular_similitud(raiz_token, tp) >= 0.60 or 
                    calcular_similitud(token_u, tp) >= 0.60
                    for tp in tokens_prod
                )
                if not match_token:
                    coincide_todo = False
                    break

            if coincide_todo:
                coincidencias_especificas.append(prod)
        
        # Si se identificaron coincidencias específicas con la combinación (ej: Mouse + Logitech), retorna solo esas
        if coincidencias_especificas:
            return coincidencias_especificas

    # 4. BÚSQUEDA DE CATEGORÍA GENERAL O PLURALES (Ej: "mouses", "teclados")
    es_solicitud_listado = tiene_intencion or len(tokens_entrada) <= 2
    if not es_solicitud_listado:
        return None

    productos_encontrados = []

    for prod in productos:
        nombre_prod = prod['nombre_busqueda']
        categoria_prod = prod.get('categoria', '')

        for token_u in tokens_clave:
            raiz_token = re.sub(r'(es|s)$', '', token_u)
            if len(raiz_token) < 3:
                raiz_token = token_u

            if (raiz_token in nombre_prod or 
                raiz_token in categoria_prod or 
                token_u in nombre_prod or 
                token_u in categoria_prod):
                if prod not in productos_encontrados:
                    productos_encontrados.append(prod)
                continue

            for tp in nombre_prod.split():
                if calcular_similitud(raiz_token, tp) >= 0.70 or calcular_similitud(token_u, tp) >= 0.70:
                    if prod not in productos_encontrados:
                        productos_encontrados.append(prod)
                    break

    return productos_encontrados if productos_encontrados else None


@app.post("/chat")
def procesar_mensaje(consulta: Consulta):
    entrada_limpia = normalizar_texto(consulta.texto)
    
    # 1. EVALUAR SI ES UNA SOLICITUD DE LISTADO (Ej: "qué monitores hay", "teclados", "mouses")
    listado_encontrado = buscar_listado_productos(entrada_limpia)

    if listado_encontrado:
        cantidad_prods = len(listado_encontrado)
        respuesta = f"Encontré {cantidad_prods} producto(s) en nuestro catálogo que coinciden con tu búsqueda."

        return {
            "entrada_original": consulta.texto,
            "entrada_procesada": entrada_limpia,
            "respuesta": respuesta,
            "estado": "resuelto",
            "productos": listado_encontrado,  # Lista explícita para renderizar Cards en Frontend
            "contexto_guardado": listado_encontrado
        }

    # 2. BÚSQUEDA INDIVIDUAL (Fallback anterior)
    producto_encontrado, contexto_relacionados = buscar_producto_similar(entrada_limpia)

    if producto_encontrado:
        respuesta = f"Aquí tienes los detalles del producto que consultaste:"
        productos_a_mostrar = [producto_encontrado]
        estado = "resuelto"
    else:
        respuesta = "No he podido identificar el producto en tu consulta o no tenemos información al respecto. Te transfiero con un agente humano para que te ayude."
        productos_a_mostrar = []
        estado = "escalado"

    return {
        "entrada_original": consulta.texto,
        "entrada_procesada": entrada_limpia,
        "respuesta": respuesta,
        "estado": estado,
        "productos": productos_a_mostrar,  # Devuelve array con el producto individual o vacío
        "contexto_guardado": contexto_relacionados
    }
