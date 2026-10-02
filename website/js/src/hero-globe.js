/*
 * Growth & Beyond: 3D hero
 * The logo in 3D: a dotted globe, a graduation cap resting on it and the green
 * growth arrow sweeping past, with study-abroad routes flying out of Chennai.
 *
 * Source file. The page loads the bundled build at js/hero-globe.js; see README.
 */
import {
  AdditiveBlending,
  AmbientLight,
  BackSide,
  BoxGeometry,
  BufferGeometry,
  CanvasTexture,
  CatmullRomCurve3,
  Color,
  ConeGeometry,
  CylinderGeometry,
  DirectionalLight,
  DoubleSide,
  EdgesGeometry,
  Float32BufferAttribute,
  Group,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  RingGeometry,
  Scene,
  ShaderMaterial,
  SphereGeometry,
  SRGBColorSpace,
  TorusGeometry,
  TubeGeometry,
  Vector3,
  WebGLRenderer,
} from 'three';
import { LAND } from './landmask.js';

const R = 2;
const DEG = Math.PI / 180;
const BRAND = {
  sky: new Color('#4cc0f5'),
  skyDeep: new Color('#2f8fd6'),
  green: new Color('#2fa84f'),
  greenLight: new Color('#6fe08a'),
};

const CHENNAI = { name: 'Chennai', lat: 13.08, lon: 80.27 };
const DESTINATIONS = [
  { name: 'UK', lat: 51.51, lon: -0.13, anchor: 'left' },
  { name: 'Singapore', lat: 1.35, lon: 103.82, anchor: 'right' },
  { name: 'USA', lat: 40.71, lon: -74.0, anchor: 'right' },
  { name: 'Australia', lat: -33.87, lon: 151.21, anchor: 'up' },
  { name: 'Germany', lat: 52.52, lon: 13.4, anchor: 'right' },
  { name: 'Canada', lat: 43.65, lon: -79.38, anchor: 'left' },
  { name: 'Malaysia', lat: 3.14, lon: 101.69, anchor: 'left' },
  { name: 'Ireland', lat: 53.35, lon: -6.26, anchor: 'up' },
  { name: 'New Zealand', lat: -36.85, lon: 174.76, anchor: 'right' },
  { name: 'Europe', lat: 45.46, lon: 9.19, anchor: 'down' },
];

const ARC = { grow: 1.6, hold: 1.5, retract: 1.0 };
const ANCHORS = {
  up: 'translate(-50%, -150%)',
  down: 'translate(-50%, 70%)',
  left: 'translate(calc(-100% - 12px), -50%)',
  right: 'translate(12px, -50%)',
};

const toVec = (lat, lon, r = R) => {
  const phi = lat * DEG;
  const lam = lon * DEG;
  return new Vector3(r * Math.cos(phi) * Math.sin(lam), r * Math.sin(phi), r * Math.cos(phi) * Math.cos(lam));
};
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);

function dotTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(0.55, 'rgba(255,255,255,0.95)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.beginPath();
  g.arc(32, 32, 32, 0, Math.PI * 2);
  g.fill();
  const tex = new CanvasTexture(c);
  tex.colorSpace = SRGBColorSpace;
  return tex;
}

function landDots(count) {
  const bits = Uint8Array.from(atob(LAND), (ch) => ch.charCodeAt(0));
  const isLand = (lat, lon) => {
    const row = Math.min(179, Math.max(0, Math.floor(90 - lat)));
    const col = Math.min(359, Math.max(0, Math.floor(lon + 180)));
    const i = row * 360 + col;
    return (bits[i >> 3] >> (i & 7)) & 1;
  };

  const positions = [];
  const colors = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  const c = new Color();
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const theta = golden * i;
    const x = Math.cos(theta) * radius;
    const z = Math.sin(theta) * radius;
    const lat = Math.asin(y) / DEG;
    const lon = Math.atan2(x, z) / DEG;
    if (!isLand(lat, lon)) continue;
    positions.push(x * R * 1.003, y * R * 1.003, z * R * 1.003);
    const india = lat > 6 && lat < 36 && lon > 67 && lon < 98;
    if (india) c.copy(BRAND.greenLight);
    else c.copy(BRAND.sky).lerp(BRAND.skyDeep, Math.random() * 0.35).multiplyScalar(1.15);
    colors.push(c.r, c.g, c.b);
  }
  const geo = new BufferGeometry();
  geo.setAttribute('position', new Float32BufferAttribute(positions, 3));
  geo.setAttribute('color', new Float32BufferAttribute(colors, 3));
  return geo;
}

