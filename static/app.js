// Application State
const state = {
    activeTab: 'audit',
    documents: { regulations: [], procedures: [] },
    graphData: { nodes: [], edges: [] },
    networkInstance: null,
    allNodes: null, // vis.DataSet for nodes
    allEdges: null  // vis.DataSet for edges
};

// DOM Elements
const elements = {
    navItems: document.querySelectorAll('.nav-item'),
    tabPanes: document.querySelectorAll('.tab-pane'),
    pageTitle: document.getElementById('page-title'),
    pageSubtitle: document.getElementById('page-subtitle'),
    
    // Audit Tab
    sopSelector: document.getElementById('sop-selector'),
    btnRunAudit: document.getElementById('btn-run-audit'),
    auditStatsCard: document.getElementById('audit-stats-card'),
    auditScoreCircle: document.getElementById('audit-score-circle'),
    auditScoreText: document.getElementById('audit-score-text'),
    auditSummaryDesc: document.getElementById('audit-summary-desc'),
    auditResultsContainer: document.getElementById('audit-results-container'),
    findingsList: document.getElementById('findings-list'),
    
    // Graph Tab
    graphContainer: document.getElementById('graph-container'),
    graphSearch: document.getElementById('graph-search'),
    btnFitGraph: document.getElementById('btn-fit-graph'),
    nodeDetailsContent: document.getElementById('node-details-content'),
    
    // Search Tab
    searchInput: document.getElementById('search-input'),
    btnSearch: document.getElementById('btn-search'),
    searchResultsContainer: document.getElementById('search-results-container'),
    searchResultsList: document.getElementById('search-results-list'),
    
    // Document Tab
    regulationsList: document.getElementById('regulations-list'),
    proceduresList: document.getElementById('procedures-list')
};

// Title and Subtitle Mapping for Tabs
const tabMeta = {
    audit: {
        title: 'SOP Compliance Audit',
        subtitle: 'Evaluate industrial standard operating procedures against federal safety regulations'
    },
    graph: {
        title: 'Safety Knowledge Graph',
        subtitle: 'Explore semantic connections between safety requirements, rules, roles, and equipment'
    },
    search: {
        title: 'Hybrid RAG Search',
        subtitle: 'Search across all rules and standard operating procedures using vector and semantic queries'
    },
    documents: {
        title: 'Document Management',
        subtitle: 'Browse and inspect ingested regulatory guidelines and operating procedures'
    }
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupTabNavigation();
    fetchDocuments();
    setupAuditTab();
    setupSearchTab();
    setupGraphTab();
});

// 1. Tab Navigation
function setupTabNavigation() {
    elements.navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            
            // Update Active Menu State
            elements.navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            // Switch Tab Content Panes
            elements.tabPanes.forEach(pane => pane.classList.remove('active'));
            document.getElementById(`tab-${tabId}`).classList.add('active');
            
            // Update Headers
            state.activeTab = tabId;
            elements.pageTitle.textContent = tabMeta[tabId].title;
            elements.pageSubtitle.textContent = tabMeta[tabId].subtitle;
            
            // Load Graph Tab triggers initialization if needed
            if (tabId === 'graph' && !state.networkInstance) {
                initKnowledgeGraph();
            }
        });
    });
}

// 2. Fetch Ingested Documents
async function fetchDocuments() {
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        state.documents = data;
        
        // Populate Selector
        elements.sopSelector.innerHTML = '<option value="" disabled selected>Choose a Standard Operating Procedure...</option>';
        data.procedures.forEach(proc => {
            const opt = document.createElement('option');
            opt.value = proc;
            opt.textContent = proc.replace(/_/g, ' ').replace('.pdf', '');
            elements.sopSelector.appendChild(opt);
        });
        
        // Populate Lists in Document Manager Tab
        elements.regulationsList.innerHTML = data.regulations.map(reg => `
            <li class="doc-item">
                <div class="doc-info">
                    <i class="fa-solid fa-gavel"></i>
                    <span class="doc-name">${reg.replace(/_/g, ' ').replace('.pdf', '')}</span>
                </div>
                <span class="doc-badge">PDF Standard</span>
            </li>
        `).join('') || '<div class="empty-state"><p>No regulations ingested</p></div>';
        
        elements.proceduresList.innerHTML = data.procedures.map(proc => `
            <li class="doc-item">
                <div class="doc-info">
                    <i class="fa-solid fa-file-lines"></i>
                    <span class="doc-name">${proc.replace(/_/g, ' ').replace('.pdf', '')}</span>
                </div>
                <span class="doc-badge">SOP Document</span>
            </li>
        `).join('') || '<div class="empty-state"><p>No procedures ingested</p></div>';
        
    } catch (error) {
        console.error('Error fetching documents:', error);
    }
}

