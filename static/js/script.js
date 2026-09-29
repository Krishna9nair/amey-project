document.addEventListener("DOMContentLoaded", () => {
    // Bootstrap-style client-side validation, plus password match check
    document.querySelectorAll("form.needs-validation").forEach((form) => {
        const password = form.querySelector("#password");
        const confirmPassword = form.querySelector("#confirm_password");

        const checkMatch = () => {
            if (password && confirmPassword) {
                confirmPassword.setCustomValidity(
                    password.value === confirmPassword.value ? "" : "Passwords do not match"
                );
            }
        };
        password?.addEventListener("input", checkMatch);
        confirmPassword?.addEventListener("input", checkMatch);

        form.addEventListener("submit", (e) => {
            checkMatch();
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });

    // Show a free-text course field when "Other" department is chosen
    const departmentSelect = document.getElementById("department");
    const otherGroup = document.getElementById("departmentOtherGroup");
    const otherInput = document.getElementById("department_other");
    if (departmentSelect && otherGroup && otherInput) {
        const toggleOther = () => {
            const isOther = departmentSelect.value === "Other";
            otherGroup.classList.toggle("d-none", !isOther);
            otherInput.required = isOther;
            if (isOther) {
                otherInput.focus();
            } else {
                otherInput.value = "";
            }
        };
        departmentSelect.addEventListener("change", toggleOther);
    }

    // Confirmation prompt for destructive actions
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (e) => {
            if (!window.confirm(form.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Show / hide password
    document.querySelectorAll("[data-toggle-password]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const input = document.getElementById(btn.dataset.togglePassword);
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            btn.innerHTML = show ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
        });
    });

    // Live search + category filter for card / table listings
    const searchInput = document.getElementById("liveSearch");
    const filterButtons = document.querySelectorAll(".filter-btn");
    const items = document.querySelectorAll(".searchable-item");
    const emptyState = document.getElementById("noResults");
    let activeCategory = "all";

    const applyFilters = () => {
        const term = (searchInput?.value || "").trim().toLowerCase();
        let visible = 0;
        items.forEach((item) => {
            const matchesText = item.dataset.search.toLowerCase().includes(term);
            const matchesCategory = activeCategory === "all" || item.dataset.category === activeCategory;
            const show = matchesText && matchesCategory;
            item.classList.toggle("d-none", !show);
            if (show) visible++;
        });
        emptyState?.classList.toggle("d-none", visible !== 0);
    };

    searchInput?.addEventListener("input", applyFilters);
    filterButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            filterButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            activeCategory = btn.dataset.filter;
            applyFilters();
        });
    });

    // Auto-dismiss flash messages
    document.querySelectorAll(".flash-container .alert").forEach((alert) => {
        setTimeout(() => bootstrap.Alert.getOrCreateInstance(alert).close(), 5000);
    });

    // Live countdown on event detail page
    const countdown = document.getElementById("countdown");
    if (countdown) {
        const target = new Date(countdown.dataset.target).getTime();
        const tick = () => {
            const diff = target - Date.now();
            if (diff <= 0) {
                countdown.textContent = "Event has started!";
                return;
            }
            const d = Math.floor(diff / 86400000);
            const h = Math.floor((diff % 86400000) / 3600000);
            const m = Math.floor((diff % 3600000) / 60000);
            const s = Math.floor((diff % 60000) / 1000);
            countdown.textContent = `${d}d ${h}h ${m}m ${s}s`;
            setTimeout(tick, 1000);
        };
        tick();
    }
});
