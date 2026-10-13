// Shell behaviour: Flowbite init after every htmx load, and the log out button.
htmx.onLoad(function () {
  initFlowbite();
});

document.addEventListener("click", function (event) {
  const button = event.target.closest("[data-logout]");
  if (!button) {
    return;
  }
  button.disabled = true;
  fetch("/auth/jwt/logout", { method: "POST" })
    .then(function (response) {
      if (!response.ok) {
        throw new Error("Log out failed");
      }
      window.location.href = "/login";
    })
    .catch(function (error) {
      console.error("Error:", error);
      button.disabled = false;
    });
});
