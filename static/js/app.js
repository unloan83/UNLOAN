const definitions = {
  expenses: [
    ["rent", "🏠", "House rent"], ["home_loan_emi", "🏡", "Home loan EMI"], ["food", "🛒", "Food & groceries"],
    ["transport", "🚗", "Transport"], ["utilities", "⚡", "Utilities"], ["insurance", "🛡️", "Insurance"],
    ["education", "🎓", "Education"], ["healthcare", "💊", "Healthcare"], ["lifestyle", "✨", "Lifestyle"],
    ["domestic_help", "🤝", "Domestic help"], ["parents_support", "♥", "Parents support"], ["child_expenses", "🧸", "Child expenses"],
    ["subscriptions", "▣", "Subscriptions"], ["miscellaneous", "•••", "Miscellaneous"],
  ],
  investments: [
    ["bank_savings", "🏦", "Bank savings"], ["emergency_fund", "☂️", "Emergency fund"], ["fixed_deposit", "🔒", "Fixed deposits"],
    ["recurring_deposit", "↻", "Recurring deposits"], ["mutual_funds", "📈", "Mutual funds"], ["stocks", "▥", "Stocks"],
    ["gold", "◆", "Gold"], ["retirement_funds", "🌴", "PPF / EPF / NPS"], ["insurance_savings", "🛡", "Insurance savings"],
    ["real_estate", "🏢", "Real estate"], ["crypto", "₿", "Crypto"], ["other_investment", "＋", "Other investments"],
  ],
  debts: [
    ["home_loan", "🏠", "Home loan"], ["personal_loan", "₹", "Personal loan"], ["credit_card", "💳", "Credit card dues"],
    ["vehicle_loan", "🚙", "Vehicle loan"], ["education_loan", "🎓", "Education loan"], ["business_loan", "💼", "Business loan"],
    ["friends_family", "🤝", "Friends / family"], ["other_loan", "＋", "Other loans"],
  ],
  goals: [
    ["emergency_goal", "☂️", "Build emergency fund", 500000, 2], ["debt_free", "🕊", "Become debt-free", 500000, 3],
    ["first_lakh", "🏅", "First ₹1 lakh", 100000, 1], ["first_ten_lakh", "💎", "First ₹10 lakh net worth", 1000000, 5],
    ["buy_house", "🏡", "Buy a house", 3000000, 8], ["buy_vehicle", "🚗", "Buy a vehicle", 1000000, 4],
    ["child_education", "🎓", "Child education", 2500000, 12], ["marriage", "💍", "Marriage planning", 1500000, 5],
    ["retirement", "🌴", "Retirement planning", 20000000, 20], ["business", "🚀", "Start a business", 2000000, 6],
    ["travel", "✈️", "Travel goal", 500000, 3], ["wealth_milestone", "📈", "Wealth milestone", 10000000, 10],
  ],
};

const state = { mode: "short", step: 1, stability: "stable", riskProfile: "balanced", selected: { expenses: {}, investments: {}, debts: {}, goals: {} }, record: null, breakdown: "assets" };
const stepTitles = ["About you", "Income", "Expenses", "Savings", "Debts", "Goals"];
const form = document.getElementById("plannerForm");

const money = (value) => {
  const amount = Number(value || 0);
  const sign = amount < 0 ? "−" : "";
  const absolute = Math.abs(amount);
  if (absolute >= 10000000) return `${sign}₹${(absolute / 10000000).toFixed(2).replace(/\.00$/, "")} Cr`;
  if (absolute >= 100000) return `${sign}₹${(absolute / 100000).toFixed(1).replace(/\.0$/, "")} L`;
  return `${sign}${new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(absolute)}`;
};
const safe = (text) => String(text).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const getNumber = (id) => Number(document.getElementById(id)?.value || 0);
const goalDefinition = (key) => definitions.goals.find((item) => item[0] === key) || definitions.goals.at(-1);

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll("[data-mode]").forEach((button) => button.classList.toggle("selected", button.dataset.mode === mode));
  document.getElementById("shortPlanForm").classList.toggle("hidden", mode !== "short");
  document.getElementById("detailedPlanForm").classList.toggle("hidden", mode !== "detailed");
  document.querySelector(".step-sidebar").classList.toggle("hidden", mode !== "detailed");
  document.querySelector(".mobile-progress").classList.toggle("hidden", mode !== "detailed");
  if (mode === "detailed") showStep(state.step);
}

