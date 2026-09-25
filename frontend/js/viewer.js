import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export class BuildingViewer {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.onFloorSelect = options.onFloorSelect || (() => {});
    this.onFloorHover = options.onFloorHover || (() => {});
    this.onModelLoaded = options.onModelLoaded || (() => {});

    this.floorMeshes = new Map(); // floorNumber -> mesh
    this.selectedFloorNumber = null;
    this.hoveredFloorNumber = null;
    this.currentModelRoot = null;
    this.isExploded = false;
    this.isWireframe = false;

    this.initScene();
    this.initLights();
    this.initEnvironment();
    this.initControls();
    this.initRaycaster();
    this.initEvents();
    this.animate();
  }

  initScene() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xf8f9fa); // Off-white/light gray
    this.scene.fog = new THREE.FogExp2(0xf8f9fa, 0.015);

    const width = this.container.clientWidth || 600;
    const height = this.container.clientHeight || 500;

    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    this.camera.position.set(24, 18, 30);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;

    this.container.appendChild(this.renderer.domElement);
  }

  initLights() {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    this.scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe9ecef, 0.6);
    hemiLight.position.set(0, 50, 0);
    this.scene.add(hemiLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.4);
    dirLight.position.set(30, 50, 35);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 150;
    const d = 35;
    dirLight.shadow.camera.left = -d;
    dirLight.shadow.camera.right = d;
    dirLight.shadow.camera.top = d;
    dirLight.shadow.camera.bottom = -d;
    dirLight.shadow.bias = -0.0005;
    this.scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x6c757d, 0.6);
    fillLight.position.set(-30, 20, -30);
    this.scene.add(fillLight);
  }

  initEnvironment() {
    const gridHelper = new THREE.GridHelper(60, 30, 0xadb5bd, 0xdee2e6);
    gridHelper.position.y = -0.01;
    this.scene.add(gridHelper);

    const planeGeo = new THREE.PlaneGeometry(120, 120);
    const planeMat = new THREE.ShadowMaterial({ opacity: 0.35 });
    const plane = new THREE.Mesh(planeGeo, planeMat);
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = -0.02;
    plane.receiveShadow = true;
    this.scene.add(plane);
  }

  initControls() {
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.maxPolarAngle = Math.PI / 2 - 0.02; // Keep above ground
    this.controls.minDistance = 5;
    this.controls.maxDistance = 150;
    this.controls.target.set(0, 6, 0);
  }

  initRaycaster() {
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2(-999, -999);
  }

  initEvents() {
    window.addEventListener("resize", () => this.onWindowResize());

    const canvas = this.renderer.domElement;
    let isDragging = false;
    let downPos = { x: 0, y: 0 };

    canvas.addEventListener("pointerdown", (e) => {
      isDragging = false;
      downPos = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener("pointermove", (e) => {
      const dx = Math.abs(e.clientX - downPos.x);
      const dy = Math.abs(e.clientY - downPos.y);
      if (dx > 3 || dy > 3) isDragging = true;

      const rect = canvas.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.checkHover(e);
    });

    canvas.addEventListener("pointerup", (e) => {
      if (!isDragging) {
        this.checkClick();
      }
    });

    canvas.addEventListener("pointerleave", () => {
      this.mouse.set(-999, -999);
      if (
        this.hoveredFloorNumber !== null &&
        this.hoveredFloorNumber !== this.selectedFloorNumber
      ) {
        this.unhighlightMesh(this.floorMeshes.get(this.hoveredFloorNumber));
        this.hoveredFloorNumber = null;
        this.onFloorHover(null);
      }
    });
  }

  onWindowResize() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (width === 0 || height === 0) return;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  loadModel(url) {
    this.clearModel();

    const loader = new GLTFLoader();
    return new Promise((resolve, reject) => {
      loader.load(
        url,
        (gltf) => {
          this.currentModelRoot = gltf.scene;

          const registeredFloors = [];

          gltf.scene.traverse((obj) => {
            if (obj.isMesh) {
              obj.castShadow = true;
              obj.receiveShadow = true;

              let floorNum =
                obj.userData.floor_number !== undefined
                  ? Number(obj.userData.floor_number)
                  : null;

              if (floorNum === null && obj.userData.Floor_Level !== undefined) {
                floorNum = Number(obj.userData.Floor_Level);
              }

              if (floorNum !== null) {
                obj.userData.originalMaterial = obj.material;
                obj.userData.originalPosition = obj.position.clone();
                this.floorMeshes.set(obj.uuid, obj);

                const height_m =
                  obj.userData.height_m !== undefined
                    ? obj.userData.height_m
                    : 3.0;
                const unit_type =
                  obj.userData.unit_type ||
                  obj.userData.Compartment_Type ||
                  "Unknown";
                const area_sqm =
                  obj.userData.area_sqm !== undefined
                    ? obj.userData.area_sqm
                    : obj.userData.Area_sqm || 0;
                const owner_name =
                  obj.userData.owner_name ||
                  `Owner of ${obj.userData.Apartment_Number || "Unit"}`;
                const ulpin_3d =
                  obj.userData.ulpin_3d || obj.userData.ULPIN || null;

                obj.userData.height_m = height_m;
                obj.userData.unit_type = unit_type;
                obj.userData.area_sqm = area_sqm;
                obj.userData.owner_name = owner_name;
                obj.userData.floor_number = floorNum;
                obj.userData.ulpin_3d = ulpin_3d;

                registeredFloors.push({
                  floor_number: floorNum,
                  height_m: height_m,
                  unit_type: unit_type,
                  area_sqm: area_sqm,
                  owner_name: owner_name,
                  ulpin_3d: ulpin_3d,
                  meshName: obj.name,
                  meshId: obj.uuid,
                });
              }
            }
          });

          this.scene.add(gltf.scene);

          this.fitCameraToModel(gltf.scene);

          registeredFloors.sort((a, b) => a.floor_number - b.floor_number);
          this.onModelLoaded(registeredFloors);
          resolve(registeredFloors);
        },
        undefined,
        (err) => {
          console.error("Error loading GLB model:", err);
          reject(err);
        },
      );
    });
  }

  fitCameraToModel(root) {
    const box = new THREE.Box3().setFromObject(root);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = this.camera.fov * (Math.PI / 180);
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.6;

    this.camera.position.set(
      center.x + cameraZ * 0.75,
      center.y + maxDim * 0.6,
      center.z + cameraZ * 0.85,
    );
    this.controls.target.copy(center);
    this.controls.update();

    this.defaultCameraState = {
      position: this.camera.position.clone(),
      target: this.controls.target.clone(),
    };
  }

  clearModel() {
    if (this.currentModelRoot) {
      this.scene.remove(this.currentModelRoot);
      this.currentModelRoot.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material))
            obj.material.forEach((m) => m.dispose());
          else obj.material.dispose();
        }
      });
      this.currentModelRoot = null;
    }
    this.floorMeshes.clear();
    this.selectedMeshId = null;
    this.hoveredMeshId = null;
    this.isExploded = false;
  }

  checkHover(event) {
    if (!this.currentModelRoot) return;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = Array.from(this.floorMeshes.values());
    const intersects = this.raycaster.intersectObjects(meshes, false);

    if (intersects.length > 0) {
      const hitMesh = intersects[0].object;
      const meshId = hitMesh.uuid;

      this.renderer.domElement.style.cursor = "pointer";

      if (this.hoveredMeshId !== meshId) {
        if (
          this.hoveredMeshId !== null &&
          this.hoveredMeshId !== this.selectedMeshId
        ) {
          this.unhighlightMesh(this.floorMeshes.get(this.hoveredMeshId));
        }

        this.hoveredMeshId = meshId;

        if (meshId !== this.selectedMeshId) {
          this.highlightMesh(hitMesh, 0x0d6efd, 0.3); // Primary blue subtle hover
        }

        this.onFloorHover({
          floor_number: hitMesh.userData.floor_number,
          height_m: hitMesh.userData.height_m,
          unit_type: hitMesh.userData.unit_type,
          owner_name: hitMesh.userData.owner_name,
          area_sqm: hitMesh.userData.area_sqm,
          ulpin_3d: hitMesh.userData.ulpin_3d,
          meshName: hitMesh.name,
          clientX: event.clientX,
          clientY: event.clientY,
        });
      }
    } else {
      this.renderer.domElement.style.cursor = "default";
      if (
        this.hoveredMeshId !== null &&
        this.hoveredMeshId !== this.selectedMeshId
      ) {
        this.unhighlightMesh(this.floorMeshes.get(this.hoveredMeshId));
      }
      this.hoveredMeshId = null;
      this.onFloorHover(null);
    }
  }

  checkClick() {
    if (!this.currentModelRoot) return;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = Array.from(this.floorMeshes.values());
    const intersects = this.raycaster.intersectObjects(meshes, false);

    if (intersects.length > 0) {
      const hitMesh = intersects[0].object;
      this.selectFloor(hitMesh.uuid);
    } else {
      this.deselectFloor();
    }
  }

  selectFloor(meshId) {
    if (typeof meshId === "number") {
      const meshArray = Array.from(this.floorMeshes.values());
      const found = meshArray.find((m) => m.userData.floor_number === meshId);
      if (found) meshId = found.uuid;
      else return;
    }

    if (this.selectedMeshId !== null) {
      this.unhighlightMesh(this.floorMeshes.get(this.selectedMeshId));
    }

    this.selectedMeshId = meshId;
    const mesh = this.floorMeshes.get(meshId);

    if (mesh) {
      this.highlightMesh(mesh, 0xfd7e14, 0.85);

      this.onFloorSelect({
        floor_number: mesh.userData.floor_number,
        height_m: mesh.userData.height_m,
        unit_type: mesh.userData.unit_type,
        owner_name: mesh.userData.owner_name,
        area_sqm: mesh.userData.area_sqm,
        ulpin_3d: mesh.userData.ulpin_3d,
        meshName: mesh.name,
        meshId: mesh.uuid,
      });
    }
  }

  deselectFloor() {
    if (this.selectedMeshId !== null) {
      this.unhighlightMesh(this.floorMeshes.get(this.selectedMeshId));
      this.selectedMeshId = null;
      this.onFloorSelect(null);
    }
  }

  highlightMesh(mesh, emissiveHex, intensity = 0.5) {
    if (!mesh || !mesh.material) return;

    if (!mesh.userData.clonedMaterial) {
      mesh.userData.clonedMaterial = mesh.material.clone();
      mesh.material = mesh.userData.clonedMaterial;
    }

    if (mesh.material.emissive) {
      mesh.material.emissive.setHex(emissiveHex);
      mesh.material.emissiveIntensity = intensity;
    }
  }

  unhighlightMesh(mesh) {
    if (!mesh || !mesh.userData.originalMaterial) return;
    mesh.material = mesh.userData.originalMaterial;
    mesh.userData.clonedMaterial = null;
  }

  toggleExplode() {
    this.setExploded(!this.isExploded);
    return this.isExploded;
  }

  setExploded(explode) {
    this.isExploded = explode;
    const spacing = 1.8;

    this.floorMeshes.forEach((mesh) => {
      const floorNum = mesh.userData.floor_number || 0;
      const origPos = mesh.userData.originalPosition || mesh.position;
      mesh.userData.targetY = explode
        ? origPos.y + floorNum * spacing
        : origPos.y;
    });

    if (this.currentModelRoot) {
      this.fitCameraToModel(this.currentModelRoot);
    }
  }

  toggleWireframe() {
    this.isWireframe = !this.isWireframe;
    this.floorMeshes.forEach((mesh) => {
      if (mesh.material) {
        mesh.material.wireframe = this.isWireframe;
      }
    });
    return this.isWireframe;
  }

  resetView() {
    this.deselectFloor();
    this.setExploded(false);
    if (this.isWireframe) this.toggleWireframe();

    if (this.defaultCameraState) {
      this.camera.position.copy(this.defaultCameraState.position);
      this.controls.target.copy(this.defaultCameraState.target);
      this.controls.update();
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    this.floorMeshes.forEach((mesh) => {
      if (mesh.userData.targetY !== undefined) {
        mesh.position.y = THREE.MathUtils.lerp(
          mesh.position.y,
          mesh.userData.targetY,
          0.1,
        );
      }
    });

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
