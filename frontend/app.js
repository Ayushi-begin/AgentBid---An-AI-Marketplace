/**
 * AgentBid AI — Multi-Role Frontend Client Application
 * Supports Client, Service Provider, and Reviewer Modes.
 */

const API_BASE = "/api";

let appState = {
    currentRole: "CLIENT", // "CLIENT", "PROVIDER", "REVIEWER"
    currentTaskId: null,
    currentTask: null,
    tasks: [],
    bids: [],
    agents: [],
    transactions: [],
    userWallet: "0x71C8363820F8031971300a20824b942f73AC2023",
    userBalance: "2.450 ETH"
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", async () => {
    setupTabNavigation();
    await loadInitialData();
});

function setupTabNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");
            showTab(targetTab);
        });
    });
}

function showTab(tabId) {
    document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));

    const activeNav = document.querySelector(`[data-tab="${tabId}"]`);
    const activePane = document.getElementById(tabId);
    if (activeNav) activeNav.classList.add("active");
    if (activePane) activePane.classList.add("active");

    if (tabId === "tab-dashboard") loadTasks();
    if (tabId === "tab-transactions") loadTransactions();
    if (tabId === "tab-agents") loadAgents();
    if (tabId === "tab-provider") loadProviderHub();
    if (tabId === "tab-reviewer") loadDisputedTasks();
}

async function loadInitialData() {
    await Promise.all([
        loadTasks(),
        loadAgents(),
        loadTransactions()
    ]);
}

// --- Multi-Role Switcher ---
function handleRoleSwitch(role) {
    appState.currentRole = role;
    const walletAddrEl = document.getElementById("user-wallet-addr");
    const walletBalEl = document.getElementById("user-wallet-bal");

    if (role === "CLIENT") {
        appState.userWallet = "0x71C8363820F8031971300a20824b942f73AC2023";
        appState.userBalance = "2.450 ETH";
        walletAddrEl.textContent = "0x71C8...3aB9";
        walletBalEl.textContent = "2.450 ETH";
        showToast("Switched to Client Mode: Commission tasks, fund escrow & approve work.", "info");
        showTab("tab-dashboard");
    } else if (role === "PROVIDER") {
        appState.userWallet = "0x2222222222222222222222222222222222222222";
        appState.userBalance = "0.840 ETH";
        walletAddrEl.textContent = "0x2222...2222";
        walletBalEl.textContent = "0.840 ETH";
        showToast("Switched to Service Provider Mode: Manage AI agents & track escrow payouts!", "success");
        showTab("tab-provider");
    } else if (role === "REVIEWER") {
        appState.userWallet = "0x9999999999999999999999999999999999999999";
        appState.userBalance = "10.000 ETH";
        walletAddrEl.textContent = "0x9999...9999";
        walletBalEl.textContent = "10.000 ETH";
        showToast("Switched to Reviewer Mode: Arbitrate disputes & resolve smart contract funds.", "info");
        showTab("tab-reviewer");
    }
}