function renderOptionGrids() {
  Object.entries(definitions).forEach(([type, items]) => {
    const container = document.getElementById(`${type === "investments" ? "investment" : type.slice(0, -1)}Options`);
    container.innerHTML = items.map(([key, icon, label]) => `<button type="button" class="option-card" data-type="${type}" data-key="${key}"><span>${icon}</span><b>${label}</b><i>✓</i></button>`).join("");
  });
  document.querySelectorAll(".option-card").forEach((card) => card.addEventListener("click", () => toggleOption(card.dataset.type, card.dataset.key)));
}

function toggleOption(type, key) {
  if (state.selected[type][key]) delete state.selected[type][key];
  else {
    const definition = definitions[type].find((item) => item[0] === key);
    state.selected[type][key] = { key, name: definition[2], icon: definition[1], amount: definition[3] || 0, years: definition[4] || 0, custom: false };
  }
  syncOptions(type);
  renderDetails(type);
}

function syncOptions(type) {
  document.querySelectorAll(`.option-card[data-type="${type}"]`).forEach((card) => card.classList.toggle("selected", Boolean(state.selected[type][card.dataset.key])));
}

function renderDetails(type) {
  const singular = type === "investments" ? "investment" : type.slice(0, -1);
  const container = document.getElementById(`${singular}Details`);
  const rows = Object.values(state.selected[type]);
  if (!rows.length) { container.innerHTML = ""; return; }
  container.innerHTML = `<div class="details-heading"><span>SELECTED ${type.toUpperCase()}</span><b>${rows.length} added</b></div>${rows.map((item) => detailTemplate(type, item)).join("")}`;
  container.querySelectorAll(".remove-detail").forEach((button) => button.addEventListener("click", () => toggleOption(type, button.dataset.key)));
  bindDetailInputs(type, container);
  queueBenchmark();
}

function bindDetailInputs(type, container) {
  container.querySelectorAll("input,select").forEach((field) => field.addEventListener("input", () => {
    const parts = field.id.split("-"); const key = parts.slice(1, -1).join("-"); const property = parts.at(-1);
    if (!state.selected[type][key]) return;
    const propertyMap = { amount: "amount", outstanding: "outstanding", emi: "emi", interest: "interestRate", tenure: "tenureMonths", years: "years", priority: "priority" };
    state.selected[type][key][propertyMap[property] || property] = field.tagName === "SELECT" ? field.value : Number(field.value || 0);
    queueBenchmark();
  }));
}

function detailTemplate(type, item) {
  const key = safe(item.key); const name = safe(item.name); const icon = safe(item.icon);
  if (type === "expenses" || type === "investments") return `<div class="detail-row simple"><div class="detail-name"><span>${icon}</span><b>${name}</b></div><label>${type === "expenses" ? "Monthly amount" : "Current value"}<div class="money-field compact"><span>₹</span><input id="${type}-${key}-amount" type="number" min="0" inputmode="decimal" value="${item.amount || ""}" placeholder="0" /></div></label><button type="button" class="remove-detail" data-key="${key}" aria-label="Remove ${name}">×</button></div>`;
  if (type === "debts") return `<div class="detail-row expanded"><div class="detail-name"><span>${icon}</span><b>${name}</b><button type="button" class="remove-detail" data-key="${key}">Remove</button></div><div class="mini-grid four"><label>Outstanding<div class="money-field compact"><span>₹</span><input id="debts-${key}-outstanding" type="number" min="0" value="${item.outstanding || ""}" placeholder="0" /></div></label><label>Monthly EMI<div class="money-field compact"><span>₹</span><input id="debts-${key}-emi" type="number" min="0" value="${item.emi || ""}" placeholder="0" /></div></label><label>Interest %<input id="debts-${key}-interest" type="number" min="0" max="60" step="0.1" value="${item.interestRate || ""}" placeholder="e.g. 12" /></label><label>Months left<input id="debts-${key}-tenure" type="number" min="0" value="${item.tenureMonths || ""}" placeholder="e.g. 36" /></label></div></div>`;
  return `<div class="detail-row expanded goal-row"><div class="detail-name"><span>${icon}</span><b>${name}</b><button type="button" class="remove-detail" data-key="${key}">Remove</button></div><div class="mini-grid three"><label>Target amount<div class="money-field compact"><span>₹</span><input id="goals-${key}-amount" type="number" min="1" value="${item.amount || ""}" placeholder="0" /></div></label><label>Years from now<input id="goals-${key}-years" type="number" min="1" max="50" value="${item.years || ""}" /></label><label>Priority<select id="goals-${key}-priority"><option value="high" ${item.priority === "high" ? "selected" : ""}>High — must happen</option><option value="medium" ${!item.priority || item.priority === "medium" ? "selected" : ""}>Medium</option><option value="low" ${item.priority === "low" ? "selected" : ""}>Low — flexible</option></select></label></div></div>`;
}