// 3. SOP Audit Logic
function setupAuditTab() {
    elements.btnRunAudit.addEventListener('click', async () => {
        const selectedSop = elements.sopSelector.value;
        if (!selectedSop) return;
        
        // UI Loading State
        elements.btnRunAudit.disabled = true;
        elements.btnRunAudit.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Auditing...';
        elements.auditStatsCard.style.display = 'none';
        elements.auditResultsContainer.style.display = 'none';
        
        try {
            const response = await fetch('/api/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sop_name: selectedSop })
            });
            
            if (!response.ok) throw new Error('Audit API request failed');
            
            const auditReport = await response.json();
            renderAuditReport(auditReport);
            
        } catch (error) {
            console.error('Error running audit:', error);
            alert('Failed to audit SOP. Make sure ingestion is complete.');
        } finally {
            elements.btnRunAudit.disabled = false;
            elements.btnRunAudit.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Run Audit';
        }
    });
}

function renderAuditReport(report) {
    // Show Score
    elements.auditStatsCard.style.display = 'block';
    elements.auditScoreText.textContent = `${report.compliance_score}%`;
    
    // Set circular progress (conic gradient angle calculation)
    const angle = (report.compliance_score / 100) * 360;
    elements.auditScoreCircle.style.setProperty('--score-angle', `${angle}deg`);
    
    // Adjust colors of score circle based on grade
    let scoreColor = 'var(--success)';
    if (report.compliance_score < 50) scoreColor = 'var(--danger)';
    else if (report.compliance_score < 80) scoreColor = 'var(--major)';
    else if (report.compliance_score < 95) scoreColor = 'var(--warning)';
    
    elements.auditScoreText.style.color = scoreColor;
    elements.auditScoreCircle.style.background = `conic-gradient(${scoreColor} ${angle}deg, rgba(255, 255, 255, 0.05) ${angle}deg)`;
    
    // Set Summary
    elements.auditSummaryDesc.textContent = report.summary;
    
    // Render Findings List
    elements.findingsList.innerHTML = '';
    elements.auditResultsContainer.style.display = 'block';
    
    report.findings.forEach(finding => {
        const card = document.createElement('div');
        const severityClass = finding.severity.toLowerCase();
        card.className = `card glass-card finding-card ${severityClass}`;
        
        const statusBadge = finding.status === 'Compliant' 
            ? `<span class="badge compliant"><i class="fa-solid fa-check-circle"></i> Compliant</span>`
            : `<span class="badge ${severityClass}"><i class="fa-solid fa-triangle-exclamation"></i> ${finding.severity} Gap</span>`;
            
        const isCompliant = finding.status === 'Compliant';
        
        let detailsHtml = '';
        if (!isCompliant) {
            detailsHtml = `
                <div class="violated-rule">
                    <i class="fa-solid fa-ban"></i> <strong>Violated Safety Standard:</strong> ${finding.violated_regulation}
                </div>
                <p class="gap-text"><strong>Issue Found:</strong> ${finding.gap_explanation}</p>
                <div class="rec-block">
                    <h5><i class="fa-solid fa-lightbulb"></i> Recommended Rewrite</h5>
                    <p>${finding.recommendation}</p>
                </div>
            `;
        } else {
            detailsHtml = `
                <div class="violated-rule">
                    <i class="fa-solid fa-circle-check"></i> <strong>Safety Compliance:</strong> ${finding.violated_regulation}
                </div>
                <p class="gap-text">${finding.gap_explanation}</p>
            `;
        }
        
        card.innerHTML = `
            <div class="card-header">
                <span class="sop-clause-ref">${finding.status === 'Compliant' ? 'Verified Compliance' : 'Safety Deviation'}</span>
                ${statusBadge}
            </div>
            <div class="card-body">
                ${detailsHtml}
            </div>
        `;
        
        elements.findingsList.appendChild(card);
    });
}

