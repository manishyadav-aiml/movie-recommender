(function () {
  "use strict";
  // 13. Password visibility toggle
  var btn = document.getElementById("toggle-password");
  var input = document.getElementById("password");
  if (btn && input) {
    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Hide" : "Show";
      btn.setAttribute("aria-pressed", String(show));
    });
  }
  // 17. Confirmation modal before deleting a message
  var dialog = document.getElementById("confirm-dialog");
  document.querySelectorAll("form[data-confirm-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (form.dataset.confirmed === "1" || !dialog || !dialog.showModal) return;
      e.preventDefault();
      dialog.addEventListener("close", function onClose() {
        dialog.removeEventListener("close", onClose);
        if (dialog.returnValue === "ok") { form.dataset.confirmed = "1"; form.submit(); }
      });
      dialog.showModal();
    });
  });
})();