document.querySelectorAll(".add-custom").forEach((button) => button.addEventListener("click", () => {
  const type = button.dataset.custom;
  const name = window.prompt(`Name your custom ${type === "goals" ? "goal" : type.slice(0, -1)}:`)?.trim();
  if (!name) return;
  const key = `custom_${Date.now()}`;
  state.selected[type][key] = { key, name, icon: "✦", amount: 0, years: type === "goals" ? 5 : 0, custom: true };
  renderDetails(type);
}));

document.querySelectorAll("[data-choice]").forEach((group) => group.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
  group.querySelectorAll("button").forEach((item) => item.classList.remove("selected"));
  button.classList.add("selected"); state[group.dataset.choice] = button.dataset.value;
})));
document.getElementById("annualGrowth").addEventListener("input", (event) => { document.getElementById("growthOutput").textContent = `${event.target.value}%`; });

let benchmarkTimer;
function queueBenchmark() { clearTimeout(benchmarkTimer); benchmarkTimer = setTimeout(updateBenchmarks, 250); }
function benchmarkPayload() {
  const expenses = Object.values(state.selected.expenses).map((item) => ({ ...item, amount: getNumber(`expenses-${item.key}-amount`) || item.amount || 0 }));
  const debts = Object.values(state.selected.debts).map((item) => ({ ...item, emi: getNumber(`debts-${item.key}-emi`) || item.emi || 0 }));
  const investments = Object.values(state.selected.investments).map((item) => ({ ...item, amount: getNumber(`investments-${item.key}-amount`) || item.amount || 0 }));
  return {
    age: getNumber("age") || 30, region: document.getElementById("region").value,
    employmentStatus: document.getElementById("employmentStatus").value, dependents: getNumber("dependents"),
    monthlyIncome: getNumber("monthlyIncome"), otherIncome: getNumber("otherIncome"),
    monthlyExpenses: expenses.reduce((sum, item) => sum + item.amount, 0),
    rent: expenses.find((item) => item.key === "rent")?.amount || 0,
    monthlyEmi: debts.reduce((sum, item) => sum + item.emi, 0),
    liquidSavings: investments.filter((item) => ["bank_savings", "emergency_fund", "fixed_deposit", "recurring_deposit"].includes(item.key)).reduce((sum, item) => sum + item.amount, 0),
  };
}
async function updateBenchmarks() {
  try {
    const response = await fetch("/api/benchmarks/context", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(benchmarkPayload()) });
    const data = await response.json(); if (!data.ok) return;
    const b = data.benchmark, r = b.ranges, a = b.actuals;
    document.getElementById("incomeBenchmark").innerHTML = r.monthly_savings_amount[1] ? `For this profile, a <b>${r.savings_rate_percent[0]}–${r.savings_rate_percent[1]}%</b> planning range equals roughly <b>${money(r.monthly_savings_amount[0])}–${money(r.monthly_savings_amount[1])}</b> monthly.` : "Add your income to see a gentle savings guide.";
    const rentComparison = a.rent_share_percent == null ? "Select rent to compare its share of income." : `Your rent is <b>${a.rent_share_percent}%</b> of income; the estimated regional planning range is <b>${r.rent_share_percent[0]}–${r.rent_share_percent[1]}%</b>.`;
    let savingsComparison = "";
    if (a.savings_rate_percent != null) {
      const position = a.savings_rate_percent < r.savings_rate_percent[0] ? "below" : a.savings_rate_percent > r.savings_rate_percent[1] ? "above" : "within";
      savingsComparison = ` Your current available rate is <b>${a.savings_rate_percent}%</b>, ${position} the estimated <b>${r.savings_rate_percent[0]}–${r.savings_rate_percent[1]}%</b> range—and simply shows where your next opportunity may be.`;
    }
    document.getElementById("expenseBenchmark").innerHTML = rentComparison + savingsComparison;
    const safetyComparison = a.emergency_months == null ? `A suggested buffer for this profile is <b>${r.emergency_months[0]}–${r.emergency_months[1]} months</b> of essential expenses.` : `Your selected liquid savings cover about <b>${a.emergency_months} months</b>; the estimated guide is <b>${r.emergency_months[0]}–${r.emergency_months[1]} months</b>.`;
    document.getElementById("savingsBenchmark").innerHTML = safetyComparison;
    const emiComparison = a.emi_share_percent == null ? `A common planning guardrail is to keep total EMIs below <b>${r.healthy_emi_max_percent}%</b> of take-home income.` : `Your selected EMIs use <b>${a.emi_share_percent}%</b> of income; the planning guardrail is below <b>${r.healthy_emi_max_percent}%</b>.`;
    document.getElementById("debtBenchmark").innerHTML = emiComparison;
  } catch (_) { /* Benchmarks are helpful, never blocking. */ }
}
document.querySelectorAll("#age,#region,#employmentStatus,#dependents,#monthlyIncome,#otherIncome").forEach((field) => field.addEventListener("input", queueBenchmark));

