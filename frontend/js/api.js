const API_BASE = "http://127.0.0.1:5000";

export async function fetchAllParcels() {
  const response = await fetch(`${API_BASE}/api/parcels`);
  if (!response.ok) {
    throw new Error(`Failed to fetch parcels: ${response.statusText}`);
  }
  return await response.json();
}

export async function fetchParcelByUlpin(ulpin) {
  const clean = encodeURIComponent(ulpin.trim());
  const response = await fetch(`${API_BASE}/api/parcels/by-ulpin/${clean}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Parcel ${ulpin} not found`);
  }
  return await response.json();
}

export async function fetchParcelByLocation(lat, lng) {
  const response = await fetch(
    `${API_BASE}/api/parcels/by-location?lat=${lat}&lng=${lng}`,
  );
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.error || "No registered vertical parcel near this location",
    );
  }
  return await response.json();
}

export async function verifyPassword(ulpin, password) {
  const response = await fetch(`${API_BASE}/api/verify-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ulpin, password }),
  });
  const data = await response.json();
  if (!response.ok || !data.success) {
    throw new Error(data.error || "INCORRECT PASSWORD");
  }
  return data;
}
