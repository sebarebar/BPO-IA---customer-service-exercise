const chatBox = document.getElementById("chatBox");
const userInput = document.getElementById("userInput");
const cardsGrid = document.getElementById("cardsGrid");

let productosActuales = []; // Copia global de los productos obtenidos

document.addEventListener("DOMContentLoaded", () => {
    const historial = JSON.parse(localStorage.getItem("chat_historial")) || [];
    historial.forEach(item => agregarMensajeDOM(item.texto, item.sender));
});

function agregarMensajeDOM(texto, sender) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");
    msgDiv.textContent = texto;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function guardarEnLocalStorage(texto, sender) {
    const historial = JSON.parse(localStorage.getItem("chat_historial")) || [];
    historial.push({ texto, sender });
    localStorage.setItem("chat_historial", JSON.stringify(historial));
}

function renderizarCards(productos) {
    cardsGrid.innerHTML = "";
    if (!productos || productos.length === 0) {
        cardsGrid.innerHTML = `<p style="color: #a0aec0; grid-column: 1/-1;">No se encontraron productos para mostrar.</p>`;
        document.getElementById("productsHeaderTitle").textContent = "Resultados de Búsqueda";
        return;
    }

    document.getElementById("productsHeaderTitle").textContent = `Productos Encontrados (${productos.length})`;

    productos.forEach(p => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
                <div>
                    <div class="card-title">${p.nombre}</div>
                    <div class="card-price">$${p.precio}</div>
                    <div class="card-stock">✓ ${p.cantidad} unidades disponibles</div>
                </div>
                <div class="card-desc">${p.desc}</div>
            `;
        cardsGrid.appendChild(card);
    });
}

function aplicarOrdenamiento() {
    if (!productosActuales || productosActuales.length === 0) return;

    const criterio = document.getElementById("sortSelect").value;
    let listaOrdenada = [...productosActuales];

    if (criterio === "precio-asc") {
        listaOrdenada.sort((a, b) => a.precio - b.precio);
    } else if (criterio === "precio-desc") {
        listaOrdenada.sort((a, b) => b.precio - a.precio);
    } else if (criterio === "stock-desc") {
        listaOrdenada.sort((a, b) => b.cantidad - a.cantidad);
    } else if (criterio === "stock-asc") {
        listaOrdenada.sort((a, b) => a.cantidad - b.cantidad);
    }

    renderizarCards(listaOrdenada);
}

async function enviarMensaje() {
    const texto = userInput.value.trim();
    if (!texto) return;

    agregarMensajeDOM(texto, "user");
    guardarEnLocalStorage(texto, "user");
    userInput.value = "";

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ texto: texto })
        });
        const data = await res.json();

        agregarMensajeDOM(data.respuesta, "bot");
        guardarEnLocalStorage(data.respuesta, "bot");

        if (data.productos) {
            productosActuales = data.productos;
            document.getElementById("sortSelect").value = "default";
            renderizarCards(productosActuales);
        }
    } catch (err) {
        agregarMensajeDOM("Error de conexión con el servidor.", "bot");
    }
}

function limpiarHistorial() {
    localStorage.removeItem("chat_historial");
    if (chatBox) chatBox.innerHTML = "";
    if (cardsGrid) cardsGrid.innerHTML = `<p style="color: #a0aec0; grid-column: 1/-1;">Escribe en el chat o realiza una búsqueda para ver los productos aquí.</p>`;

    const headerTitle = document.getElementById("productsHeaderTitle");
    if (headerTitle) headerTitle.textContent = "Resultados de Búsqueda";

    const sortSelect = document.getElementById("sortSelect");
    if (sortSelect) sortSelect.value = "default";

    productosActuales = [];
}

// --- RECONOCIMIENTO DE VOZ ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let escuchando = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.continuous = false;

    recognition.onstart = () => {
        escuchando = true;
        const micBtn = document.getElementById("micBtn");
        micBtn.classList.add("escuchando");
        micBtn.textContent = "🎙️...";
    };

    recognition.onresult = (event) => {
        userInput.value = event.results[0][0].transcript;
        enviarMensaje();
    };

    recognition.onerror = () => detenerMicrofono();
    recognition.onend = () => detenerMicrofono();
} else {
    const micBtn = document.getElementById("micBtn");
    if (micBtn) micBtn.style.display = "none";
}

function toggleReconocimientoVoz() {
    if (!recognition) return;
    escuchando ? recognition.stop() : recognition.start();
}

function detenerMicrofono() {
    escuchando = false;
    const micBtn = document.getElementById("micBtn");
    if (micBtn) {
        micBtn.classList.remove("escuchando");
        micBtn.textContent = "🎤";
    }
}


function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    document.getElementById("themeToggleBtn").textContent = newTheme === "dark" ? "☀️" : "🌙";
}

// Cargar tema guardado al iniciar
document.addEventListener("DOMContentLoaded", () => {
    const savedTheme = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    const btn = document.getElementById("themeToggleBtn");
    if (btn) btn.textContent = savedTheme === "dark" ? "☀️" : "🌙";
});