function showStep(nextStep) {
  state.step = Math.max(1, Math.min(6, nextStep));
  document.querySelectorAll(".form-step").forEach((section) => section.classList.toggle("hidden", Number(section.dataset.step) !== state.step));
  document.querySelectorAll("#stepNav button").forEach((button, index) => { button.classList.toggle("active", index + 1 === state.step); button.classList.toggle("complete", index + 1 < state.step); });
  const percent = Math.round(state.step / 6 * 100);
  document.getElementById("sidebarProgress").textContent = `${state.step} of 6`;
  document.getElementById("mobileStep").textContent = `STEP ${state.step} OF 6`;
  document.getElementById("mobileTitle").textContent = stepTitles[state.step - 1];
  document.getElementById("progressPercent").textContent = `${percent}%`;
  document.getElementById("progressBar").style.width = `${percent}%`;
  document.getElementById("backButton").classList.toggle("hidden", state.step === 1);
  document.getElementById("skipButton").classList.toggle("hidden", state.step < 3 || state.step === 6);
  document.getElementById("nextButton").innerHTML = state.step === 6 ? `Reveal my wealth roadmap <span>✦</span>` : `Continue <span>→</span>`;
  document.getElementById("planner").scrollIntoView({ behavior: "smooth", block: "start" });
}

function validateCurrentStep() {
  const section = document.querySelector(`.form-step[data-step="${state.step}"]`);
  const invalid = [...section.querySelectorAll("input[required],select[required]")].find((field) => !field.checkValidity());
  if (invalid) { invalid.reportValidity(); invalid.focus(); return false; }
  if (state.step === 2 && getNumber("monthlyIncome") + getNumber("otherIncome") <= 0) { document.getElementById("monthlyIncome").setCustomValidity("Add at least one monthly income source."); document.getElementById("monthlyIncome").reportValidity(); document.getElementById("monthlyIncome").setCustomValidity(""); return false; }
  return true;
}

function validateShortPlan() {
  const invalid = [...document.querySelectorAll("#shortPlanForm input[required],#shortPlanForm select[required]")].find((field) => !field.checkValidity());
  if (invalid) { invalid.reportValidity(); invalid.focus(); return false; }
  if (getNumber("shortMonthlyIncome") <= 0) { document.getElementById("shortMonthlyIncome").setCustomValidity("Add your monthly income."); document.getElementById("shortMonthlyIncome").reportValidity(); document.getElementById("shortMonthlyIncome").setCustomValidity(""); return false; }
  return true;
}

document.getElementById("backButton").addEventListener("click", () => showStep(state.step - 1));
document.getElementById("skipButton").addEventListener("click", () => showStep(state.step + 1));
document.getElementById("nextButton").addEventListener("click", () => { if (!validateCurrentStep()) return; if (state.step < 6) showStep(state.step + 1); else submitPlan(); });
document.getElementById("shortSubmitButton").addEventListener("click", () => { if (validateShortPlan()) submitPlan(); });
document.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
document.querySelectorAll("#stepNav button").forEach((button) => button.addEventListener("click", () => { const target = Number(button.dataset.go); if (target <= state.step) showStep(target); }));

