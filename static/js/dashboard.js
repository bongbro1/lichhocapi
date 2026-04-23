// Dashboard Logic - Obfuscated Version Pending
(function () {
    const appConfig = document.getElementById('app-config').dataset;

    const sessionPayload = {
        username: appConfig.username,
        domain: appConfig.domain
    };

    const state = {
        users: [],
        selectedStudentId: ""
    };

    const usersGrid = document.getElementById("usersGrid");
    const output = document.getElementById("apiOutput");
    const selectedUserCard = document.getElementById("selectedUserCard");
    const selectedUserName = document.getElementById("selectedUserName");
    const selectedUserMeta = document.getElementById("selectedUserMeta");
    const studentIdInput = document.getElementById("studentId");
    const userSearchInput = document.getElementById("userSearch");

    function setOutput(payload) {
        output.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
    }

    function setSelectedUser(user) {
        state.selectedStudentId = user?.studentId || "";
        studentIdInput.value = state.selectedStudentId;

        if (!user) {
            selectedUserCard.classList.add("hidden");
            selectedUserName.textContent = "";
            selectedUserMeta.textContent = "";
            return;
        }

        selectedUserCard.classList.remove("hidden");
        selectedUserName.textContent = user.name || "Người dùng không xác định";
        selectedUserMeta.textContent = [
            user.studentId,
            user.className,
            user.schoolName
        ].filter(Boolean).join(" • ");
    }

    function renderUsers(usersToRender) {
        usersGrid.innerHTML = "";

        if (!usersToRender || !usersToRender.length) {
            usersGrid.innerHTML = `
                <div class="col-span-full rounded-2xl border border-dashed border-white/10 bg-slate-900/60 p-6 text-center text-sm text-slate-400">
                    Không tìm thấy người dùng nào.
                </div>
            `;
            return;
        }

        usersToRender.forEach((user) => {
            const card = document.createElement("button");
            card.type = "button";
            card.className = "rounded-2xl border border-white/10 bg-slate-900/70 p-4 text-left transition hover:border-sky-400/60 hover:bg-slate-900";
            card.onclick = () => setSelectedUser(user);

            card.innerHTML = `
                <div class="flex items-start gap-3">
                    <div class="h-11 w-11 shrink-0 overflow-hidden rounded-2xl bg-slate-800">
                        ${user.avatar ? `<img src="${user.avatar}" alt="${user.name}" class="h-full w-full object-cover">` : `<div class="flex h-full w-full items-center justify-center text-sm font-semibold text-slate-300">${(user.name || "U").slice(0, 1).toUpperCase()}</div>`}
                    </div>
                    <div class="min-w-0">
                        <p class="truncate text-sm font-semibold text-white">${user.name || "Người dùng không xác định"}</p>
                        <p class="truncate text-xs text-slate-400">${user.studentId || ""}</p>
                        <p class="mt-1 truncate text-xs text-slate-500">${[user.className, user.schoolName].filter(Boolean).join(" • ")}</p>
                    </div>
                </div>
            `;
            usersGrid.appendChild(card);
        });
    }

    async function handleAction(endpoint, method = "GET", body = null) {
        setOutput("Đang xử lý...");
        try {
            const options = {
                method,
                headers: { "Content-Type": "application/json" }
            };
            if (body) options.body = JSON.stringify({ ...sessionPayload, ...body });
            else if (method === "POST") options.body = JSON.stringify(sessionPayload);

            const res = await fetch(endpoint, options);
            const data = await res.json();
            setOutput(data);
            return data;
        } catch (err) {
            setOutput({ error: err.message });
        }
    }

    // Event Listeners
    window.getUsers = async (query = "") => {
        const data = await handleAction(`/api/admin/users?query=${encodeURIComponent(query)}`);
        if (data?.success && data?.data) {
            state.users = data.data;
            renderUsers(state.users);
        }
    };

    window.getSchedule = () => {
        if (!state.selectedStudentId) return alert("Vui lòng chọn người dùng");
        handleAction("/schedule", "POST"); // Dùng sessionPayload tự động
    };

    window.getNotifications = async (event) => {
        if (event) event.preventDefault();
        const studentId = document.getElementById("studentId").value.trim();
        const title = document.getElementById("notificationTitle").value.trim();
        const body = document.getElementById("notificationBody").value.trim();

        if (!studentId || !title || !body) return alert("Vui lòng nhập đầy đủ thông tin");

        handleAction("/api/admin/system-notifications", "POST", {
            studentId,
            title,
            body,
            data: { source: "admin_dashboard" }
        });
    };

    window.getGrades = () => {
        if (!state.selectedStudentId) return alert("Vui lòng chọn người dùng");
        handleAction("/student_marks", "POST");
    };

    userSearchInput.addEventListener("input", (e) => {
        const term = e.target.value.toLowerCase();
        window.getUsers(term); // Gọi trực tiếp API search của backend
    });

    document.getElementById("notificationForm").addEventListener("submit", window.getNotifications);
    document.getElementById("fetchScheduleBtn").addEventListener("click", window.getSchedule);
    document.getElementById("fetchMarksBtn").addEventListener("click", window.getGrades);
    document.getElementById("clearOutputBtn").addEventListener("click", () => setOutput("Sẵn sàng."));

    // Initial load
    window.getUsers();
})();