// --- Toast Alerts ---
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Tasks API ---
async function loadTasks(statusFilter = null) {
    try {
        let url = `${API_BASE}/tasks`;
        if (statusFilter) url += `?status=${statusFilter}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to load tasks");
        const tasks = await res.json();
        appState.tasks = tasks;

        // Update metrics
        document.getElementById("metric-tasks-count").textContent = tasks.length;
        const totalVolume = tasks
            .filter(t => ["FUNDED", "IN_PROGRESS", "DELIVERED", "SETTLED"].includes(t.status))
            .reduce((acc, t) => acc + parseFloat(t.budget || 0), 0);
        document.getElementById("metric-escrow-volume").textContent = `${totalVolume.toFixed(3)} ETH`;

        renderTasksTable(tasks);
    } catch (err) {
        showToast(err.message, "error");
    }
}

function renderTasksTable(tasks) {
    const tbody = document.getElementById("tasks-tbody");
    if (!tasks || tasks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No tasks published yet. Click "Create Digital Task" to begin.</td></tr>`;
        return;
    }

    tbody.innerHTML = tasks.map(task => {
        const deadlineDate = new Date(task.deadline).toLocaleDateString();
        const badgeClass = `badge-${task.status.toLowerCase()}`;
        return `
            <tr>
                <td>
                    <strong style="color: #fff;">${task.title}</strong><br>
                    <small style="font-family: monospace; color: var(--text-muted);">${task.id.slice(0, 13)}...</small>
                </td>
                <td><span style="color: var(--primary-cyan); font-weight: 600;">${task.task_type}</span></td>
                <td><strong>${task.budget} ${task.currency}</strong></td>
                <td><span class="badge ${badgeClass}">${task.status}</span></td>
                <td>${deadlineDate}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="selectTaskAndOpenArena('${task.id}')">
                        Inspect Workflow &rarr;
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

// --- Task Creation ---
function populateDemoTask() {
    document.getElementById("task-title").value = "Analyze Ecommerce Transactions & Detect Fraud Anomalies";
    document.getElementById("task-type").value = "data_analysis";
    document.getElementById("task-budget").value = "0.015";
    document.getElementById("task-desc").value = "Examine 5,000 transaction records for anomalous micro-charges, high-value deviations, and card-testing spikes. Structure verified output with descriptive statistics.";
    document.getElementById("dataset-url").value = "ecommerce_transactions_oct2026.csv";
    showToast("Demo CSV analysis preset loaded!", "success");
}

function addCriterionInput() {
    const list = document.getElementById("criteria-list");
    const div = document.createElement("div");
    div.className = "criteria-row";
    div.innerHTML = `<input type="text" class="criterion-input" placeholder="Specify verifiable condition..." required>`;
    list.appendChild(div);
}

async function handleCreateTask(e) {
    e.preventDefault();
    const submitBtn = document.getElementById("btn-submit-task");
    submitBtn.disabled = true;
    submitBtn.textContent = "Broadcasting to Agents...";

    try {
        const title = document.getElementById("task-title").value;
        const task_type = document.getElementById("task-type").value;
        const budget = document.getElementById("task-budget").value;
        const description = document.getElementById("task-desc").value;
        const dataset_url = document.getElementById("dataset-url").value;

        const criteriaInputs = document.querySelectorAll(".criterion-input");
        const acceptance_criteria = Array.from(criteriaInputs).map(i => i.value.trim()).filter(Boolean);

        const deadline = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

        const payload = {
            title,
            task_type,
            budget,
            currency: "TEST_ETH",
            deadline,
            acceptance_criteria,
            dataset_url,
            client_wallet: appState.userWallet
        };

        const res = await fetch(`${API_BASE}/tasks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Failed to create task");
        }

        const createdTask = await res.json();
        showToast("Task published! Dispatching to AI Agents...", "success");

        await selectTaskAndOpenArena(createdTask.id);
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Publish Task & Broadcast to Agents";
    }
}

// --- Bidding Arena & Ranking ---
async function selectTaskAndOpenArena(taskId) {
    appState.currentTaskId = taskId;
    const task = appState.tasks.find(t => t.id === taskId) || await (await fetch(`${API_BASE}/tasks/${taskId}`)).json();
    appState.currentTask = task;

    document.getElementById("active-task-label").textContent = `Task: ${task.title} (${task.status})`;
    showTab("tab-bids");

    if (task.status === "OPEN") {
        await triggerBidding(taskId);
    } else {
        await fetchTaskBids(taskId);
        syncLifecycleView(task);
    }
}

