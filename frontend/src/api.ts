const API_URL = import.meta.env.VITE_API_URL ?? '/api'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: 'include',
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    const message =
      typeof detail?.detail === 'string' ? detail.detail : `Ошибка запроса (${response.status})`
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

// --- типы ---

export type Role = 'manager' | 'technologist'

export type User = {
  id: number
  email: string
  full_name: string
  role: Role
}

export type Fabric = {
  id: number
  name: string
  width_cm: number
  price_per_m: number
  density: string | null
  is_active: boolean
}

export type Hardware = {
  id: number
  name: string
  unit: 'piece' | 'per_item'
  price: number
  is_active: boolean
}

export type Branding = {
  id: number
  name: string
  price: number
  is_active: boolean
}

export type ProductType = {
  id: number
  name: string
  base_sewing_hours: number
  is_active: boolean
}

export type ComplexityLevel = {
  id: number
  code: string
  name: string
  factor: number
}

export type Contractor = {
  id: number
  name: string
  contact_email: string | null
  phone: string | null
}

export type LogoMeta = {
  has_logo: boolean
  updated_at: string | null
}

export type Settings = {  sewing_normohour: number
  cutting_normohour: number
  waste_coefficient: number
  cutting_rate_parts_per_hour: number
  seam_allowance_cm: number
  lining_factor: number
  hood_factor: number
  pockets_factor: number
  daily_capacity_units: number
  lead_time_buffer_days: number
  company_name: string
  company_requisites: string
}

export type Dictionaries = {
  fabrics: Fabric[]
  hardware: Hardware[]
  branding: Branding[]
  product_types: ProductType[]
  complexity_levels: ComplexityLevel[]
  contractors: Contractor[]
  settings: Settings
}

export type PartInput = {
  name: string
  length_cm: number
  width_cm: number
  count_per_unit: number
}

export type EstimateRequest = {
  product_type_id: number
  complexity_id: number
  quantity: number
  has_lining: boolean
  has_hood: boolean
  has_pockets: boolean
  fabric_id: number
  fabric_width_cm?: number
  fabric_price_per_m?: number
  waste_coefficient?: number
  seam_allowance_cm?: number
  parts: PartInput[]
  hardware: { hardware_id: number; qty_per_unit: number }[]
  branding: { branding_id: number; positions: number }[]
  contractor_id?: number | null
  contractor_name?: string | null
  notes?: string | null
}

export type LayoutRow = {
  pieces: number
  height_cm: number
  used_width_cm: number
}

export type EstimatePreview = {
  sewing: {
    base_hours_per_unit: number
    complexity_factor: number
    modifier: number
    hours: number
    normohour: number
    cost: number
  }
  cutting: {
    pieces_total: number
    rows: LayoutRow[]
    rows_total: number
    rows_truncated: boolean
    length_cm: number
    length_with_waste_m: number
    approximate: boolean
    hours: number
    normohour: number
    cost: number
  }
  material: {
    fabric_name: string
    roll_width_cm: number
    length_with_waste_m: number
    price_per_m: number
    waste_coefficient: number
    seam_allowance_cm: number
    cost: number
  }
  hardware: { hardware_id: number | null; name: string; unit: string; price: number; qty_per_unit: number; total: number }[]
  branding: { branding_id: number | null; name: string; price: number; positions: number; total: number }[]
  totals: {
    material_cost: number
    cutting_cost: number
    sewing_cost: number
    hardware_cost: number
    branding_cost: number
    total_cost: number
    unit_cost: number
    quantity: number
  }
  lead_time_days: number
  warnings: string[]
}

export type EstimateListItem = {
  id: number
  number: string
  created_at: string
  contractor_name: string | null
  product_type_name: string
  quantity: number
  total_cost: number
  unit_cost: number
  author_name: string | null
}

export type Estimate = {
  id: number
  number: string
  created_at: string
  author_id: number
  author_name: string | null
  product_type_id: number
  complexity_id: number
  fabric_id: number | null
  contractor_name: string | null
  contractor_email: string | null
  product_type_name: string
  complexity_name: string
  complexity_factor: number
  quantity: number
  has_lining: boolean
  has_hood: boolean
  has_pockets: boolean
  fabric_name: string
  fabric_width_cm: number
  fabric_price_per_m: number
  waste_coefficient: number
  seam_allowance_cm: number
  sewing_hours: number
  sewing_normohour: number
  sewing_cost: number
  cutting_hours: number
  cutting_normohour: number
  cutting_cost: number
  material_length_m: number
  material_cost: number
  hardware_cost: number
  branding_cost: number
  total_cost: number
  unit_cost: number
  lead_time_days: number
  notes: string | null
  share_token: string | null
  parts: { name: string; length_cm: number; width_cm: number; count_per_unit: number }[]
  hardware_items: { hardware_id: number | null; name: string; unit: string; price: number; qty_per_unit: number; total: number }[]
  branding_items: { branding_id: number | null; name: string; price: number; positions: number; total: number }[]
}

