document.addEventListener("alpine:init", () => {
  Alpine.data("register", () => ({
    message: "",
    showUsernameError: false,
    showRepeatPasswordError: false,
    showPasswordError: false,
    showPassword: false,
    showServerError: false,
    username: "",
    password: "",
    repeatPassword: "",
    emailPattern: /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/,
    csrfToken: "",
    passwordPattern: /^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$/,
    init() {
      // The token comes from the server in data-csrf-token on the component root
      this.csrfToken = this.$el.dataset.csrfToken || "";
      this.$watch("username", () => this.checkUsername());
      this.$watch("password", () => {
        this.validatePassword();
        this.passwordsMatch();
      });
      this.$watch("showServerError", (value) => {
        if (value) {
          setTimeout(() => {
            this.showServerError = false;
          }, 3000);
        }
      });
      this.$watch("repeatPassword", () => this.passwordsMatch());
    },
    get submitDisabled() {
      return (
        !this.username ||
        !this.password ||
        !this.repeatPassword ||
        this.showUsernameError ||
        this.showPasswordError ||
        this.showRepeatPasswordError
      );
    },
    get submitClass() {
      return this.submitDisabled
        ? "text-fg-disabled bg-disabled border-default-medium cursor-not-allowed"
        : "text-white bg-brand border-transparent hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium";
    },
    checkUsername() {
      if (!this.username) {
        this.showUsernameError = false;
      } else if (!this.emailPattern.test(this.username)) {
        this.showUsernameError = true;
        this.showPassword = false;
      } else {
        this.showUsernameError = false;
        this.showPassword = true;
      }
    },
    passwordsMatch() {
      if (!this.repeatPassword) {
        this.showRepeatPasswordError = false;
      } else if (this.password !== this.repeatPassword) {
        this.showRepeatPasswordError = true;
      } else {
        this.showRepeatPasswordError = false;
      }
    },
    validatePassword() {
      if (!this.password) {
        this.showPasswordError = false;
      } else if (!this.passwordPattern.test(this.password)) {
        this.showPasswordError = true;
      } else {
        this.showPasswordError = false;
      }
    },
    async registerUser() {
      if (!this.username || !this.password || !this.repeatPassword) {
        this.message = "Please fill in all fields";
        this.showServerError = true;
        return;
      }
      if (this.password !== this.repeatPassword) {
        this.message = "Passwords do not match";
        this.showServerError = true;
        return;
      }
      const formData = {
        email: this.username,
        password: this.password,
      };
      try {
        const response = await fetch("/auth/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": this.csrfToken,
          },
          body: JSON.stringify(formData),
        });
        if (response.status === 201) {
          this.message = "User created successfully";
          this.showServerError = true;
          setTimeout(() => {
            window.location.href = "/";
          }, 1000);
        } else if (response.status === 400) {
          this.message = "User already exists";
          this.showServerError = true;
        } else if (response.status === 403) {
          this.message = "Your session expired. Reload the page and try again.";
          this.showServerError = true;
        } else {
          this.message = "Registration failed. Try again.";
          this.showServerError = true;
        }
      } catch (error) {
        this.message = "Registration failed. Try again.";
        this.showServerError = true;
      }
    },
  }));
});

document.addEventListener("alpine:init", () => {
  // Alpine component to control the login form and other attributes for login page
  Alpine.data("login", () => ({
    username: "",
    password: "",
    message: "",
    showError: false,
    showUsernameError: false,
    showPasswordDiv: false,
    showInputButton: false,
    csrfToken: "",

    init() {
      // The token comes from the server in data-csrf-token on the component root
      this.csrfToken = this.$el.dataset.csrfToken || "";
      this.$watch("showError", (value) => {
        if (value) {
          setTimeout(() => {
            this.showError = false;
          }, 3000);
        }
      });
    },

    checkLoginUsername() {
      const emailPattern = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
      if (this.username === "") {
        this.showUsernameError = true;
      } else if (!emailPattern.test(this.username)) {
        this.showUsernameError = true;
      } else {
        this.showUsernameError = false;
        this.showPasswordDiv = true;
      }
    },

    setCookie() {
      if (!this.password) {
        this.message = "Enter your password";
        this.showError = true;
        return;
      }
      const formData = new URLSearchParams();
      formData.append("grant_type", "password");
      formData.append("username", this.username);
      formData.append("password", this.password);
      formData.append("scope", "");
      formData.append("client_id", "");
      formData.append("client_secret", "");

      fetch("/auth/jwt/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRF-Token": this.csrfToken,
        },
        body: formData,
      })
        .then((response) => {
          if (response.status === 204) {
            // Successful login, navigate to /dashboard
            window.location.href = "/dashboard";
          } else if (response.status === 400) {
            this.message = "Incorrect username or password";
            this.showError = true;
          } else if (response.status === 403) {
            this.message = "Your session expired. Reload the page and try again.";
            this.showError = true;
          } else {
            this.message = "Login failed. Try again.";
            this.showError = true;
          }
        })
        .catch(() => {
          this.message = "Login failed. Try again.";
          this.showError = true;
        });
    },
  }));
});