async function triggerBidding(taskId) {
    try {
        const container = document.getElementById("bids-cards-container");
        container.innerHTML = `<div class="text-center py-5"><p class="text-muted">Agents evaluating requirements and computing scores...</p></div>`;

        const res = await fetch(`${API_BASE}/tasks/${taskId}/bids`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to generate agent bids");
        const bids = await res.json();
        appState.bids = bids;
        renderBids(bids);
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function fetchTaskBids(taskId) {
    try {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/bids`);
        if (!res.ok) throw new Error("Failed to fetch bids");
        const bids = await res.json();
        appState.bids = bids;
        renderBids(bids);
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function retriggerBidding() {
    if (!appState.currentTaskId) {
        showToast("No active task selected", "info");
        return;
    }
    await triggerBidding(appState.currentTaskId);
}

function renderBids(bids) {
    const container = document.getElementById("bids-cards-container");
    if (!bids || bids.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No bids submitted for this task.</p></div>`;
        return;
    }

    container.innerHTML = bids.map((bid, index) => {
        const isWinner = index === 0;
        const b = bid.score_breakdown || {};
        const cap = ((b.capability_component || 0) * 100).toFixed(1);
        const qual = ((b.quality_component || 0) * 100).toFixed(1);
        const price = ((b.price_component || 0) * 100).toFixed(1);
        const dline = ((b.deadline_component || 0) * 100).toFixed(1);

        return `
            <div class="bid-card ${isWinner ? 'top-ranked' : ''}">
                <div>
                    <div class="bid-header">
                        <div>
                            <span class="bid-archetype">${bid.agent_archetype || 'AGENT'}</span>
                            <h3 class="bid-agent-name">${bid.agent_name || 'Autonomous Agent'}</h3>
                        </div>
                        ${isWinner ? '<span class="badge badge-settled">Top Ranked</span>' : ''}
                    </div>

                    <div class="bid-price">${bid.amount} ${bid.currency}</div>
                    <div class="bid-meta">
                        <span>⏱️ ETA: ${bid.eta_minutes} mins</span>
                        <span>🎯 Fit: ${(bid.capability_match * 100).toFixed(0)}%</span>
                    </div>

                    <div class="score-breakdown-box">
                        <div class="score-header">
                            <span>Transparent Score:</span>
                            <span style="color: var(--primary-cyan); font-weight: 800;">${(bid.score * 100).toFixed(1)} / 100</span>
                        </div>
                        <div class="score-bar-group">
                            <div>Capability (40%): ${cap}%</div>
                            <div class="score-bar-track"><div class="score-bar-fill" style="width: ${cap}%;"></div></div>
                            <div>Quality (25%): ${qual}%</div>
                            <div class="score-bar-track"><div class="score-bar-fill" style="width: ${qual}%;"></div></div>
                            <div>Price Savings (20%): ${price}%</div>
                            <div class="score-bar-track"><div class="score-bar-fill" style="width: ${price}%;"></div></div>
                            <div>Deadline Fit (15%): ${dline}%</div>
                            <div class="score-bar-track"><div class="score-bar-fill" style="width: ${dline}%;"></div></div>
                        </div>
                    </div>

                    <div style="margin-top: 1rem;">
                        <strong style="font-size: 0.82rem; color: var(--text-muted);">Proposed Plan:</strong>
                        <ul class="plan-list">
                            ${(bid.plan || []).map(p => `<li>${p}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <div style="margin-top: 1.5rem;">
                    ${appState.currentTask.status === "OPEN" ? `
                        <button class="btn btn-primary" style="width: 100%;" onclick="selectWinnerBid('${bid.id}')">
                            Select Agent & Lock Terms
                        </button>
                    ` : (bid.status === "ACCEPTED" ? `
                        <button class="btn btn-secondary" style="width: 100%;" disabled>
                            ✓ Selected Winning Provider
                        </button>
                    ` : `
                        <button class="btn btn-secondary" style="width: 100%;" disabled>
                            Not Selected
                        </button>
                    `)}
                </div>
            </div>
        `;
    }).join("");
}

async function selectWinnerBid(bidId) {
    try {
        const taskId = appState.currentTaskId;
        const res = await fetch(`${API_BASE}/tasks/${taskId}/select-agent`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bid_id: bidId })
        });
        if (!res.ok) throw new Error("Failed to assign agent");
        const updatedTask = await res.json();
        appState.currentTask = updatedTask;

        showToast("Agent assigned! Proceeding to Escrow Funding.", "success");
        syncLifecycleView(updatedTask);
        showTab("tab-execution");
    } catch (err) {
        showToast(err.message, "error");
    }
}

// --- Lifecycle & Execution Flow ---
function syncLifecycleView(task) {
    document.getElementById("exec-task-label").textContent = `Task: ${task.title}`;
    const status = task.status;
    document.getElementById("current-task-status-badge").textContent = status;
    document.getElementById("current-task-status-badge").className = `badge badge-${status.toLowerCase()}`;

    const nodeAssigned = document.getElementById("step-node-assigned");
    const nodeFunded = document.getElementById("step-node-funded");
    const nodeDelivered = document.getElementById("step-node-delivered");
    const nodeSettled = document.getElementById("step-node-settled");
    const conn1 = document.getElementById("conn-1");
    const conn2 = document.getElementById("conn-2");
    const conn3 = document.getElementById("conn-3");

    [nodeAssigned, nodeFunded, nodeDelivered, nodeSettled].forEach(n => n.className = "step-node");
    [conn1, conn2, conn3].forEach(c => c.className = "step-connector");

    nodeAssigned.classList.add("completed");

    const container = document.getElementById("action-body-container");
    const actionTitle = document.getElementById("current-action-title");
    const actionDesc = document.getElementById("current-action-desc");

    if (status === "ASSIGNED") {
        nodeFunded.classList.add("active");
        actionTitle.textContent = "Step 2: Deposit Funds into Escrow";
        actionDesc.textContent = "Lock agreed funds in the AgentBidEscrow smart contract. The agent will only begin computation once funding is confirmed on-chain.";
        container.innerHTML = `
            <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 8px; margin-bottom: 1rem;">
                <div><strong>Contract:</strong> <code>0x5FbDB2315678afecb367f032d93F642f64180aa3</code></div>
                <div><strong>Deposit Value:</strong> <span style="color: var(--primary-cyan); font-weight: 700;">${task.budget} ETH</span></div>
            </div>
            <button class="btn btn-primary btn-lg" style="width: 100%;" onclick="executeEscrowFunding()">
                Deposit & Confirm Escrow [Sign Tx]
            </button>
        `;
    } else if (status === "FUNDED") {
        conn1.classList.add("completed");
        nodeFunded.classList.add("completed");
        nodeDelivered.classList.add("active");
        actionTitle.textContent = "Step 3: Dispatch Worker Agent";
        actionDesc.textContent = "Escrow is locked! Click to trigger the assigned AI agent runner to process data and submit findings.";
        container.innerHTML = `
            <div style="margin-bottom: 1rem; color: var(--primary-emerald); font-weight: 600;">
                ✓ Escrow deposit verified on Sepolia!
            </div>
            <button class="btn btn-primary btn-lg" style="width: 100%;" onclick="executeAgentRun()">
                Run Agent Analysis & Generate Delivery
            </button>
        `;
    } else if (status === "DELIVERED") {
        conn1.classList.add("completed");
        conn2.classList.add("completed");
        nodeFunded.classList.add("completed");
        nodeDelivered.classList.add("completed");
        nodeSettled.classList.add("active");
        actionTitle.textContent = "Step 4: Review Delivery & Release Payment";
        actionDesc.textContent = "Inspect the findings and automated verification report. Approving triggers atomic payout to the agent wallet.";
        container.innerHTML = `
            <div style="display: flex; gap: 10px; margin-top: 1rem;">
                <button class="btn btn-primary btn-lg" style="flex: 2;" onclick="approveDelivery()">
                    Approve & Release Payment (5 ★)
                </button>
                <button class="btn btn-secondary btn-lg" style="flex: 1; border-color: var(--accent-rose); color: var(--accent-rose);" onclick="disputeDelivery()">
                    Open Dispute
                </button>
            </div>
        `;
        fetchDeliveryDetails(task.id);
    } else if (status === "SETTLED") {
        conn1.classList.add("completed");
        conn2.classList.add("completed");
        conn3.classList.add("completed");
        nodeFunded.classList.add("completed");
        nodeDelivered.classList.add("completed");
        nodeSettled.classList.add("completed");
        actionTitle.textContent = "Escrow Settled Successfully!";
        actionDesc.textContent = "Payment released to agent. Outcome recorded on verifiable blockchain ledger, and agent reputation updated.";
        container.innerHTML = `
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); padding: 16px; border-radius: 8px;">
                <h4 style="color: var(--primary-emerald);">✓ Task Complete & Settled</h4>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">Smart contract released funds. Reputation incremented.</p>
            </div>
        `;
        fetchDeliveryDetails(task.id);
    } else if (status === "DISPUTED") {
        actionTitle.textContent = "Escrow Frozen — Under Review";
        actionDesc.textContent = "A formal dispute has been opened. Funds are securely locked in smart contract custody pending human arbitrator resolution.";
        container.innerHTML = `
            <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); padding: 16px; border-radius: 8px;">
                <h4 style="color: var(--accent-amber);">⚖️ Dispute Active</h4>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">Switch to Reviewer / Arbitrator Mode to review evidence and adjudicate payment.</p>
            </div>
        `;
        fetchDeliveryDetails(task.id);
    }
}

async function executeEscrowFunding() {
    try {
        const taskId = appState.currentTaskId;
        showToast("Initiating Web3 transaction on Sepolia...", "info");
        const res = await fetch(`${API_BASE}/tasks/${taskId}/fund`, { method: "POST" });
        if (!res.ok) throw new Error("Funding failed");
        const updatedTask = await res.json();
        appState.currentTask = updatedTask;
        showToast("Escrow deposit confirmed on blockchain!", "success");
        syncLifecycleView(updatedTask);
        loadTransactions();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function executeAgentRun() {
    try {
        const taskId = appState.currentTaskId;
        const logBox = document.getElementById("execution-logs");
        logBox.textContent = "Booting isolated execution runner...\nIngesting dataset...\nComputing Z-score outlier distributions...";

        const res = await fetch(`${API_BASE}/tasks/${taskId}/execute`, { method: "POST" });
        if (!res.ok) throw new Error("Agent execution failed");
        const delivery = await res.json();

        showToast("Delivery submitted & verifier checks passed!", "success");
        const taskRes = await fetch(`${API_BASE}/tasks/${taskId}`);
        const updatedTask = await taskRes.json();
        appState.currentTask = updatedTask;

        syncLifecycleView(updatedTask);
        renderDeliveryOutput(delivery);
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function fetchDeliveryDetails(taskId) {
    try {
        const res = await fetch(`${API_BASE}/tasks/${taskId}`);
        const task = await res.json();
        if (task.delivery) {
            renderDeliveryOutput(task.delivery);
        }
    } catch (err) {
        console.error(err);
    }
}

function renderDeliveryOutput(delivery) {
    const vBadge = document.getElementById("verification-badge");
    vBadge.textContent = delivery.verification_status;
    vBadge.className = `badge ${delivery.verification_status === 'PASSED' ? 'badge-settled' : 'badge-funded'}`;

    const logBox = document.getElementById("execution-logs");
    const rep = delivery.verification_report || {};
    const checksText = (rep.checklist || []).map(c => `[${c.status}] ${c.criterion} (${c.detail})`).join('\n');

    logBox.textContent = `=== CONTENT HASH ===\n${delivery.result_hash}\n\n=== VERIFICATION CHECKLIST ===\n${checksText}\n\n=== FINDINGS SUMMARY ===\n${delivery.summary}\n\n=== DETAILED ANOMALIES DETECTED ===\n${JSON.stringify(delivery.output_data?.anomalies_detected, null, 2)}`;
}

async function approveDelivery() {
    try {
        const taskId = appState.currentTaskId;
        const res = await fetch(`${API_BASE}/tasks/${taskId}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ feedback_rating: 5, comments: "Analysis passed all checklist criteria. Accurate findings." })
        });
        if (!res.ok) throw new Error("Approval failed");
        const updatedTask = await res.json();
        appState.currentTask = updatedTask;
        showToast("Escrow released! Payout transferred to agent wallet.", "success");
        syncLifecycleView(updatedTask);
        loadTransactions();
        loadAgents();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function disputeDelivery() {
    const reason = prompt("Enter formal reason for dispute:");
    if (!reason) return;
    try {
        const taskId = appState.currentTaskId;
        const res = await fetch(`${API_BASE}/tasks/${taskId}/dispute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason })
        });
        if (!res.ok) throw new Error("Dispute failed");
        const updatedTask = await res.json();
        appState.currentTask = updatedTask;
        showToast("Task disputed. Escrow frozen pending reviewer resolution.", "error");
        syncLifecycleView(updatedTask);
    } catch (err) {
        showToast(err.message, "error");
    }
}

// --- Service Provider Hub ---
async function loadProviderHub() {
    try {
        const res = await fetch(`${API_BASE}/agents`);
        if (!res.ok) return;
        const agents = await res.json();
        
        document.getElementById("provider-agents-count").textContent = agents.length;

        // Render matching tasks feed
        const feed = document.getElementById("provider-tasks-feed");
        const openTasks = appState.tasks.filter(t => t.status === "OPEN");
        if (openTasks.length === 0) {
            feed.innerHTML = `<p class="text-muted" style="font-size: 0.85rem;">No open tasks awaiting bids right now. Client tasks will appear here.</p>`;
            return;
        }

        feed.innerHTML = openTasks.map(task => `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #fff; font-size: 0.9rem;">${task.title}</strong><br>
                    <small style="color: var(--primary-cyan);">${task.task_type} • Budget: ${task.budget} ETH</small>
                </div>
                <button class="btn btn-primary btn-sm" onclick="selectTaskAndOpenArena('${task.id}')">
                    Submit Agent Bid
                </button>
            </div>
        `).join("");
    } catch (err) {
        console.error(err);
    }
}

async function handleRegisterAgent(e) {
    e.preventDefault();
    const submitBtn = document.getElementById("btn-register-agent");
    submitBtn.disabled = true;
    submitBtn.textContent = "Registering on Protocol...";

    try {
        const name = document.getElementById("reg-agent-name").value;
        const archetype = document.getElementById("reg-agent-archetype").value;
        const wallet_address = document.getElementById("reg-agent-wallet").value;
        const description = document.getElementById("reg-agent-desc").value;

        const capCheckboxes = document.querySelectorAll("input[name='caps']:checked");
        const capabilities = Array.from(capCheckboxes).map(c => c.value);

        const res = await fetch(`${API_BASE}/agents`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                archetype,
                wallet_address,
                description,
                capabilities
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Agent registration failed");
        }

        const newAgent = await res.json();
        showToast(`Agent "${newAgent.name}" registered successfully! Ready to bid.`, "success");
        document.getElementById("register-agent-form").reset();
        await loadAgents();
        await loadProviderHub();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Register Agent on Protocol";
    }
}

// --- Reviewer / Arbitrator Hub ---
async function loadDisputedTasks() {
    try {
        const container = document.getElementById("disputes-container");
        const disputedTasks = appState.tasks.filter(t => t.status === "DISPUTED");

        if (disputedTasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state py-5 text-center">
                    <p class="text-muted">Zero active disputes. All current marketplace escrows are in good standing.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = disputedTasks.map(task => `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--accent-amber); border-radius: 12px; padding: 18px; margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="badge badge-funded">DISPUTED TASK</span>
                        <h4 style="color: #fff; font-size: 1.1rem; margin-top: 6px;">${task.title}</h4>
                        <small style="color: var(--text-muted); font-family: monospace;">Task ID: ${task.id}</small>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.2rem; font-weight: 800; color: var(--primary-cyan);">${task.budget} ETH</span>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Held in Escrow</div>
                    </div>
                </div>

                <div style="margin: 1rem 0; font-size: 0.88rem; color: var(--text-secondary);">
                    <strong>Task Type:</strong> ${task.task_type}<br>
                    <strong>Escrow Contract:</strong> <code>0x5FbDB2315678afecb367f032d93F642f64180aa3</code>
                </div>

                <div style="border-top: 1px solid var(--border-color); padding-top: 12px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-primary btn-sm" onclick="executeDisputeResolution('${task.id}', 'PAY_AGENT')">
                        🟢 Resolve: Pay Agent (${task.budget} ETH)
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="executeDisputeResolution('${task.id}', 'REFUND_CLIENT')">
                        🔵 Resolve: Full Refund to Client
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="executeDisputeResolution('${task.id}', 'SPLIT_50_50')">
                        🟡 Resolve: Split 50 / 50
                    </button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error(err);
    }
}

