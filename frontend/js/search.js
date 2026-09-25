import { fetchAllParcels, fetchParcelByUlpin, verifyPassword } from "./api.js";
import { BuildingViewer } from "./viewer.js";
import { ParcelMap } from "./map.js";

export class AppController {
  constructor() {
    this.currentParcel = null;
    this.selectedFloor = null;

    this.initDOMElements();
    this.init3DViewer();
    this.initMap();
    this.bindEvents();
  }

  initDOMElements() {
    this.searchForm = document.getElementById("search-form");
    this.ulpinInput = document.getElementById("ulpin-input");
    this.searchBtn = document.getElementById("search-btn");
    this.statusToast = document.getElementById("status-toast");

    this.resetViewBtn = document.getElementById("btn-reset-view");
    this.explodeBtn = document.getElementById("btn-explode");
    this.wireframeBtn = document.getElementById("btn-wireframe");
    this.viewerStatus = document.getElementById("viewer-status");

    this.parcelUlpinEl = document.getElementById("meta-ulpin");
    this.parcelAddressEl = document.getElementById("meta-address");
    this.parcelLocationEl = document.getElementById("meta-location");
    this.parcelFloorsEl = document.getElementById("meta-floors");
    this.parcelHeightEl = document.getElementById("meta-height");
    this.parcelModelUrlEl = document.getElementById("meta-model-url");
    this.meta3dUlpinEl = document.getElementById("meta-3d-ulpin");

    this.floorListContainer = document.getElementById("floor-list");
    this.selectedFloorCard = document.getElementById("selected-floor-card");
    this.selectedFloorNumEl = document.getElementById("sel-floor-num");
    this.selectedFloor3dUlpinEl = document.getElementById("sel-3d-ulpin");
    this.selectedFloorTypeEl = document.getElementById("sel-unit-type");
    this.selectedFloorHeightEl = document.getElementById("sel-height");
    this.selectedFloorAreaEl = document.getElementById("sel-area");
    this.selectedFloorOwnerEl = document.getElementById("sel-owner");

    this.passwordModal = document.getElementById("password-modal");
    this.modalUlpinDisplay = document.getElementById("modal-ulpin-display");
    this.passwordForm = document.getElementById("password-form");
    this.modalPasswordInput = document.getElementById("modal-password-input");
    this.passwordError = document.getElementById("password-error");
    this.modalCancelBtn = document.getElementById("modal-cancel-btn");

    this.hoverTooltip = document.getElementById("floor-tooltip");
  }

  init3DViewer() {
    this.viewer = new BuildingViewer("viewer-canvas-container", {
      onFloorSelect: (floorData) => this.handleFloorSelectedFrom3D(floorData),
      onFloorHover: (hoverData) => this.handleFloorHoverFrom3D(hoverData),
      onModelLoaded: (floors) => {
        this.setViewerStatus(
          `3D Model Loaded (${floors.length} vertical units)`,
        );
      },
    });
  }

  async initMap() {
    try {
      this.allParcels = await fetchAllParcels();
    } catch (e) {
      console.warn("Could not preload parcels list:", e);
      this.allParcels = [];
    }

    this.map = new ParcelMap("map-container", {
      onParcelSelect: (parcelData) => this.handleParcelLoaded(parcelData, true),
      onStatusMessage: (msg) => this.showToast(msg.text, msg.type),
    });

    await this.map.init(this.allParcels);

    if (this.allParcels.length > 0) {
      this.loadParcelByUlpin(this.allParcels[0].ulpin);
    }
  }

