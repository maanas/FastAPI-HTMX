// Upload page behaviour. Loaded by the shell on every page, so the listener
// sits on document.body (it survives swaps) and ignores anything that is not
// the upload form.

// After the upload request: reset the form and the Alpine state of #upload-page.
document.body.addEventListener("htmx:afterRequest", function (evt) {
  const form = evt.target.closest ? evt.target.closest("#upload-form") : null;
  if (!form || evt.target !== form) {
    return;
  }
  if (evt.detail.successful) {
    form.reset();
  }
  resetUploadState(evt.detail.successful);
});

// Ends the loading state; after a successful upload the chosen file is cleared too.
function resetUploadState(successful) {
  const component = document.getElementById("upload-page");
  if (!component) {
    return;
  }
  const data = Alpine.$data(component);
  data.isLoading = false;
  if (successful) {
    data.fileLoaded = false;
    data.fileName = "";
  }
}