function gridLines() {
  const pts = [];
  const seg = 96;
  for (let lat = -60; lat <= 60; lat += 30) {
    for (let i = 0; i < seg; i++) {
      const a = toVec(lat, (i / seg) * 360 - 180, R * 1.001);
      const b = toVec(lat, ((i + 1) / seg) * 360 - 180, R * 1.001);
      pts.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
  }
  for (let lon = -180; lon < 180; lon += 30) {
    for (let i = 0; i < seg / 2; i++) {
      const a = toVec((i / (seg / 2)) * 180 - 90, lon, R * 1.001);
      const b = toVec(((i + 1) / (seg / 2)) * 180 - 90, lon, R * 1.001);
      pts.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
  }
  const geo = new BufferGeometry();
  geo.setAttribute('position', new Float32BufferAttribute(pts, 3));
  return new LineSegments(geo, new LineBasicMaterial({ color: BRAND.sky, transparent: true, opacity: 0.09, depthWrite: false }));
}

const fresnelVertex = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

function globeBody() {
  return new Mesh(
    new SphereGeometry(R, 64, 64),
    new ShaderMaterial({
      vertexShader: fresnelVertex,
      fragmentShader: /* glsl */ `
        varying vec3 vNormal;
        varying vec3 vView;
        void main() {
          float f = 1.0 - max(dot(vNormal, vView), 0.0);
          vec3 base = vec3(0.027, 0.086, 0.215);
          vec3 rim = vec3(0.16, 0.52, 0.86);
          gl_FragColor = vec4(mix(base, rim, pow(f, 2.4) * 0.7), 1.0);
        }
      `,
    }),
  );
}

function atmosphere() {
  return new Mesh(
    new SphereGeometry(R * 1.16, 64, 64),
    new ShaderMaterial({
      vertexShader: fresnelVertex,
      fragmentShader: /* glsl */ `
        varying vec3 vNormal;
        varying vec3 vView;
        void main() {
          // back faces: 0 at the outer edge, rising towards the globe
          float d = clamp(-dot(vNormal, vView), 0.0, 1.0);
          float i = pow(d, 2.0) * 2.4;
          gl_FragColor = vec4(0.30, 0.75, 0.96, 1.0) * i;
        }
      `,
      side: BackSide,
      blending: AdditiveBlending,
      transparent: true,
      depthWrite: false,
    }),
  );
}

function makeArc(from, to, index) {
  const a = toVec(from.lat, from.lon);
  const b = toVec(to.lat, to.lon);
  const angle = a.angleTo(b);
  const axis = new Vector3().crossVectors(a, b).normalize();
  const height = Math.min(0.55, 0.1 + angle * 0.2);
  const pts = [];
  for (let i = 0; i <= 48; i++) {
    const t = i / 48;
    pts.push(a.clone().applyAxisAngle(axis, angle * t).setLength(R + Math.sin(Math.PI * t) * height));
  }
  const curve = new CatmullRomCurve3(pts);
  const segments = 140;
  const radial = 6;
  const geo = new TubeGeometry(curve, segments, 0.0085, radial, false);

  // colour runs green at Chennai to sky blue at the destination
  const uv = geo.attributes.uv;
  const colors = new Float32Array(uv.count * 3);
  const c = new Color();
  for (let i = 0; i < uv.count; i++) {
    c.copy(BRAND.greenLight).lerp(BRAND.sky, uv.getX(i));
    colors.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new Float32BufferAttribute(colors, 3));
  geo.setDrawRange(0, 0);
  const tube = new Mesh(geo, new MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.95, depthWrite: false }));

  const head = new Mesh(new SphereGeometry(0.03, 12, 12), new MeshBasicMaterial({ color: '#e9fbff' }));
  const halo = new Mesh(
    new SphereGeometry(0.07, 12, 12),
    new MeshBasicMaterial({ color: BRAND.sky, transparent: true, opacity: 0.35, blending: AdditiveBlending, depthWrite: false }),
  );
  head.add(halo);
  head.visible = false;

  const normal = b.clone().normalize();
  const marker = new Mesh(new SphereGeometry(0.024, 12, 12), new MeshBasicMaterial({ color: BRAND.sky }));
  marker.position.copy(normal.clone().multiplyScalar(R * 1.004));
  const ring = new Mesh(
    new RingGeometry(0.035, 0.05, 32),
    new MeshBasicMaterial({ color: BRAND.sky, transparent: true, opacity: 0, side: DoubleSide, depthWrite: false }),
  );
  ring.position.copy(normal.clone().multiplyScalar(R * 1.006));
  ring.quaternion.setFromUnitVectors(new Vector3(0, 0, 1), normal);

  return {
    to,
    curve,
    tube,
    head,
    marker,
    ring,
    normal,
    segments,
    indexPerSegment: radial * 6,
    offset: index * 0.85,
    idle: 0.6 + ((index * 7) % 5) * 0.45,
    label: null,
    labelAlpha: 0,
  };
}