async function executeDisputeResolution(taskId, outcome) {
    const notes = prompt(`Enter arbitration notes for outcome [${outcome}]:`, "Arbitrator binding resolution.");
    if (notes === null) return;

    try {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/resolve-dispute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ outcome, reviewer_notes: notes })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Dispute resolution failed");
        }

        showToast(`Dispute resolved with outcome [${outcome}]! Smart contract settled.`, "success");
        await loadTasks();
        await loadDisputedTasks();
        await loadTransactions();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// --- Blockchain Explorer ---
async function loadTransactions() {
    try {
        const res = await fetch(`${API_BASE}/transactions`);
        if (!res.ok) return;
        const txs = await res.json();
        appState.transactions = txs;

        const tbody = document.getElementById("tx-tbody");
        if (!txs || txs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No blockchain transactions recorded yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = txs.map(tx => {
            const dateStr = new Date(tx.confirmed_at).toLocaleTimeString();
            return `
                <tr>
                    <td><code style="color: var(--primary-cyan); font-family: monospace;">${tx.tx_hash.slice(0, 16)}...</code></td>
                    <td><span class="badge badge-assigned">${tx.event_type}</span></td>
                    <td><small style="font-family: monospace;">${tx.task_id.slice(0, 8)}...</small></td>
                    <td><strong>${tx.amount ? tx.amount + ' ETH' : 'N/A'}</strong></td>
                    <td><small style="font-family: monospace;">${tx.from_address?.slice(0, 8)} &rarr; ${tx.to_address?.slice(0, 8)}</small></td>
                    <td><span class="badge badge-settled">${tx.status}</span></td>
                    <td>${dateStr}</td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        console.error(err);
    }
}

// --- Agent Registry Leaderboard ---
async function loadAgents() {
    try {
        const res = await fetch(`${API_BASE}/agents`);
        if (!res.ok) return;
        const agents = await res.json();
        appState.agents = agents;

        document.getElementById("active-agents-count").textContent = `${agents.length} Registered`;
        const container = document.getElementById("agents-registry-container");

        container.innerHTML = agents.map(agent => {
            return `
                <div class="agent-card">
                    <div class="agent-card-header">
                        <div>
                            <span class="badge badge-open">${agent.archetype}</span>
                            <h3 style="font-size: 1.2rem; font-weight: 700; margin-top: 6px;">${agent.name}</h3>
                        </div>
                        <div class="agent-score-pill">★ ${agent.reputation_score}</div>
                    </div>

                    <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">
                        ${agent.description || 'Autonomous marketplace worker.'}
                    </p>

                    <div style="font-size: 0.82rem; margin-bottom: 1rem;">
                        <span style="color: var(--text-muted);">Completed Tasks:</span>
                        <strong style="color: #fff;"> ${agent.settled_tasks_count} Settled</strong>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Capabilities:</span>
                        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                            ${(agent.capabilities || []).map(c => `<span class="badge" style="background: rgba(255,255,255,0.06); font-size: 0.7rem;">${c}</span>`).join('')}
                        </div>
                    </div>

                    <div style="border-top: 1px solid var(--border-color); padding-top: 10px;">
                        <code style="font-size: 0.72rem; color: var(--text-muted); font-family: monospace;">
                            ${agent.wallet_address}
                        </code>
                    </div>
                </div>
            `;
        }).join("");
    } catch (err) {
        console.error(err);
    }
}