function collectSimple(type) {
  return Object.values(state.selected[type]).map((item) => ({ key: item.key, name: item.name, amount: getNumber(`${type}-${item.key}-amount`) })).filter((item) => item.amount > 0);
}
function buildShortPayload() {
  const goal = goalDefinition(document.getElementById("shortMainGoal").value);
  const timeline = Math.max(getNumber("shortGoalTimeline"), 1);
  const income = getNumber("shortMonthlyIncome");
  const expenses = getNumber("shortEssentialExpenses");
  const emi = getNumber("shortEmi");
  const surplus = Math.max(income - expenses - emi, 0);
  const targetAmount = goal[3] || Math.max(surplus * 12 * timeline, income * 6);
  const debts = emi > 0 ? [{ key: "other_loan", name: "Loan / EMI", outstanding: emi * 24, emi, interestRate: 10, tenureMonths: 24 }] : [];
  const investments = [
    { key: "bank_savings", name: "Current savings", amount: getNumber("shortSavings") },
    { key: "mutual_funds", name: "Current investments", amount: getNumber("shortInvestments") },
  ].filter((item) => item.amount > 0);
  return {
    planMode: "short",
    profile: { name: "Friend", age: getNumber("shortAge"), city: document.getElementById("shortCity").value, region: "urban", employmentStatus: "salaried", maritalStatus: "single", dependents: 0, financialGoalCategory: goal[0], riskProfile: "balanced" },
    income: { monthlyIncome: income, otherIncome: 0, stability: "stable", annualGrowth: 5 },
    expenses: expenses > 0 ? [{ key: "essentials", name: "Essential expenses", amount: expenses }] : [],
    investments,
    debts,
    goals: [{ key: goal[0], name: goal[2], targetAmount, targetYears: timeline, priority: "high" }],
  };
}
function buildPayload() {
  if (state.mode === "short") return buildShortPayload();
  return {
    planMode: "detailed",
    profile: { name: document.getElementById("name").value, age: getNumber("age"), city: document.getElementById("city").value, region: document.getElementById("region").value, employmentStatus: document.getElementById("employmentStatus").value, maritalStatus: document.getElementById("maritalStatus").value, dependents: getNumber("dependents"), financialGoalCategory: document.getElementById("financialGoalCategory").value, riskProfile: state.riskProfile },
    income: { monthlyIncome: getNumber("monthlyIncome"), otherIncome: getNumber("otherIncome"), stability: state.stability, annualGrowth: getNumber("annualGrowth") },
    expenses: collectSimple("expenses"), investments: collectSimple("investments"),
    debts: Object.values(state.selected.debts).map((item) => ({ key: item.key, name: item.name, outstanding: getNumber(`debts-${item.key}-outstanding`), emi: getNumber(`debts-${item.key}-emi`), interestRate: getNumber(`debts-${item.key}-interest`), tenureMonths: getNumber(`debts-${item.key}-tenure`) })).filter((item) => item.outstanding > 0 || item.emi > 0),
    goals: Object.values(state.selected.goals).map((item) => ({ key: item.key, name: item.name, targetAmount: getNumber(`goals-${item.key}-amount`), targetYears: getNumber(`goals-${item.key}-years`), priority: document.getElementById(`goals-${item.key}-priority`)?.value || "medium" })).filter((item) => item.targetAmount > 0 && item.targetYears > 0),
  };
}