function makeCap() {
  const cap = new Group();
  const navy = new MeshStandardMaterial({ color: '#13285a', roughness: 0.5, metalness: 0.25 });
  const navyDark = new MeshStandardMaterial({ color: '#0b1a3d', roughness: 0.55, metalness: 0.2 });
  const sky = new MeshStandardMaterial({ color: '#4cc0f5', emissive: '#1a6fa8', emissiveIntensity: 0.6, roughness: 0.35 });
  const green = new MeshStandardMaterial({ color: '#3cbf5a', emissive: '#135f28', emissiveIntensity: 0.5, roughness: 0.4 });

  const boardGeo = new BoxGeometry(1.3, 0.06, 1.3);
  const board = new Mesh(boardGeo, navy);
  board.rotation.y = Math.PI / 4;
  cap.add(board);
  const edges = new LineSegments(new EdgesGeometry(boardGeo), new LineBasicMaterial({ color: '#9fe0ff', transparent: true, opacity: 0.85 }));
  edges.rotation.y = Math.PI / 4;
  cap.add(edges);

  const base = new Mesh(new CylinderGeometry(0.42, 0.47, 0.36, 48), navyDark);
  base.position.y = -0.21;
  cap.add(base);
  const band = new Mesh(new TorusGeometry(0.465, 0.03, 12, 64), sky);
  band.rotation.x = Math.PI / 2;
  band.position.y = -0.36;
  cap.add(band);
  const button = new Mesh(new CylinderGeometry(0.055, 0.055, 0.045, 20), sky);
  button.position.y = 0.05;
  cap.add(button);

  const cord = new CatmullRomCurve3([
    new Vector3(0, 0.06, 0),
    new Vector3(0.5, 0.065, 0),
    new Vector3(0.9, 0.045, 0),
    new Vector3(0.94, -0.2, 0.02),
    new Vector3(0.95, -0.44, 0.03),
  ]);
  cap.add(new Mesh(new TubeGeometry(cord, 48, 0.013, 8), green));
  const tassel = new Mesh(new CylinderGeometry(0.028, 0.06, 0.2, 14), green);
  tassel.position.set(0.95, -0.53, 0.03);
  cap.add(tassel);
  return cap;
}

