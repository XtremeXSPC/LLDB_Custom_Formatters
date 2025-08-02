// common.js
// Contains shared functions and configurations for all visualizers.

// ----- Tokyo Night Color Palette ----- //
const colorPalette = {
  // Theme colors for nodes and edges
  nodeDefault: "#7aa2f7",
  nodeBorder: "#565f89",
  nodeSelected: "#bb9af7",
  nodeSelectedBorder: "#9d7cd8",
  nodeHighlighted: "#e0af68",
  nodeHighlightedBorder: "#c49a61",
  nodeAnimated: "#9ece6a",
  nodeAnimatedBorder: "#73a84c",
  nodeSearchResult: "#f7768e",
  nodeSearchBorder: "#e06b83",
  nodeHover: "#9ece6a",

  edgeDefault: "#565f89",
  edgeSelected: "#bb9af7",
  edgeHighlighted: "#e0af68",

  textDefault: "#ffffffff",

  // Theme structure
  blue: "#7aa2f7",
  purple: "#bb9af7",
  red: "#f7768e",
  orange: "#e0af68",
  green: "#9ece6a",

  dark: {
    text: "#c0caf5",
    surface: "#24283b",
    border: "#414868",
  },
  light: {
    text: "#1a1b26",
    surface: "#c0caf5",
    border: "#a9b1d6",
  },
};

