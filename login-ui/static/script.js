document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    const button = form.querySelector("button");

    form.addEventListener("submit", function () {
        button.disabled = true;
        button.innerHTML = `<span class="spinner"></span> Logging in...`;
    });

    // Toast function
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add("show");
        }, 100);

        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Example: show error if login failed (server sets ?error=1 in URL)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("error")) {
        showToast("❌ Invalid username or password!", "error");
    }
    if (urlParams.get("success")) {
        showToast("✅ Login successful!", "success");
    }
});
