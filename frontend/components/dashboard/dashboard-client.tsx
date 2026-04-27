"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { format } from "date-fns"
import { Warning, CheckCircle, Play, SignOut, Broadcast, GlobeHemisphereEast, Package, Factory, ClipboardText, Lightning, ArrowSquareOut } from "@phosphor-icons/react"
import { ApprovalModal } from "@/components/dashboard/approval-modal"
import {
  createSupplier,
  createTask,
  fetchDisruption,
  fetchDisruptions,
  fetchPendingDecisions,
  fetchSuppliers,
  fetchTasks,
  fetchTopologyNetwork,
  triggerLiveScan,
  triggerManualSignal,
  updateTask,
} from "@/lib/api"
import { useDisruptionsWS } from "@/hooks/use-disruptions-ws"
import { createSupabaseBrowserClient } from "@/lib/supabase"

const MANUAL_SIGNAL_PRESETS = [
  {
    label: "Suez Disruption",
    value: "Suez Canal traffic disruption causing rerouting pressure across Europe-bound pharmaceutical shipments.",
  },
  {
    label: "Factory Fire",
    value: "Factory fire at a semiconductor supplier in Taiwan has halted production and threatens downstream inventory commitments.",
  },
  {
    label: "Extreme Weather",
    value: "Severe cyclone activity near the Bay of Bengal is delaying vessel departures and increasing cold-chain risk for outbound cargo.",
  },
  {
    label: "Port Congestion",
    value: "Port of Rotterdam congestion has increased berth waiting times beyond 48 hours, putting critical replenishment lanes at risk.",
  },
]

function projectPoint(latitude: number, longitude: number) {
  const width = 1000
  const height = 460
  const x = ((longitude + 180) / 360) * width
  const y = ((90 - latitude) / 180) * height
  return { x, y }
}

function getModeColor(mode?: string) {
  switch (mode) {
    case "air":
      return "#7dd3fc"
    case "road":
      return "#86efac"
    case "rail":
      return "#f9a8d4"
    default:
      return "#fbbf24"
  }
}

function getTaskStatusClasses(status?: string) {
  switch (status) {
    case "done":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
    case "in_progress":
      return "border-amber-500/30 bg-amber-500/10 text-amber-200"
    case "closed":
      return "border-slate-500/30 bg-slate-500/10 text-slate-200"
    default:
      return "border-cyan-500/30 bg-cyan-500/10 text-cyan-200"
  }
}

function getPriorityClasses(priority?: string) {
  switch (priority) {
    case "critical":
      return "border-red-500/30 bg-red-500/10 text-red-200"
    case "high":
      return "border-orange-500/30 bg-orange-500/10 text-orange-200"
    case "low":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
    default:
      return "border-white/10 bg-white/5 text-gray-200"
  }
}

