# 🤖 Asistente Virtual de Ventas y Atención al Cliente

Sistema web interactivo basado en un chatbot inteligente capaz de consultar un catálogo de productos en tiempo real, interpretar intenciones de búsqueda avanzadas con tolerancia a errores ortográficos, y presentar información de inventario en una interfaz web moderna y responsiva con soporte para temas personalizables.

---

## 📸 Vista General de la Solución

La aplicación cuenta con una interfaz dividida en un panel dual en tiempo real:
* **Panel Izquierdo (Chatbot):** Interfaz conversacional con soporte de entrada por texto, reconocimiento de voz (vía Web Speech API) y opción para limpiar historial.
* **Panel Derecho (Catálogo & Resultados):** Vista en cuadrícula (*cards*) que despliega los productos consultados en tiempo real con capacidad de ordenamiento dinámico por precio (*Menor/Mayor*) y stock (*Mayor/Menor*).

---

## 🚀 Tecnologías Aplicadas

### **Backend**
* **Python 3.10+**: Lenguaje principal de desarrollo.
* **FastAPI**: Framework web asíncrono para la construcción de la API REST y renderizado de plantillas.
* **Pandas & OpenPyXL**: Para la ingesta, limpieza, normalización y tratamiento de nulos del catálogo en Excel (`productos.xlsx`).
* **Uvicorn**: Servidor ASGI de alto rendimiento para ejecutar la aplicación.
* **Difflib & Regex**: Algoritmos de similitud de cadenas, lematización, manejo de plurales y tolerancia a tipografía errónea sin dependencias de LLMs/IA externas.

### **Frontend**
* **HTML5**: Estructura semántica de la aplicación.
* **CSS3 (Variables CSS / Flexbox / Grid / Glassmorphism)**: Estilizado adaptativo con **Modo Claro** profesional y **Modo Oscuro** en tonos morados con acentos RGB/neón.
* **JavaScript ES6+ (Vanilla JS)**: Manejo del DOM, peticiones HTTP asíncronas (`fetch`), persistencia del tema en `localStorage` y ordenamiento de datos del lado del cliente.
* **Web Speech API**: Dictado por voz nativo desde el navegador.

---

## 💡 Planteamiento de la Solución

El motor de búsqueda fue desarrollado para resolver consultas en lenguaje natural de manera local y eficiente:

1. **Higienización Automática de Datos:**
   Al iniciar la aplicación, `Pandas` lee el archivo `productos.xlsx`, estandariza los nombres de columnas a minúsculas, elimina caracteres especiales/espacios y reemplaza valores nulos (`NaN`) para garantizar compatibilidad estricta con JSON y evitar errores HTTP 500.

2. **Procesamiento de Lenguaje Natural (NLP Local):**
   * **Intención Explícita vs. Búsqueda Específica:** El servidor identifica si la consulta requiere un listado global (ej. *"ver stock"*, *"inventario"*) o un producto puntual (ej. *"Mouse logic"*, *"teklado logy"*).
   * **Lematización y Plurales:** Algoritmo que procesa palabras clave reduciendo sufijos (*-s*, *-es*) para emparejar términos de búsqueda con los campos del catálogo.
   * **Tolerancia a Errores Tipográficos:** Evalúa la similitud fonética y de texto entre palabras mediante subcadenas y comparaciones con `difflib` (umbral `≥ 0.60`), permitiendo encontrar marcas o modelos con errores de ortografía.

3. **Experiencia de Usuario (UX/UI):**
   * **Filtros Client-Side:** Los productos devueltos se almacenan temporalmente en el cliente (`productosActuales`), permitiendo reordenar las tarjetas en pantalla sin volver a consultar al servidor.
   * **Tema Dinámico:** Botón flotante en la esquina inferior izquierda que conmuta entre temas claros y oscuros, guardando la preferencia del usuario.

---

## ⚙️ Requisitos Previos

* **Python 3.9** o superior.
* **pip** (gestor de paquetes de Python).
* Navegador web moderno (Google Chrome o MS Edge recomendados para la función de micrófono).

---

## 🛠️ Instalación y Puesta en Marcha

### 1. Clonar o Descargar el Proyecto
```bash
git clone <URL_DE_TU_REPOSITORIO>
cd customer_service