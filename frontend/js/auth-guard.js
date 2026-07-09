// auth-guard.js

async function checkAuth() {

    try {

        const { data, error } =
            await supabaseClient.auth.getSession();

        if (error || !data.session) {

            window.location.replace("auth.html");
            return;

        }

        window.currentUser = data.session.user;

    }

    catch (err) {

        console.error(err);
        window.location.replace("auth.html");

    }

}

checkAuth();