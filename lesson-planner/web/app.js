const FIELDS = [
  { key: "escola", label: "Escola", placeholder: "Nome da escola", single: true },
  { key: "professor", label: "Professor(a)", placeholder: "Nome do(a) professor(a)", single: true },
  { key: "componenteCurricular", label: "Componente Curricular", placeholder: "Ex.: Língua Portuguesa, Matemática, Ciências", single: true },
  { key: "anoSerie", label: "Ano/Série", placeholder: "Ex.: 5º ano do Ensino Fundamental", single: true },
  { key: "turma", label: "Turma", placeholder: "Ex.: 5A", single: true },
  { key: "data", label: "Data", placeholder: "Ex.: 15/08/2025", single: true, type: "date" },
  { key: "duracao", label: "Duração", placeholder: "Ex.: 2 aulas de 50 minutos", single: true },
  { key: "tema", label: "Tema da aula", placeholder: "Ex.: Interpretação de textos narrativos", single: true },
  { key: "objetivos", label: "Objetivos de aprendizagem", placeholder: "O que os alunos devem aprender ao final da aula" },
  { key: "conteudos", label: "Conteúdos", placeholder: "Conteúdos conceituais, procedimentais e atitudinais" },
  { key: "habilidadesBncc", label: "Habilidades BNCC", placeholder: "Clique em \"Gerar BNCC\" para sugerir automaticamente" },
  { key: "competenciasGerais", label: "Competências gerais da BNCC", placeholder: "Competências gerais trabalhadas" },
  { key: "metodologia", label: "Metodologia / Desenvolvimento", placeholder: "Descreva o passo a passo da aula" },
  { key: "recursos", label: "Recursos didáticos", placeholder: "Livro didático, quadro, datashow, materiais manipuláveis…" },
  { key: "avaliacao", label: "Avaliação", placeholder: "Como a aprendizagem será avaliada" },
  { key: "referencias", label: "Referências", placeholder: "Livros, artigos e sites consultados" },
];

const STORAGE_KEY = "planoAula.v1";
const SETTINGS_KEY = "planoAula.settings.v1";

const $ = (sel) => document.querySelector(sel);
const form = $("#form");

function loadPlan() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function savePlan(plan) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(plan));
}

function loadSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY)) || { apiKey: "", model: "gpt-4o-mini" };
  } catch {
    return { apiKey: "", model: "gpt-4o-mini" };
  }
}

function saveSettings(s) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

function renderForm() {
  const plan = loadPlan();
  form.innerHTML = "";
  for (const f of FIELDS) {
    const wrap = document.createElement("div");
    const label = document.createElement("label");
    label.className = "block text-sm font-medium text-slate-700 mb-1";
    label.textContent = f.label;
    label.setAttribute("for", `field-${f.key}`);
    wrap.appendChild(label);

    const el = f.single
      ? document.createElement("input")
      : document.createElement("textarea");
    el.id = `field-${f.key}`;
    el.name = f.key;
    el.placeholder = f.placeholder;
    el.value = plan[f.key] || "";
    el.spellcheck = true;
    el.lang = "pt-BR";
    el.className =
      "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1E6091] bg-white";
    if (!f.single) {
      el.rows = 4;
      el.className += " resize-y";
    }
    if (f.type) el.type = f.type;
    el.addEventListener("input", () => {
      const p = loadPlan();
      p[f.key] = el.value;
      savePlan(p);
    });
    wrap.appendChild(el);
    form.appendChild(wrap);
  }
}

function toast(msg, durationMs = 3000) {
  const el = $("#toast");
  el.textContent = msg;
  el.style.opacity = "1";
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.style.opacity = "0"), durationMs);
}

// Settings modal
const modal = $("#settingsModal");
const inputApiKey = $("#inputApiKey");
const inputModel = $("#inputModel");

$("#btnSettings").addEventListener("click", () => {
  const s = loadSettings();
  inputApiKey.value = s.apiKey || "";
  inputModel.value = s.model || "gpt-4o-mini";
  modal.classList.remove("hidden");
  modal.classList.add("flex");
});

$("#btnCancel").addEventListener("click", closeModal);
modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});
function closeModal() {
  modal.classList.add("hidden");
  modal.classList.remove("flex");
}

$("#btnSave").addEventListener("click", () => {
  saveSettings({ apiKey: inputApiKey.value.trim(), model: inputModel.value });
  toast("Ajustes salvos.");
  closeModal();
});