async function submitPlan() {
  const button = state.mode === "short" ? document.getElementById("shortSubmitButton") : document.getElementById("nextButton");
  const error = state.mode === "short" ? document.getElementById("shortFormError") : document.getElementById("formError");
  const resetLabel = state.mode === "short" ? `Create short plan <span>→</span>` : `Reveal my wealth roadmap <span>✦</span>`;
  button.disabled = true; button.innerHTML = `Building your roadmap… <span class="spinner"></span>`; error.textContent = "";
  try {
    const response = await fetch("/api/plan/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(buildPayload()) });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "We couldn’t build your plan yet.");
    state.record = data.record; renderResults(data.record);
  } catch (issue) { error.textContent = issue.message; }
  finally { button.disabled = false; button.innerHTML = resetLabel; }
}

function renderResults(record) {
  const s = record.summary;
  const isShort = record.plan_mode === "short" || state.mode === "short";
  document.getElementById("results").classList.toggle("short-results", isShort);
  document.getElementById("resultTitle").textContent = `${record.profile.name}, your path is ready.`;
  document.getElementById("coachMessage").textContent = isShort ? "Here is what you can build from today, using the numbers you shared." : s.coach_message;
  document.getElementById("wealthStage").textContent = s.wealth_stage;
  document.getElementById("healthScore").textContent = s.health_score;
  document.getElementById("healthLabel").textContent = s.health_label;
  document.getElementById("netWorth").textContent = money(s.net_worth);
  document.getElementById("assetDebtText").textContent = `${money(s.assets)} assets · ${money(s.liabilities)} debt`;
  document.getElementById("monthlySurplus").textContent = money(s.monthly_surplus);
  document.getElementById("savingsText").textContent = `${s.savings_ratio}% of income available`;
  document.getElementById("emergencyProgress").textContent = `${s.emergency_progress}%`;
  document.getElementById("emergencyText").textContent = `${money(s.emergency_fund)} of ${money(s.emergency_target)}`;
  document.getElementById("debtRatio").textContent = `${s.debt_ratio}%`;
  document.getElementById("scoreStatusBadge").textContent = s.health_label;
  document.getElementById("scoreStatusBadge").dataset.status = s.health_label.toLowerCase().replaceAll(" ", "-");
  document.getElementById("scoreReasons").innerHTML = s.score_reasons.map((reason) => `<li><i>✓</i><span>${safe(reason)}</span></li>`).join("");
  document.getElementById("roadmapTimeline").innerHTML = s.roadmap.map((phase, index) => `<div><span>${index + 1}</span><i></i><article><small>${safe(phase.period)}</small><b>${safe(phase.title)}</b><p>${safe(phase.focus)}</p><em>${safe(phase.target)}</em></article></div>`).join("");

  const income = Math.max(s.monthly_income, 1), expensePct = s.monthly_expenses / income * 100, debtPct = s.monthly_debt_emi / income * 100, surplusPct = Math.max(100 - expensePct - debtPct, 0);
  document.getElementById("cashflowDonut").style.background = `conic-gradient(#ff8e78 0 ${expensePct}%, #ffca6a ${expensePct}% ${expensePct + debtPct}%, #4dd3a9 ${expensePct + debtPct}% 100%)`;
  document.getElementById("donutIncome").textContent = money(s.monthly_income);
  document.getElementById("cashflowLegend").innerHTML = [["Living expenses", s.monthly_expenses, expensePct, "coral"], ["Loan EMIs", s.monthly_debt_emi, debtPct, "gold"], ["Free cash flow", s.monthly_surplus, surplusPct, "green"]].map(([label, value, pct, color]) => `<div><i class="${color}"></i><span>${label}<small>${Math.round(pct)}% of income</small></span><b>${money(value)}</b></div>`).join("");

  const allocations = [["Necessities", s.allocation.safety, "◉", "purple"], ["Debt freedom", s.allocation.debt_freedom, "↘", "coral"], ["Life goals", s.allocation.goals, "★", "blue"], ["Long-term wealth", s.allocation.wealth, "↗", "green"]];
  const allocationMax = Math.max(...allocations.map((item) => item[1]), 1);
  document.getElementById("allocationPlan").innerHTML = allocations.map(([label, value, icon, color]) => `<div class="allocation-item"><span class="allocation-icon ${color}">${icon}</span><div><p><b>${label}</b><strong>${money(value)}<small>/mo</small></strong></p><i><em class="${color}" style="width:${value / allocationMax * 100}%"></em></i></div></div>`).join("");

  const recommendationRows = isShort ? s.recommendations.slice(0, 3) : s.recommendations;
  const actionRows = isShort ? s.action_plan.slice(0, 3) : s.action_plan;
  document.getElementById("recommendations").innerHTML = recommendationRows.map((item, index) => `<article><div><span>${index + 1}</span><i>${["◉", "★", "↗", "✦", "✓"][index]}</i></div><small>${safe(item.category)}</small><h4>${safe(item.title)}</h4><p>${safe(item.detail)}</p><b>${safe(item.impact)} →</b></article>`).join("");
  document.getElementById("actionPlan").innerHTML = actionRows.map((item, index) => `<div><span>${index + 1}</span><p><b>${safe(item.action)}</b><small>${safe(item.reason)}</small></p><strong>${money(item.monthly_amount)}<small>/month</small></strong></div>`).join("");
  document.getElementById("milestoneProjections").innerHTML = s.milestone_projections.map((item) => `<div><p><b>${safe(item.name)}</b><small>${safe(item.note)}</small></p><span><strong>${safe(item.projected_date)}</strong><i><em style="width:${item.progress}%"></em></i></span></div>`).join("");
  const coachRows = isShort ? s.coach_insights.slice(0, 1) : s.coach_insights;
  document.getElementById("coachInsights").innerHTML = coachRows.map((item, index) => `<article><span>${["✓", "1", "30", "↗", "★"][index]}</span><div><small>${safe(item.label)}</small><b>${safe(item.title)}</b><p>${safe(item.message)}</p></div></article>`).join("");
  document.getElementById("goalResults").innerHTML = s.goals.length ? s.goals.map((goal) => `<div class="goal-result"><div class="goal-main"><span class="goal-symbol">${definitions.goals.find((item) => item[0] === goal.key)?.[1] || "✦"}</span><div><b>${safe(goal.name)}</b><small>${goal.priority} priority · ${goal.target_years} years</small></div></div><div class="goal-progress"><p><span>Plan coverage</span><b>${goal.funding_ratio}%</b></p><i><em style="width:${goal.funding_ratio}%"></em></i><small>${safe(goal.advice)}</small></div><div class="goal-amount"><strong>${money(goal.monthly_required)}</strong><span>needed / month</span><small>${money(goal.future_cost)} future cost</small></div><span class="goal-status ${goal.status.toLowerCase().replaceAll(" ", "-")}">${goal.status}</span></div>`).join("") : `<div class="empty-state"><span>🌱</span><b>No milestones selected yet</b><p>Your surplus is focused on financial safety and long-term wealth.</p></div>`;

  const projectionMax = Math.max(...s.projections.map((item) => item.expected), 1);
  document.getElementById("projectionChart").innerHTML = s.projections.map((item) => `<div class="projection-group"><div class="bar-pair"><i class="conservative" style="height:${Math.max(item.conservative / projectionMax * 180, 10)}px"><span>${money(item.conservative)}</span></i><i class="expected" style="height:${Math.max(item.expected / projectionMax * 180, 14)}px"><span>${money(item.expected)}</span></i></div><b>${item.years} years</b><small>${money(item.contributed)} put in</small></div>`).join("");
  document.getElementById("assumptionText").textContent = s.assumptions.join(" ");
  state.breakdown = "assets"; renderBreakdown();
  document.getElementById("planner").classList.add("hidden"); document.getElementById("results").classList.remove("hidden"); document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderBreakdown() {
  if (!state.record) return;
  const s = state.record.summary;
  let rows, total;
  if (state.breakdown === "assets") { rows = s.asset_breakdown; total = s.assets; }
  else if (state.breakdown === "expenses") { rows = s.expense_breakdown; total = s.monthly_expenses; }
  else { rows = s.debt_breakdown.map((item) => ({ name: item.name, amount: item.outstanding })); total = s.liabilities; }
  const colors = ["#6857f5", "#3fbf9a", "#4c9df0", "#ff9a72", "#f1bb56"];
  document.getElementById("breakdownList").innerHTML = rows.length ? rows.slice(0, 6).map((row, index) => `<div><p><i style="background:${colors[index % colors.length]}"></i><span>${safe(row.name)}</span><b>${money(row.amount)}</b></p><span><em style="width:${total ? row.amount / total * 100 : 0}%;background:${colors[index % colors.length]}"></em></span></div>`).join("") : `<div class="empty-mini">Nothing added in this category.</div>`;
}

document.querySelectorAll("[data-breakdown]").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll("[data-breakdown]").forEach((item) => item.classList.remove("active")); button.classList.add("active"); state.breakdown = button.dataset.breakdown; renderBreakdown(); }));
document.getElementById("editPlan").addEventListener("click", () => { document.getElementById("results").classList.add("hidden"); document.getElementById("planner").classList.remove("hidden"); setMode(state.mode); if (state.mode === "detailed") showStep(1); });
document.getElementById("printPlan").addEventListener("click", () => window.print());

renderOptionGrids(); setMode("short"); showStep(1); queueBenchmark();
