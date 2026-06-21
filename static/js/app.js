const milestoneDefs = [
  { key: "emergency", icon: "✦", name: "Extra safety cushion", amount: 300000, years: 2 },
  { key: "vehicle", icon: "↗", name: "Car / vehicle", amount: 800000, years: 4 },
  { key: "marriage", icon: "♡", name: "Wedding", amount: 1200000, years: 5 },
  { key: "home", icon: "⌂", name: "Home down payment", amount: 2500000, years: 8 },
  { key: "education", icon: "◇", name: "Education", amount: 1500000, years: 12 },
  { key: "travel", icon: "◌", name: "Dream experience", amount: 500000, years: 3 },
];

const form = document.getElementById("plannerForm");
const formatMoney = (value) => {
  const number = Number(value || 0);
  if (number >= 10000000) return `₹${(number / 10000000).toFixed(2).replace(/\.00$/, "")} Cr`;
  if (number >= 100000) return `₹${(number / 100000).toFixed(1).replace(/\.0$/, "")} L`;
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(number);
};

function renderMilestones() {
  document.getElementById("milestonesBox").innerHTML = milestoneDefs.map((goal, index) => `
    <label class="milestone-card ${index < 3 ? "selected" : ""}">
      <div class="milestone-top">
        <input id="use-${goal.key}" type="checkbox" ${index < 3 ? "checked" : ""} />
        <span class="goal-icon">${goal.icon}</span>
        <b>${goal.name}</b>
      </div>
      <div class="goal-fields">
        <span>Today’s cost<div class="money-input compact"><span>₹</span><input id="amt-${goal.key}" type="number" min="1" value="${goal.amount}" /></div></span>
        <span>Years<input id="yr-${goal.key}" type="number" min="1" max="50" value="${goal.years}" /></span>
      </div>
    </label>
  `).join("");
  document.querySelectorAll(".milestone-card input[type=checkbox]").forEach((box) => {
    box.addEventListener("change", () => box.closest(".milestone-card").classList.toggle("selected", box.checked));
  });
}

function showStep(step) {
  document.querySelectorAll(".form-step").forEach((section) => section.classList.toggle("hidden", Number(section.dataset.step) !== step));
  document.querySelectorAll(".step-indicator span").forEach((dot, index) => dot.classList.toggle("active", index + 1 <= step));
  document.querySelectorAll(".step-indicator i").forEach((line, index) => line.classList.toggle("active", index + 1 < step));
  document.getElementById("planner").scrollIntoView({ behavior: "smooth", block: "start" });
}

function validateStep(step) {
  const section = document.querySelector(`[data-step="${step}"]`);
  const fields = [...section.querySelectorAll("input[required], select[required]")];
  const invalid = fields.find((field) => !field.checkValidity());
  if (invalid) {
    invalid.reportValidity();
    invalid.focus();
    return false;
  }
  if (step === 1 && Number(document.getElementById("retirementAge").value) <= Number(document.getElementById("age").value)) {
    document.getElementById("retirementAge").setCustomValidity("Retirement age must be after your current age.");
    document.getElementById("retirementAge").reportValidity();
    document.getElementById("retirementAge").setCustomValidity("");
    return false;
  }
  return true;
}

document.querySelectorAll(".next-btn").forEach((button) => button.addEventListener("click", () => {
  const step = Number(button.closest(".form-step").dataset.step);
  if (validateStep(step)) showStep(step + 1);
}));
document.querySelectorAll(".back-btn").forEach((button) => button.addEventListener("click", () => {
  showStep(Number(button.closest(".form-step").dataset.step) - 1);
}));
document.querySelectorAll(".mode-toggle button").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".mode-toggle button").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  document.getElementById("inputMode").value = button.dataset.mode;
}));