// --- методы ---

export const api = {
  login: (email: string, password: string) =>
    request<User>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  me: () => request<User>('/auth/me'),

  dictionaries: () => request<Dictionaries>('/dictionaries'),

  preview: (payload: EstimateRequest) =>
    request<EstimatePreview>('/estimates/preview', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createEstimate: (payload: EstimateRequest) =>
    request<Estimate>('/estimates', { method: 'POST', body: JSON.stringify(payload) }),
  listEstimates: (params: Record<string, string | number | undefined> = {}) => {
    const search = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') search.set(key, String(value))
    })
    const query = search.toString()
    return request<{ items: EstimateListItem[]; total: number }>(
      `/estimates${query ? `?${query}` : ''}`,
    )
  },
  getEstimate: (id: number) => request<Estimate>(`/estimates/${id}`),
  deleteEstimate: (id: number) => request<void>(`/estimates/${id}`, { method: 'DELETE' }),
  shareEstimate: (id: number) =>
    request<{ token: string; path: string }>(`/estimates/${id}/share`, { method: 'POST' }),
  sendEmail: (id: number, payload: { to: string; message?: string | null }) =>
    request<{ status: 'sent' | 'outbox'; detail: string; to: string }>(
      `/estimates/${id}/send-email`,
      { method: 'POST', body: JSON.stringify(payload) },
    ),
  getSharedEstimate: (token: string) => request<Estimate>(`/public/estimates/${token}`),

  getLogoMeta: () => request<LogoMeta>('/public/logo/meta'),
  uploadLogo: async (file: File) => {
    const body = new FormData()
    body.append('file', file)
    const response = await fetch(`${API_URL}/dictionaries/logo`, {
      method: 'POST',
      credentials: 'include',
      body,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      const message =
        typeof detail?.detail === 'string' ? detail.detail : `Ошибка загрузки (${response.status})`
      throw new ApiError(message, response.status)
    }
    return (await response.json()) as LogoMeta
  },
  deleteLogo: () => request<void>('/dictionaries/logo', { method: 'DELETE' }),

  createContractor: (payload: { name: string; contact_email?: string | null; phone?: string | null }) =>
    request<Contractor>('/contractors', { method: 'POST', body: JSON.stringify(payload) }),

  saveFabric: (payload: Partial<Fabric> & { id?: number }) =>
    payload.id
      ? request<Fabric>(`/dictionaries/fabrics/${payload.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : request<Fabric>('/dictionaries/fabrics', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
  saveHardware: (payload: Partial<Hardware> & { id?: number }) =>
    payload.id
      ? request<Hardware>(`/dictionaries/hardware/${payload.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : request<Hardware>('/dictionaries/hardware', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
  saveBranding: (payload: Partial<Branding> & { id?: number }) =>
    payload.id
      ? request<Branding>(`/dictionaries/branding/${payload.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : request<Branding>('/dictionaries/branding', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
  saveProductType: (payload: Partial<ProductType> & { id?: number }) =>
    payload.id
      ? request<ProductType>(`/dictionaries/product-types/${payload.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : request<ProductType>('/dictionaries/product-types', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
  saveComplexity: (payload: Partial<ComplexityLevel> & { id?: number }) =>
    payload.id
      ? request<ComplexityLevel>(`/dictionaries/complexity/${payload.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : request<ComplexityLevel>('/dictionaries/complexity', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
  saveSettings: (payload: Partial<Settings>) =>
    request<Settings>('/dictionaries/settings', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
}

export const pdfUrl = (id: number) => `${API_URL}/estimates/${id}/pdf`
export const sharedPdfUrl = (token: string) => `${API_URL}/public/estimates/${token}/pdf`

export function logoUrl(version?: string | number): string {
  if (!version) return `${API_URL}/public/logo`
  const stamp = typeof version === 'number' ? version : new Date(version).getTime()
  return `${API_URL}/public/logo?v=${Number.isFinite(stamp) ? stamp : Date.now()}`
}

export function exportCsvUrl(params: Record<string, string | number | undefined> = {}): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value))
  })
  const query = search.toString()
  return `${API_URL}/estimates/export.csv${query ? `?${query}` : ''}`
}
