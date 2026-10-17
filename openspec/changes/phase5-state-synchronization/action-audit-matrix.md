# Phase 5 action audit supplement

Current snapshot: 281 source controls across 49 files. Prior phase matrices remain historical checkpoints. Run `node frontend/scripts/audit-phase5-actions.mjs --check` for current drift.

| Owner | Action / authority / feedback | Regression coverage |
| --- | --- | --- |
| DraftConflict | Compare/export, check server, retain tab draft, confirmed discard, explicit non-overlapping rebase. Reads require existing workflow.view/session controls; no save or release effect. Busy lock/errors, overlap paths and in-flight reload guard. | phase5-sync.test.tsx; phase5.spec.ts desktop/mobile/two tabs |
| WorkflowControls | Existing explicit lifecycle actions; exact confirmed baseline, fresh Registry notice, unknown-outcome feedback and stale error clearing. Server permissions/idempotency unchanged. | Phase 3/4/5 unit/browser suites; test_phase5_state.py and actual PostgreSQL |
| RunWorkflowDialog | Canonical field feedback and retained unknown-outcome inputs. Exact published schema/execute authority; no uncertain automatic replay. | phase3-actions.test.tsx; phase5-sync.test.tsx; prior typed-run browser scenarios |
| Monitoring | Validated authenticated read, non-overlapping refresh, safe structured errors; no mutation. | app.monitoring.test.tsx; phase5-sync.test.tsx |
| Editor / draft storage | Focus and bounded exact-revision checks; independent tab recovery, unchanged-read no-op, explicit storage failure/export. No role or grant authority from storage. | phase5-sync.test.tsx; phase5.spec.ts two-tab/lost-response/reload |

## Current source inventory