export default function DashboardClient() {
  const router = useRouter()
  const [disruptions, setDisruptions] = useState<any[]>([])
  const [pendingDecisions, setPendingDecisions] = useState<any[]>([])
  const [selectedDecision, setSelectedDecision] = useState<any>(null)
  const [loadingScan, setLoadingScan] = useState(false)
  const [submittingSignal, setSubmittingSignal] = useState(false)
  const [savingSupplier, setSavingSupplier] = useState(false)
  const [savingTask, setSavingTask] = useState(false)
  const [authReady, setAuthReady] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [focusDisruption, setFocusDisruption] = useState<any>(null)
  const [topology, setTopology] = useState<any>(null)
  const [suppliers, setSuppliers] = useState<any[]>([])
  const [tasks, setTasks] = useState<any[]>([])
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeKey, setSelectedEdgeKey] = useState<string | null>(null)
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null)
  const [supplierSearch, setSupplierSearch] = useState("")
  const [taskSearch, setTaskSearch] = useState("")
  const [taskStatusFilter, setTaskStatusFilter] = useState("all")
  const [laneSearch, setLaneSearch] = useState("")
  const [laneModeFilter, setLaneModeFilter] = useState("all")
  const [manualSignal, setManualSignal] = useState(
    "Suez Canal traffic disruption causing rerouting pressure across Europe-bound pharmaceutical shipments.",
  )
  const [supplierForm, setSupplierForm] = useState({
    supplierCode: "",
    legalName: "",
    country: "",
    city: "",
    businessType: "manufacturer",
    registrationNumber: "",
    materials: "",
    modes: "sea,road",
    contactEmail: "",
  })
  const [taskForm, setTaskForm] = useState({
    title: "",
    priority: "high",
    assignee: "",
    taskType: "follow_up",
    description: "",
  })

  const { events, connected, status: wsStatus } = useDisruptionsWS("default")

  const loadData = async () => {
    try {
      const [disruptionList, decisionList, topologyData, supplierList, taskList] = await Promise.all([
        fetchDisruptions(),
        fetchPendingDecisions(),
        fetchTopologyNetwork(),
        fetchSuppliers(),
        fetchTasks(),
      ])

      setDisruptions(disruptionList.items || [])
      setPendingDecisions(decisionList.items || [])
      setTopology(topologyData)
      setSuppliers(supplierList.items || [])
      setTasks(taskList.items || [])
      setSelectedNodeId((current) => {
        const nextNodes = topologyData?.nodes || []
        if (current && nextNodes.some((node: any) => node.id === current)) return current
        return nextNodes[0]?.id || null
      })
      setSelectedEdgeKey((current) => {
        const nextEdges = topologyData?.edges || []
        if (current && nextEdges.some((edge: any) => `${edge.source}-${edge.target}` === current)) return current
        return nextEdges[0] ? `${nextEdges[0].source}-${nextEdges[0].target}` : null
      })
      setSelectedShipmentId((current) => {
        const nextShipments = topologyData?.shipments || []
        if (current && nextShipments.some((shipment: any) => shipment.id === current)) return current
        return nextShipments[0]?.id || null
      })

      if (disruptionList.items?.[0]?.id) {
        const detail = await fetchDisruption(disruptionList.items[0].id)
        setFocusDisruption(detail)
      } else {
        setFocusDisruption(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard data.")
    }
  }

  useEffect(() => {
    const supabase = createSupabaseBrowserClient()
    let mounted = true

    const initialize = async () => {
      const { data } = await supabase.auth.getUser()
      if (!mounted) return

      if (!data.user) {
        router.replace("/login")
        return
      }

      setUser(data.user)
      setAuthReady(true)
      await loadData()
    }

    initialize().catch(() => router.replace("/login"))

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.replace("/login")
        return
      }

      setUser(session.user)
    })

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [router])

  useEffect(() => {
    if (!authReady || events.length === 0) return
    loadData().catch(() => null)
  }, [events, authReady])

  const handleTriggerScan = async () => {
    setLoadingScan(true)
    setError(null)
    try {
      await triggerLiveScan()
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run the live scan.")
    }
    setLoadingScan(false)
  }

  const handleSubmitManualSignal = async () => {
    if (manualSignal.trim().length < 10) {
      setError("Manual signal must be at least 10 characters.")
      return
    }

    setSubmittingSignal(true)
    setError(null)
    try {
      await triggerManualSignal(manualSignal.trim(), "manual", "default")
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit manual signal.")
    }
    setSubmittingSignal(false)
  }

  const handleCreateSupplier = async () => {
    if (!supplierForm.supplierCode || !supplierForm.legalName || !supplierForm.country) {
      setError("Supplier code, legal name, and country are required.")
      return
    }

    setSavingSupplier(true)
    setError(null)
    try {
      const materials = supplierForm.materials
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
        .map((material) => ({ material, category: "registered" }))
      const lanePreferences = supplierForm.modes
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
        .map((mode) => ({ mode, active: true }))

      await createSupplier({
        supplier_code: supplierForm.supplierCode,
        legal_name: supplierForm.legalName,
        country: supplierForm.country,
        city: supplierForm.city || undefined,
        business_type: supplierForm.businessType,
        registration_number: supplierForm.registrationNumber || undefined,
        contact_email: supplierForm.contactEmail || undefined,
        material_profiles: materials,
        lane_preferences: lanePreferences,
      })

      setSupplierForm({
        supplierCode: "",
        legalName: "",
        country: "",
        city: "",
        businessType: "manufacturer",
        registrationNumber: "",
        materials: "",
        modes: "sea,road",
        contactEmail: "",
      })
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to register supplier.")
    }
    setSavingSupplier(false)
  }

  const handleCreateTask = async () => {
    if (!taskForm.title) {
      setError("Task title is required.")
      return
    }

    setSavingTask(true)
    setError(null)
    try {
      await createTask({
        title: taskForm.title,
        description: taskForm.description || undefined,
        priority: taskForm.priority,
        assignee: taskForm.assignee || undefined,
        task_type: taskForm.taskType,
        disruption_id: focusDisruption?.id,
        metadata_json: {
          source: "dashboard",
          linked_geography: focusDisruption?.geography || null,
        },
      })
      setTaskForm({
        title: "",
        priority: "high",
        assignee: "",
        taskType: "follow_up",
        description: "",
      })
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create task.")
    }
    setSavingTask(false)
  }

  const handleTaskStatusUpdate = async (taskId: string, status: string) => {
    setError(null)
    try {
      await updateTask(taskId, { status })
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update task.")
    }
  }

  const handleSignOut = async () => {
    const supabase = createSupabaseBrowserClient()
    await supabase.auth.signOut()
    router.replace("/login")
  }

  if (!authReady) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-sm text-gray-400">
        Loading secure operations console...
      </div>
    )
  }

  const nodeLookup = new Map<string, any>((topology?.nodes || []).map((node: any) => [node.id, node]))
  const allEdges = topology?.edges || []
  const allShipments = topology?.shipments || []
  const allSuppliers = suppliers || []
  const allTasks = tasks || []
  const shipmentCount = topology?.stats?.shipment_count || 0
  const supplierCount = topology?.stats?.supplier_count || 0
  const taskOpenCount = tasks.filter((task) => task.status !== "done" && task.status !== "closed").length
  const selectedNode = selectedNodeId ? nodeLookup.get(selectedNodeId) : null
  const filteredEdges = allEdges.filter((edge: any) => {
    const matchesMode = laneModeFilter === "all" || (edge.mode || "unknown") === laneModeFilter
    const haystack = `${edge.source} ${edge.target} ${edge.mode || ""}`.toLowerCase()
    const matchesSearch = laneSearch.trim() === "" || haystack.includes(laneSearch.trim().toLowerCase())
    return matchesMode && matchesSearch
  })
  const filteredShipments = allShipments.filter((shipment: any) => {
    if (laneModeFilter !== "all" && (shipment.mode || "unknown") !== laneModeFilter) return false
    if (laneSearch.trim() === "") return true
    const haystack = `${shipment.id} ${shipment.origin} ${shipment.destination} ${shipment.material || ""} ${(shipment.route || []).join(" ")}`.toLowerCase()
    return haystack.includes(laneSearch.trim().toLowerCase())
  })
  const filteredSuppliers = allSuppliers.filter((supplier: any) => {
    const haystack = `${supplier.legal_name} ${supplier.supplier_code} ${supplier.country} ${supplier.city || ""} ${(supplier.material_profiles || []).map((item: any) => item.material).join(" ")}`.toLowerCase()
    return supplierSearch.trim() === "" || haystack.includes(supplierSearch.trim().toLowerCase())
  })
  const filteredTasks = allTasks.filter((task: any) => {
    const matchesStatus = taskStatusFilter === "all" || task.status === taskStatusFilter
    const haystack = `${task.title} ${task.description || ""} ${task.task_type} ${task.assignee || ""}`.toLowerCase()
    const matchesSearch = taskSearch.trim() === "" || haystack.includes(taskSearch.trim().toLowerCase())
    return matchesStatus && matchesSearch
  })
  const selectedEdge =
    filteredEdges.find((edge: any) => `${edge.source}-${edge.target}` === selectedEdgeKey) ||
    allEdges.find((edge: any) => `${edge.source}-${edge.target}` === selectedEdgeKey) ||
    null
  const selectedShipment = filteredShipments.find((shipment: any) => shipment.id === selectedShipmentId) ||
    allShipments.find((shipment: any) => shipment.id === selectedShipmentId) ||
    null
  const relatedShipments = selectedNodeId
    ? filteredShipments.filter((shipment: any) => (shipment.route || []).includes(selectedNodeId))
    : []
  const focusPendingDecision = focusDisruption
    ? pendingDecisions.find((decision) => decision.disruption_id === focusDisruption.id)
    : null
  const scenarioCards = (focusDisruption?.scenarios || []).map((scenario: any) => {
    const linkedSupplier = filteredSuppliers.find((supplier: any) =>
      scenario.label?.toLowerCase().includes((supplier.legal_name || "").toLowerCase()),
    ) || allSuppliers.find((supplier: any) =>
      scenario.label?.toLowerCase().includes((supplier.legal_name || "").toLowerCase()),
    )
    return { ...scenario, linkedSupplier }
  })

  return (
    <div className="p-6 h-full flex flex-col gap-6 overflow-y-auto">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Active Operations</h1>
          <p className="text-sm text-gray-500 mt-1 flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-500" : "bg-amber-500"} shadow-[0_0_8px_rgba(16,185,129,0.5)]`}></span>
            {user?.email ? `Signed in as ${user.email}` : "Supabase session active"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSignOut}
            className="border border-white/10 bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-md font-medium text-sm flex items-center gap-2 transition-all"
          >
            <SignOut weight="bold" />
            Sign out
          </button>
          <button
            onClick={handleTriggerScan}
            disabled={loadingScan}
            className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md font-medium text-sm flex items-center gap-2 transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50"
          >
            <Play weight="fill" />
            {loadingScan ? "Scanning..." : "Run Live Scan"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-white/5 bg-white/5 p-4">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-gray-400">
            <GlobeHemisphereEast size={16} />
            Network
          </div>
          <div className="mt-3 text-2xl font-semibold text-white">{topology?.stats?.node_count || 0}</div>
          <div className="mt-1 text-sm text-gray-400">Mapped nodes across active topology</div>
        </div>
        <div className="rounded-xl border border-white/5 bg-white/5 p-4">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-gray-400">
            <Package size={16} />
            Shipments
          </div>
          <div className="mt-3 text-2xl font-semibold text-white">{shipmentCount}</div>
          <div className="mt-1 text-sm text-gray-400">Tracked lanes across sea, road, rail, and air</div>
        </div>
        <div className="rounded-xl border border-white/5 bg-white/5 p-4">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-gray-400">
            <Factory size={16} />
            Suppliers
          </div>
          <div className="mt-3 text-2xl font-semibold text-white">{supplierCount}</div>
          <div className="mt-1 text-sm text-gray-400">Registered businesses with material profiles</div>
        </div>
        <div className="rounded-xl border border-white/5 bg-white/5 p-4">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-gray-400">
            <ClipboardText size={16} />
            Tasks
          </div>
          <div className="mt-3 text-2xl font-semibold text-white">{taskOpenCount}</div>
          <div className="mt-1 text-sm text-gray-400">Open actions tracked from live operations</div>
        </div>
      </div>

      <div className="rounded-xl border border-white/5 bg-white/5 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
          <div className="w-full lg:max-w-56">
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-400">
              Presets
            </label>
            <select
              className="h-11 w-full rounded-lg border border-white/10 bg-black/30 px-3 text-sm text-white outline-none transition-colors focus:border-blue-500/60"
              defaultValue={MANUAL_SIGNAL_PRESETS[0].value}
              onChange={(e) => setManualSignal(e.target.value)}
            >
              {MANUAL_SIGNAL_PRESETS.map((preset) => (
                <option key={preset.label} value={preset.value} className="bg-[#111]">
                  {preset.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-400">
              Signal Intake
            </label>
            <textarea
              value={manualSignal}
              onChange={(e) => setManualSignal(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none transition-colors placeholder:text-gray-500 focus:border-blue-500/60"
              placeholder="Paste a disruption signal to run through the backend pipeline..."
            />
          </div>
          <button
            onClick={handleSubmitManualSignal}
            disabled={submittingSignal}
            className="h-11 rounded-md bg-emerald-600 px-4 text-sm font-medium text-white transition-all hover:bg-emerald-500 disabled:opacity-50"
          >
            {submittingSignal ? "Submitting..." : "Submit Manual Signal"}
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-white/5 bg-white/5 overflow-hidden">
        <div className="border-b border-white/5 bg-black/20 p-4">
          <h2 className="text-sm font-medium tracking-wide uppercase text-gray-400">Scenario Cards</h2>
          <p className="mt-1 text-xs text-gray-500">Recommended response options with supplier-aware reasoning from the disruption engine.</p>
        </div>
        <div className="p-4">
          {scenarioCards.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-3">
              {scenarioCards.map((scenario: any) => (
                <div
                  key={scenario.id}
                  className={`rounded-xl border p-4 ${
                    scenario.recommended
                      ? "border-emerald-400/30 bg-emerald-500/10"
                      : "border-white/5 bg-black/20"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-white">{scenario.label}</div>
                      <div className="mt-1 text-xs text-gray-400">
                        Option {scenario.option_index} {scenario.recommended ? "• Recommended" : ""}
                      </div>
                    </div>
                    <span className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-gray-200">
                      Score {scenario.composite_score ?? "--"}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-gray-300">{scenario.description || "No scenario reasoning returned."}</p>
                  {scenario.linkedSupplier ? (
                    <div className="mt-3 rounded-lg border border-cyan-400/20 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100">
                      Supplier match: {scenario.linkedSupplier.legal_name} • Materials: {(scenario.linkedSupplier.material_profiles || []).map((item: any) => item.material).filter(Boolean).join(", ") || "n/a"}
                    </div>
                  ) : null}
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-gray-400">
                    <div className="rounded-lg border border-white/5 bg-white/5 px-2 py-2">
                      Cost
                      <div className="mt-1 text-sm text-white">${scenario.cost_delta_usd ?? "--"}</div>
                    </div>
                    <div className="rounded-lg border border-white/5 bg-white/5 px-2 py-2">
                      Delay
                      <div className="mt-1 text-sm text-white">{scenario.time_delta_days ?? "--"}d</div>
                    </div>
                    <div className="rounded-lg border border-white/5 bg-white/5 px-2 py-2">
                      Risk
                      <div className="mt-1 text-sm text-white">{scenario.risk_score ?? "--"}</div>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between gap-3">
                    <div className="text-xs text-gray-400">
                      {scenario.recommended
                        ? focusPendingDecision
                          ? "Awaiting approval"
                          : focusDisruption?.status === "resolved"
                            ? "Already executed"
                            : "Top-ranked option"
                        : "Alternative path"}
                    </div>
                    <div className="flex gap-2">
                      {scenario.recommended && focusPendingDecision ? (
                        <button
                          onClick={() => setSelectedDecision(focusPendingDecision)}
                          className="rounded-md bg-amber-500 px-3 py-2 text-xs font-semibold text-black transition-colors hover:bg-amber-400"
                        >
                          <span className="inline-flex items-center gap-1">
                            <Lightning weight="fill" />
                            Review
                          </span>
                        </button>
                      ) : null}
                      {scenario.recommended && !focusPendingDecision && focusDisruption?.status === "resolved" ? (
                        <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-200">
                          Executed
                        </span>
                      ) : null}
                      {!scenario.recommended && focusPendingDecision ? (
                        <button
                          onClick={() => setSelectedDecision(focusPendingDecision)}
                          className="rounded-md border border-white/10 px-3 py-2 text-xs font-semibold text-gray-200 transition-colors hover:bg-white/10"
                        >
                          <span className="inline-flex items-center gap-1">
                            <ArrowSquareOut />
                            Compare
                          </span>
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 bg-black/20 px-4 py-8 text-center text-sm text-gray-500">
              Run a live scan or submit a signal to generate scenario cards with supplier-aware reasoning.
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[2fr_1fr]">
        <div className="border border-white/5 bg-white/5 rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-white/5 flex justify-between items-center bg-black/20">
            <div>
              <h2 className="text-sm font-medium tracking-wide uppercase text-gray-400">Network Topology Map</h2>
              <p className="mt-1 text-xs text-gray-500">
                Live network rendered from topology nodes, lanes, and shipments instead of chip-only disruption summaries.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Broadcast size={16} className={wsStatus === "degraded" ? "text-amber-400" : connected ? "text-emerald-400" : "text-amber-400"} />
              {wsStatus === "degraded" ? "WebSocket degraded" : connected ? "WebSocket live" : "WebSocket reconnecting"}
            </div>
          </div>

          <div className="p-4">
            {topology?.nodes?.length ? (
              <div className="space-y-4">
                <div className="overflow-hidden rounded-2xl border border-white/5 bg-[#06111d]">
                  <div className="border-b border-white/5 bg-black/20 p-3">
                    <div className="grid gap-3 md:grid-cols-2">
                      <input
                        value={laneSearch}
                        onChange={(e) => setLaneSearch(e.target.value)}
                        placeholder="Search lanes, nodes, materials, shipments"
                        className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
                      />
                      <select
                        value={laneModeFilter}
                        onChange={(e) => setLaneModeFilter(e.target.value)}
                        className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
                      >
                        <option value="all">All modes</option>
                        {(topology?.stats?.modes || []).map((mode: string) => (
                          <option key={mode} value={mode}>
                            {mode}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <svg viewBox="0 0 1000 460" className="w-full">
                    <defs>
                      <linearGradient id="bgGrid" x1="0%" x2="100%" y1="0%" y2="100%">
                        <stop offset="0%" stopColor="#08111f" />
                        <stop offset="100%" stopColor="#0f2133" />
                      </linearGradient>
                    </defs>
                    <rect width="1000" height="460" fill="url(#bgGrid)" />
                    {[...Array(10)].map((_, index) => (
                      <line
                        key={`v-${index}`}
                        x1={index * 100}
                        y1="0"
                        x2={index * 100}
                        y2="460"
                        stroke="rgba(148,163,184,0.10)"
                      />
                    ))}
                    {[...Array(5)].map((_, index) => (
                      <line
                        key={`h-${index}`}
                        x1="0"
                        y1={index * 92}
                        x2="1000"
                        y2={index * 92}
                        stroke="rgba(148,163,184,0.10)"
                      />
                    ))}

                    {filteredEdges.map((edge: any) => {
                      const source = nodeLookup.get(edge.source)
                      const target = nodeLookup.get(edge.target)
                      if (!source || !target || source.latitude == null || target.latitude == null) return null
                      const start = projectPoint(source.latitude, source.longitude)
                      const end = projectPoint(target.latitude, target.longitude)
                      return (
                        <g key={`${edge.source}-${edge.target}`}>
                          <line
                            x1={start.x}
                            y1={start.y}
                            x2={end.x}
                            y2={end.y}
                            stroke={getModeColor(edge.mode)}
                            strokeWidth="3"
                            opacity="0.8"
                            onClick={() => setSelectedEdgeKey(`${edge.source}-${edge.target}`)}
                            className="cursor-pointer"
                          />
                          <circle cx={(start.x + end.x) / 2} cy={(start.y + end.y) / 2} r="3" fill={getModeColor(edge.mode)} />
                        </g>
                      )
                    })}

                    {(topology.nodes || []).map((node: any) => {
                      if (node.latitude == null || node.longitude == null) return null
                      const point = projectPoint(node.latitude, node.longitude)
                      const isAffected = Boolean(focusDisruption?.affected_nodes?.includes(node.id))
                      const isCascade = Boolean(focusDisruption?.cascade_nodes?.includes(node.id))
                      const isSelected = selectedNodeId === node.id
                      const connectedToVisibleLane =
                        laneSearch.trim() === "" && laneModeFilter === "all"
                          ? true
                          : filteredEdges.some((edge: any) => edge.source === node.id || edge.target === node.id)
                      if (!connectedToVisibleLane) return null
                      const fill = isAffected ? "#ef4444" : isCascade ? "#38bdf8" : "#f8fafc"
                      return (
                        <g key={node.id}>
                          <circle
                            cx={point.x}
                            cy={point.y}
                            r={isSelected ? "10" : "8"}
                            fill={fill}
                            stroke={isSelected ? "#f59e0b" : "#020617"}
                            strokeWidth={isSelected ? "3" : "2"}
                            onClick={() => setSelectedNodeId(node.id)}
                            className="cursor-pointer"
                          />
                          <text x={point.x + 12} y={point.y - 12} fill="#e2e8f0" fontSize="12">
                            {node.name}
                          </text>
                          <text x={point.x + 12} y={point.y + 4} fill="#94a3b8" fontSize="10">
                            {node.type}
                          </text>
                        </g>
                      )
                    })}
                  </svg>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
                    <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-red-300">
                      <Warning size={16} weight="fill" />
                      Directly affected
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(focusDisruption?.affected_nodes || []).length > 0 ? (
                        (focusDisruption?.affected_nodes || []).map((node: string) => (
                          <span key={node} className="rounded-full border border-red-400/30 bg-red-500/10 px-3 py-1 text-xs text-red-100">
                            {node}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-gray-400">No mapped nodes returned.</span>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                    <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-300">
                      <CheckCircle size={16} weight="fill" />
                      Cascade impact
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(focusDisruption?.cascade_nodes || []).length > 0 ? (
                        (focusDisruption?.cascade_nodes || []).map((node: string) => (
                          <span key={node} className="rounded-full border border-blue-400/30 bg-blue-500/10 px-3 py-1 text-xs text-blue-100">
                            {node}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-gray-400">No downstream cascade nodes returned.</span>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-emerald-300">Transport modes</div>
                    <div className="flex flex-wrap gap-2">
                    {(topology?.stats?.modes || []).map((mode: string) => (
                        <span key={mode} className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-100">
                          {mode}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-3">
                  <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">Selected Node</div>
                    {selectedNode ? (
                      <div className="mt-3 space-y-2 text-sm">
                        <div className="font-medium text-white">{selectedNode.name}</div>
                        <div className="text-gray-400">{selectedNode.location}</div>
                        <div className="text-gray-400">Type: {selectedNode.type}</div>
                        <div className="text-gray-400">Tier: {selectedNode.tier}</div>
                        <div className="text-gray-400">Related shipments: {relatedShipments.length}</div>
                      </div>
                    ) : (
                      <div className="mt-3 text-sm text-gray-500">Click a node on the map.</div>
                    )}
                  </div>

                  <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">Selected Lane</div>
                    {selectedEdge ? (
                      <div className="mt-3 space-y-2 text-sm">
                        <div className="font-medium text-white">{selectedEdge.source} → {selectedEdge.target}</div>
                        <div className="text-gray-400">Mode: {selectedEdge.mode || "unknown"}</div>
                        <div className="text-gray-400">Transit: {selectedEdge.transit_days || "--"} days</div>
                        <div className="text-gray-400">Risk level: {selectedEdge.risk_level || "--"}</div>
                        <div className="text-gray-400">Cost factor: {selectedEdge.cost_factor || "--"}</div>
                      </div>
                    ) : (
                      <div className="mt-3 text-sm text-gray-500">Click a lane on the map or narrow the lane filters to inspect a route.</div>
                    )}
                  </div>

                  <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">Selected Shipment</div>
                    {selectedShipment ? (
                      <div className="mt-3 space-y-2 text-sm">
                        <div className="font-medium text-white">{selectedShipment.id}</div>
                        <div className="text-gray-400">Material: {selectedShipment.material || "Unspecified"}</div>
                        <div className="text-gray-400">Mode: {selectedShipment.mode || "unknown"}</div>
                        <div className="text-gray-400">Origin: {selectedShipment.origin}</div>
                        <div className="text-gray-400">Destination: {selectedShipment.destination}</div>
                      </div>
                    ) : (
                      <div className="mt-3 text-sm text-gray-500">Select a shipment below to inspect material, route, and mode details.</div>
                    )}
                  </div>
                </div>

                <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                  <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">Shipment Routes</div>
                  {filteredShipments.length > 0 ? (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {filteredShipments.map((shipment: any) => (
                      <button
                        key={shipment.id}
                        onClick={() => setSelectedShipmentId(shipment.id)}
                        className={`rounded-lg border p-3 text-left transition-colors ${
                          selectedShipmentId === shipment.id
                            ? "border-cyan-400/40 bg-cyan-500/10"
                            : "border-white/5 bg-white/5 hover:bg-white/10"
                        }`}
                      >
                        <div className="font-medium text-white">{shipment.id}</div>
                        <div className="mt-1 text-xs text-gray-400">{shipment.material || "Unspecified material"} • {shipment.mode || "unknown"}</div>
                        <div className="mt-2 text-[11px] text-gray-500">{(shipment.route || []).join(" → ")}</div>
                      </button>
                    ))}
                  </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-white/10 bg-white/5 px-4 py-6 text-sm text-gray-500">
                      No shipment routes match the current lane filters.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-white/10 bg-black/20 px-4 py-10 text-center text-sm text-gray-400">
                No topology data loaded yet. Run a live scan or confirm the backend network has initialized.
              </div>
            )}
          </div>
        </div>

        <div className="border border-white/5 bg-white/5 rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-black/20 flex gap-4">
            <div className="text-sm font-medium tracking-wide uppercase text-white border-b-2 border-blue-500 pb-1">Activity Stream</div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {pendingDecisions.length > 0 && (
              <div className="mb-6 space-y-3">
                <h3 className="text-xs uppercase text-amber-500 font-bold tracking-wider">Requires Approval</h3>
                {pendingDecisions.map((decision) => (
                  <div key={decision.id} className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-1 h-full bg-amber-500 block"></div>
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-amber-400 font-medium text-sm mb-1">{decision.scenario_id ? "Escalation" : "Manual review required"}</div>
                        <div className="text-xs text-gray-400">Confidence limits exceeded. Human input required.</div>
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedDecision(decision)}
                      className="mt-3 w-full py-1.5 bg-amber-500/20 hover:bg-amber-500/30 transition-colors rounded text-xs text-amber-300 font-medium"
                    >
                      Review Options
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-3">
              <h3 className="text-xs uppercase text-gray-500 font-bold tracking-wider">Live Log</h3>
              {disruptions.length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 bg-white/5 px-4 py-6 text-center text-sm text-gray-500">
                  No active disruptions yet. Use `Run Live Scan` or submit a manual signal to start the decision flow.
                </div>
              ) : disruptions.map((disruption) => (
                <div key={disruption.id} className="p-3 bg-black/30 border border-white/5 rounded-lg flex gap-3 text-sm">
                  <div className="mt-0.5">
                    {disruption.severity_score >= 8 ? <Warning className="text-red-500" size={16} /> : <CheckCircle className="text-green-500" size={16} />}
                  </div>
                  <div>
                    <div className="font-medium text-gray-200">
                      {disruption.geography} <span className="mx-1 text-gray-600">•</span> <span className="text-white text-xs px-1.5 py-0.5 bg-white/10 rounded">{disruption.event_type}</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1 line-clamp-2">
                      Severity: <span className="text-gray-200">{disruption.severity_score}/10</span>. Detected and persisted by the backend decision engine.
                    </div>
                    <div className="text-[11px] text-gray-500 mt-1">{format(new Date(disruption.created_at), "MMM d, HH:mm")}</div>
                  </div>
                </div>
              ))}
            </div>

            {events.length > 0 ? (
              <div className="space-y-3">
                <h3 className="text-xs uppercase text-gray-500 font-bold tracking-wider">Realtime Events</h3>
                {events.slice(0, 5).map((event, index) => (
                  <div key={`${event.type}-${index}`} className="rounded-lg border border-white/5 bg-black/20 p-3 text-xs text-gray-300">
                    <div className="font-medium text-white">{event.event || event.type}</div>
                    <div className="mt-1 text-gray-400">{event.geography || event.message || "Stream update received."}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-white/5 bg-white/5 overflow-hidden">
          <div className="border-b border-white/5 bg-black/20 p-4">
            <h2 className="text-sm font-medium tracking-wide uppercase text-gray-400">Supplier Registration</h2>
            <p className="mt-1 text-xs text-gray-500">Register business identity, materials, and transport modes so disruptions can be mapped beyond ports.</p>
          </div>
          <div className="p-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <input
                value={supplierForm.supplierCode}
                onChange={(e) => setSupplierForm((current) => ({ ...current, supplierCode: e.target.value }))}
                placeholder="Supplier code"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <input
                value={supplierForm.legalName}
                onChange={(e) => setSupplierForm((current) => ({ ...current, legalName: e.target.value }))}
                placeholder="Legal business name"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <input
                value={supplierForm.country}
                onChange={(e) => setSupplierForm((current) => ({ ...current, country: e.target.value }))}
                placeholder="Country"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <input
                value={supplierForm.city}
                onChange={(e) => setSupplierForm((current) => ({ ...current, city: e.target.value }))}
                placeholder="City"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <input
                value={supplierForm.registrationNumber}
                onChange={(e) => setSupplierForm((current) => ({ ...current, registrationNumber: e.target.value }))}
                placeholder="Registration number"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <input
                value={supplierForm.contactEmail}
                onChange={(e) => setSupplierForm((current) => ({ ...current, contactEmail: e.target.value }))}
                placeholder="Contact email"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                value={supplierForm.materials}
                onChange={(e) => setSupplierForm((current) => ({ ...current, materials: e.target.value }))}
                placeholder="Materials, comma separated"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <input
                value={supplierForm.modes}
                onChange={(e) => setSupplierForm((current) => ({ ...current, modes: e.target.value }))}
                placeholder="Modes, comma separated"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
            </div>
            <button
              onClick={handleCreateSupplier}
              disabled={savingSupplier}
              className="rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-cyan-500 disabled:opacity-50"
            >
              {savingSupplier ? "Registering..." : "Register Supplier"}
            </button>

            <input
              value={supplierSearch}
              onChange={(e) => setSupplierSearch(e.target.value)}
              placeholder="Search suppliers, codes, countries, or materials"
              className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
            />

            <div className="space-y-3">
              {filteredSuppliers.length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 bg-white/5 px-4 py-6 text-sm text-gray-500">
                  No suppliers match the current search.
                </div>
              ) : filteredSuppliers.map((supplier) => (
                <div key={supplier.id} className="rounded-lg border border-white/5 bg-black/20 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{supplier.legal_name}</div>
                      <div className="text-xs text-gray-400">{supplier.supplier_code} • {supplier.country}{supplier.city ? `, ${supplier.city}` : ""}</div>
                    </div>
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-200">
                      {supplier.business_type}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(supplier.material_profiles || []).map((item: any, index: number) => (
                      <span key={`${supplier.id}-material-${index}`} className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-gray-200">
                        {item.material}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-white/5 overflow-hidden">
          <div className="border-b border-white/5 bg-black/20 p-4">
            <h2 className="text-sm font-medium tracking-wide uppercase text-gray-400">Task Management</h2>
            <p className="mt-1 text-xs text-gray-500">Track follow-ups, approvals, and manual work so the execution layer has an operating queue.</p>
          </div>
          <div className="p-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <input
                value={taskForm.title}
                onChange={(e) => setTaskForm((current) => ({ ...current, title: e.target.value }))}
                placeholder="Task title"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <input
                value={taskForm.assignee}
                onChange={(e) => setTaskForm((current) => ({ ...current, assignee: e.target.value }))}
                placeholder="Assignee"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
            </div>
            <textarea
              value={taskForm.description}
              onChange={(e) => setTaskForm((current) => ({ ...current, description: e.target.value }))}
              rows={3}
              placeholder="What should operations do next?"
              className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
            />
            <div className="grid gap-3 md:grid-cols-2">
              <select
                value={taskForm.priority}
                onChange={(e) => setTaskForm((current) => ({ ...current, priority: e.target.value }))}
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <select
                value={taskForm.taskType}
                onChange={(e) => setTaskForm((current) => ({ ...current, taskType: e.target.value }))}
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              >
                <option value="follow_up">Follow up</option>
                <option value="supplier_onboarding">Supplier onboarding</option>
                <option value="lane_review">Lane review</option>
                <option value="approval">Approval</option>
              </select>
            </div>
            <button
              onClick={handleCreateTask}
              disabled={savingTask}
              className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:opacity-50"
            >
              {savingTask ? "Creating..." : "Create Task"}
            </button>

            <div className="grid gap-3 md:grid-cols-2">
              <input
                value={taskSearch}
                onChange={(e) => setTaskSearch(e.target.value)}
                placeholder="Search tasks, assignees, or descriptions"
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              />
              <select
                value={taskStatusFilter}
                onChange={(e) => setTaskStatusFilter(e.target.value)}
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none"
              >
                <option value="all">All statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="done">Done</option>
                <option value="closed">Closed</option>
              </select>
            </div>

            <div className="space-y-3">
              {filteredTasks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 bg-white/5 px-4 py-6 text-sm text-gray-500">
                  No tasks match the current filters.
                </div>
              ) : filteredTasks.map((task) => (
                <div key={task.id} className="rounded-lg border border-white/5 bg-black/20 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{task.title}</div>
                      <div className="mt-1 text-xs text-gray-400">{task.task_type} • {task.assignee || "Unassigned"}</div>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-[11px] ${getPriorityClasses(task.priority)}`}>
                      {task.priority}
                    </span>
                  </div>
                  {task.description ? <div className="mt-2 text-sm text-gray-300">{task.description}</div> : null}
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <div className={`rounded-full border px-2 py-1 text-[11px] ${getTaskStatusClasses(task.status)}`}>
                      {task.status}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleTaskStatusUpdate(task.id, "open")}
                        className="rounded border border-white/10 px-2 py-1 text-[11px] text-gray-300 transition-colors hover:bg-white/10"
                      >
                        Open
                      </button>
                      <button
                        onClick={() => handleTaskStatusUpdate(task.id, "in_progress")}
                        className="rounded border border-white/10 px-2 py-1 text-[11px] text-gray-300 transition-colors hover:bg-white/10"
                      >
                        In Progress
                      </button>
                      <button
                        onClick={() => handleTaskStatusUpdate(task.id, "done")}
                        className="rounded border border-emerald-500/30 px-2 py-1 text-[11px] text-emerald-200 transition-colors hover:bg-emerald-500/10"
                      >
                        Done
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <ApprovalModal
        decision={selectedDecision}
        onClose={() => setSelectedDecision(null)}
        onActionCb={loadData}
        approverId={user?.email || user?.id || "operator"}
      />
    </div>
  )
}
