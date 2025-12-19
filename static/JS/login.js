 function showMsg(text, ok=true) {
    const el = document.getElementById("msg");
    el.className = "msg " + (ok ? "ok" : "err");
    el.textContent = text;
  }

  async function onTelegramAuth(user) {
    try {
      showMsg("Проверка Telegram…", true);

      const res = await fetch("/auth/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(user),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showMsg(data.detail || "Ошибка авторизации", false);
        return;
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("account_id", data.account_id);

      window.location.href = "/";
    } catch (e) {
      showMsg("Ошибка сети: " + e.message, false);
    }
  }

  window.onTelegramAuth = onTelegramAuth;