// Limpar formulário
$("#btnLimpar").addEventListener("click", () => {
  if (!confirm("Tem certeza que deseja limpar todos os campos?")) return;
  localStorage.removeItem(STORAGE_KEY);
  renderForm();
  toast("Formulário limpo.");
});

// BNCC via OpenAI
$("#btnBncc").addEventListener("click", async () => {
  const s = loadSettings();
  if (!s.apiKey) {
    toast("Configure a chave da OpenAI em Ajustes.");
    return;
  }
  const plan = loadPlan();

  const btn = $("#btnBncc");
  const label = $("#btnBnccLabel");
  btn.disabled = true;
  label.textContent = "Gerando...";

  try {
    const resposta = await gerarBncc(s.apiKey, s.model || "gpt-4o-mini", plan);
    aplicarBncc(plan, resposta);
    savePlan(plan);
    renderForm();
    toast("Habilidades BNCC sugeridas.");
  } catch (e) {
    console.error(e);
    toast("Erro: " + (e.message || "falha ao gerar BNCC"), 5000);
  } finally {
    btn.disabled = false;
    label.textContent = "Gerar BNCC";
  }
});

async function gerarBncc(apiKey, model, plan) {
  const system = `Você é um especialista em BNCC (Base Nacional Comum Curricular) do Brasil.
Analise um planejamento de aula e sugira:
1) Habilidades BNCC aplicáveis (códigos oficiais como EF05LP01, EF67EF03, EM13CHS101, EI03TS01, etc.) com a descrição oficial resumida.
2) Competências gerais da BNCC (1 a 10) pertinentes.
Todos os textos devem estar em português do Brasil com ortografia correta.
Retorne SEMPRE um JSON válido com o formato:
{"habilidades":[{"codigo":"EF05LP01","descricao":"..."}],"competencias":[{"numero":4,"descricao":"..."}],"observacoes":"texto curto opcional"}`;

  const userPrompt = [
    "Analise o planejamento de aula abaixo e sugira habilidades e competências da BNCC.",
    "",
    `Componente curricular: ${plan.componenteCurricular || "(não informado)"}`,
    `Ano/Série: ${plan.anoSerie || "(não informado)"}`,
    `Tema da aula: ${plan.tema || "(não informado)"}`,
    plan.objetivos ? `Objetivos: ${plan.objetivos}` : null,
    plan.conteudos ? `Conteúdos: ${plan.conteudos}` : null,
    plan.metodologia ? `Metodologia: ${plan.metodologia}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: system },
        { role: "user", content: userPrompt },
      ],
    }),
  });

  if (!response.ok) {
    const txt = await response.text();
    throw new Error(`OpenAI HTTP ${response.status}: ${txt}`);
  }
  const data = await response.json();
  const content = data.choices?.[0]?.message?.content || "{}";
  return JSON.parse(content);
}

function aplicarBncc(plan, resposta) {
  const habilidades = (resposta.habilidades || [])
    .map((h) => (h.descricao ? `${h.codigo} — ${h.descricao}` : h.codigo))
    .join("\n");
  const competencias = (resposta.competencias || [])
    .map((c) => `Competência Geral ${c.numero}: ${c.descricao}`)
    .join("\n");
  const obs = resposta.observacoes ? `\nObservações: ${resposta.observacoes}` : "";
  if (habilidades) plan.habilidadesBncc = habilidades + obs;
  if (competencias) plan.competenciasGerais = competencias;
}

// PDF export
$("#btnPdf").addEventListener("click", () => {
  const plan = loadPlan();
  exportarPdf(plan);
});

function exportarPdf(plan) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 40;
  const maxWidth = pageWidth - margin * 2;
  let y = margin + 10;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("Planejamento de Aula", margin, y);
  y += 26;

  for (const f of FIELDS) {
    const value = (plan[f.key] || "").trim();
    if (!value) continue;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    const labelHeight = 16;
    if (y + labelHeight > pageHeight - margin) {
      doc.addPage();
      y = margin + 10;
    }
    doc.text(f.label, margin, y);
    y += labelHeight;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    const lines = doc.splitTextToSize(value, maxWidth);
    for (const line of lines) {
      if (y + 14 > pageHeight - margin) {
        doc.addPage();
        y = margin + 10;
      }
      doc.text(line, margin, y);
      y += 14;
    }
    y += 8;
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  doc.save(`planejamento_${stamp}.pdf`);
  toast("PDF gerado.");
}

renderForm();