document.addEventListener("alpine:init", () => {
  // Alert state shared by the list pages and the upload page. showAlertMessage() below
  // sets isUpdated / isAdded / isDeleted / isError and message; each flag resets after 3 seconds.
  const alertState = () => ({
    isLoading: false,
    isUpdated: false,
    isAdded: false,
    isDeleted: false,
    isError: false,
    message: "",
    watchAlerts() {
      for (const flag of ["isUpdated", "isAdded", "isDeleted", "isError"]) {
        this.$watch(flag, (value) => {
          if (value) {
            setTimeout(() => {
              this[flag] = false;
            }, 3000);
          }
        });
      }
    },
  });

  // Roles, groups and users list pages
  Alpine.data("listAlerts", () => ({
    ...alertState(),
    init() {
      this.watchAlerts();
    },
  }));

  // Upload page; upload.js also writes isLoading, fileLoaded and fileName
  Alpine.data("uploadPage", () => ({
    ...alertState(),
    fileLoaded: false,
    fileName: "",
    init() {
      this.watchAlerts();
    },
    selectFile(event) {
      const file = event.target.files[0];
      this.fileName = file ? file.name : "";
      this.fileLoaded = Boolean(file);
    },
    get readyMessage() {
      if (!this.fileName) {
        return "";
      }
      const base = this.fileName.split(".").slice(0, -1).join(".");
      return `'${base}' is ready for upload`;
    },
    get submitClass() {
      return this.fileLoaded && !this.isLoading
        ? "text-white bg-brand hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium"
        : "text-fg-disabled bg-disabled cursor-not-allowed";
    },
    startLoading() {
      this.isLoading = true;
    },
  }));
});

// Store pending alerts during page transitions
window.pendingAlerts = [];

// Handle direct HTMX swaps
document.body.addEventListener("htmx:afterSettle", function (evt) {
  try {
    const triggerHeader = evt.detail.xhr?.getResponseHeader("HX-Trigger");

    if (triggerHeader) {
      const triggerData = JSON.parse(triggerHeader);
      if (triggerData.showAlert) {
        showAlertMessage(triggerData.showAlert);
      }
    }

    // Check for pending alerts from page transitions
    while (window.pendingAlerts.length > 0) {
      const alertData = window.pendingAlerts.pop();
      showAlertMessage(alertData);
    }
  } catch (error) {
    console.error("Error handling afterSettle:", error);
  }
});

// Handle page transitions with HX-Location
document.body.addEventListener("showAlert", function (evt) {
  try {
    // A refused action (alert_error) leaves the page as it is: no swap follows, so
    // show it now instead of waiting for the next afterSettle
    if (evt.detail.type === "error") {
      showAlertMessage(evt.detail);
      return;
    }
    // Store alert for processing after page load
    window.pendingAlerts.push(evt.detail);
  } catch (error) {
    console.error("Error handling showAlert:", error);
  }
});

function showAlertMessage(alertData) {
  const component = htmx.find(`#${alertData.source}`);

  if (!component) {
    throw new Error(`No element with id '${alertData.source}' found`);
  }

  const data = Alpine.$data(component);

  // The delay lets a page that is still being swapped in settle; an error has no swap
  const delay = alertData.type === "error" ? 0 : 1000;

  setTimeout(function () {
    if (alertData.type === "updated") {
      data.isUpdated = true;
      data.message = alertData.message;
    } else if (alertData.type === "added") {
      data.isAdded = true;
      data.message = alertData.message;
    } else if (alertData.type === "deleted") {
      data.isDeleted = true;
      data.message = alertData.message;
    } else if (alertData.type === "error") {
      data.isError = true;
      data.message = alertData.message;
    }
  }, delay);
}
