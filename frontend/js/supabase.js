const SUPABASE_URL = "https://ekwwhsjmuyascogdtnok.supabase.co";

const SUPABASE_KEY = "sb_publishable_VGMhWAEVKk_0qCWZaOcI1Q_nopCAPLx";

// Create ONE global client
window.supabaseClient = window.supabase.createClient(
    SUPABASE_URL,
    SUPABASE_KEY
);