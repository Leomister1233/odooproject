window.toggleSidebar = (forceOpen) => {
  const root = document.documentElement;
  const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : !root.classList.contains("sidebar-open");
  root.classList.toggle("sidebar-open", shouldOpen);
};

window.toggleSidebarCollapse = () => {
  document.documentElement.classList.toggle("sidebar-collapsed");
}
document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      window.toggleSidebar(false);
    }
  });

  if (window.Chart) {
    Chart.defaults.font.family = '"Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif';
    Chart.defaults.color = "#475569";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 10;
  }

  const revenueCtx = document.getElementById("revenueChart");
  if (window.Chart && revenueCtx) {
    const labels = JSON.parse(revenueCtx.dataset.labels || "[]");
    const values = JSON.parse(revenueCtx.dataset.values || "[]");
    new Chart(revenueCtx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Revenue",
          data: values,
          borderColor: "#1f84ff",
          backgroundColor: "rgba(31, 132, 255, 0.14)",
          borderWidth: 3,
          pointRadius: 0,
          pointHoverRadius: 5,
          tension: 0.36,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: "rgba(148, 163, 184, 0.14)" } },
        },
      },
    });
  }

  const statusCtx = document.getElementById("statusChart");
  if (window.Chart && statusCtx) {
    const values = JSON.parse(statusCtx.dataset.values || "[]");
    new Chart(statusCtx, {
      type: "doughnut",
      data: {
        labels: ["Draft", "Posted", "Paid", "Overdue"],
        datasets: [{
          data: values,
          backgroundColor: ["#94a3b8", "#60a5fa", "#34d399", "#fb7185"],
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "72%",
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  const taxCtx = document.getElementById("taxChart");
  if (window.Chart && taxCtx) {
    const labels = JSON.parse(taxCtx.dataset.labels || "[]");
    const values = JSON.parse(taxCtx.dataset.values || "[]");
    new Chart(taxCtx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Tax",
          data: values,
          borderRadius: 10,
          backgroundColor: "rgba(17, 103, 219, 0.78)",
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: "rgba(148, 163, 184, 0.14)" } },
        },
      },
    });
  }

  const linesContainer = document.getElementById("invoice-lines");
  const addLineBtn = document.getElementById("add-line-btn");
  if (linesContainer && addLineBtn) {
    const updateRemoveButtons = () => {
      const rows = Array.from(linesContainer.querySelectorAll(".line-card"));
      rows.forEach((row, index) => {
        const removeBtn = row.querySelector(".remove-line-btn");
        const indexNode = row.querySelector("[data-line-index]");
        if (indexNode) {
          indexNode.textContent = `Line ${index + 1}`;
        }
        if (!removeBtn) return;
        removeBtn.classList.toggle("hidden", rows.length === 1);
        removeBtn.onclick = () => {
          if (rows.length > 1) {
            row.remove();
            updateRemoveButtons();
          }
        };
      });
    };

    const addLine = (event) => {
      if (event) event.preventDefault();
      const firstRow = linesContainer.querySelector(".line-card");
      if (!firstRow) return;
      const clone = firstRow.cloneNode(true);
      clone.querySelectorAll("input").forEach((input) => {
        if (input.name === "quantity") input.value = "1";
        else if (input.name === "unit_price") input.value = "100";
        else input.value = "";
      });
      clone.querySelectorAll("select").forEach((select) => {
        select.selectedIndex = 0;
      });
      linesContainer.appendChild(clone);
      updateRemoveButtons();
    };

    window.addInvoiceLine = addLine;
    addLineBtn.addEventListener("click", addLine);
    updateRemoveButtons();
  }
});
