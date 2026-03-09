export type AcademicLevelKey = 'hs' | 'ug12' | 'ug34' | 'grad' | 'phd'
export type DeadlineKey = '14d' | '7d' | '5d' | '3d' | '48h' | '24h' | '8h' | '4h'

export const PRICING_TABLE: Record<DeadlineKey, Record<AcademicLevelKey, number>> = {
  '14d': { hs: 10, ug12: 15, ug34: 20, grad: 25, phd: 29 },
  '7d':  { hs: 16, ug12: 17, ug34: 21, grad: 27, phd: 31 },
  '5d':  { hs: 18, ug12: 19, ug34: 23, grad: 29, phd: 35 },
  '3d':  { hs: 20, ug12: 24, ug34: 28, grad: 33, phd: 37 },
  '48h': { hs: 24, ug12: 26, ug34: 30, grad: 36, phd: 45 },
  '24h': { hs: 27, ug12: 30, ug34: 32, grad: 39, phd: 50 },
  '8h':  { hs: 34, ug12: 39, ug34: 41, grad: 48, phd: 58 },
  '4h':  { hs: 39, ug12: 43, ug34: 51, grad: 61, phd: 73 },
}

/** Maps the job-form academic level string to a pricing table key */
export const ACADEMIC_LEVEL_PRICING_KEY: Record<string, AcademicLevelKey> = {
  'High School': 'hs',
  'Undergraduate 1-2': 'ug12',
  'Undergraduate 3-4': 'ug34',
  'Graduate': 'grad',
  'PhD': 'phd',
  'Professional': 'phd',
}

/** Resolves the deadline pricing tier from a deadline ISO string */
export function getDeadlineKey(deadlineIso: string): DeadlineKey {
  const hoursLeft = (new Date(deadlineIso).getTime() - Date.now()) / 3_600_000
  if (hoursLeft <= 4) return '4h'
  if (hoursLeft <= 8) return '8h'
  if (hoursLeft <= 24) return '24h'
  if (hoursLeft <= 48) return '48h'
  if (hoursLeft <= 72) return '3d'
  if (hoursLeft <= 120) return '5d'
  if (hoursLeft <= 168) return '7d'
  return '14d'
}

/** Calculates the suggested total price given academic level, pages and deadline */
export function calculateSuggestedPrice(
  academicLevel: string,
  pages: number,
  deadlineIso: string,
): number {
  const levelKey = ACADEMIC_LEVEL_PRICING_KEY[academicLevel] ?? 'ug12'
  const deadlineKey = getDeadlineKey(deadlineIso)
  return PRICING_TABLE[deadlineKey][levelKey] * pages
}

/** Per-page rate for a given level + deadline combo */
export function getPerPageRate(academicLevel: string, deadlineIso: string): number {
  const levelKey = ACADEMIC_LEVEL_PRICING_KEY[academicLevel] ?? 'ug12'
  const deadlineKey = getDeadlineKey(deadlineIso)
  return PRICING_TABLE[deadlineKey][levelKey]
}

/** Per-page rate using a deadline key directly (same as homepage calculator) */
export function getPerPageRateByKey(academicLevel: string, deadlineKey: DeadlineKey): number {
  const levelKey = ACADEMIC_LEVEL_PRICING_KEY[academicLevel] ?? 'ug12'
  return PRICING_TABLE[deadlineKey][levelKey]
}

/** Human-readable labels for deadline keys */
export const DEADLINE_LABELS: Record<DeadlineKey, string> = {
  '4h':  '4 Hours',
  '8h':  '8 Hours',
  '24h': '24 Hours',
  '48h': '48 Hours',
  '3d':  '3 Days',
  '5d':  '5 Days',
  '7d':  '7 Days',
  '14d': '14 Days',
}

/** Deadline key ordering (shortest to longest) */
export const DEADLINE_KEYS: DeadlineKey[] = ['4h', '8h', '24h', '48h', '3d', '5d', '7d', '14d']

/** Convert a deadline key to an absolute ISO datetime from now */
export function deadlineKeyToIso(key: DeadlineKey): string {
  const hoursMap: Record<DeadlineKey, number> = {
    '4h': 4, '8h': 8, '24h': 24, '48h': 48,
    '3d': 72, '5d': 120, '7d': 168, '14d': 336,
  }
  return new Date(Date.now() + hoursMap[key] * 3_600_000).toISOString()
}
