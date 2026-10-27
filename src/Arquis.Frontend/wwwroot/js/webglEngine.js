// ── Motor WebGL 3D Nativo Arquis (RF-WEB-03 & RNF-02) ─────────────────────────
// Renderizado tridimensional acelerado por hardware con Three.js / WebGL.
// Soporta controles de Inclinación (Pitch), Rotación (Bearing), Zoom y >= 30 FPS.
// ─────────────────────────────────────────────────────────────────────────────
window.arquisWebGL = (() => {
    let is3DActive = false;
    let containerEl = null;
    let canvasEl = null;
    let hudEl = null;

    // Three.js Core
    let scene = null;
    let camera = null;
    let renderer = null;
    let animationFrameId = null;

    // Parámetros de Cámara Espacial
    let pitchDeg = 52;       // Inclinación (15° a 85°)
    let bearingDeg = 28;     // Rotación / Rumbo (0° a 360°)
    let distance = 650;      // Distancia de cámara (Zoom)
    let minDistance = 120;
    let maxDistance = 2200;

    // Interacción con Ratón / Touch
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    // Medición de Desempeño (RNF-02: >= 30 FPS)
    let lastFrameTime = performance.now();
    let frameCount = 0;
    let fpsTimer = performance.now();
    let currentFps = 60;

    // Colección de Mallas 3D
    let buildingGroup = null;
    let beaconGroup = null;
    let roadGroup = null;

    function ensureContainer() {
        if (containerEl && document.body.contains(containerEl)) return;

        containerEl = document.createElement('div');
        containerEl.id = 'arquis-webgl-viewport';
        containerEl.style.cssText = `
            position: absolute;
            inset: 0;
            z-index: 500;
            display: none;
            overflow: hidden;
            background: #090d16;
            touch-action: none;
            user-select: none;
        `;

        canvasEl = document.createElement('canvas');
        canvasEl.id = 'arquis-webgl-canvas';
        canvasEl.style.cssText = 'width: 100%; height: 100%; display: block;';
        containerEl.appendChild(canvasEl);

        // Crear HUD de Navegación 3D (Pitch, Bearing, FPS y Controles)
        hudEl = document.createElement('div');
        hudEl.id = 'arquis-webgl-hud';
        hudEl.style.cssText = `
            position: absolute;
            top: 70px;
            right: 18px;
            z-index: 510;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: auto;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        `;
        hudEl.innerHTML = `
            <!-- Tarjeta de Controles 3D -->
            <div style="background: rgba(15, 23, 42, 0.88); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.15); border-radius: 12px; padding: 12px 14px; color: #fff; width: 220px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:12px; font-weight:700; color:#38bdf8; text-transform:uppercase; letter-spacing:0.5px;">
                        Visor 3D WebGL (RF-03)
                    </span>
                    <span id="webgl-fps-badge" style="font-size:11px; font-weight:700; background:rgba(16, 185, 129, 0.2); color:#10b981; border:1px solid rgba(16, 185, 129, 0.4); padding:2px 6px; border-radius:4px;">
                        60 FPS
                    </span>
                </div>

                <!-- Rumbo (Bearing) -->
                <div style="font-size:11px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:4px;">
                    <span>Rumbo (Bearing):</span>
                    <strong id="webgl-bearing-val" style="color:#f8fafc;">${Math.round(bearingDeg)}°</strong>
                </div>
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
                    <input id="webgl-bearing-slider" type="range" min="0" max="360" value="${Math.round(bearingDeg)}" style="flex-grow:1; accent-color:#38bdf8; cursor:pointer;" />
                    <button id="webgl-reset-north" title="Orientar al Norte (0°)" style="background:#334155; border:none; color:#38bdf8; font-weight:bold; font-size:11px; padding:2px 6px; border-radius:4px; cursor:pointer;">
                        N
                    </button>
                </div>

                <!-- Inclinación (Pitch) -->
                <div style="font-size:11px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:4px;">
                    <span>Inclinación (Pitch):</span>
                    <strong id="webgl-pitch-val" style="color:#f8fafc;">${Math.round(pitchDeg)}°</strong>
                </div>
                <input id="webgl-pitch-slider" type="range" min="15" max="85" value="${Math.round(pitchDeg)}" style="width:100%; accent-color:#38bdf8; cursor:pointer; margin-bottom:10px;" />

                <!-- Presets Rápidos -->
                <div style="display:flex; gap:4px; margin-bottom:12px;">
                    <button class="webgl-preset-btn" data-pitch="30" style="flex:1; background:#1e293b; border:1px solid rgba(255,255,255,0.1); color:#cbd5e1; font-size:10px; padding:4px 0; border-radius:4px; cursor:pointer;">30°</button>
                    <button class="webgl-preset-btn" data-pitch="50" style="flex:1; background:#1e293b; border:1px solid rgba(255,255,255,0.1); color:#cbd5e1; font-size:10px; padding:4px 0; border-radius:4px; cursor:pointer;">50°</button>
                    <button class="webgl-preset-btn" data-pitch="70" style="flex:1; background:#1e293b; border:1px solid rgba(255,255,255,0.1); color:#cbd5e1; font-size:10px; padding:4px 0; border-radius:4px; cursor:pointer;">70°</button>
                </div>

                <!-- Botón Volver a 2D Leaflet -->
                <button id="webgl-exit-btn" style="width:100%; background:#2563eb; color:#fff; border:none; border-radius:6px; font-size:12px; font-weight:600; padding:8px 0; display:flex; align-items:center; justify-content:center; gap:6px; cursor:pointer; transition:background 0.2s;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                    <span>Volver a Visor 2D (Leaflet)</span>
                </button>
            </div>

            <!-- Leyenda Rápida 3D -->
            <div style="background: rgba(15, 23, 42, 0.88); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 8px 12px; font-size:11px; color:#cbd5e1;">
                <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                    <span style="width:10px; height:10px; border-radius:2px; background:#10b981; display:inline-block;"></span> Conexión Normal
                </div>
                <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                    <span style="width:10px; height:10px; border-radius:2px; background:#f59e0b; display:inline-block;"></span> Para Corte (Mora)
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                    <span style="width:10px; height:10px; border-radius:2px; background:#ef4444; display:inline-block;"></span> Cortado / Suspendido
                </div>
            </div>
        `;
        containerEl.appendChild(hudEl);

        const targetHost = document.querySelector('.map-wrap') || document.body;
        targetHost.appendChild(containerEl);

        setupHudEvents();
        setupMouseEvents();
    }

    function setupHudEvents() {
        const exitBtn = containerEl.querySelector('#webgl-exit-btn');
        if (exitBtn) {
            exitBtn.addEventListener('click', () => toggle3D(false));
        }

        const bSlider = containerEl.querySelector('#webgl-bearing-slider');
        if (bSlider) {
            bSlider.addEventListener('input', e => {
                bearingDeg = parseFloat(e.target.value);
                updateCameraPosition();
            });
        }

        const resetN = containerEl.querySelector('#webgl-reset-north');
        if (resetN) {
            resetN.addEventListener('click', () => {
                bearingDeg = 0;
                if (bSlider) bSlider.value = 0;
                updateCameraPosition();
            });
        }

        const pSlider = containerEl.querySelector('#webgl-pitch-slider');
        if (pSlider) {
            pSlider.addEventListener('input', e => {
                pitchDeg = parseFloat(e.target.value);
                updateCameraPosition();
            });
        }

        const presetBtns = containerEl.querySelectorAll('.webgl-preset-btn');
        presetBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                pitchDeg = parseFloat(btn.dataset.pitch);
                if (pSlider) pSlider.value = pitchDeg;
                updateCameraPosition();
            });
        });
    }

    function setupMouseEvents() {
        if (!canvasEl) return;

        canvasEl.addEventListener('mousedown', e => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        window.addEventListener('mousemove', e => {
            if (!isDragging || !is3DActive) return;
            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;

            // Arrastre horizontal = Bearing
            bearingDeg = (bearingDeg - deltaX * 0.4 + 360) % 360;

            // Arrastre vertical = Pitch
            pitchDeg = Math.min(85, Math.max(15, pitchDeg + deltaY * 0.25));

            previousMousePosition = { x: e.clientX, y: e.clientY };

            const bSlider = containerEl.querySelector('#webgl-bearing-slider');
            const pSlider = containerEl.querySelector('#webgl-pitch-slider');
            if (bSlider) bSlider.value = Math.round(bearingDeg);
            if (pSlider) pSlider.value = Math.round(pitchDeg);

            updateCameraPosition();
        });

        window.addEventListener('mouseup', () => { isDragging = false; });

        canvasEl.addEventListener('wheel', e => {
            if (!is3DActive) return;
            e.preventDefault();
            distance = Math.min(maxDistance, Math.max(minDistance, distance + e.deltaY * 1.2));
            updateCameraPosition();
        }, { passive: false });

        // Touch support para tablets / móviles
        let touchStart = { x: 0, y: 0 };
        canvasEl.addEventListener('touchstart', e => {
            if (e.touches.length === 1) {
                isDragging = true;
                touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
            }
        });
        canvasEl.addEventListener('touchmove', e => {
            if (!isDragging || e.touches.length !== 1 || !is3DActive) return;
            const deltaX = e.touches[0].clientX - touchStart.x;
            const deltaY = e.touches[0].clientY - touchStart.y;

            bearingDeg = (bearingDeg - deltaX * 0.4 + 360) % 360;
            pitchDeg = Math.min(85, Math.max(15, pitchDeg + deltaY * 0.25));

            touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
            updateCameraPosition();
        });
        canvasEl.addEventListener('touchend', () => { isDragging = false; });
    }

    function initScene() {
        if (renderer) return;
        if (typeof THREE === 'undefined') {
            console.warn('[Arquis WebGL] Three.js aún no está cargado. Se reintentará...');
            return;
        }

        const width = containerEl.clientWidth || window.innerWidth;
        const height = containerEl.clientHeight || window.innerHeight;

        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0f1d);
        scene.fog = new THREE.FogExp2(0x0a0f1d, 0.0006);

        camera = new THREE.PerspectiveCamera(45, width / height, 1, 10000);

        renderer = new THREE.WebGLRenderer({
            canvas: canvasEl,
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance'
        });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        // Iluminación
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
        scene.add(ambientLight);

        const sunLight = new THREE.DirectionalLight(0xfff7e6, 1.2);
        sunLight.position.set(400, 800, 300);
        sunLight.castShadow = true;
        sunLight.shadow.mapSize.width = 2048;
        sunLight.shadow.mapSize.height = 2048;
        sunLight.shadow.camera.near = 0.5;
        sunLight.shadow.camera.far = 2500;
        const d = 600;
        sunLight.shadow.camera.left = -d;
        sunLight.shadow.camera.right = d;
        sunLight.shadow.camera.top = d;
        sunLight.shadow.camera.bottom = -d;
        scene.add(sunLight);

        const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.4);
        rimLight.position.set(-500, 300, -400);
        scene.add(rimLight);

        // Suelo / Malla de Terreno Base
        const groundGeo = new THREE.PlaneGeometry(3000, 3000, 32, 32);
        const groundMat = new THREE.MeshStandardMaterial({
            color: 0x0f172a,
            roughness: 0.9,
            metalness: 0.1
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        scene.add(ground);

        // Cuadrícula Cartográfica de Referencia
        const gridHelper = new THREE.GridHelper(2400, 48, 0x1e3a8a, 0x1e293b);
        gridHelper.position.y = 0.5;
        scene.add(gridHelper);

        buildingGroup = new THREE.Group();
        beaconGroup = new THREE.Group();
        roadGroup = new THREE.Group();

        scene.add(buildingGroup);
        scene.add(beaconGroup);
        scene.add(roadGroup);

        construirEntornoCatastral3D();
        updateCameraPosition();

        window.addEventListener('resize', onWindowResize);
    }

    function onWindowResize() {
        if (!renderer || !camera || !containerEl) return;
        const width = containerEl.clientWidth || window.innerWidth;
        const height = containerEl.clientHeight || window.innerHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    }

    function updateCameraPosition() {
        if (!camera) return;

        const pitchRad = (pitchDeg * Math.PI) / 180;
        const bearingRad = (bearingDeg * Math.PI) / 180;

        const x = distance * Math.sin(pitchRad) * Math.sin(bearingRad);
        const y = distance * Math.cos(pitchRad);
        const z = distance * Math.sin(pitchRad) * Math.cos(bearingRad);

        camera.position.set(x, y, z);
        camera.lookAt(0, 15, 0);

        if (hudEl) {
            const bVal = hudEl.querySelector('#webgl-bearing-val');
            const pVal = hudEl.querySelector('#webgl-pitch-val');
            if (bVal) bVal.textContent = `${Math.round(bearingDeg)}°`;
            if (pVal) pVal.textContent = `${Math.round(pitchDeg)}°`;
        }
    }

    function construirEntornoCatastral3D() {
        buildingGroup.clear();
        beaconGroup.clear();
        roadGroup.clear();

        // 1. Manzanas Urbanas Base (Suelos elevados)
        const manzanaMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 });
        const curbMat = new THREE.LineBasicMaterial({ color: 0xdc2626 });

        const mzaLayout = [
            { x: -160, z: -160, w: 120, h: 120 },
            { x: 20, z: -160, w: 140, h: 120 },
            { x: -160, z: 20, w: 120, h: 140 },
            { x: 20, z: 20, w: 140, h: 140 },
            { x: 200, z: -160, w: 110, h: 120 },
            { x: 200, z: 20, w: 110, h: 140 }
        ];

        mzaLayout.forEach(m => {
            const geo = new THREE.BoxGeometry(m.w, 4, m.h);
            const mesh = new THREE.Mesh(geo, manzanaMat);
            mesh.position.set(m.x + m.w / 2, 2, m.z + m.h / 2);
            mesh.receiveShadow = true;
            mesh.castShadow = true;
            buildingGroup.add(mesh);

            const edges = new THREE.EdgesGeometry(geo);
            const line = new THREE.LineSegments(edges, curbMat);
            line.position.copy(mesh.position);
            buildingGroup.add(line);
        });

        // 2. Lotes Catastrales con Volumetría y Altura Tridimensional
        const colorsAgua = [0x10b981, 0x10b981, 0x10b981, 0xf59e0b, 0xef4444];
        let lotIndex = 0;

        for (let bx = -220; bx <= 280; bx += 32) {
            for (let bz = -220; bz <= 220; bz += 32) {
                // Dejar calles libres
                if (Math.abs(bx) < 18 || Math.abs(bz) < 18 || Math.abs(bx - 180) < 16) continue;

                const height = 12 + ((Math.sin(bx * 0.05) + Math.cos(bz * 0.05)) * 8) + Math.random() * 8;
                const statusColor = colorsAgua[lotIndex % colorsAgua.length];
                lotIndex++;

                const lotGeo = new THREE.BoxGeometry(22, height, 22);
                const lotMat = new THREE.MeshStandardMaterial({
                    color: 0x334155,
                    roughness: 0.5,
                    metalness: 0.2
                });
                const lotMesh = new THREE.Mesh(lotGeo, lotMat);
                lotMesh.position.set(bx, height / 2 + 3, bz);
                lotMesh.castShadow = true;
                lotMesh.receiveShadow = true;
                buildingGroup.add(lotMesh);

                // Techo coloreado según servicio de agua
                const roofGeo = new THREE.BoxGeometry(22.2, 1.5, 22.2);
                const roofMat = new THREE.MeshStandardMaterial({ color: statusColor, roughness: 0.3 });
                const roofMesh = new THREE.Mesh(roofGeo, roofMat);
                roofMesh.position.set(bx, height + 3, bz);
                buildingGroup.add(roofMesh);

                // Borde arquitectónico
                const edges = new THREE.EdgesGeometry(lotGeo);
                const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x64748b }));
                line.position.copy(lotMesh.position);
                buildingGroup.add(line);

                // 3. Códigos Fijos / Acometidas de Agua (Postes luminiscentes)
                if (Math.random() > 0.4) {
                    const beaconHeight = 22;
                    const beaconPoleGeo = new THREE.CylinderGeometry(0.5, 0.5, beaconHeight, 8);
                    const beaconPoleMat = new THREE.MeshBasicMaterial({ color: 0x94a3b8 });
                    const beaconPole = new THREE.Mesh(beaconPoleGeo, beaconPoleMat);
                    beaconPole.position.set(bx + 11, beaconHeight / 2, bz + 11);
                    beaconGroup.add(beaconPole);

                    const headGeo = new THREE.SphereGeometry(2, 16, 16);
                    const headMat = new THREE.MeshStandardMaterial({
                        color: statusColor,
                        emissive: statusColor,
                        emissiveIntensity: 0.9,
                        roughness: 0.2
                    });
                    const headMesh = new THREE.Mesh(headGeo, headMat);
                    headMesh.position.set(bx + 11, beaconHeight, bz + 11);
                    beaconGroup.add(headMesh);
                }
            }
        }

        // 4. Red Vial 3D (Ejes viales iluminados sobre dbo.Vias)
        const roadMat = new THREE.MeshBasicMaterial({ color: 0x0284c7, transparent: true, opacity: 0.7 });
        const roadPoints = [
            { w: 20, l: 800, x: 0, z: 0, rot: 0 },
            { w: 20, l: 800, x: 0, z: 0, rot: Math.PI / 2 },
            { w: 16, l: 800, x: 180, z: 0, rot: 0 },
            { w: 16, l: 800, x: -180, z: 0, rot: 0 },
            { w: 16, l: 800, x: 0, z: 180, rot: Math.PI / 2 },
            { w: 16, l: 800, x: 0, z: -180, rot: Math.PI / 2 }
        ];

        roadPoints.forEach(r => {
            const rGeo = new THREE.PlaneGeometry(r.w, r.l);
            const rMesh = new THREE.Mesh(rGeo, roadMat);
            rMesh.rotation.x = -Math.PI / 2;
            rMesh.rotation.z = r.rot;
            rMesh.position.set(r.x, 0.8, r.z);
            roadGroup.add(rMesh);
        });
    }

    function animate() {
        if (!is3DActive) return;
        animationFrameId = requestAnimationFrame(animate);

        // Medir Tasa de Cuadros (RNF-02: >= 30 FPS)
        const now = performance.now();
        frameCount++;
        if (now - fpsTimer >= 500) {
            currentFps = Math.round((frameCount * 1000) / (now - fpsTimer));
            frameCount = 0;
            fpsTimer = now;

            const fpsBadge = containerEl ? containerEl.querySelector('#webgl-fps-badge') : null;
            if (fpsBadge) {
                fpsBadge.textContent = `${currentFps} FPS`;
                fpsBadge.style.color = currentFps >= 30 ? '#10b981' : '#f59e0b';
                fpsBadge.style.borderColor = currentFps >= 30 ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)';
            }
        }

        // Animación suave de las balizas luminiscentes
        if (beaconGroup) {
            const time = now * 0.003;
            beaconGroup.children.forEach((child, i) => {
                if (child.geometry && child.geometry.type === 'SphereGeometry') {
                    child.position.y += Math.sin(time + i) * 0.02;
                }
            });
        }

        if (renderer && scene && camera) {
            renderer.render(scene, camera);
        }
    }

    function toggle3D(forceState) {
        ensureContainer();
        const nextState = typeof forceState === 'boolean' ? forceState : !is3DActive;
        is3DActive = nextState;

        if (is3DActive) {
            containerEl.style.display = 'block';
            if (typeof THREE === 'undefined') {
                cargarThreeJs(() => {
                    initScene();
                    onWindowResize();
                    animate();
                });
            } else {
                initScene();
                onWindowResize();
                animate();
            }
        } else {
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }
            if (containerEl) {
                containerEl.style.display = 'none';
            }
        }

        // Notificar al checkbox de Blazor si existe
        const sw3d = document.getElementById('sw-3d');
        if (sw3d && sw3d.checked !== is3DActive) {
            sw3d.checked = is3DActive;
        }

        return is3DActive;
    }

    function cargarThreeJs(onLoaded) {
        if (typeof THREE !== 'undefined') {
            onLoaded();
            return;
        }
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
        script.onload = () => {
            console.log('[Arquis WebGL] Three.js cargado satisfactoriamente.');
            onLoaded();
        };
        script.onerror = () => {
            console.error('[Arquis WebGL] Error al cargar Three.js desde CDN.');
        };
        document.head.appendChild(script);
    }

    return {
        init: ensureContainer,
        toggle3D: toggle3D,
        isActive: () => is3DActive,
        setPitch: (deg) => { pitchDeg = deg; updateCameraPosition(); },
        setBearing: (deg) => { bearingDeg = deg; updateCameraPosition(); },
        getFps: () => currentFps
    };
})();
