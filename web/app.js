let currentIssues = [];
let activeCategory = 'all';
let selectedIssueIds = new Set();
let scanCompleted = false;
let isBusy = false;

window.addEventListener('pywebviewready', async () => {
    initEventDelegation();
    await fetchSystemOverview();
});

function setBusy(state) {
    isBusy = state;
    const appWrapper = document.querySelector('.app-wrapper');
    if (appWrapper) {
        if (state) {
            appWrapper.classList.add('busy-state');
        } else {
            appWrapper.classList.remove('busy-state');
        }
    }
    const btnScan = document.getElementById('btn-scan');
    const btnElevate = document.getElementById('btn-elevate');
    if (btnScan) btnScan.disabled = state;
    if (btnElevate) btnElevate.disabled = state;
    updateFixSelectedButton();
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function initEventDelegation() {
    const container = document.getElementById('issues-container');
    if (container) {
        container.addEventListener('click', async (e) => {
            if (isBusy) return;

            const actionTarget = e.target.closest('[data-action]');
            if (actionTarget) {
                const action = actionTarget.getAttribute('data-action');
                const id = actionTarget.getAttribute('data-id');
                if (action === 'fix') {
                    await fixSingle(id);
                } else if (action === 'revert') {
                    await revertSingle(id);
                }
                return;
            }

            const checkTarget = e.target.closest('[data-toggle-id]');
            if (checkTarget) {
                const id = checkTarget.getAttribute('data-toggle-id');
                toggleSelect(id);
            }
        });
    }

    const overlay = document.getElementById('console-overlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                toggleConsole();
            }
        });
    }

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const overlay = document.getElementById('console-overlay');
            if (overlay && overlay.classList.contains('open')) {
                toggleConsole();
            }
        }
    });
}

async function fetchSystemOverview() {
    try {
        if (window.pywebview && window.pywebview.api) {
            const info = await window.pywebview.api.get_system_overview();
            document.getElementById('os-platform').innerText = `${info.hostname} • ${info.os}`;
            if (info.is_admin) {
                document.getElementById('admin-badge').classList.remove('hidden');
                document.getElementById('btn-elevate').classList.add('hidden');
            } else {
                document.getElementById('btn-elevate').classList.remove('hidden');
            }
        }
    } catch (err) {
        console.error(err);
    }
}

async function elevatePrivileges() {
    if (isBusy) return;
    setBusy(true);
    showToast("Requesting administrator elevation via UAC...", "info");
    try {
        if (window.pywebview && window.pywebview.api) {
            await window.pywebview.api.request_admin();
        }
    } catch (e) {
        showToast("UAC Elevation Fault: " + e, "danger");
    } finally {
        setBusy(false);
    }
}

function setHeroStatus(mode, vulnCount = 0, critCount = 0) {
    const glowContainer = document.getElementById('hero-glow-container');
    const iconBox = document.getElementById('hero-icon-box');
    const icon = document.getElementById('hero-icon');
    const title = document.getElementById('hero-title');
    const desc = document.getElementById('hero-desc');

    glowContainer.className = `glow-container theme-${mode}`;
    iconBox.className = `hero-icon-box ${mode}`;

    if (mode === 'idle') {
        icon.innerHTML = `<polygon points="10 8 16 12 10 16 10 8"/><circle cx="12" cy="12" r="10"/>`;
        title.innerText = "Audit Required";
        desc.innerText = "Trigger a complete scan to inspect system telemetry conduits, artificial intelligence indexing, and network leakage surfaces.";
    } else if (mode === 'threats') {
        icon.innerHTML = `<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>`;
        title.innerText = `${vulnCount} Vulnerabilities Detected`;
        desc.innerText = `Active risk vectors: ${vulnCount} (${critCount} critical severity). Enforcing security policies is strongly advised.`;
    } else if (mode === 'secure') {
        icon.innerHTML = `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>`;
        title.innerText = "System Fortified";
        desc.innerText = "All audited vectors conform to maximum exposure mitigation policies. Diagnostic monitors and tracking hooks remain disabled.";
    }
}

