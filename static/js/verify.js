// Dynamic label for document number based on type
document.addEventListener("DOMContentLoaded", function () {
  const docType = document.getElementById("documentType");
  const docLabel = document.getElementById("documentLabel");
  const docInput = document.getElementById("document");

  docType.addEventListener("change", function () {
    const type = this.value;
    if (type === "pan") {
      docLabel.textContent = "PAN Number *";
      docInput.placeholder = "e.g. ABCDE1234F";
    } else if (type === "aadhaar") {
      docLabel.textContent = "Aadhaar Number *";
      docInput.placeholder = "e.g. 1234 5678 9012";
    } else if (type === "visa") {
      docLabel.textContent = "Visa Number *";
      docInput.placeholder = "e.g. V1234567";
    } else {
      docLabel.textContent = "Document Number *";
      docInput.placeholder = "Enter document number";
    }
  });

  // Form submission
  const form = document.getElementById("verifyForm");
  const submitBtn = document.getElementById("submitBtn");
  const errorDiv = document.getElementById("errorMessage");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const resultPlaceholder = document.getElementById("resultPlaceholder");
  const resultContent = document.getElementById("resultContent");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Hide previous error
    errorDiv.classList.add("hidden");
    errorDiv.textContent = "";

    // Gather form data
    const formData = new FormData(form);

    // Basic validation
    const docType = formData.get("documentType");
    const name = formData.get("name")?.trim();
    const docNum = formData.get("document")?.trim();
    const file = formData.get("documentFile");

    if (!docType) {
      showError("Please select a document type.");
      return;
    }
    if (!name) {
      showError("Please enter your name.");
      return;
    }
    if (!docNum) {
      showError("Please enter the document number.");
      return;
    }
    if (!file || file.size === 0) {
      showError("Please choose a document image.");
      return;
    }

    // Show loading
    loadingOverlay.classList.remove("hidden");
    submitBtn.disabled = true;

    try {
      const response = await fetch("/api/verify", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      console.log("Verification response:", data);

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Verification failed.");
      }

      // Display results
      displayResults(data);
    } catch (err) {
      showError(err.message || "An unexpected error occurred.");
      resultContent.classList.add("hidden");
      resultPlaceholder.classList.remove("hidden");
    } finally {
      loadingOverlay.classList.add("hidden");
      submitBtn.disabled = false;
    }
  });

  function showError(msg) {
    errorDiv.textContent = msg;
    errorDiv.classList.remove("hidden");
  }

  function displayResults(data) {
    // Hide placeholder, show results
    resultPlaceholder.classList.add("hidden");
    resultContent.classList.remove("hidden");

    // Risk
    const riskLevel = data.risk?.level || "Unknown";
    const riskScore = data.risk?.score ?? "--";
    document.getElementById("riskLevel").textContent = riskLevel;
    document.getElementById("riskLevel").className =
      "badge " + getRiskClass(riskLevel);
    document.getElementById("riskScore").textContent = riskScore;

    // Document
    const doc = data.document || {};
    document.getElementById("enteredNumber").textContent =
      doc.entered_number || "--";
    document.getElementById("detectedNumber").textContent =
      doc.detected_number || "Not detected";
    // number_match
    const matchEl = document.getElementById("numberMatch");
    if (doc.number_match === true) {
      matchEl.textContent = "✅ Match";
      matchEl.className = "status-badge status-success";
    } else if (doc.number_match === false) {
      matchEl.textContent = "❌ Mismatch";
      matchEl.className = "status-badge status-fail";
    } else {
      matchEl.textContent = "⚠️ Unknown";
      matchEl.className = "status-badge status-neutral";
    }
    // format_valid
    const formatEl = document.getElementById("formatValid");
    if (doc.format_valid === true) {
      formatEl.textContent = "✅ Valid";
      formatEl.className = "status-badge status-success";
    } else if (doc.format_valid === false) {
      formatEl.textContent = "❌ Invalid";
      formatEl.className = "status-badge status-fail";
    } else {
      formatEl.textContent = "⚠️ Unknown";
      formatEl.className = "status-badge status-neutral";
    }

    // Identity
    const identity = data.identity || {};
    const similarity = identity.name_similarity ?? "--";
    document.getElementById("nameSimilarity").textContent = similarity + "%";
    // AI Visual Analysis
    const aiStatus = document.getElementById("aiStatus");
    const aiConfidence = document.getElementById("aiConfidence");
    const aiRiskScore = document.getElementById("aiRiskScore");
    const aiReasons = document.getElementById("aiReasons");

    if (data.ai_analysis) {
      const ai = data.ai_analysis;

      aiStatus.textContent = ai.suspicious
        ? "Suspicious indicators detected"
        : "No suspicious indicators detected";

      aiConfidence.textContent = `${Math.round(ai.confidence * 100)}%`;

      aiRiskScore.textContent = `${ai.risk_score}/100`;

      aiReasons.innerHTML = "";

      if (ai.reasons && ai.reasons.length > 0) {
        ai.reasons.forEach((reason) => {
          const li = document.createElement("li");
          li.textContent = reason;
          aiReasons.appendChild(li);
        });
      } else {
        const li = document.createElement("li");
        li.textContent = "No suspicious visual indicators detected.";
        aiReasons.appendChild(li);
      }
    }
  }

  function getRiskClass(level) {
    const l = level.toLowerCase();
    if (l === "low risk") return "badge-low";
    if (l === "medium risk") return "badge-medium";
    if (l === "high risk") return "badge-high";
    return "badge-unknown";
  }
});

// Document image preview
const documentFile = document.getElementById("documentFile");
const documentPreview = document.getElementById("documentPreview");
const previewContainer = document.getElementById("previewContainer");
const removeFile = document.getElementById("removeFile");

documentFile.addEventListener("change", function () {
    const file = this.files[0];

    if (!file) {
        previewContainer.classList.add("hidden");
        return;
    }

    // Check file type
    const allowedTypes = ["image/jpeg", "image/png"];

    if (!allowedTypes.includes(file.type)) {
        alert("Please select a JPG, JPEG or PNG image.");
        this.value = "";
        previewContainer.classList.add("hidden");
        return;
    }

    // Check file size (5 MB)
    if (file.size > 5 * 1024 * 1024) {
        alert("File size must be less than 5 MB.");
        this.value = "";
        previewContainer.classList.add("hidden");
        return;
    }

    // Display preview
    const reader = new FileReader();

    reader.onload = function (event) {
        documentPreview.src = event.target.result;
        previewContainer.classList.remove("hidden");
    };

    reader.readAsDataURL(file);
});


// Remove selected document
removeFile.addEventListener("click", function () {
    documentFile.value = "";
    documentPreview.src = "";
    previewContainer.classList.add("hidden");
});