// 4. Hybrid Search Logic
function setupSearchTab() {
    const runSearch = async () => {
        const query = elements.searchInput.value.trim();
        if (!query) return;
        
        elements.btnSearch.disabled = true;
        elements.btnSearch.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
        
        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, n_results: 5 })
            });
            
            if (!response.ok) throw new Error('Search failed');
            
            const data = await response.json();
            renderSearchResults(data.results);
            
        } catch (error) {
            console.error('Search error:', error);
            alert('Search failed. Make sure ingestion completed.');
        } finally {
            elements.btnSearch.disabled = false;
            elements.btnSearch.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Search';
        }
    };

    elements.btnSearch.addEventListener('click', runSearch);
    elements.searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') runSearch();
    });
}

function renderSearchResults(results) {
    elements.searchResultsContainer.style.display = 'block';
    
    if (results.length === 0) {
        elements.searchResultsList.innerHTML = '<div class="empty-state"><p>No relevant regulatory guidelines matched your query.</p></div>';
        return;
    }
    
    elements.searchResultsList.innerHTML = results.map(res => `
        <div class="card glass-card search-result-card">
            <div class="card-body">
                <div class="search-result-header">
                    <span class="search-result-title">${res.doc_name.replace(/_/g, ' ').replace('.pdf', '')} - ${res.reference}</span>
                    <span class="search-result-meta">${res.doc_type.toUpperCase()}</span>
                </div>
                <p class="search-result-text">${res.text}</p>
                <div class="search-result-source">
                    <i class="fa-solid fa-layer-group"></i> Retrieval Channel: ${res.source}
                </div>
            </div>
        </div>
    `).join('');
}

// 5. Knowledge Graph Rendering
function setupGraphTab() {
    elements.btnFitGraph.addEventListener('click', () => {
        if (state.networkInstance) {
            state.networkInstance.fit({ animation: true });
        }
    });
    
    elements.graphSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!state.networkInstance || !state.allNodes) return;
        
        if (!query) {
            // Reset to defaults
            const updateArray = state.allNodes.get().map(node => {
                node.hidden = false;
                node.opacity = 1.0;
                return node;
            });
            state.allNodes.update(updateArray);
            return;
        }
        
        // Filter nodes
        const updateArray = state.allNodes.get().map(node => {
            const matches = node.label.toLowerCase().includes(query) || 
                            node.title.toLowerCase().includes(query);
            node.opacity = matches ? 1.0 : 0.15;
            return node;
        });
        state.allNodes.update(updateArray);
    });
}

