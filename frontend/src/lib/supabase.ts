import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

export function supabaseEnabled(): boolean {
  return Boolean(url && anonKey)
}

export const supabase: SupabaseClient | null = supabaseEnabled()
  ? createClient(url as string, anonKey as string)
  : null