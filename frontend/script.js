"use strict";

const DEFAULT_API_PORT = 5000;

function resolveApiBase() {
  if (typeof window === "undefined") {
    return `http://localhost:${DEFAULT_API_PORT}/api`;
  }

  if (window.API_BASE_URL) {
    return window.API_BASE_URL.replace(/\/+$/, "");
  }

  const { location } = window;
  if (
    location &&
    typeof location.origin === "string" &&
    location.origin !== "null" &&
    location.protocol.startsWith("http")
  ) {
    return `${location.origin.replace(/\/+$/, "")}/api`;
  }

  if (window.API_PORT) {
    return `http://localhost:${String(window.API_PORT).trim()}/api`;
  }

  return `http://localhost:${DEFAULT_API_PORT}/api`;
}

const API_BASE = resolveApiBase();

const AUTH_FLAG_KEY = "auth:isAuthenticated";
const AUTH_USER_KEY = "auth:username";
const LOGIN_SUCCESS_KEY = "auth:login-success";

function isAuthenticated() {
  return localStorage.getItem(AUTH_FLAG_KEY) === "true";
}

function setSession(username) {
  localStorage.setItem(AUTH_FLAG_KEY, "true");
  localStorage.setItem(AUTH_USER_KEY, username);
}

function clearSession() {
  localStorage.removeItem(AUTH_FLAG_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

function getStoredUsername() {
  return localStorage.getItem(AUTH_USER_KEY) || "";
}

function showMessage(element, text = "", type = "info") {
  if (!element) {
    return;
  }

  const output = text.trim();
  element.textContent = output;
  element.className = "message";

  if (type && type !== "info") {
    element.classList.add(type);
  }

  if (!output) {
    element.classList.add("hidden");
  } else {
    element.classList.remove("hidden");
  }
}

function handleSignupPage() {
  if (isAuthenticated()) {
    window.location.href = "dashboard.html";
    return;
  }

  const form = document.getElementById("signup-form");
  const message = document.getElementById("signup-message");

  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage(message, "");

    const username = form.username.value.trim();
    const email = form.email ? form.email.value.trim() : "";
    const password = form.password.value.trim();

    if (!username || !password || !email) {
      showMessage(
        message,
        "Please provide username, email, and password.",
        "error"
      );
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Signup failed.");
      }

      showMessage(
        message,
        "Account created. Check your email for the OTP after logging in.",
        "success"
      );
      form.reset();
    } catch (err) {
      showMessage(message, err.message, "error");
    }
  });
}

function handleLoginPage() {
  if (isAuthenticated()) {
    window.location.href = "dashboard.html";
    return;
  }

  const loginForm = document.getElementById("login-form");
  const verifyForm = document.getElementById("verify-form");
  const loginMessage = document.getElementById("login-message");
  const otpMessage = document.getElementById("otp-message");
  const otpSection = document.getElementById("otp-section");
  const otpInput = document.getElementById("otp-input");
  const otpInfo = document.getElementById("otp-info");

  if (!loginForm || !verifyForm) {
    return;
  }

  let pendingUsername = "";

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    pendingUsername = "";
    showMessage(loginMessage, "");
    showMessage(otpMessage, "");
    if (otpSection) {
      otpSection.classList.add("hidden");
    }

    const username = loginForm.username.value.trim();
    const password = loginForm.password.value.trim();

    if (!username || !password) {
      showMessage(loginMessage, "Please enter username and password.", "error");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Login failed.");
      }

      pendingUsername = username;
      const emailHint = data.email_hint || "your email address on file";
      showMessage(loginMessage, `We sent a one-time code to ${emailHint}.`, "success");

      if (otpInfo) {
        otpInfo.textContent = data.email_hint
          ? `Enter the 6-digit code we emailed to ${data.email_hint}.`
          : "Enter the 6-digit code we emailed to your account.";
      }

      if (otpSection) {
        otpSection.classList.remove("hidden");
      }
      if (otpInput) {
        otpInput.value = "";
        otpInput.focus();
      }
    } catch (err) {
      showMessage(loginMessage, err.message, "error");
    }
  });

  verifyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage(otpMessage, "");

    if (!pendingUsername) {
      showMessage(otpMessage, "Please request a new OTP by logging in first.", "error");
      return;
    }

    const otp = otpInput ? otpInput.value.trim() : "";

    if (!otp) {
      showMessage(otpMessage, "Enter the 6-digit OTP.", "error");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: pendingUsername, otp }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "OTP verification failed.");
      }

      sessionStorage.setItem(LOGIN_SUCCESS_KEY, "You successfully logged in.");
      setSession(pendingUsername);
      window.location.href = "dashboard.html";
    } catch (err) {
      showMessage(otpMessage, err.message, "error");
    }
  });
}

function handleDashboardPage() {
  if (!isAuthenticated()) {
    window.location.href = "login.html";
    return;
  }

  const userDisplay = document.getElementById("dashboard-user");
  const logoutBtn = document.getElementById("logout-btn");
  const statusMessage = document.getElementById("dashboard-message");
  const username = getStoredUsername();
  const loginSuccessText = sessionStorage.getItem(LOGIN_SUCCESS_KEY);

  if (userDisplay) {
    userDisplay.textContent = username || "User";
  }

  if (statusMessage && loginSuccessText) {
    showMessage(statusMessage, loginSuccessText, "success");
    sessionStorage.removeItem(LOGIN_SUCCESS_KEY);
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      clearSession();
      sessionStorage.removeItem(LOGIN_SUCCESS_KEY);
      window.location.href = "login.html";
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page || "";

  switch (page) {
    case "signup":
      handleSignupPage();
      break;
    case "login":
      handleLoginPage();
      break;
    case "dashboard":
      handleDashboardPage();
      break;
    default:
      break;
  }
});