// Object to hold clean, professional SVG icons.
const svgIcons = {
  theme: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`,
  expand: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>`,
  collapse: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="9" y1="15" x2="15" y2="15"></line></svg>`,
  center: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"></circle><line x1="12" y1="1" x2="12" y2="4"></line><line x1="12" y1="20" x2="12" y2="23"></line><line x1="4" y1="12" x2="1" y2="12"></line><line x1="23" y1="12" x2="20" y2="12"></line><line x1="19.07" y1="4.93" x2="16.95" y2="7.05"></line><line x1="7.05" y1="16.95" x2="4.93" y2="19.07"></line><line x1="19.07" y1="19.07" x2="16.95" y2="16.95"></line><line x1="7.05" y1="7.05" x2="4.93" y2="4.93"></line></svg>`,
  clear: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"></path><line x1="18" y1="9" x2="12" y2="15"></line><line x1="12" y1="9" x2="18" y2="15"></line></svg>`,
  png: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`,
  json: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`,
  play: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`,
  pause: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>`,
  stop: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16"></rect></svg>`,
  step: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="5 4 15 12 5 20 5 4"></polygon><line x1="19" y1="5" x2="19" y2="19"></line></svg>`,
};

// ----- Shared Utility Functions ----- //

/**
 * Injects SVG icons into their respective buttons.
 */
function applyIcons() {
  for (const [key, svg] of Object.entries(svgIcons)) {
    const button = document.getElementById(`btn-${key}`);
    if (button) {
      // Preserve the original text content and prepend the icon
      const originalText = button.textContent.trim();
      button.innerHTML = `<span class="button-icon">${svg}</span> ${originalText}`;
    }
  }
}

/**
 * Manages theme switching (light/dark) and saves the preference.
 */
function toggleTheme() {
  const body = document.body;
  body.classList.toggle("light-theme");
  const isLight = body.classList.contains("light-theme");
  try {
    localStorage.setItem("theme", isLight ? "light" : "dark");
  } catch (e) {
    // Handle localStorage not available
    console.warn("localStorage not available for theme persistence");
  }
  updateThemeButton(isLight);
}

/**
 * Updates the theme button's text and icon.
 * @param {boolean} isLight - True if the current theme is light.
 */
function updateThemeButton(isLight) {
  const themeToggleButton = document.getElementById("theme-toggle-btn");
  if (themeToggleButton) {
    const themeName = isLight ? "Dark" : "Light";
    themeToggleButton.innerHTML = `<span class="button-icon">${svgIcons.theme}</span> Switch to ${themeName} Theme`;
  }
}

/**
 * Auto-executing function to apply the saved theme on page load.
 */
(function () {
  let savedTheme = "dark"; // default to dark
  try {
    savedTheme = localStorage.getItem("theme") || "dark";
  } catch (e) {
    console.warn("localStorage not available for theme persistence");
  }

  const isLight = savedTheme === "light";
  if (isLight) {
    document.body.classList.add("light-theme");
  }

  // Update the button text after the DOM is fully loaded.
  document.addEventListener("DOMContentLoaded", () => {
    updateThemeButton(isLight);
    applyIcons(); // Apply all other icons as well
  });
})();

/**
 * Toggles the visibility of the info panel.
 */
function toggleInfoBox() {
  const infoBox = document.getElementById("info-box");
  const toggleBtn = document.getElementById("toggle-info-btn");

  if (!infoBox || !toggleBtn) return;

  infoBox.classList.toggle("hidden");
  if (infoBox.classList.contains("hidden")) {
    toggleBtn.classList.remove("info-visible");
    toggleBtn.innerHTML = "⚙️";
    toggleBtn.title = "Show Info Panel";
  } else {
    toggleBtn.classList.add("info-visible");
    toggleBtn.innerHTML = "➡️";
    toggleBtn.title = "Hide Info Panel";
  }
}

/**
 * Exports the current network view as a PNG image.
 */
function exportPNG() {
  if (!network || !network.canvas || !network.canvas.frame) {
    console.error("Network canvas not available for PNG export");
    return;
  }

  const canvas = network.canvas.frame.canvas;
  const link = document.createElement("a");
  link.download = "visualization.png";
  link.href = canvas.toDataURL();
  link.click();
}

/**
 * Exports the provided data object as a JSON file.
 * @param {object} dataToExport - The specific data object to be stringified and exported.
 * @param {string} filename - The desired name for the downloaded file.
 */
function exportJSON(dataToExport, filename = "data.json") {
  const blob = new Blob([JSON.stringify(dataToExport, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Fits the network view to the screen.
 */
function centerView() {
  if (network) network.fit();
}

/**
 * Clears the current selection and hides the node info panel.
 */
function clearSelection() {
  if (network) {
    network.unselectAll();
    resetColors();
    hideNodeInfo();
  }
}

/**
 * Hides the node information panel.
 */
function hideNodeInfo() {
  const nodeInfo = document.getElementById("node-info");
  if (nodeInfo) nodeInfo.style.display = "none";
}

/**
 * Resets the colors of all nodes and edges to their default state.
 */
function resetColors() {
  if (!nodes || !edges) return;

  const nodeUpdates = nodes.getIds().map((id) => ({
    id: id,
    color: {
      background: colorPalette.nodeDefault,
      border: colorPalette.nodeBorder,
    },
  }));
  if (nodeUpdates.length > 0) nodes.update(nodeUpdates);

  const edgeUpdates = edges.getIds().map((id) => ({
    id: id,
    color: { color: colorPalette.edgeDefault },
  }));
  if (edgeUpdates.length > 0) edges.update(edgeUpdates);
}

/**
 * Clears any highlighting from search or selection.
 */
function clearHighlights() {
  resetColors();
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.value = "";
  }
}

/**
 * Highlights nodes that match a search query.
 * @param {string} query - The text to search for in node labels and titles.
 */
function searchNodes(query) {
  if (!nodes) return;

  resetColors();
  if (!query.trim()) return;

  const matchingNodes = nodes.get({
    filter: (node) =>
      String(node.label).toLowerCase().includes(query.toLowerCase()) ||
      (node.title &&
        String(node.title).toLowerCase().includes(query.toLowerCase())),
  });

  if (matchingNodes.length > 0) {
    const updates = matchingNodes.map((node) => ({
      id: node.id,
      color: {
        background: colorPalette.nodeSearchResult,
        border: colorPalette.nodeSearchBorder,
      },
    }));
    nodes.update(updates);
  }
}

/**
 * Handles the hover event on a node to show its title.
 */
function handleNodeHover(params) {
  if (!params.node || !nodes) return;

  const nodeId = params.node;
  const nodeData = nodes.get(nodeId);
  if (!nodeData) return;

  const title = nodeData.title || `Label: ${nodeData.label}`;
  const networkElement = document.getElementById("mynetwork");
  if (networkElement) {
    networkElement.title = `${title}\nClick for details`;
  }
}

/**
 * Handles the blur event on a node to clear the title.
 */
function handleNodeBlur() {
  const networkElement = document.getElementById("mynetwork");
  if (networkElement) {
    networkElement.title = "";
  }
}

// ----- Initial UI State Setup ----- //
document.addEventListener("DOMContentLoaded", () => {
  const infoBox = document.getElementById("info-box");
  const toggleBtn = document.getElementById("toggle-info-btn");
  if (infoBox && toggleBtn) {
    infoBox.classList.add("hidden");
    toggleBtn.classList.remove("info-visible");
    toggleBtn.innerHTML = "⚙️";
    toggleBtn.title = "Show Info Panel";
  }
});
