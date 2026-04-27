const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    })
  } catch (error) {
    throw new Error(
      `Unable to reach backend at ${API_BASE_URL}. Make sure the FastAPI server is running and restart Next.js after env changes.`,
    )
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = data.detail || detail
    } catch {}
    throw new Error(detail || "Request failed.")
  }

  return response.json() as Promise<T>
}

function mapScenario(row: Record<string, any>) {
  const composite = typeof row.composite_score === "number" ? row.composite_score : null
  return {
    ...row,
    name: row.label,
    estimated_cost_usd: row.cost_delta_usd ?? null,
    estimated_delay_days: row.time_delta_days ?? null,
    success_confidence:
      composite !== null ? Math.max(0.1, Math.min(0.99, 1 - composite)) : row.recommended ? 0.8 : 0.65,
  }
}

export async function fetchDisruptions() {
  return apiFetch<{ items: any[]; total: number; page: number; page_size: number }>("/disruptions")
}

export async function fetchDisruption(disruptionId: string) {
  return apiFetch<any>(`/disruptions/${disruptionId}`)
}

export async function fetchPendingDecisions() {
  const decisionList = await apiFetch<{
    items: any[]
    total: number
    page: number
    page_size: number
    pending_count: number
  }>("/decisions")

  const pending = decisionList.items.filter((item) => item.status === "pending")
  const enriched = await Promise.all(
    pending.map(async (decision) => {
      try {
        const scenarioList = await apiFetch<{ scenarios: any[] }>(`/disruptions/${decision.disruption_id}/scenarios`)
        return {
          ...decision,
          scenarios: (scenarioList.scenarios || []).map(mapScenario),
        }
      } catch {
        return {
          ...decision,
          scenarios: [],
        }
      }
    }),
  )

  return {
    items: enriched,
    total: decisionList.total,
    page: decisionList.page,
    page_size: decisionList.page_size,
    pending_count: decisionList.pending_count,
  }
}

export async function triggerLiveScan() {
  return apiFetch<any>("/disruptions/ingest", { method: "POST" })
}

export async function triggerManualSignal(rawSignal: string, source: string = "manual", companyId?: string) {
  return apiFetch<any>("/disruptions/trigger", {
    method: "POST",
    body: JSON.stringify({
      raw_signal: rawSignal,
      source,
      company_id: companyId,
    }),
  })
}

export async function approveDecision(decisionId: string, approverId: string = "operator") {
  return apiFetch<any>(`/decisions/${decisionId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approver_id: approverId }),
  })
}

export async function rejectDecision(decisionId: string, approverId: string = "operator") {
  return apiFetch<any>(`/decisions/${decisionId}/reject`, {
    method: "POST",
    body: JSON.stringify({ approver_id: approverId }),
  })
}

export async function fetchTopologyNetwork() {
  return apiFetch<any>("/topology/network")
}

export async function fetchSuppliers() {
  return apiFetch<{ items: any[]; total: number }>("/suppliers")
}

export async function createSupplier(payload: Record<string, any>) {
  return apiFetch<any>("/suppliers", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function fetchTasks() {
  return apiFetch<{ items: any[]; total: number }>("/tasks")
}

export async function createTask(payload: Record<string, any>) {
  return apiFetch<any>("/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function updateTask(taskId: string, payload: Record<string, any>) {
  return apiFetch<any>(`/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}