| File:line | Control | Handler / disabled |
| --- | --- | --- |
| frontend/src/components/mesh/Logo.tsx:17 | Link | Native or caller delegated; disabled=None |
| frontend/src/components/ui/calendar.tsx:153 | Button | Native or caller delegated; disabled=None |
| frontend/src/components/ui/carousel.tsx:120 | div | onKeyDownCapture={handleKeyDown}; disabled=None |
| frontend/src/components/ui/carousel.tsx:182 | Button | onClick={scrollPrev}; disabled={!canScrollPrev} |
| frontend/src/components/ui/carousel.tsx:210 | Button | onClick={scrollNext}; disabled={!canScrollNext} |
| frontend/src/components/ui/input.tsx:8 | input | Native or caller delegated; disabled=None |
| frontend/src/components/ui/pagination.tsx:35 | a | Native or caller delegated; disabled=None |
| frontend/src/components/ui/sidebar.tsx:191 | Sheet | onOpenChange={setOpenMobile}; disabled=None |
| frontend/src/components/ui/sidebar.tsx:267 | Button | onClick={(event) => {         onClick?.(event);         toggleSidebar();       }}; disabled=None |
| frontend/src/components/ui/sidebar.tsx:291 | button | onClick={toggleSidebar}; disabled=None |
| frontend/src/components/ui/sidebar.tsx:336 | Input | Native or caller delegated; disabled=None |
| frontend/src/components/ui/textarea.tsx:8 | textarea | Native or caller delegated; disabled=None |
| frontend/src/features/agents/AgentControlsCard.tsx:40 | Switch | onCheckedChange={(v) => setPaused(agent.id, !v)}; disabled={!allowed} |
| frontend/src/features/agents/AgentControlsCard.tsx:43 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/agents/AgentControlsCard.tsx:47 | input | onChange={(e) => update(agent.id, { budgetUsd: e.target.value === "" ? null : Math.max(0, Number(e.target.value)) })}; onBlur={() => audited("Set agent budget", `${agent.name} → ${agent.budgetUsd == null ? "no cap" : `$${agent.budgetUsd}`}`)}; disabled={!allowed} |
| frontend/src/features/agents/AgentControlsCard.tsx:58 | Switch | onCheckedChange={(v) => { update(agent.id, { requireApproval: v }); audited(v ? "Required approval for agent" : "Removed agent approval", agent.name); }}; disabled={!allowed} |
| frontend/src/features/agents/AgentControlsCard.tsx:62 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:44 | TabsTrigger | Native or caller delegated; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:49 | input | onChange={(e) => set({ name: e.target.value })}; disabled={agent.origin === "backend"} |
| frontend/src/features/agents/AgentInspector.tsx:50 | input | onChange={(e) => set({ role: e.target.value })}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:51 | textarea | onChange={(e) => set({ purpose: e.target.value })}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:52 | textarea | onChange={(e) => set({ instructions: e.target.value })}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:64 | button | onClick={() => pickModel(m.id)}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:79 | Slider | onValueChange={([v]) => set({ temperature: v ?? 0 })}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:81 | button | onClick={() => setAdvanced((a) => !a)}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:86 | input | onChange={(e) => set({ maxTokens: Math.max(64, Number(e.target.value) \|\| 64) })}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:88 | select | onChange={(e) => set({ fallbackModelId: e.target.value })}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:93 | select | onChange={(e) => set({ memory: e.target.value as Agent["memory"] })}; disabled={agent.origin === "backend"} |
| frontend/src/features/agents/AgentInspector.tsx:97 | textarea | onChange={(e) => set({ outputSchema: e.target.value })}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:113 | Switch | onCheckedChange={() => toggle("tools", t)}; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:116 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:123 | Switch | onCheckedChange={() => toggle("knowledge", k.name)}; disabled={k.status === "failed"} |
| frontend/src/features/agents/AgentInspector.tsx:126 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/agents/AgentInspector.tsx:138 | Switch | onCheckedChange={(v) => set({ guardrails: { ...agent.guardrails, [k]: v } })}; disabled={agent.origin === "backend"} |
| frontend/src/features/builder/AgentCommunication.tsx:35 | Dialog | onOpenChange={setOpen}; disabled=None |
| frontend/src/features/builder/AgentCommunication.tsx:36 | DialogTrigger | Native or caller delegated; disabled=None |
| frontend/src/features/builder/AgentCommunication.tsx:110 | select | onChange={(e) => setMode(e.target.value as "configured" \| "run")}; disabled=None |
| frontend/src/features/builder/AgentCommunication.tsx:122 | select | onChange={(e) => trace.selectRun(e.target.value)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:457 | button | onClick={() => { setMode(view); setPanel(null); }}; disabled=None |
| frontend/src/features/builder/Builder.tsx:460 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/builder/Builder.tsx:461 | RevisionHistory | onClose={() => setHistoryOpen(false)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:464 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/builder/Builder.tsx:471 | input | onChange={(e) => store.renameWorkflow(workflow.id, e.target.value)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:486 | button | onClick={undo}; disabled={!past.length} |
| frontend/src/features/builder/Builder.tsx:494 | button | onClick={redo}; disabled={!future.length} |
| frontend/src/features/builder/Builder.tsx:503 | DropdownMenuTrigger | Native or caller delegated; disabled=None |
| frontend/src/features/builder/Builder.tsx:511 | DropdownMenuItem | onSelect={() => addNode(k)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:522 | DropdownMenuItem | onSelect={() => insertPatternAt(p.id)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:536 | DropdownMenuItem | onSelect={() => addNode("agent", a.id)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:543 | DropdownMenuTrigger | Native or caller delegated; disabled=None |
| frontend/src/features/builder/Builder.tsx:550 | DropdownMenuItem | onSelect={tidy}; disabled=None |
| frontend/src/features/builder/Builder.tsx:554 | DropdownMenuItem | onSelect={() => {                 const id = store.duplicateWorkflow(workflow.id);                 if (id) navigate({ to: "/app/workflows/$id", params: { id } });               }}; disabled=None |
| frontend/src/features/builder/Builder.tsx:567 | DropdownMenuItem | onSelect={() => setHistoryOpen(true)}; disabled={!current.serverVersion} |
| frontend/src/features/builder/Builder.tsx:573 | DropdownMenuItem | onSelect={() => { setMode("execution"); setPanel(null); }}; disabled=None |
| frontend/src/features/builder/Builder.tsx:580 | GraphTools | onSelect={id => { setSelectedId(id);  setPanel("inspector"); }}; onConnect={(source,target,label) => {         if (edgesRef.current.some(e => e.source === source && (label ? e.label === label : e.target === target))) { toast.error("This connection or branch outcome is already used. Remove it before reconnecting."); return; }         commit({nodes:clean(nodesRef.current),edges:[...edgesRef.current,{id:uid("edge"),source,target,...(label?{label}:{})}]});       }}; onRemove={id => { if(window.confirm("Remove this connection from the working draft?")) commit({nodes:clean(nodesRef.current),edges:edgesRef.current.filter(e=>e.id!==id)}); }}; disabled=None |
| frontend/src/features/builder/Builder.tsx:585 | ExecutionView | onDesign={() => setMode("design")}; disabled=None |
| frontend/src/features/builder/Builder.tsx:585 | HierarchyView | onEdit={id=>{setMode("design");setSelectedId(id);setPanel("inspector");}}; disabled=None |
| frontend/src/features/builder/Builder.tsx:596 | button | onClick={() => {                         setSelectedId(n.id);                          setPanel("inspector");                       }}; disabled=None |
| frontend/src/features/builder/Builder.tsx:624 | PatternsPanel | onInsert={(k) => insertPatternAt(k)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:625 | ReactFlow | onDragOver={(e) => {                   if (e.dataTransfer.types.includes(PATTERN_MIME)) {                     e.preventDefault();                     e.dataTransfer.dropEffect = "copy";                   }                 }}; onDrop={onDrop}; onNodesChange={onNodesChange}; onEdgesChange={onEdgesChange}; onConnect={onConnect}; onNodeDragStart={() => { dragStart.current = structuredClone({nodes:clean(nodesRef.current),edges:edgesRef.current}); }}; onNodeDragStop={() => {                   if (dragStart.current) { const previous = dragStart.current; setPast(p=>[...p.slice(-49),previous]); setFuture([]); dragStart.current=null; }                   commit({ nodes: nodesRef.current, edges: edgesRef.current }, {history:false});                 }}; onNodeClick={(_, n) => {                   setSelectedId(n.id);                    setPanel("inspector");                 }}; onPaneClick={() => {                   setSelectedId(null);                   setPanel((p) => (p === "inspector" ? null : p));                 }}; disabled=None |
| frontend/src/features/builder/Builder.tsx:665 | Controls | Native or caller delegated; disabled=None |
| frontend/src/features/builder/Builder.tsx:683 | button | onClick={() => setComposerOpen((o) => !o)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:698 | form | onSubmit={(e) => {                       e.preventDefault();                       runCommand();                     }}; disabled=None |
| frontend/src/features/builder/Builder.tsx:705 | input | onChange={(e) => setCmd(e.target.value)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:712 | button | Native or caller delegated; disabled=None |
| frontend/src/features/builder/Builder.tsx:721 | button | onClick={() => runCommand(c)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:752 | input | onChange={(e) => updateNodeData({ label: e.target.value })}; disabled=None |
| frontend/src/features/builder/Builder.tsx:758 | button | onClick={() => onNodesChange([{ type: "remove", id: selected.id }])}; disabled=None |
| frontend/src/features/builder/Builder.tsx:765 | button | onClick={() => setPanel(null)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:777 | HierarchyBox | onSelect={(id) => setSelectedId(id)}; onAdd={() => addChild(selected.id)}; onRemove={() => removeChild(selected.id)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:787 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/builder/Builder.tsx:807 | textarea | onChange={(e) => updateNodeData({ description: e.target.value })}; disabled=None |
| frontend/src/features/builder/Builder.tsx:817 | input | onChange={(e) => updateNodeData({ condition: { condition_id: String(selected.data["conditionId"] ?? `condition_${selected.id}`), outcomes: (selected.data["condition"] as { outcomes?: string[] } \| undefined)?.outcomes ?? ["critical", "standard"], expression: e.target.value } })}; disabled=None |
| frontend/src/features/builder/Builder.tsx:818 | input | onChange={(e) => updateNodeData({ condition: { condition_id: String(selected.data["conditionId"] ?? `condition_${selected.id}`), expression: String((selected.data["condition"] as { expression?: string } \| undefined)?.expression ?? ""), outcomes: e.target.value.split(",").map((value) => value.trim()).filter(Boolean) } })}; disabled=None |
| frontend/src/features/builder/Builder.tsx:876 | button | onClick={onRemove}; disabled=None |
| frontend/src/features/builder/Builder.tsx:887 | button | onClick={() => onSelect(parent.id)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:896 | button | onClick={() => onSelect(k.id)}; disabled=None |
| frontend/src/features/builder/Builder.tsx:906 | button | onClick={onAdd}; disabled=None |
| frontend/src/features/builder/CommunicationDiagram.tsx:38 | div | onKeyDown={(e) => {         if (e.key === "Enter" \|\| e.key === " ") {           e.preventDefault();           data.inspect();         }       }}; disabled=None |
| frontend/src/features/builder/CommunicationDiagram.tsx:111 | button | onClick={(e) => {             e.stopPropagation();             data?.inspect();           }}; disabled=None |
| frontend/src/features/builder/CommunicationDiagram.tsx:218 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/builder/CommunicationDiagram.tsx:282 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/builder/CommunicationDiagram.tsx:349 | ReactFlow | onNodeClick={(_, node) => setSelection({ kind: "node", id: node.id })}; onEdgeClick={(_, edge) => setSelection({ kind: "connection", id: edge.id })}; onPaneClick={() => setSelection(undefined)}; disabled=None |
| frontend/src/features/builder/CommunicationDiagram.tsx:366 | Controls | Native or caller delegated; disabled=None |
| frontend/src/features/builder/CommunicationDiagram.tsx:375 | button | onClick={() => setSelection(undefined)}; disabled=None |
| frontend/src/features/builder/CommunicationEvidence.tsx:16 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/builder/ExecutionView.tsx:55 | select | onChange={(e) => {             setSelected("");             trace.selectRun(e.target.value);           }}; disabled={!trace.available \|\| !trace.runs.length} |
| frontend/src/features/builder/ExecutionView.tsx:73 | button | onClick={trace.retry}; disabled={trace.loading} |
| frontend/src/features/builder/ExecutionView.tsx:81 | button | onClick={onDesign}; disabled=None |
| frontend/src/features/builder/ExecutionView.tsx:110 | ReactFlow | onNodeClick={(_, n) => setSelected(n.id)}; disabled=None |
| frontend/src/features/builder/ExecutionView.tsx:126 | Controls | Native or caller delegated; disabled=None |
| frontend/src/features/builder/ExecutionView.tsx:138 | button | onClick={() => setSelected(n.id)}; disabled=None |
| frontend/src/features/builder/ExecutionView.tsx:156 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:30 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:43 | button | onClick={() => onSelect(x.nodeId!)}; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:63 | button | onClick={() => onSelect(n.id)}; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:74 | form | onSubmit={(e) => {           e.preventDefault();           if (source && target && (!outcomes.length \|\| label))             onConnect(source, target, label \|\| undefined);         }}; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:84 | select | onChange={(e) => {               setSource(e.target.value);               setLabel("");             }}; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:105 | select | onChange={(e) => setTarget(e.target.value)}; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:124 | select | onChange={(e) => setLabel(e.target.value)}; disabled=None |
| frontend/src/features/builder/GraphTools.tsx:137 | button | Native or caller delegated; disabled={!source \|\| !target \|\| (outcomes.length > 0 && !label)} |
| frontend/src/features/builder/GraphTools.tsx:151 | button | onClick={() => onRemove(e.id)}; disabled=None |
| frontend/src/features/builder/HierarchyView.tsx:93 | button | onClick={() => onEdit(row.node!.id)}; disabled=None |
| frontend/src/features/builder/HierarchyView.tsx:101 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/builder/MeshNode.tsx:66 | button | onClick={(e) => { e.stopPropagation(); actions.toggleCollapse(id); }}; disabled=None |
| frontend/src/features/builder/NodeTrace.tsx:37 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/builder/PatternsPanel.tsx:13 | button | onClick={() => setOpen(true)}; disabled=None |
| frontend/src/features/builder/PatternsPanel.tsx:22 | button | onClick={() => setOpen(false)}; disabled=None |
| frontend/src/features/builder/PatternsPanel.tsx:29 | button | onDragStart={(e) => { e.dataTransfer.setData(PATTERN_MIME, p.id); e.dataTransfer.effectAllowed = "copy"; }}; onClick={() => onInsert(p.id)}; disabled=None |
| frontend/src/features/governance/AgentControlTab.tsx:51 | Switch | onCheckedChange={(v) => set(scope, { executionEnabled: v })}; disabled={!allowed} |
| frontend/src/features/governance/AgentControlTab.tsx:56 | input | onBlur={(e) => { const v = Number(e.target.value); if (!Number.isFinite(v) \|\| v < 0) { toast.error("Enter a number of 0 or more"); e.target.value = String(c[n.key]); return; } if (v !== c[n.key]) set(scope, { [n.key]: v }); }}; onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}; disabled={!allowed} |
| frontend/src/features/governance/AgentControlTab.tsx:67 | Switch | onCheckedChange={(v) => set(scope, { approvalForSensitive: v })}; disabled={!allowed} |
| frontend/src/features/governance/AgentControlTab.tsx:70 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/governance/AgentControlTab.tsx:71 | Switch | onCheckedChange={(v) => set(scope, { allowedTools: v ? [...TOOL_CATALOG] : null })}; disabled={!allowed} |
| frontend/src/features/governance/AgentControlTab.tsx:76 | button | onClick={() => set(scope, { allowedTools: on ? c.allowedTools!.filter((x) => x !== t) : [...c.allowedTools!, t] })}; disabled={!allowed} |
| frontend/src/features/governance/AgentControlTab.tsx:84 | button | onClick={() => set(scope, { blockedModels: on ? c.blockedModels.filter((x) => x !== m.id) : [...c.blockedModels, m.id] })}; disabled={!allowed} |
| frontend/src/features/governance/UsageTab.tsx:55 | button | onClick={() => setSort((s) => ({ key: k, dir: s.key === k ? (s.dir === 1 ? -1 : 1) : k === "cost" \|\| k === "runs" ? -1 : 1 }))}; disabled=None |
| frontend/src/features/governance/UsageTab.tsx:71 | input | onChange={(e) => setQ(e.target.value)}; disabled=None |
| frontend/src/features/governance/UsageTab.tsx:74 | select | onChange={(e) => setStatus(e.target.value as typeof status)}; disabled=None |
| frontend/src/features/governance/UsageTab.tsx:96 | button | onClick={() => setAgentPaused(r.agent.id, !r.agent.paused)}; disabled={!mayControl} |
| frontend/src/features/governance/UsageTab.tsx:97 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/landing/cinematic/CinematicHero.tsx:40 | EngineScene | onContextLost={() => setLost(true)}; onFirstFrame={() => setShown(true)}; disabled=None |
| frontend/src/features/landing/cinematic/CinematicHero.tsx:100 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/landing/cinematic/EngineScene.tsx:426 | Canvas | onCreated={({ gl }) => {         gl.toneMapping = THREE.ACESFilmicToneMapping;         gl.toneMappingExposure = 0.95;         gl.domElement.addEventListener("webglcontextlost", (e) => {           e.preventDefault();           onContextLost();         });       }}; disabled=None |
| frontend/src/features/landing/cinematic/EngineScene.tsx:442 | FirstFrame | onReady={onFirstFrame}; disabled=None |
| frontend/src/features/runs/ReplyCases.tsx:67 | button | onClick={() => void refresh()}; disabled={refreshing \|\| busy} |
| frontend/src/features/runs/ReplyCases.tsx:88 | button | onClick={() => void act(item.case_id, reply.reply_id, kind)}; disabled={busy \|\| !backend.can("workflow.approve")} |
| frontend/src/features/runs/ServerRunView.tsx:30 | button | onClick={() => void decide(decision)}; disabled={busy} |
| frontend/src/features/runs/ServerRunView.tsx:95 | button | onClick={() => void loadRun(item.run_id)}; disabled={busy} |
| frontend/src/features/runs/ServerRunView.tsx:100 | form | onSubmit={(event) => { event.preventDefault(); void load(); }}; disabled=None |
| frontend/src/features/runs/ServerRunView.tsx:101 | input | onChange={(event) => setRunId(event.target.value)}; disabled={busy} |
| frontend/src/features/runs/ServerRunView.tsx:102 | button | Native or caller delegated; disabled={busy \|\| !runId.trim()} |
| frontend/src/features/runs/ServerRunView.tsx:110 | ApprovalControl | onUpdated={() => void loadRun(run.run_id)}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:29 | CommandDialog | onOpenChange={onOpenChange}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:34 | CommandItem | onSelect={() => go(() => navigate({ to: "/app" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:39 | CommandItem | onSelect={() => go(() => navigate({ to: "/app" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:40 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/workflows" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:41 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/agents" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:42 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/marketplace" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:43 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/integrations" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:44 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/knowledge" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:45 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/approvals" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:46 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/runs" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:47 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/monitoring" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:48 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/governance" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:49 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/settings" }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:54 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/workflows/$id", params: { id: w.id } }))}; disabled=None |
| frontend/src/features/shell/CommandPalette.tsx:63 | CommandItem | onSelect={() => go(() => navigate({ to: "/app/agents", search: { agent: a.id } }))}; disabled=None |
| frontend/src/features/shell/Shortcuts.tsx:49 | Dialog | onOpenChange={onOpenChange}; disabled=None |
| frontend/src/features/workflows/ApiFeedback.tsx:21 | button | onClick={onRetry}; disabled={retrying} |
| frontend/src/features/workflows/CustomerAutomationReview.tsx:8 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/DraftConflict.tsx:103 | button | onClick={() =>               useMesh.setState((s) => ({                 workflows: s.workflows.map((w) =>                   w.id === workflow.id ? { ...w, tabConflict: undefined } : w,                 ),               }))             }; disabled=None |
| frontend/src/features/workflows/DraftConflict.tsx:117 | button | onClick={() => void run("check")}; disabled={busy} |
| frontend/src/features/workflows/DraftConflict.tsx:125 | button | onClick={() => void run("rebase")}; disabled={busy \|\| !workflow.remote \|\| !workflow.canonical} |
| frontend/src/features/workflows/DraftConflict.tsx:133 | button | onClick={() => void run("reload")}; disabled={busy} |
| frontend/src/features/workflows/DraftConflict.tsx:141 | button | onClick={() => {             try {               const state = useMesh.getState();               setExported(                 JSON.stringify(                   {                     format: "mesh-working-draft-recovery-v1",                     workflow,                     agents: state.agents.filter((a) => ownsAgent(workflow, a)),                   },                   null,                   2,                 ),               );             } catch (caught) {               setError(caught instanceof Error ? caught : new Error("Export unavailable."));             }           }}; disabled=None |
| frontend/src/features/workflows/DraftConflict.tsx:168 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/DraftConflict.tsx:178 | textarea | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/LifecycleJourney.tsx:201 | button | onClick={() => setAttempt((n) => n + 1)}; disabled=None |
| frontend/src/features/workflows/LifecycleJourney.tsx:206 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/LifecycleJourney.tsx:232 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/LifecycleJourney.tsx:236 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/LifecycleJourney.tsx:240 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/PlanReview.tsx:76 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/PlanReview.tsx:96 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/ProcurementReview.tsx:98 | input | onChange={e => change({ ...value, [field]: e.target.value })}; disabled={disabled} |
| frontend/src/features/workflows/ProcurementReview.tsx:100 | input | onChange={e => change({ ...value, [field]: Number(e.target.value) })}; disabled={disabled} |
| frontend/src/features/workflows/ProcurementReview.tsx:101 | input | onChange={e => change({ ...value, allow_delivery_reschedule: e.target.checked })}; disabled={disabled} |
| frontend/src/features/workflows/ProcurementReview.tsx:105 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/ProcurementReview.tsx:109 | button | onClick={e => e.currentTarget.closest("details")?.removeAttribute("open")}; disabled=None |
| frontend/src/features/workflows/ProcurementReview.tsx:118 | input | onChange={e => setDraft({ ...draft, [kind]: { ...source, range: e.target.value } })}; disabled={!editable \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:121 | input | onChange={e => setDraft({ ...draft, [kind]: { ...source, columns: { ...source.columns, [field]: e.target.value } } })}; disabled={!editable \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:125 | input | onChange={e => setDraft({ ...draft, context: { ...draft.context, [field]: e.target.value \|\| null } })}; disabled={!editable \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:131 | input | onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, calendar_id: e.target.value } })}; disabled={!editable \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:133 | input | onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, reminder_minutes: Number(e.target.value) } })}; disabled={!editable \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:135 | input | onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, purchasing_limit: e.target.value \|\| null } })}; disabled={!editable \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:137 | input | onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, allow_single_offer: e.target.checked } })}; disabled={!editable \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:141 | input | onChange={e => setDraft({ ...draft, phase3: e.target.checked ? fulfilment : null })}; disabled=None |
| frontend/src/features/workflows/ProcurementReview.tsx:144 | button | onClick={() => void save()}; disabled={busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:150 | button | onClick={() => void start()}; disabled={busy \|\| !publishedVersion \|\| !backend.can("workflow.execute") \|\| !backend.session?.runtime_available} |
| frontend/src/features/workflows/ProcurementReview.tsx:151 | button | onClick={() => void load()}; disabled={busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:162 | button | onClick={() => void activateFulfilment()}; disabled={busy \|\| !backend.can("workflow.approve") \|\| !fulfilment.buyer_email \|\| !fulfilment.manager_email} |
| frontend/src/features/workflows/ProcurementReview.tsx:178 | input | onChange={e => setSelected(e.target.checked ? [...selected, c.candidate_id] : selected.filter(id => id !== c.candidate_id))}; disabled={!c.email \|\| busy} |
| frontend/src/features/workflows/ProcurementReview.tsx:181 | a | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/ProcurementReview.tsx:184 | button | onClick={() => void reviewSuppliers("approved")}; disabled={busy \|\| !backend.can("workflow.approve")} |
| frontend/src/features/workflows/ProcurementReview.tsx:185 | button | onClick={() => void reviewSuppliers("rejected")}; disabled={busy \|\| !backend.can("workflow.approve")} |
| frontend/src/features/workflows/ProcurementReview.tsx:188 | a | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/ProcurementReview.tsx:190 | a | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/RevisionHistory.tsx:18 | Dialog | onOpenChange={value => { if (!value) onClose(); }}; disabled=None |
| frontend/src/features/workflows/RevisionHistory.tsx:19 | form | onSubmit={event => { event.preventDefault(); void load(); }}; disabled=None |
| frontend/src/features/workflows/RevisionHistory.tsx:19 | input | onChange={event => setVersion(event.target.value)}; disabled=None |
| frontend/src/features/workflows/RevisionHistory.tsx:19 | button | Native or caller delegated; disabled={busy} |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:33 | Dialog | onOpenChange={open => { if (!open && !submitting.current) onClose(); }}; disabled=None |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:34 | DialogContent | onEscapeKeyDown={event => { if (busy) event.preventDefault(); }}; onPointerDownOutside={event => { if (busy) event.preventDefault(); }}; disabled=None |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:37 | form | onSubmit={event => { event.preventDefault(); void submit(); }}; disabled=None |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:39 | select | onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))}; disabled={busy} |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:40 | textarea | onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))}; disabled={busy} |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:41 | input | onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))}; disabled={busy} |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:44 | button | Native or caller delegated; disabled={busy \|\| !!blocker} |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:47 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/RunWorkflowDialog.tsx:48 | button | onClick={onClose}; disabled={busy} |
| frontend/src/features/workflows/SheetAccessReview.tsx:21 | summary | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/SheetAccessReview.tsx:26 | a | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/WorkflowControls.tsx:85 | button | onClick={() => void act(action)}; disabled={!!busy \|\| !!reason} |
| frontend/src/features/workflows/WorkflowControls.tsx:88 | button | onClick={() => void act("reload")}; disabled={!!busy \|\| !!blocker("reload")} |
| frontend/src/features/workflows/WorkflowReviewQueue.tsx:35 | Link | Native or caller delegated; disabled=None |
| frontend/src/features/workflows/WorkflowReviewQueue.tsx:36 | button | onClick={() => void approve(workflow)}; disabled={!!busy \|\| !backend.can("workflow.approve")} |
| frontend/src/screens/app.agents.tsx:31 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.agents.tsx:32 | button | onClick={() => navigate({ search: { agent: createAgent() } })}; disabled=None |
| frontend/src/screens/app.agents.tsx:37 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.agents.tsx:46 | button | onClick={() => navigate({ search: { agent: a.id } })}; disabled=None |
| frontend/src/screens/app.agents.tsx:55 | button | onClick={() => setPaused(a.id, !a.paused)}; disabled={!mayControl} |
| frontend/src/screens/app.governance.tsx:51 | Switch | onCheckedChange={(v) => upsertPolicy({ ...p, enabled: v })}; disabled={!allowed} |
| frontend/src/screens/app.governance.tsx:52 | button | onClick={() => { if (window.confirm(`Delete local policy draft "${p.name}"?`)) removePolicy(p.id); }}; disabled=None |
| frontend/src/screens/app.governance.tsx:64 | TabsTrigger | Native or caller delegated; disabled=None |
| frontend/src/screens/app.governance.tsx:64 | TabsTrigger | Native or caller delegated; disabled=None |
| frontend/src/screens/app.governance.tsx:64 | TabsTrigger | Native or caller delegated; disabled=None |
| frontend/src/screens/app.governance.tsx:64 | TabsTrigger | Native or caller delegated; disabled=None |
| frontend/src/screens/app.governance.tsx:64 | TabsTrigger | Native or caller delegated; disabled=None |
| frontend/src/screens/app.governance.tsx:73 | select | onChange={(e) => setType(e.target.value as PolicyRule["type"])}; disabled=None |
| frontend/src/screens/app.governance.tsx:74 | select | onChange={(e) => setModelId(e.target.value)}; disabled=None |
| frontend/src/screens/app.governance.tsx:75 | select | onChange={(e) => setGuard(e.target.value as GuardrailKey)}; disabled=None |
| frontend/src/screens/app.governance.tsx:76 | input | onChange={(e) => setUsd(e.target.value)}; disabled=None |
| frontend/src/screens/app.governance.tsx:77 | button | onClick={add}; disabled=None |
| frontend/src/screens/app.index.tsx:71 | textarea | onChange={(e) => setDescription(e.target.value)}; disabled=None |
| frontend/src/screens/app.index.tsx:73 | select | onChange={e=>setInputMode(e.target.value as "automatic" \| "manual")}; disabled={planning} |
| frontend/src/screens/app.index.tsx:77 | button | onClick={() => void cancel()}; disabled={cancelling} |
| frontend/src/screens/app.index.tsx:78 | button | onClick={() => void generate()}; disabled={planning \|\| !description.trim()} |
| frontend/src/screens/app.index.tsx:83 | button | onClick={openResult}; disabled={planning} |
| frontend/src/screens/app.index.tsx:84 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.index.tsx:84 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.integrations.tsx:33 | button | onClick={() => void check(provider, "configuration")}; disabled={pending[provider] \|\| !backend.can("tools.read")} |
| frontend/src/screens/app.integrations.tsx:34 | button | onClick={() => void check(provider, "connection")}; disabled={pending[provider] \|\| !admin \|\| !result.configured} |
| frontend/src/screens/app.knowledge.tsx:19 | button | onClick={() => { setLoading(true); setReload(value => value + 1); }}; disabled={loading \|\| backend.status !== "connected"} |
| frontend/src/screens/app.marketplace.tsx:67 | input | onChange={(e) => setQ(e.target.value)}; disabled=None |
| frontend/src/screens/app.marketplace.tsx:69 | button | onClick={() => setOrgOnly((o) => !o)}; disabled=None |
| frontend/src/screens/app.marketplace.tsx:75 | button | onClick={() => setKind(k.id)}; disabled=None |
| frontend/src/screens/app.marketplace.tsx:86 | button | onClick={() => navigate({ search: { asset: a.id } })}; disabled=None |
| frontend/src/screens/app.marketplace.tsx:134 | button | onClick={() => doInstall(sel)}; disabled={isInstalled(sel)} |
| frontend/src/screens/app.settings.tsx:34 | button | onClick={() => { if (value !== saved && !window.confirm("Reload settings and discard unsaved changes?")) return; setLoading(true); setReload(current => current + 1); }}; disabled={busy \|\| backend.status !== "connected"} |
| frontend/src/screens/app.settings.tsx:35 | form | onSubmit={event => { event.preventDefault(); void save(); }}; disabled=None |
| frontend/src/screens/app.settings.tsx:36 | input | onChange={event => { setValue(event.target.value); setSuccess(""); }}; disabled={!loaded \|\| loading \|\| busy \|\| !administrative} |
| frontend/src/screens/app.settings.tsx:39 | button | Native or caller delegated; disabled={!loaded \|\| loading \|\| busy \|\| !administrative \|\| value === saved} |
| frontend/src/screens/app.tsx:64 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:70 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:80 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:97 | button | onClick={() => setCollapsed((c) => !c)}; disabled=None |
| frontend/src/screens/app.tsx:105 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:113 | button | onClick={() => setCmd(true)}; disabled=None |
| frontend/src/screens/app.tsx:118 | button | onClick={() => setHelp(true)}; disabled=None |
| frontend/src/screens/app.tsx:120 | PopoverTrigger | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:125 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:130 | button | onClick={() => a.workflowId && navigate({ to: "/app/workflows/$id", params: { id: a.workflowId } })}; disabled={!a.workflowId} |
| frontend/src/screens/app.tsx:139 | DropdownMenuTrigger | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:146 | DropdownMenuItem | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:146 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:155 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.tsx:159 | button | onClick={() => setMore(true)}; disabled=None |
| frontend/src/screens/app.tsx:161 | Sheet | onOpenChange={setMore}; disabled=None |
| frontend/src/screens/app.tsx:169 | Link | onClick={() => setMore(false)}; disabled=None |
| frontend/src/screens/app.tsx:179 | CommandPalette | onOpenChange={setCmd}; disabled=None |
| frontend/src/screens/app.tsx:180 | ShortcutsDialog | onOpenChange={setHelp}; disabled=None |
| frontend/src/screens/app.workflows.$id.tsx:37 | ApiFeedback | onRetry={()=>setAttempt(n=>n+1)}; disabled=None |
| frontend/src/screens/app.workflows.$id.tsx:38 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:93 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:103 | RunWorkflowDialog | onClose={() => setRunDocument(undefined)}; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:105 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:113 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:120 | DropdownMenuTrigger | Native or caller delegated; disabled={busy} |
| frontend/src/screens/app.workflows.index.tsx:122 | DropdownMenuItem | onSelect={() => void run(w.id)}; disabled={busy \|\| !live?.published_version \|\| !backend.session?.runtime_available \|\| !backend.can("workflow.execute")} |
| frontend/src/screens/app.workflows.index.tsx:124 | DropdownMenuItem | onSelect={() => navigate({ to: "/app/workflows/$id", params: { id: w.id } })}; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:125 | DropdownMenuItem | onSelect={() => void disable(w.id)}; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:126 | DropdownMenuItem | onSelect={() => { const id = dup(w.id); if (id) toast("Duplicated as a local draft. Save draft to persist it on the server."); if (id) navigate({ to: "/app/workflows/$id", params: { id } }); }}; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:127 | DropdownMenuItem | onSelect={() => void remove(w.id, w.name)}; disabled=None |
| frontend/src/screens/app.workflows.index.tsx:128 | DropdownMenuItem | onSelect={() => { if (window.confirm(`Delete local draft "${w.name}" from this browser?`)) { del(w.id); toast(`Deleted local draft "${w.name}"`); } }}; disabled=None |
| frontend/src/screens/index.tsx:79 | a | onClick={toTop}; disabled=None |
| frontend/src/screens/index.tsx:93 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/index.tsx:150 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/index.tsx:233 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/index.tsx:417 | Link | Native or caller delegated; disabled=None |
| frontend/src/screens/index.tsx:509 | Link | Native or caller delegated; disabled=None |