function payloadFromForm() {
  const value = (id) => Number(document.getElementById(id).value || 0);
  return {
    name: document.getElementById("name").value,
    age: value("age"),
    retirementAge: value("retirementAge"),
    location: document.getElementById("location").value,
    dependents: value("dependents"),
    maritalStatus: document.getElementById("maritalStatus").value,
    hasHealthInsurance: document.getElementById("hasHealthInsurance").checked,
    hasTermInsurance: document.getElementById("hasTermInsurance").checked,
    inputMode: document.getElementById("inputMode").value,
    income: value("income"), rent: value("rent"), food: value("food"), misc: value("misc"), debtEmi: value("debtEmi"),
    currentSavings: value("currentSavings"), currentInvestments: value("currentInvestments"),
    riskProfile: document.getElementById("riskProfile").value,
    milestones: milestoneDefs.filter((goal) => document.getElementById(`use-${goal.key}`).checked).map((goal) => ({
      key: goal.key, name: goal.name, amount: value(`amt-${goal.key}`), years: value(`yr-${goal.key}`),
    })),
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateStep(3)) return;
  const button = form.querySelector(".generate-btn");
  const error = document.getElementById("formError");
  button.disabled = true;
  button.textContent = "Building your view…";
  error.textContent = "";
  try {
    const response = await fetch("/api/plan/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payloadFromForm()) });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "We couldn’t build the plan.");
    renderResults(data.record);
  } catch (problem) {
    error.textContent = problem.message;
  } finally {
    button.disabled = false;
    button.innerHTML = "Build my money view <span>↗</span>";
  }
});

function renderResults(record) {
  const summary = record.summary;
  document.getElementById("resultTitle").textContent = `${record.profile.name === "Your" ? "Here’s" : `${record.profile.name}, here’s`} your path forward.`;
  document.getElementById("healthScore").textContent = summary.health_score;
  document.getElementById("healthNote").textContent = summary.health_note;
  document.getElementById("surplus").textContent = formatMoney(summary.surplus);
  document.getElementById("savingsRatio").textContent = `${summary.savings_ratio}% savings rate`;
  document.getElementById("emergencyTarget").textContent = formatMoney(summary.emergency_target);
  document.getElementById("emergencyGap").textContent = summary.emergency_gap ? `${formatMoney(summary.emergency_gap)} remaining` : "Funded — keep it liquid";
  document.getElementById("insuranceTarget").textContent = formatMoney(summary.insurance_target);
  document.getElementById("debtRatio").textContent = `${summary.debt_ratio}%`;

  const allocation = [
    ["Safety reserve", summary.allocation.emergency, "mint"],
    ["Protection", summary.allocation.protection, "rose"],
    ["Life milestones", summary.allocation.milestones, "blue"],
    ["Long-term wealth", summary.allocation.retirement, "gold"],
  ];
  const max = Math.max(...allocation.map((item) => item[1]), 1);
  document.getElementById("allocationBars").innerHTML = allocation.map(([label, amount, color]) => `
    <div class="allocation-row"><div><span>${label}</span><b>${formatMoney(amount)}<small>/month</small></b></div><i><em class="${color}" style="width:${Math.max(amount / max * 100, amount ? 3 : 0)}%"></em></i></div>
  `).join("");
  document.getElementById("nextSteps").innerHTML = summary.next_steps.map((step) => `<li>${step}</li>`).join("");
  document.getElementById("goalResults").innerHTML = summary.goals.length ? summary.goals.map((goal) => `
    <div class="goal-result">
      <div class="goal-result-name"><b>${goal.name}</b><span>${goal.years} years · future cost ${formatMoney(goal.future_cost)}</span></div>
      <div class="funding"><i><em style="width:${goal.funding_ratio}%"></em></i><span>${goal.funding_ratio}% funded</span></div>
      <div class="goal-number"><b>${formatMoney(goal.monthly_required)}</b><span>needed monthly</span></div>
      <div class="status ${goal.status.toLowerCase().replaceAll(" ", "-")}">${goal.status}</div>
      <p>${goal.recommendation}</p>
    </div>
  `).join("") : `<div class="empty-state">No milestones selected. Your available investing amount is directed to long-term wealth.</div>`;
  document.getElementById("projections").innerHTML = summary.projections.map((projection) => `
    <div><span>In ${projection.years} years</span><strong>${formatMoney(projection.projected_value)}</strong><small>on ${formatMoney(projection.invested)} contributed</small></div>
  `).join("");
  document.getElementById("assumptions").innerHTML = summary.assumptions.map((note) => `<li>${note}</li>`).join("");
  document.getElementById("planner").classList.add("hidden");
  document.getElementById("results").classList.remove("hidden");
  document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

document.getElementById("editPlan").addEventListener("click", () => {
  document.getElementById("results").classList.add("hidden");
  document.getElementById("planner").classList.remove("hidden");
  showStep(1);
});
document.getElementById("printPlan").addEventListener("click", () => window.print());
renderMilestones();
