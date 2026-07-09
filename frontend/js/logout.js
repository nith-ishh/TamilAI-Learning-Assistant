async function logout() {

    const { error } = await supabaseClient.auth.signOut();

    if (error) {
        alert(error.message);
        return;
    }

    window.location.replace("auth.html");

}