function makeArrow() {
  const curve = new CatmullRomCurve3([
    new Vector3(-2.15, -1.55, 1.5),
    new Vector3(-0.95, -0.95, 2.2),
    new Vector3(0.25, -0.2, 2.35),
    new Vector3(1.25, 0.75, 2.0),
    new Vector3(2.0, 1.8, 1.4),
  ]);
  const segments = 180;
  const radial = 18;
  const geo = new TubeGeometry(curve, segments, 0.072, radial, false);
  const uv = geo.attributes.uv;
  const colors = new Float32Array(uv.count * 3);
  const dark = new Color('#14652b');
  const light = new Color('#4fd06b');
  const c = new Color();
  for (let i = 0; i < uv.count; i++) {
    c.copy(dark).lerp(light, uv.getX(i));
    colors.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new Float32BufferAttribute(colors, 3));
  geo.setDrawRange(0, 0);
  const material = new MeshStandardMaterial({
    vertexColors: true,
    emissive: '#0d5a23',
    emissiveIntensity: 0.55,
    roughness: 0.32,
    metalness: 0.18,
  });
  const tube = new Mesh(geo, material);

  const end = curve.getPoint(1);
  const tangent = curve.getTangent(1).normalize();
  const head = new Mesh(new ConeGeometry(0.2, 0.44, 32), new MeshStandardMaterial({ color: '#4fd06b', emissive: '#16702f', emissiveIntensity: 0.55, roughness: 0.3, metalness: 0.15 }));
  head.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), tangent);
  head.position.copy(end).add(tangent.clone().multiplyScalar(0.18));
  head.scale.setScalar(0.001);

  const group = new Group();
  group.add(tube, head);
  return { group, tube, head, total: segments * radial * 6 };
}