async function triggerScan() {
    if (isBusy) return;
    setBusy(true);

    const icon = document.getElementById('scan-icon');
    if (icon) icon.classList.add('animate-spin');

    showToast("Analyzing system parameters and telemetry policies...", "info");

    try {
        if (window.pywebview && window.pywebview.api) {
            const result = await window.pywebview.api.start_full_scan();
            currentIssues = result.issues;
            scanCompleted = true;
            selectedIssueIds.clear();

            if (result.vulnerable_count > 0) {
                setHeroStatus('threats', result.vulnerable_count, result.critical_count);
            } else {
                setHeroStatus('secure', 0, 0);
            }

            renderIssues();
            updateConsole(result.logs);
            showToast(`Audit complete: ${result.vulnerable_count} issues detected`, result.vulnerable_count > 0 ? "warning" : "success");
        }
    } catch (e) {
        showToast("Kernel API fault: " + e, "danger");
    } finally {
        if (icon) icon.classList.remove('animate-spin');
        setBusy(false);
    }
}

function filterCategory(cat) {
    activeCategory = cat;
    ['all', 'telemetry', 'network', 'permissions', 'services', 'artifacts'].forEach(c => {
        const el = document.getElementById(`tab-${c}`);
        if (el) {
            if (c === cat) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        }
    });
    renderIssues();
}

function toggleSelect(id) {
    if (isBusy) return;
    if (selectedIssueIds.has(id)) {
        selectedIssueIds.delete(id);
    } else {
        selectedIssueIds.add(id);
    }
    updateFixSelectedButton();
    renderIssues();
}

function selectAllVulnerable() {
    if (isBusy) return;
    const activeThreats = currentIssues.filter(x => x.status === 'vulnerable');
    activeThreats.forEach(item => {
        selectedIssueIds.add(item.id);
    });
    updateFixSelectedButton();
    renderIssues();
    if (activeThreats.length > 0) {
        showToast(`Selected ${selectedIssueIds.size} vulnerable vectors`, "info");
    }
}

function updateFixSelectedButton() {
    const btn = document.getElementById('btn-fix-selected');
    if (!btn) return;
    if (selectedIssueIds.size > 0 && !isBusy) {
        btn.disabled = false;
        btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg><span>Remediate Selected (${selectedIssueIds.size})</span>`;
    } else {
        btn.disabled = true;
        btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg><span>Remediate Selected</span>`;
    }
}

async function fixSingle(id) {
    if (isBusy) return;
    setBusy(true);
    showToast("Enforcing mitigation policy...", "info");
    try {
        if (window.pywebview && window.pywebview.api) {
            const res = await window.pywebview.api.fix_issue(id);
            if (res.success) {
                const target = currentIssues.find(x => x.id === id);
                if (target) target.status = "secure";
                selectedIssueIds.delete(id);
                updateFixSelectedButton();

                if (res.vulnerable_count > 0) {
                    setHeroStatus('threats', res.vulnerable_count, res.critical_count);
                } else {
                    setHeroStatus('secure', 0, 0);
                }

                renderIssues();
                updateConsole(res.logs);
                showToast("Vector successfully secured", "success");
            } else {
                showToast(res.error || "Policy enforcement denied", "danger");
                updateConsole(res.logs);
            }
        }
    } catch (err) {
        showToast("Execution error: " + err, "danger");
    } finally {
        setBusy(false);
    }
}

async function revertSingle(id) {
    if (isBusy) return;
    setBusy(true);
    showToast("Restoring original configuration...", "info");
    try {
        if (window.pywebview && window.pywebview.api) {
            const res = await window.pywebview.api.revert_issue(id);
            if (res.success) {
                const target = currentIssues.find(x => x.id === id);
                if (target) target.status = res.status;
                selectedIssueIds.delete(id);
                updateFixSelectedButton();

                if (res.vulnerable_count > 0) {
                    setHeroStatus('threats', res.vulnerable_count, res.critical_count);
                } else {
                    setHeroStatus('secure', 0, 0);
                }

                renderIssues();
                updateConsole(res.logs);
                showToast("Baseline configuration restored", "info");
            } else {
                showToast(res.error || "Reversion fault", "danger");
            }
        }
    } catch (err) {
        showToast("Reversion failure: " + err, "danger");
    } finally {
        setBusy(false);
    }
}

