const API = 'https://tamilai-backend-ev5r.onrender.com/api';
    let currentRole = 'student';

    // ── Panel switch ─────────────────────────────────────────
    function showPanel(name) {
      ['login','register'].forEach(p => {
        document.getElementById(`panel-${p}`).style.display = p === name ? 'block' : 'none';
        document.getElementById(`tab-${p}`).classList.toggle('active', p === name);
      });
    }

    // ── Role selection ───────────────────────────────────────
    function selectRole(role) {
      currentRole = role;
      ['student','teacher','parent'].forEach(r => {
        document.getElementById(`role-${r}`).classList.toggle('selected', r === role);
      });
      document.getElementById('student-fields').style.display = role === 'student' ? 'grid' : 'none';
    }

    // ── Password toggle ──────────────────────────────────────
    function togglePwd(id, btn) {
      const input = document.getElementById(id);
      input.type = input.type === 'password' ? 'text' : 'password';
      btn.textContent = input.type === 'password' ? '👁' : '🙈';
    }

    // ── Password strength ────────────────────────────────────
    function checkStrength(val) {
      const fill  = document.getElementById('strength-fill');
      const label = document.getElementById('strength-label');
      let score = 0;
      if (val.length >= 6)  score++;
      if (val.length >= 10) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;

      const levels = [
        { w: '0%',   color: '',                  text: 'Enter a password' },
        { w: '25%',  color: '#EF4444',           text: 'Too weak' },
        { w: '50%',  color: '#F59E0B',           text: 'Fair' },
        { w: '75%',  color: '#3B82F6',           text: 'Good' },
        { w: '100%', color: '#10B981',           text: 'Strong ✓' },
      ];
      const l = levels[Math.min(score, 4)];
      fill.style.width = l.w;
      fill.style.background = l.color;
      label.textContent = l.text;
      label.style.color = l.color || '#94A3B8';
    }

    // ── Helpers ──────────────────────────────────────────────
    function showError(id, msg) {
      const el = document.getElementById(id);
      el.textContent = msg; el.classList.add('show');
    }
    function clearErrors(prefix) {
      document.querySelectorAll(`[id^="${prefix}"]`).forEach(el => el.classList.remove('show'));
    }
    function setLoading(prefix, loading) {
      document.getElementById(`${prefix}-spinner`).style.display = loading ? 'block' : 'none';
      document.getElementById(`${prefix}-btn-text`).style.display = loading ? 'none' : 'inline';
      document.getElementById(`${prefix}-btn`).disabled = loading;
    }

    function showSuccess(name) {
      document.getElementById('panel-login').style.display    = 'none';
      document.getElementById('panel-register').style.display = 'none';
      document.querySelector('.auth-tabs').style.display      = 'none';
      const sc = document.getElementById('success-screen');
      sc.style.display = 'block';
      setTimeout(() => { document.getElementById('progress-bar').style.width = '100%'; }, 100);
      setTimeout(() => { window.location.href = 'dashboard.html'; }, 2200);
    }

    // ── Login (Supabase) ────────────────────────────────
async function handleLogin(e) {
    e.preventDefault();

    clearErrors("login");

    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;

    let ok = true;

    if (!email) {
        showError("login-email-err", "Email is required");
        ok = false;
    }

    if (!password) {
        showError("login-pwd-err", "Password is required");
        ok = false;
    }

    if (!ok) return;

    setLoading("login", true);

    try {

        const { data, error } =
            await supabaseClient.auth.signInWithPassword({
                email,
                password
            });

        if (error) {
    console.error(error);

    const banner = document.getElementById("login-error");
    banner.textContent = error.message;
    banner.classList.add("show");
    return;
}

        const user = data.user;

        const { data: profile } =
    await supabaseClient
        .from("profiles")
        .select("*")
        .eq("id", user.id)
        .single();

        localStorage.setItem(
            "tamilai_user",
            JSON.stringify(profile)
        );

        showSuccess(profile.full_name);

        setTimeout(() => {
            window.location.href = "dashboard.html";
        }, 1000);

    }
    catch (err) {
    console.error(err);

    const banner = document.getElementById("login-error");
    banner.textContent = err.message || JSON.stringify(err);
    banner.classList.add("show");
}
    finally {
        setLoading("login", false);
    }
}

    
    // ── Register (Supabase) ─────────────────────────────
async function handleRegister(e) {

    e.preventDefault();

    clearErrors("reg");

    const name = document.getElementById("reg-name").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    const cls = document.getElementById("reg-class").value;
    const school = document.getElementById("reg-school").value;

    let ok = true;

    if (!name) {
        showError("reg-name-err", "Name is required");
        ok = false;
    }

    if (!email) {
        showError("reg-email-err", "Email is required");
        ok = false;
    }

    if (password.length < 6) {
        showError("reg-pwd-err", "Minimum 6 characters");
        ok = false;
    }

    if (!ok) return;

    setLoading("reg", true);

    try {

        const { data, error } =
            await supabaseClient.auth.signUp({

                email,

                password

            });

        if (error) {

            const banner =
                document.getElementById("register-error");

            banner.textContent = error.message;

            banner.classList.add("show");

            return;

        }

        const user = data.user;

        const { error: profileError } =
    await supabaseClient
        .from("profiles")
        .insert({
                    id: user.id,

                    full_name: name,

                    role: currentRole,

                    class_grade: cls,

                    school: school

                });

        if (profileError) {

            console.error(profileError);

            const banner =
                document.getElementById("register-error");

            banner.textContent =
                profileError.message;

            banner.classList.add("show");

            return;

        }

        showSuccess(name);

        setTimeout(() => {

            showPanel("login");

        }, 1000);

    }

    catch (err) {

        console.error(err);

        const banner =
            document.getElementById("register-error");

        banner.textContent =
            "Registration failed.";

        banner.classList.add("show");

    }

    finally {

        setLoading("reg", false);

    }

}

    // Auto-show register tab if URL has ?register
    if (location.search.includes('register')) showPanel('register');