export function initHeroGlobe(container) {
  const canvas = container.querySelector('canvas');
  const labelLayer = container.querySelector('.globe3d__labels');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const small = window.matchMedia('(max-width: 640px)').matches;

  const probe = document.createElement('canvas');
  if (!(probe.getContext('webgl2') || probe.getContext('webgl'))) return null;

  let renderer;
  try {
    renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch (err) {
    return null;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.75 : 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = SRGBColorSpace;

  const scene = new Scene();
  const camera = new PerspectiveCamera(32, 1, 0.1, 100);
  const camBase = new Vector3(0, 0.2, 9.4);
  camera.position.copy(camBase);

  scene.add(new AmbientLight('#bcd7ff', 0.75));
  const key = new DirectionalLight('#ffffff', 1.7);
  key.position.set(3, 5, 6);
  scene.add(key);
  const rim = new DirectionalLight('#38b2f0', 1.4);
  rim.position.set(-5, 1.5, -2);
  scene.add(rim);

  // root holds the whole logo composition; the globe group spins inside it
  const root = new Group();
  scene.add(root);
  const globe = new Group();
  globe.rotation.x = 0.36;
  root.add(globe);

  globe.add(globeBody());
  root.add(atmosphere());
  globe.add(gridLines());
  const dots = new Points(
    landDots(small ? 15000 : 24000),
    new PointsMaterial({ size: small ? 0.056 : 0.05, map: dotTexture(), vertexColors: true, transparent: true, depthWrite: false, alphaTest: 0.02 }),
  );
  globe.add(dots);

  // Chennai: home base
  const home = toVec(CHENNAI.lat, CHENNAI.lon, R * 1.006);
  const homeNormal = home.clone().normalize();
  const homeDot = new Mesh(new SphereGeometry(0.045, 16, 16), new MeshBasicMaterial({ color: BRAND.greenLight }));
  homeDot.position.copy(home);
  globe.add(homeDot);
  const homeRings = [0, 1].map(() => {
    const ring = new Mesh(
      new RingGeometry(0.06, 0.075, 40),
      new MeshBasicMaterial({ color: BRAND.greenLight, transparent: true, opacity: 0, side: DoubleSide, depthWrite: false }),
    );
    ring.position.copy(home);
    ring.quaternion.setFromUnitVectors(new Vector3(0, 0, 1), homeNormal);
    globe.add(ring);
    return ring;
  });

  const arcs = DESTINATIONS.map((d, i) => {
    const arc = makeArc(CHENNAI, d, i);
    globe.add(arc.tube, arc.head, arc.marker, arc.ring);
    return arc;
  });

  // HTML labels that follow points on the globe
  const makeLabel = (text, cls) => {
    const el = document.createElement('span');
    el.className = `globe3d__label ${cls || ''}`;
    el.textContent = text;
    labelLayer.appendChild(el);
    return el;
  };
  const homeLabel = makeLabel(CHENNAI.name, 'is-home');
  arcs.forEach((arc) => { arc.label = makeLabel(arc.to.name); });

  const cap = makeCap();
  cap.position.set(-1.05, 1.92, 0.7);
  cap.rotation.set(0.42, 0.25, 0.22);
  root.add(cap);

  const arrow = makeArrow();
  root.add(arrow.group);

  /* ---------- sizing ---------- */
  let width = 0;
  let height = 0;
  const resize = () => {
    const rect = container.getBoundingClientRect();
    width = Math.max(1, Math.round(rect.width));
    height = Math.max(1, Math.round(rect.height));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  resize();

  /* ---------- interaction ---------- */
  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  const hero = container.closest('.hero') || container;
  if (!reduceMotion && window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    hero.addEventListener('pointermove', (e) => {
      const r = hero.getBoundingClientRect();
      pointer.tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
      pointer.ty = ((e.clientY - r.top) / r.height - 0.5) * 2;
    });
    hero.addEventListener('pointerleave', () => { pointer.tx = 0; pointer.ty = 0; });
  }
  let scrollP = 0;
  const readScroll = () => {
    const r = container.getBoundingClientRect();
    const vh = window.innerHeight || 1;
    scrollP = clamp01((vh * 0.5 - (r.top + r.height * 0.5)) / vh);
  };
  window.addEventListener('scroll', readScroll, { passive: true });
  readScroll();

  /* ---------- per-frame update ---------- */
  const tmp = new Vector3();
  const tmp2 = new Vector3();
  const centre = new Vector3();
  const toCam = new Vector3();

  const placeLabel = (el, worldPos, normalWorld, alpha, anchor = 'up') => {
    toCam.copy(camera.position).sub(worldPos).normalize();
    const facing = normalWorld.dot(toCam);
    const vis = alpha * clamp01((facing - 0.18) / 0.25);
    if (vis <= 0.01) {
      el.style.opacity = '0';
      return;
    }
    tmp2.copy(worldPos).project(camera);
    const x = (tmp2.x * 0.5 + 0.5) * width;
    const y = (-tmp2.y * 0.5 + 0.5) * height;
    el.style.opacity = vis.toFixed(3);
    el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) ${ANCHORS[anchor]}`;
  };

  const update = (t) => {
    // gentle sway keeps India in view while showing routes east and west
    const lonCentre = 52 + Math.sin(t * 0.11) * 38 + scrollP * 45;
    globe.rotation.y = -lonCentre * DEG;

    pointer.x += (pointer.tx - pointer.x) * 0.05;
    pointer.y += (pointer.ty - pointer.y) * 0.05;
    root.rotation.y = pointer.x * 0.22;
    root.rotation.x = pointer.y * 0.12;
    root.position.y = scrollP * 0.7;
    camera.position.set(camBase.x, camBase.y, camBase.z - scrollP * 1.1);
    camera.lookAt(0, 0.15 + scrollP * 0.4, 0);

    // cap floats on the globe; arrow draws itself in once
    cap.position.y = 1.92 + Math.sin(t * 1.1) * 0.06 + scrollP * 0.4;
    cap.rotation.z = 0.22 + Math.sin(t * 0.8) * 0.04;
    const draw = easeInOut(clamp01((t - 0.5) / 1.8));
    arrow.tube.geometry.setDrawRange(0, Math.floor(draw * arrow.total));
    arrow.head.scale.setScalar(Math.max(0.001, easeOut(clamp01((t - 2.0) / 0.5))));

    homeRings.forEach((ring, i) => {
      const k = ((t * 0.6 + i * 0.5) % 1);
      ring.scale.setScalar(1 + k * 2.4);
      ring.material.opacity = (1 - k) * 0.8;
    });

    root.updateMatrixWorld();
    root.getWorldPosition(centre);

    arcs.forEach((arc) => {
      const period = ARC.grow + ARC.hold + ARC.retract + arc.idle;
      const local = t - arc.offset - 0.8;
      let head = 0;
      let tail = 0;
      let show = false;
      let arrived = 0;
      if (local > 0) {
        const p = local % period;
        if (p < ARC.grow) {
          head = easeInOut(p / ARC.grow);
          show = true;
        } else if (p < ARC.grow + ARC.hold) {
          head = 1;
          show = true;
          arrived = (p - ARC.grow) / ARC.hold;
        } else if (p < ARC.grow + ARC.hold + ARC.retract) {
          head = 1;
          tail = easeInOut((p - ARC.grow - ARC.hold) / ARC.retract);
          show = true;
        }
      }
      if (reduceMotion) {
        head = 1;
        tail = 0;
        show = true;
        arrived = 0.5;
      }
      const s0 = Math.floor(tail * arc.segments);
      const s1 = Math.floor(head * arc.segments);
      arc.tube.geometry.setDrawRange(s0 * arc.indexPerSegment, show ? Math.max(0, s1 - s0) * arc.indexPerSegment : 0);
      arc.head.visible = show && head < 1;
      if (arc.head.visible) arc.head.position.copy(arc.curve.getPoint(head));

      const ringK = arrived > 0 ? (arrived * 1.6) % 1 : 0;
      arc.ring.scale.setScalar(1 + ringK * 2.2);
      arc.ring.material.opacity = arrived > 0 ? (1 - ringK) * 0.9 : 0;

      const target = arrived > 0 || (show && head >= 1 && tail < 0.6) ? 1 : 0;
      arc.labelAlpha += (target - arc.labelAlpha) * 0.12;
      arc.marker.getWorldPosition(tmp);
      placeLabel(arc.label, tmp, tmp.clone().sub(centre).normalize(), small ? 0 : arc.labelAlpha, arc.to.anchor);
    });

    homeDot.getWorldPosition(tmp);
    placeLabel(homeLabel, tmp, tmp.clone().sub(centre).normalize(), 1);
  };

  /* ---------- render loop ---------- */
  let running = false;
  let visible = true;
  let start = performance.now();
  let pausedAt = 0;
  let frame = 0;

  const render = () => {
    const t = (performance.now() - start) / 1000;
    update(reduceMotion ? 6 : t);
    renderer.render(scene, camera);
    if (!container.classList.contains('is-ready')) {
      container.classList.add('is-ready');
      container.closest('.hero__visual')?.classList.add('has-3d');
    }
  };
  const loop = () => {
    if (!running) return;
    render();
    frame = requestAnimationFrame(loop);
  };
  const play = () => {
    if (running || reduceMotion || !visible || document.hidden) return;
    running = true;
    if (pausedAt) start += performance.now() - pausedAt;
    frame = requestAnimationFrame(loop);
  };
  const pause = () => {
    if (!running) return;
    running = false;
    pausedAt = performance.now();
    cancelAnimationFrame(frame);
  };

  new ResizeObserver(() => {
    resize();
    if (!running) render();
  }).observe(container);

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) play();
      else pause();
    }).observe(container);
  }
  document.addEventListener('visibilitychange', () => (document.hidden ? pause() : play()));
  if (reduceMotion) window.addEventListener('scroll', () => requestAnimationFrame(render), { passive: true });

  render();
  play();
  return { play, pause };
}

const mount = document.querySelector('.globe3d');
if (mount) initHeroGlobe(mount);
