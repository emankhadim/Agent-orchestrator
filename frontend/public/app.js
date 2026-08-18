const stepsEl = document.getElementById("steps");
const answerEl = document.getElementById("answer");
const historyEl = document.getElementById("run-history");
const statusEl = document.getElementById("backend-status");
const input = document.getElementById("query-input");
const runBtn = document.getElementById("run-btn");

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.backend && data.backend.status === "ok") {
      statusEl.textContent = `backend ok (${data.backend.llm_mode})`;
      statusEl.className = "badge ok";
    } else {
      statusEl.textContent = "backend unreachable";
      statusEl.className = "badge fail";
    }
  } catch {
    statusEl.textContent = "backend unreachable";
    statusEl.className = "badge fail";
  }
}

function renderSteps(steps) {
  stepsEl.innerHTML = "";
  for (const step of steps) {
    const div = document.createElement("div");
    div.className = "step";
    let html = `<div class="transition">${step.from_state} → ${step.to_state}</div>`;
    html += `<div class="reasoning">${step.reasoning}</div>`;
    if (step.tool_call) {
      html += `<div class="tool">tool: ${step.tool_call.tool}(${JSON.stringify(step.tool_call.arguments)})`;
      if (step.tool_result) {
        html += ` → ${step.tool_result.output}`;
      }
      html += `</div>`;
    }
    div.innerHTML = html;
    stepsEl.appendChild(div);
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/api/runs");
    const runs = await res.json();
    historyEl.innerHTML = "";
    for (const run of runs) {
      const li = document.createElement("li");
      li.innerHTML = `<span>${run.query}</span><span>${run.status}</span>`;
      historyEl.appendChild(li);
    }
  } catch {
    // non-fatal for the demo
  }
}

async function runQuery() {
  const query = input.value.trim();
  if (!query) return;
  runBtn.disabled = true;
  runBtn.textContent = "Running…";
  answerEl.textContent = "…";
  stepsEl.innerHTML = "";
  try {
    const res = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    renderSteps(data.steps || []);
    answerEl.textContent = data.answer || "(no answer produced)";
    await loadHistory();
  } catch (err) {
    answerEl.textContent = `Error: ${err}`;
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run";
  }
}

runBtn.addEventListener("click", runQuery);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runQuery();
});

checkHealth();
loadHistory();