async function fixSelected() {
    if (isBusy) return;
    const ids = Array.from(selectedIssueIds);
    if (ids.length === 0) return;

    setBusy(true);
    showToast(`Remediating ${ids.length} selected vectors...`, "info");
    try {
        if (window.pywebview && window.pywebview.api) {
            const res = await window.pywebview.api.fix_all_vulnerabilities(ids);
            if (res.success) {
                currentIssues = res.issues;
                selectedIssueIds.clear();
                updateFixSelectedButton();

                if (res.vulnerable_count > 0) {
                    setHeroStatus('threats', res.vulnerable_count, res.critical_count);
                } else {
                    setHeroStatus('secure', 0, 0);
                }

                renderIssues();
                updateConsole(res.logs);
                showToast(`Remediation complete: ${res.remediated_count} resolved`, "success");
            }
        }
    } catch (err) {
        showToast("Batch operation error: " + err, "danger");
    } finally {
        setBusy(false);
    }
}

function renderIssues() {
    const container = document.getElementById('issues-container');
    if (!scanCompleted) return;

    const itemsToRender = currentIssues.filter(item => {
        if (activeCategory === 'all') return true;
        return item.category === activeCategory;
    });

    if (itemsToRender.length === 0) {
        container.innerHTML = `
            <div class="placeholder-card">
                <p>No active vectors found in the selected category filter.</p>
            </div>`;
        return;
    }

    container.innerHTML = itemsToRender.map(item => {
        const isChecked = selectedIssueIds.has(item.id);
        const isVulnerable = item.status === 'vulnerable';

        let severityBadge = '';
        if (item.severity === 'critical') {
            severityBadge = `<span class="severity-tag severity-critical mono">CRITICAL</span>`;
        } else if (item.severity === 'warning') {
            severityBadge = `<span class="severity-tag severity-warning mono">MEDIUM</span>`;
        } else {
            severityBadge = `<span class="severity-tag severity-low mono">LOW</span>`;
        }

        const safeId = escapeHtml(item.id);
        const safeTitle = escapeHtml(item.title);
        const safeDesc = escapeHtml(item.description);
        const safeImpact = escapeHtml(item.impact);

        const actionBtn = isVulnerable
            ? `<button data-action="fix" data-id="${safeId}" class="btn-fix">
                 <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                 <span>Remediate</span>
               </button>`
            : `<button data-action="revert" data-id="${safeId}" class="btn-revert">
                 <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                 <span>Revert</span>
               </button>`;

        return `
        <div class="issue-card">
            <div class="issue-left">
                ${isVulnerable ? `
                    <div data-toggle-id="${safeId}" class="custom-check ${isChecked ? 'checked' : ''}">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="20 6 9 17 4 12"/>
                        </svg>
                    </div>` : `
                    <div class="issue-status-shield">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="20 6 9 17 4 12"/>
                        </svg>
                    </div>`}

                <div class="issue-details">
                    <div class="issue-header-row">
                        <div class="issue-title">${safeTitle}</div>
                        ${severityBadge}
                    </div>
                    <div class="issue-desc">${safeDesc}</div>
                    <div class="issue-impact mono">
                        Impact: <span>${safeImpact}</span>
                    </div>
                </div>
            </div>

            <div class="issue-actions">
                ${actionBtn}
            </div>
        </div>`;
    }).join('');
}

function toggleConsole() {
    const overlay = document.getElementById('console-overlay');
    if (!overlay) return;
    const isOpen = overlay.classList.toggle('open');
    if (isOpen) {
        const out = document.getElementById('console-output');
        if (out) out.scrollTop = out.scrollHeight;
    }
}

function clearConsole() {
    const out = document.getElementById('console-output');
    out.innerHTML = '';
}

function updateConsole(logs) {
    if (!logs) return;
    const out = document.getElementById('console-output');
    out.innerHTML = logs.map(l => {
        const match = l.match(/^(\[\d{2}:\d{2}:\d{2}\])\s*(.*)$/);
        if (match) {
            return `<div class="log-entry"><span class="log-time">${escapeHtml(match[1])}</span><span class="log-msg">${escapeHtml(match[2])}</span></div>`;
        }
        return `<div class="log-entry"><span class="log-msg">${escapeHtml(l)}</span></div>`;
    }).join('');
    out.scrollTop = out.scrollHeight;
}

function showToast(message, type = "info") {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 250);
    }, 3200);
}
