const milestoneDefs = [
    { key: "health", name: "Health Emergency", amount: 300000, years: 2 },
    { key: "marriage", name: "Marriage", amount: 1200000, years: 5 },
    { key: "car", name: "Car", amount: 800000, years: 4 },
    { key: "home", name: "Home", amount: 2500000, years: 8 },
    { key: "education", name: "Education", amount: 1500000, years: 12 },
  ];
  
  let currentRecord = null;
  let adminToken = null;
  let chart = null;
  
  function showPage(id) {
    ["entry", "financial", "summary", "admin-login", "admin"].forEach((p) => {
      document.getElementById(p).classList.add("hidden");
    });
    document.getElementById(id).classList.remove("hidden");
  }
  
  function renderMilestones() {
    const box = document.getElementById("milestonesBox");
    box.innerHTML = milestoneDefs
      .map(
        (m) => `
        <div class="border rounded p-3 bg-white">
          <label class="font-medium text-sm"><input id="use-${m.key}" type="checkbox" checked /> ${m.name}</label>
          <div class="grid grid-cols-2 gap-2 mt-2">
            <input id="amt-${m.key}" type="number" class="input" value="${m.amount}" />
            <input id="yr-${m.key}" type="number" class="input" value="${m.years}" />
          </div>
        </div>`
      )
      .join("");
  }
  
  function payloadFromForm() {
    const milestones = milestoneDefs
      .filter((m) => document.getElementById(`use-${m.key}`).checked)
      .map((m) => ({
        key: m.key,
        name: m.name,
        amount: Number(document.getElementById(`amt-${m.key}`).value || 0),
        years: Number(document.getElementById(`yr-${m.key}`).value || 1),
      }));
  
    return {
      name: document.getElementById("name").value,
      age: Number(document.getElementById("age").value || 0),
      mobile: document.getElementById("mobile").value,
      dependents: Number(document.getElementById("dependents").value || 0),
      maritalStatus: document.getElementById("maritalStatus").value,
      hasHealthInsurance: document.getElementById("hasHealthInsurance").checked,
      hasTermInsurance: document.getElementById("hasTermInsurance").checked,
      inputMode: document.getElementById("inputMode").value,
      income: Number(document.getElementById("income").value || 0),
      rent: Number(document.getElementById("rent").value || 0),
      food: Number(document.getElementById("food").value || 0),
      misc: Number(document.getElementById("misc").value || 0),
      milestones,
      consult: document.getElementById("consult")?.checked || false,
    };
  }
  
  async function generatePlan() {
    const resp = await fetch("/api/plan/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payloadFromForm()),
    });
    const data = await resp.json();
    if (!data.ok) return alert(data.error || "Failed");
  
    currentRecord = data.record;
    document.getElementById("healthScore").textContent = currentRecord.summary.health_score;
    document.getElementById("healthNote").textContent = currentRecord.summary.health_note;
    document.getElementById("insights").innerHTML = currentRecord.summary.notes.map((n) => `<li>${n}</li>`).join("");
  
    renderChart(currentRecord.summary.allocation);
    showPage("summary");
  }
  
  function renderChart(allocation) {
    const ctx = document.getElementById("chart").getContext("2d");
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Insurance", "Short", "Long"],
        datasets: [{ data: [allocation.insurance, allocation.short_term, allocation.long_term] }],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });
  }
  
  async function savePlan() {
    if (!currentRecord) return;
    currentRecord.consult = document.getElementById("consult").checked;
    const resp = await fetch("/api/plan/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentRecord),
    });
    const data = await resp.json();
    alert(data.ok ? "Saved" : "Save failed");
  }
  
  async function adminLogin() {
    const resp = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("adminUser").value,
        password: document.getElementById("adminPass").value,
      }),
    });
    const data = await resp.json();
    if (!data.ok) return alert(data.error || "Invalid");
    adminToken = data.token;
    loadAdmin();
  }
  
  async function loadAdmin() {
    const resp = await fetch("/api/admin/plans", {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    const data = await resp.json();
    if (!data.ok) return alert(data.error || "Failed");
  
    const body = document.getElementById("adminBody");
    body.innerHTML = data.records
      .map(
        (r) => `<tr><td>${r.profile.name}</td><td>${r.profile.age}</td><td>${r.profile.mobile}</td><td>${r.summary.health_score}</td><td>${new Date(r.created_at).toLocaleDateString()}</td></tr>`
      )
      .join("");
    showPage("admin");
  }
  
  renderMilestones();
  