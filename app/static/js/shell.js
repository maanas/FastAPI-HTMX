// Shell behaviour: Flowbite init after every htmx load, and the log out button.
htmx.onLoad(function () {
  initFlowbite();
});

// htmx swaps 2xx only. An error answer the app rendered on purpose (handle_error in
// app/routes/view/errors.py) carries this header and is swapped; any other 4xx or
// 5xx (an unhandled error, the JSON 403 of the CSRF handler, a proxy page) is not.
// isError stays true, so the request still counts as failed.
document.addEventListener("htmx:beforeSwap", function (event) {
  if (event.detail.xhr.getResponseHeader("X-Error-Rendered") === "1") {
    event.detail.shouldSwap = true;
  }
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