async function initKnowledgeGraph() {
    try {
        const response = await fetch('/api/graph');
        const data = await response.json();
        state.graphData = data;
        
        // Graph Groups Colors & Formatting
        const groups = {
            chunk_regulation: {
                shape: 'box',
                color: { background: '#0284c7', border: '#0ea5e9', highlight: { background: '#0ea5e9', border: '#38bdf8' } },
                font: { color: '#ffffff', face: 'Outfit', size: 12, bold: true },
                borderWidth: 2,
                margin: 10
            },
            chunk_procedure: {
                shape: 'box',
                color: { background: '#ea580c', border: '#f97316', highlight: { background: '#f97316', border: '#fb923c' } },
                font: { color: '#ffffff', face: 'Outfit', size: 12, bold: true },
                borderWidth: 2,
                margin: 10
            },
            entity_equipment: {
                shape: 'dot',
                size: 16,
                color: { background: '#16a34a', border: '#22c55e', highlight: { background: '#22c55e', border: '#4ade80' } },
                font: { color: '#e5e7eb', face: 'Outfit', size: 11 }
            },
            entity_hazard: {
                shape: 'dot',
                size: 16,
                color: { background: '#dc2626', border: '#ef4444', highlight: { background: '#ef4444', border: '#f87171' } },
                font: { color: '#e5e7eb', face: 'Outfit', size: 11 }
            },
            entity_role: {
                shape: 'dot',
                size: 16,
                color: { background: '#ca8a04', border: '#eab308', highlight: { background: '#eab308', border: '#facc15' } },
                font: { color: '#e5e7eb', face: 'Outfit', size: 11 }
            },
            entity_procedure: {
                shape: 'dot',
                size: 16,
                color: { background: '#9333ea', border: '#a855f7', highlight: { background: '#a855f7', border: '#c084fc' } },
                font: { color: '#e5e7eb', face: 'Outfit', size: 11 }
            },
            entity_permit_type: {
                shape: 'dot',
                size: 16,
                color: { background: '#0891b2', border: '#06b6d4', highlight: { background: '#06b6d4', border: '#22d3ee' } },
                font: { color: '#e5e7eb', face: 'Outfit', size: 11 }
            },
            entity_unknown: {
                shape: 'dot',
                size: 14,
                color: { background: '#4b5563', border: '#6b7280' },
                font: { color: '#e5e7eb', face: 'Outfit', size: 11 }
            }
        };
        
        // Instantiate datasets
        state.allNodes = new vis.DataSet(data.nodes);
        state.allEdges = new vis.DataSet(data.edges);
        
        const graphContainer = elements.graphContainer;
        graphContainer.innerHTML = ''; // Clear loading screen
        
        const graphDataInput = {
            nodes: state.allNodes,
            edges: state.allEdges
        };
        
        const options = {
            groups: groups,
            nodes: {
                shadow: { enabled: true, color: 'rgba(0,0,0,0.3)', size: 4, x: 2, y: 2 }
            },
            edges: {
                color: { color: 'rgba(255,255,255,0.12)', highlight: 'var(--primary)', hover: 'rgba(255,255,255,0.3)' },
                width: 1.5,
                smooth: { type: 'continuous' }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: true
            },
            physics: {
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -35,
                    centralGravity: 0.015,
                    springLength: 90,
                    springConstant: 0.04,
                    damping: 0.8
                },
                stabilization: {
                    iterations: 150,
                    updateInterval: 25
                }
            }
        };
        
        // Render network
        state.networkInstance = new vis.Network(graphContainer, graphDataInput, options);
        
        // Handle click selection
        state.networkInstance.on('selectNode', (params) => {
            const nodeId = params.nodes[0];
            const nodeData = state.allNodes.get(nodeId);
            
            // Match with original NetworkX graph payload nodes to build deep details
            const matchedNode = data.nodes.find(n => n.id === nodeId);
            
            if (matchedNode) {
                renderNodeInspector(matchedNode);
            }
        });
        
        // Handle deselect
        state.networkInstance.on('deselectNode', () => {
            elements.nodeDetailsContent.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-mouse-pointer"></i>
                    <p>Click any node in the graph network to inspect its relationships and details</p>
                </div>
            `;
        });
        
    } catch (error) {
        console.error('Error loading graph:', error);
        elements.graphContainer.innerHTML = `
            <div class="empty-state" style="color: var(--danger);">
                <i class="fa-solid fa-circle-xmark"></i>
                <p>Failed to load knowledge graph. Verify database files exist.</p>
            </div>
        `;
    }
}

function renderNodeInspector(node) {
    const isChunk = node.group.startsWith('chunk_');
    const badgeType = node.group.replace('chunk_', '').replace('entity_', '');
    
    let contentHtml = '';
    
    if (isChunk) {
        // Retrieve title/description from Vis.js tooltip details
        const detailsPattern = /Document:\s*(.*?)\nSection:\s*(.*?)\n\n([\s\S]*)/;
        const match = node.title.match(detailsPattern);
        
        const docName = match ? match[1] : 'Unknown';
        const reference = match ? match[2] : node.label;
        const text = match ? match[3] : '';
        
        contentHtml = `
            <div class="inspector-data">
                <h4>${reference}</h4>
                <span class="badge ${badgeType === 'regulation' ? 'compliant' : 'major'}">${badgeType.toUpperCase()} PASSAGE</span>
                
                <span class="inspector-label">Source File</span>
                <span class="inspector-val">${docName}</span>
                
                <span class="inspector-label">Content</span>
                <div class="inspector-text-block">${text}</div>
            </div>
        `;
    } else {
        contentHtml = `
            <div class="inspector-data">
                <h4>${node.label}</h4>
                <span class="badge compliant">${badgeType.toUpperCase()} CONCEPT</span>
                
                <span class="inspector-label">Category</span>
                <span class="inspector-val" style="text-transform: capitalize;">${badgeType.replace('_', ' ')}</span>
                
                <span class="inspector-label">Graph Connections</span>
                <p class="gap-text">Connected to safety documents containing references to "${node.label}"</p>
            </div>
        `;
    }
    
    elements.nodeDetailsContent.innerHTML = contentHtml;
}
