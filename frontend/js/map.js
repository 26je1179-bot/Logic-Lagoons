import { fetchParcelByLocation } from "./api.js";

export class ParcelMap {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    this.onParcelSelect = options.onParcelSelect || (() => {});
    this.onStatusMessage = options.onStatusMessage || (() => {});

    this.mapType = "leaflet";
    this.map = null;
    this.clickMarker = null;
    this.proximityCircle = null;
    this.registeredMarkers = [];

    this.defaultCenter = { lat: 21.7679, lng: 78.8718 };
    this.defaultZoom = 5;
  }

  async init(knownParcels = [], googleApiKey = "") {
    this.knownParcels = knownParcels;

    if (googleApiKey && window.google && window.google.maps) {
      this.initGoogleMap(googleApiKey);
    } else if (googleApiKey) {
      const loaded = await this.loadGoogleMapsScript(googleApiKey);
      if (loaded && window.google && window.google.maps) {
        this.initGoogleMap(googleApiKey);
      } else {
        this.initLeafletMap();
      }
    } else if (window.google && window.google.maps) {
      this.initGoogleMap("");
    } else {
      this.initLeafletMap();
    }
  }

  loadGoogleMapsScript(apiKey) {
    return new Promise((resolve) => {
      if (window.google && window.google.maps) return resolve(true);

      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry`;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve(true);
      script.onerror = () => {
        console.warn(
          "Failed to load Google Maps script. Falling back to Leaflet.",
        );
        resolve(false);
      };
      document.head.appendChild(script);
    });
  }

  initGoogleMap() {
    this.mapType = "google";
    this.container.innerHTML = "";

    const mapOptions = {
      center: this.defaultCenter,
      zoom: this.defaultZoom,
      mapTypeId: "roadmap",
      mapTypeControl: true,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
      styles: [
        { featureType: "poi", stylers: [{ visibility: "simplified" }] },
        {
          featureType: "administrative.land_parcel",
          stylers: [{ visibility: "on" }],
        },
      ],
    };

    this.map = new google.maps.Map(this.container, mapOptions);

    this.plotRegisteredParcelsGoogle();

    this.map.addListener("click", (e) => {
      const lat = e.latLng.lat();
      const lng = e.latLng.lng();
      this.handleLocationClick(lat, lng);
    });

    this.onStatusMessage({
      type: "info",
      text: "Google Maps layer active. Click near any parcel to test 100m proximity lookup.",
    });
  }

  plotRegisteredParcelsGoogle() {
    this.knownParcels.forEach((p) => {
      const marker = new google.maps.Marker({
        position: { lat: p.latitude, lng: p.longitude },
        map: this.map,
        title: `${p.ulpin} - ${p.address}`,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: "#f59e0b",
          fillOpacity: 1.0,
          strokeColor: "#ffffff",
          strokeWeight: 2,
        },
      });

      const info = new google.maps.InfoWindow({
        content: `
          <div style="color: #0f172a; padding: 4px;">
            <b style="color: #d97706;">ULPIN: ${p.ulpin}</b><br/>
            <span>${p.address}</span><br/>
            <small>Floors: ${p.total_floors} | Height: ${p.total_height_m}m</small>
          </div>
        `,
      });

      marker.addListener("click", () => {
        info.open(this.map, marker);
        this.handleLocationClick(p.latitude, p.longitude);
      });

      this.registeredMarkers.push(marker);
    });
  }

  initLeafletMap() {
    this.mapType = "leaflet";
    this.container.innerHTML = "";

    if (typeof L === "undefined") {
      this.container.innerHTML =
        "<div style='color: white; padding: 20px;'>Loading map engine...</div>";
      return;
    }

    this.map = L.map(this.containerId).setView(
      [this.defaultCenter.lat, this.defaultCenter.lng],
      this.defaultZoom,
    );

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(this.map);

    this.plotRegisteredParcelsLeaflet();

    this.map.on("click", (e) => {
      this.handleLocationClick(e.latlng.lat, e.latlng.lng);
    });

    this.onStatusMessage({
      type: "info",
      text: "Interactive Map layer active. Click near any registered parcel pin to test 100m proximity lookup.",
    });

    setTimeout(() => {
      if (this.map && this.map.invalidateSize) {
        this.map.invalidateSize();
      }
    }, 250);
  }

  plotRegisteredParcelsLeaflet() {
    this.knownParcels.forEach((p) => {
      const marker = L.circleMarker([p.latitude, p.longitude], {
        radius: 8,
        fillColor: "#f59e0b",
        color: "#ffffff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.95,
      }).addTo(this.map);

      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 12px; color: #0f172a;">
          <b style="color: #d97706;">ULPIN: ${p.ulpin}</b><br/>
          <span>${p.address}</span><br/>
          <small>Floors: ${p.total_floors} | Height: ${p.total_height_m}m</small><br/>
          <button style="margin-top:6px; background:#0284c7; color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;"
            id="popup-btn-${p.id}">Inspect 3D Model</button>
        </div>
      `);

      marker.on("popupopen", () => {
        const btn = document.getElementById(`popup-btn-${p.id}`);
        if (btn) {
          btn.onclick = () => this.handleLocationClick(p.latitude, p.longitude);
        }
      });

      this.registeredMarkers.push(marker);
    });
  }

  async handleLocationClick(lat, lng) {
    this.renderClickMarker(lat, lng);

    this.onStatusMessage({
      type: "loading",
      text: `Resolving 2D ULPIN for coordinates (${lat.toFixed(4)}, ${lng.toFixed(4)})...`,
    });

    try {
      const parcelData = await fetchParcelByLocation(lat, lng);
      this.onStatusMessage({
        type: "success",
        text: `Matched parcel ULPIN: ${parcelData.ulpin} (${parcelData.matched_distance_m}m away, within 100m threshold).`,
      });

      this.onParcelSelect(parcelData);
    } catch (err) {
      this.onStatusMessage({
        type: "error",
        text: `No registered vertical parcel at this location (${err.message}). Keeping current view.`,
      });
    }
  }

  renderClickMarker(lat, lng) {
    if (this.mapType === "google") {
      if (this.clickMarker) this.clickMarker.setMap(null);
      if (this.proximityCircle) this.proximityCircle.setMap(null);

      this.clickMarker = new google.maps.Marker({
        position: { lat, lng },
        map: this.map,
        icon: "https://maps.google.com/mapfiles/ms/icons/red-dot.png",
      });

      this.proximityCircle = new google.maps.Circle({
        strokeColor: "#ef4444",
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: "#ef4444",
        fillOpacity: 0.15,
        map: this.map,
        center: { lat, lng },
        radius: 100,
      });
    } else {
      if (this.clickMarker) this.map.removeLayer(this.clickMarker);
      if (this.proximityCircle) this.map.removeLayer(this.proximityCircle);

      this.clickMarker = L.circleMarker([lat, lng], {
        radius: 9,
        fillColor: "#ef4444",
        color: "#ffffff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.95,
      }).addTo(this.map);

      this.proximityCircle = L.circle([lat, lng], {
        radius: 100,
        color: "#ef4444",
        fillColor: "#ef4444",
        fillOpacity: 0.15,
        weight: 2,
      }).addTo(this.map);
    }
  }

  panTo(lat, lng, zoom = 16) {
    if (this.mapType === "google") {
      this.map.panTo({ lat, lng });
      this.map.setZoom(zoom);
      this.renderClickMarker(lat, lng);
    } else if (this.map) {
      this.map.flyTo([lat, lng], zoom, { duration: 1.2 });
      this.renderClickMarker(lat, lng);
    }
  }
}
