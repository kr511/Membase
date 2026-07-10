const lessons = [
  { title:"Python für KI", module:"MODUL 1 · FUNDAMENT", description:"Funktionen, Listen, Dictionaries und saubere Programme.", theory:"Python ist die Hauptsprache für moderne KI-Forschung. Wichtig sind saubere Funktionen, Datenstrukturen und das Lesen fremden Codes.", code:`def mittelwert(werte):\n    return sum(werte) / len(werte)\n\nverluste = [0.9, 0.7, 0.5]\nprint(mittelwert(verluste))`, tasks:["Schreibe eine Funktion für Maximum und Minimum.","Speichere Modellwerte in einem Dictionary.","Erkläre, was return macht."] },
  { title:"NumPy und Vektoren", module:"MODUL 1 · FUNDAMENT", description:"Rechnen mit Arrays statt langsamen Python-Schleifen.", theory:"Neuronale Netze bestehen im Kern aus vielen Vektor- und Matrixoperationen. NumPy führt diese Operationen effizient aus.", code:`import numpy as np\n\nx = np.array([1.0, 2.0, 3.0])\nw = np.array([0.2, 0.5, -0.1])\nprint(np.dot(x, w))`, tasks:["Erzeuge zwei Vektoren.","Berechne ihr Skalarprodukt.","Ändere einen Gewichtswert."] },
  { title:"Lineare Algebra", module:"MODUL 2 · MATHEMATIK", description:"Vektoren, Matrizen und Matrixmultiplikation.", theory:"Eine Matrix kann viele Eingaben gleichzeitig verarbeiten. Deshalb sind Matrizen zentral für neuronale Netze.", code:`import numpy as np\nX = np.array([[1, 2], [3, 4]])\nW = np.array([[0.5], [0.2]])\nprint(X @ W)`, tasks:["Bestimme die Dimensionen.","Erkläre die zwei Ergebniszeilen.","Ändere W."] },
  { title:"Ableitungen verstehen", module:"MODUL 2 · MATHEMATIK", description:"Wie ein Modell erkennt, in welche Richtung es lernen muss.", theory:"Die Ableitung beschreibt, wie stark sich eine Ausgabe verändert, wenn du eine Eingabe leicht änderst.", code:`def f(x):\n    return x ** 2\n\nx = 3.0\nh = 0.0001\nprint((f(x + h) - f(x)) / h)`, tasks:["Teste x = 2.","Vergleiche mit 2*x.","Erkläre h."] },
  { title:"Gradient Descent", module:"MODUL 3 · LERNEN", description:"Ein Gewicht Schritt für Schritt verbessern.", theory:"Gradient Descent verändert Parameter so, dass der Fehler sinkt. Die Lernrate bestimmt die Schrittgröße.", code:`gewicht = 0.0\nlernrate = 0.1\nfor _ in range(20):\n    gradient = 2 * (gewicht - 3)\n    gewicht -= lernrate * gradient\nprint(gewicht)`, tasks:["Teste Lernrate 0.01.","Teste Lernrate 1.0.","Beschreibe den Unterschied."] },
  { title:"Neuron von Grund auf", module:"MODUL 3 · LERNEN", description:"Gewichte, Bias und Aktivierung selbst programmieren.", theory:"Ein Neuron multipliziert Eingaben mit Gewichten, addiert einen Bias und nutzt eine Aktivierungsfunktion.", code:`import numpy as np\nx = np.array([2.0, 1.0])\nw = np.array([0.5, -0.3])\nbias = 0.1\nz = np.dot(x, w) + bias\nprint(max(0, z))`, tasks:["Ändere den Bias.","Entferne ReLU.","Erkläre den Unterschied."] },
  { title:"Mini-Neuronales Netz", module:"MODUL 4 · DEEP LEARNING", description:"Mehrere Neuronen zu Schichten verbinden.", theory:"Eine Schicht enthält mehrere Neuronen. Mehrere Schichten lernen komplexere Muster.", code:`import numpy as np\nx = np.array([1.0, 2.0])\nW = np.array([[0.2, 0.8], [-0.5, 0.3]])\nb = np.array([0.1, -0.2])\nprint(np.maximum(0, x @ W + b))`, tasks:["Füge ein drittes Neuron hinzu.","Prüfe die Dimensionen.","Erkläre ReLU."] },
  { title:"PyTorch-Grundlagen", module:"MODUL 4 · DEEP LEARNING", description:"Tensoren, Autograd und Modelle.", theory:"PyTorch berechnet Ableitungen automatisch. Dadurch musst du Gradienten komplexer Modelle nicht von Hand berechnen.", code:`import torch\nx = torch.tensor(3.0, requires_grad=True)\ny = x ** 2\ny.backward()\nprint(x.grad)`, tasks:["Teste x = 5.","Erkläre requires_grad.","Erkläre backward()."] },
  { title:"Training eines Modells", module:"MODUL 5 · PRAXIS", description:"Vorhersage, Fehler und Optimierung verbinden.", theory:"Ein Trainingsloop besteht aus Vorhersage, Fehlerberechnung, Gradientenberechnung und Parameterupdate.", code:`for epoch in range(100):\n    prediction = model(x)\n    loss = loss_fn(prediction, y)\n    optimizer.zero_grad()\n    loss.backward()\n    optimizer.step()`, tasks:["Erkläre jede Zeile.","Warum zero_grad?","Was ist eine Epoche?"] },
  { title:"Tokenisierung", module:"MODUL 6 · SPRACHMODELLE", description:"Text in Zahlen umwandeln.", theory:"Sprachmodelle sehen keine Wörter. Tokenizer zerlegen Text und weisen den Teilen Zahlen zu.", code:`text = "KI lernt"\nvokabular = {"KI": 0, "lernt": 1}\ntokens = [vokabular[w] for w in text.split()]\nprint(tokens)`, tasks:["Erweitere das Vokabular.","Behandle unbekannte Wörter.","Erkläre Tokens."] },
  { title:"Attention verstehen", module:"MODUL 6 · SPRACHMODELLE", description:"Wie Wörter auf andere Wörter achten.", theory:"Attention berechnet, welche Teile einer Eingabe für einen Token besonders wichtig sind.", code:`import numpy as np\nscores = np.array([1.2, 0.3, 2.0])\nweights = np.exp(scores) / np.exp(scores).sum()\nprint(weights)`, tasks:["Prüfe die Summe.","Erhöhe einen Score.","Beschreibe die Änderung."] },
  { title:"Mini-GPT-Projekt", module:"MODUL 7 · FORSCHUNG", description:"Ein kleines Sprachmodell trainieren und untersuchen.", theory:"Verbinde Tokenisierung, Embeddings, Attention, Training und Evaluation. Ziel ist Verständnis, nicht Größe.", code:`# 1. Text laden\n# 2. Tokenisieren\n# 3. Modell definieren\n# 4. Trainieren\n# 5. Text generieren\n# 6. Ergebnisse dokumentieren`, tasks:["Wähle einen kleinen Datensatz.","Formuliere eine Forschungsfrage.","Dokumentiere Fehler und Erkenntnisse."] }
];