  bindEvents() {
    this.searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const ulpin = this.ulpinInput.value.trim();
      if (ulpin) {
        this.loadParcelByUlpin(ulpin);
      }
    });

    document.querySelectorAll(".sample-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const ulpin = chip.getAttribute("data-ulpin");
        if (ulpin) {
          this.ulpinInput.value = ulpin;
          this.loadParcelByUlpin(ulpin);
        }
      });
    });

    this.modalCancelBtn.addEventListener("click", () => {
      this.passwordModal.style.display = "none";
      this.showToast("3D model view cancelled.", "info");
    });

    this.passwordForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      this.passwordError.style.display = "none";
      const password = this.modalPasswordInput.value.trim();
      const ulpin = this.pendingParcelData.ulpin;

      try {
        await verifyPassword(ulpin, password);

        this.passwordModal.style.display = "none";
        this.unlockAndLoadModel(this.pendingParcelData);
      } catch (err) {
        this.passwordError.textContent = err.message || "INCORRECT PASSWORD";
        this.passwordError.style.display = "block";
      }
    });

    this.resetViewBtn.addEventListener("click", () => {
      this.viewer.resetView();
      this.clearSelectedFloor();
      this.showToast("View reset to original framing", "info");
    });

    this.explodeBtn.addEventListener("click", () => {
      const isExploded = this.viewer.toggleExplode();
      this.explodeBtn.classList.toggle("active", isExploded);
      this.explodeBtn.innerHTML = isExploded
        ? '<span class="icon">📦</span> Collapse Floors'
        : '<span class="icon">💥</span> Explode Floors';
      this.showToast(
        isExploded
          ? "Exploded view active: Vertical property boundaries expanded"
          : "Floors collapsed",
        "info",
      );
    });

    this.wireframeBtn.addEventListener("click", () => {
      const isWf = this.viewer.toggleWireframe();
      this.wireframeBtn.classList.toggle("active", isWf);
      this.wireframeBtn.innerHTML = isWf
        ? '<span class="icon">🧱</span> Solid View'
        : '<span class="icon">🕸️</span> Wireframe';
    });
  }

  async loadParcelByUlpin(ulpin) {
    this.showToast(`Looking up 2D ULPIN ${ulpin}...`, "loading");
    this.setViewerStatus("Pending Security Verification...");

    try {
      const parcelData = await fetchParcelByUlpin(ulpin);
      this.handleParcelLoaded(parcelData, false);
      this.showToast(
        `Loaded parcel: ${parcelData.ulpin} (${parcelData.address})`,
        "success",
      );
    } catch (err) {
      this.showToast(err.message || "Failed to load parcel", "error");
      this.setViewerStatus("Error loading model");
    }
  }

  handleParcelLoaded(parcelData, fromMapClick = false) {
    this.currentParcel = parcelData;
    this.ulpinInput.value = parcelData.ulpin;
    this.pendingParcelData = parcelData;

    if (!fromMapClick && this.map) {
      this.map.panTo(parcelData.latitude, parcelData.longitude, 16);
    }

    this.renderParcelMetadata(parcelData);

    this.renderFloorList(parcelData.floors);

    if (this.viewer && this.viewer.clearModel) {
      this.viewer.clearModel();
    }
    this.setViewerStatus("Awaiting password to display 3D model...");

    this.modalUlpinDisplay.textContent = parcelData.ulpin;
    this.modalPasswordInput.value = "";
    this.passwordError.style.display = "none";
    this.passwordModal.style.display = "flex";
  }

  unlockAndLoadModel(parcelData) {
    if (parcelData.model_url) {
      this.setViewerStatus(`Loading ${parcelData.model_url}...`);
      this.viewer
        .loadModel(parcelData.model_url)
        .then((modelFloors) => {
          if (modelFloors && modelFloors.length > 0) {
            this.renderFloorList(modelFloors);
            const defaultMesh =
              modelFloors[0].meshId || modelFloors[0].floor_number;
            this.viewer.selectFloor(defaultMesh);
          } else if (parcelData.floors && parcelData.floors.length > 0) {
            const defaultFloor = parcelData.floors[0].floor_number;
            this.viewer.selectFloor(defaultFloor);
          }
        })
        .catch((e) => {
          this.setViewerStatus("Failed to render 3D model");
        });
    }
  }

  renderParcelMetadata(p) {
    this.parcelUlpinEl.textContent = p.ulpin;
    this.parcelAddressEl.textContent = p.address;
    this.parcelLocationEl.textContent = `${p.district || ""}, ${p.state || ""} (${p.latitude.toFixed(4)}°N, ${p.longitude.toFixed(4)}°E)`;
    this.parcelFloorsEl.textContent = `${p.total_floors} Floors`;
    this.parcelHeightEl.textContent = `${p.total_height_m} m`;
    this.parcelModelUrlEl.textContent = p.model_url;

    this.meta3dUlpinEl.textContent = `${p.ulpin}-3D-BASE`;
  }

  renderFloorList(floors = []) {
    this.floorListContainer.innerHTML = "";

    const sortedFloors = [...floors].sort((a, b) => {
      if (b.floor_number !== a.floor_number)
        return b.floor_number - a.floor_number;

      return (a.meshName || "").localeCompare(b.meshName || "");
    });

    sortedFloors.forEach((f) => {
      const card = document.createElement("div");
      card.className = "floor-item";
      const clickId = f.meshId || f.floor_number;
      card.id = `floor-item-${clickId}`;
      card.setAttribute("data-floor", clickId);

      const typeBadgeClass = `badge-${f.unit_type || "default"}`;
      const floor3dUlpin =
        f.ulpin_3d ||
        `${this.currentParcel.ulpin}-${f.unit_type === "room" || f.unit_type === "Residential Apartment" ? "RM" : "FL"}${String(f.floor_number).padStart(2, "0")}`;

      let displayName = f.meshName
        ? f.meshName.replace(/_/g, " ")
        : `${f.unit_type === "room" || f.unit_type === "Residential Apartment" ? "RM" : "FL"} ${f.floor_number}`;

      card.innerHTML = `
        <div class="floor-item-header">
          <div class="floor-num-badge">${displayName}</div>
          <span class="unit-badge ${typeBadgeClass}">${(f.unit_type || "Unit").toUpperCase()}</span>
          <span class="floor-height-tag">${f.height_m}m</span>
        </div>
        <div class="floor-item-body">
          <div class="floor-owner">${f.owner_name ? `Owner: <strong>${f.owner_name}</strong>` : '<span class="text-muted">Common / Public Area</span>'}</div>
          <div class="floor-sub">3D ULPIN: <code>${floor3dUlpin}</code> &bull; Area: ${f.area_sqm} m²</div>
        </div>
      `;

      card.addEventListener("click", () => {
        this.viewer.selectFloor(clickId);
      });

      this.floorListContainer.appendChild(card);
    });
  }

  handleFloorSelectedFrom3D(floorData) {
    if (!floorData) {
      this.clearSelectedFloor();
      return;
    }

    let fullFloor = floorData;
    if (this.currentParcel && this.currentParcel.floors) {
      const matched = this.currentParcel.floors.find(
        (f) => f.floor_number === floorData.floor_number,
      );
      if (matched) {
        fullFloor = { ...matched, ...floorData };
      }
    }

    this.selectedFloor = fullFloor;
    this.updateSelectedFloorCard(fullFloor);

    document.querySelectorAll(".floor-item").forEach((item) => {
      const clickId = item.getAttribute("data-floor");

      if (clickId === fullFloor.meshId || clickId == fullFloor.floor_number) {
        item.classList.add("active");
        item.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else {
        item.classList.remove("active");
      }
    });

    const floor3dUlpin =
      fullFloor.ulpin_3d ||
      `${this.currentParcel ? this.currentParcel.ulpin : "ULPIN"}-${fullFloor.unit_type === "room" || fullFloor.unit_type === "Residential Apartment" ? "RM" : "FL"}${String(fullFloor.floor_number).padStart(2, "0")}`;
    const displayName = fullFloor.meshName
      ? fullFloor.meshName.replace(/_/g, " ")
      : `${fullFloor.unit_type === "room" || fullFloor.unit_type === "Residential Apartment" ? "Room" : "Floor"} ${fullFloor.floor_number}`;
    this.setViewerStatus(
      `Selected: ${displayName} (${fullFloor.unit_type}) — 3D ULPIN: ${floor3dUlpin}`,
    );
  }

  updateSelectedFloorCard(f) {
    this.selectedFloorCard.style.display = "block";
    const displayName = f.meshName
      ? f.meshName.replace(/_/g, " ")
      : `${f.unit_type === "room" || f.unit_type === "Residential Apartment" ? "Room" : "Floor"} ${f.floor_number}`;
    this.selectedFloorNumEl.textContent = displayName;

    const floor3dUlpin =
      f.ulpin_3d ||
      `${this.currentParcel ? this.currentParcel.ulpin : "ULPIN"}-${f.unit_type === "room" || f.unit_type === "Residential Apartment" ? "RM" : "FL"}${String(f.floor_number).padStart(2, "0")}`;
    this.selectedFloor3dUlpinEl.textContent = floor3dUlpin;

    this.selectedFloorTypeEl.textContent = (f.unit_type || "N/A").toUpperCase();
    this.selectedFloorTypeEl.className = `unit-badge badge-${f.unit_type || "default"}`;

    this.selectedFloorHeightEl.textContent = `${f.height_m} meters`;
    this.selectedFloorAreaEl.textContent = f.area_sqm
      ? `${f.area_sqm} m²`
      : "N/A";
    this.selectedFloorOwnerEl.textContent = f.owner_name
      ? f.owner_name
      : "Common / Commercial Access";
  }

  clearSelectedFloor() {
    this.selectedFloor = null;
    this.selectedFloorCard.style.display = "none";
    document
      .querySelectorAll(".floor-item")
      .forEach((item) => item.classList.remove("active"));
  }

  handleFloorHoverFrom3D(hoverData) {
    if (!hoverData) {
      this.hoverTooltip.style.display = "none";
      return;
    }

    this.hoverTooltip.style.display = "block";
    this.hoverTooltip.style.left = `${hoverData.clientX + 14}px`;
    this.hoverTooltip.style.top = `${hoverData.clientY + 14}px`;

    const displayName = hoverData.meshName
      ? hoverData.meshName.replace(/_/g, " ")
      : `Floor ${hoverData.floor_number}`;
    const ulpinText = hoverData.ulpin_3d
      ? `<br/>3D ULPIN: <code>${hoverData.ulpin_3d}</code>`
      : "";

    this.hoverTooltip.innerHTML = `
      <strong>${displayName}</strong> &bull; <span style="text-transform:capitalize;">${hoverData.unit_type}</span>
      <div style="font-size:11px; color:#cbd5e1; margin-top:2px;">Height: ${hoverData.height_m}m &bull; ${hoverData.owner_name ? hoverData.owner_name : "Common"}${ulpinText}</div>
    `;
  }

  setViewerStatus(text) {
    if (this.viewerStatus) {
      this.viewerStatus.textContent = text;
    }
  }

  showToast(message, type = "info") {
    if (!this.statusToast) return;

    this.statusToast.textContent = message;
    this.statusToast.className = `toast toast-${type} show`;

    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => {
      this.statusToast.className = "toast";
    }, 4500);
  }
}

function bootstrap() {
  if (!window.app) {
    window.app = new AppController();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}