const state = { completed: JSON.parse(localStorage.getItem("aiPathCompleted") || "[]") };
let currentLessonIndex = 0;
const lessonList = document.getElementById("lessonList");
const lessonDialog = document.getElementById("lessonDialog");
const statsDialog = document.getElementById("statsDialog");

function saveState(){ localStorage.setItem("aiPathCompleted", JSON.stringify(state.completed)); }
function getNextLessonIndex(){ const next = lessons.findIndex((_,i)=>!state.completed.includes(i)); return next === -1 ? lessons.length - 1 : next; }
function escapeHtml(text){ return text.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;"); }

function updateProgress(){
  const done = state.completed.length;
  const percent = Math.round(done / lessons.length * 100);
  const next = lessons[getNextLessonIndex()];
  document.getElementById("progressText").textContent = `${done} von ${lessons.length} Lektionen`;
  document.getElementById("progressPercent").textContent = `${percent}%`;
  document.getElementById("progressRing").style.setProperty("--progress", `${percent * 3.6}deg`);
  document.getElementById("todayTitle").textContent = done === lessons.length ? "Pfad abgeschlossen" : next.title;
  document.getElementById("todayDescription").textContent = done === lessons.length ? "Jetzt beginnt die Projektphase." : next.description;
  document.getElementById("statDone").textContent = done;
  document.getElementById("statOpen").textContent = lessons.length - done;
  document.getElementById("statPercent").textContent = `${percent}%`;
  document.getElementById("nextFocus").textContent = done === lessons.length ? "Baue ein eigenes Mini-Sprachmodell." : `${next.title}: ${next.description}`;
}

function renderLessons(){
  lessonList.innerHTML = "";
  lessons.forEach((lesson,index)=>{
    const done = state.completed.includes(index);
    const card = document.createElement("button");
    card.className = `lesson-card ${done ? "done" : ""}`;
    card.innerHTML = `<div class="lesson-number">${done ? "✓" : index + 1}</div><div><h3>${lesson.title}</h3><p class="muted">${lesson.description}</p></div><div class="lesson-status">›</div>`;
    card.addEventListener("click",()=>openLesson(index));
    lessonList.appendChild(card);
  });
}

function openLesson(index){
  currentLessonIndex = index;
  const lesson = lessons[index];
  document.getElementById("dialogModule").textContent = lesson.module;
  document.getElementById("dialogTitle").textContent = lesson.title;
  document.getElementById("dialogContent").innerHTML = `<p>${lesson.theory}</p><h3>Beispiel</h3><pre><code>${escapeHtml(lesson.code)}</code></pre><h3>Aufgaben</h3><ol class="checklist">${lesson.tasks.map(t=>`<li>${t}</li>`).join("")}</ol>`;
  document.getElementById("completeBtn").textContent = state.completed.includes(index) ? "Als offen markieren" : "Als erledigt markieren";
  lessonDialog.showModal();
}

document.getElementById("completeBtn").addEventListener("click",()=>{
  const i = currentLessonIndex;
  state.completed = state.completed.includes(i) ? state.completed.filter(x=>x!==i) : [...state.completed,i].sort((a,b)=>a-b);
  saveState(); renderLessons(); updateProgress(); lessonDialog.close();
});
document.getElementById("continueBtn").addEventListener("click",()=>openLesson(getNextLessonIndex()));
document.getElementById("closeDialog").addEventListener("click",()=>lessonDialog.close());
document.getElementById("closeStats").addEventListener("click",()=>statsDialog.close());
document.getElementById("resetBtn").addEventListener("click",()=>{ if(confirm("Fortschritt wirklich zurücksetzen?")){ state.completed=[]; saveState(); renderLessons(); updateProgress(); } });
document.querySelectorAll(".nav-item").forEach(item=>item.addEventListener("click",()=>{
  document.querySelectorAll(".nav-item").forEach(btn=>btn.classList.remove("active")); item.classList.add("active");
  if(item.dataset.view==="stats") statsDialog.showModal();
  if(item.dataset.view==="path") document.querySelector(".section-heading").scrollIntoView({behavior:"smooth"});
  if(item.dataset.view==="home") window.scrollTo({top:0,behavior:"smooth"});
}));

renderLessons();
updateProgress();
if("serviceWorker" in navigator) navigator.serviceWorker.register("service-worker.js");
