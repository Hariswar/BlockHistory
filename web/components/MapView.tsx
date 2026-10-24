"use client";

import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { PublicFinding } from "@/lib/present";
import { AREA } from "@/lib/site";

export type Coverage = {
  sheetId: string;
  year: string;
  sheetNumber: number;
  footprint: GeoJSON.Polygon;
};

// One georeferenced panel of an old map scan (web/public/overlays/<area>.json).
export type Overlay = {
  id: string;
  year: string;
  service: string;
  region: [number, number, number, number]; // x, y, w, h on the full-resolution scan
  corners: [number, number][]; // [lon, lat]: top-left, top-right, bottom-right, bottom-left
  clip: [number, number][]; // panel outline as fractions of the region
  holes: [number, number][][]; // other panels of the sheet, cut out (same fractions)
};

type Props = {
  coverage: Coverage[];
  overlays: Overlay[];
  overlayOpacity: number;
  point: { lat: number; lon: number } | null;
  radiusM: number;
  findings: PublicFinding[];
  active: number | null;
  onSelect: (id: number) => void;
};

// Free vector tiles, no key (OpenStreetMap data).
const STYLE = "https://tiles.openfreemap.org/styles/positron";
const CENTER = AREA.center as [number, number];

function circle(lat: number, lon: number, radiusM: number): GeoJSON.Polygon {
  const kx = 111_320 * Math.cos((lat * Math.PI) / 180);
  const ring = Array.from({ length: 65 }, (_, i) => {
    const a = (i / 64) * 2 * Math.PI;
    return [lon + (radiusM * Math.cos(a)) / kx, lat + (radiusM * Math.sin(a)) / 111_320];
  });
  return { type: "Polygon", coordinates: [ring] };
}

const IIIF = "https://tile.loc.gov/image-services/iiif";

// The scan region, cut to the panel outline so panels of one sheet don't cover each other.
function loadPanel(o: Overlay): Promise<HTMLCanvasElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const c = document.createElement("canvas");
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      const ctx = c.getContext("2d")!;
      ctx.beginPath();
      o.clip.forEach(([fx, fy], i) => (i ? ctx.lineTo : ctx.moveTo).call(ctx, fx * c.width, fy * c.height));
      ctx.closePath();
      ctx.clip();
      ctx.drawImage(img, 0, 0);
      ctx.globalCompositeOperation = "destination-out";
      for (const hole of o.holes) {
        ctx.beginPath();
        hole.forEach(([fx, fy], i) => (i ? ctx.lineTo : ctx.moveTo).call(ctx, fx * c.width, fy * c.height));
        ctx.fill();
      }
      resolve(c);
    };
    img.onerror = reject;
    img.src = `${IIIF}/${o.service}/${o.region.join(",")}/!2048,2048/0/default.jpg`;
  });
}

export default function MapView({
  coverage,
  overlays,
  overlayOpacity,
  point,
  radiusM,
  findings,
  active,
  onSelect,
}: Props) {
  const shownPanels = useRef(new Set<string>());
  const opacity = useRef(overlayOpacity);
  opacity.current = overlayOpacity;
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const elements = useRef(new Map<number, HTMLElement>());
  const [failed, setFailed] = useState(false);
  const select = useRef(onSelect);
  select.current = onSelect;

  useEffect(() => {
    if (!box.current) return;
    let m: maplibregl.Map;
    // MapLibre 6 runs its worker from a separate file the bundler doesn't ship; npm run
    // dev/build copies it into public/ (see package.json).
    maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
    try {
      m = new maplibregl.Map({ container: box.current, style: STYLE, center: CENTER, zoom: 14 });
    } catch {
      // No WebGL (some older devices): the list of findings still works without the map.
      setFailed(true);
      return;
    }
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      m.addSource("coverage", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "coverage-fill", type: "fill", source: "coverage", paint: { "fill-color": "#b23a2e", "fill-opacity": 0.05 } });
      m.addLayer({ id: "coverage-line", type: "line", source: "coverage", paint: { "line-color": "#b23a2e", "line-width": 1.5, "line-dasharray": [3, 2] } });
      m.addSource("radius", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "radius-fill", type: "fill", source: "radius", paint: { "fill-color": "#2c5d8a", "fill-opacity": 0.08 } });
      m.addLayer({ id: "radius-line", type: "line", source: "radius", paint: { "line-color": "#2c5d8a", "line-width": 1.5 } });
      map.current = m;
    });
    return () => {
      m.remove();
      map.current = null;
      shownPanels.current.clear();
    };
  }, []);

  // Coverage outlines.
  useEffect(() => {
    const draw = () => {
      const src = map.current?.getSource("coverage") as maplibregl.GeoJSONSource | undefined;
      src?.setData({
        type: "FeatureCollection",
        features: coverage.map((c) => ({ type: "Feature", properties: { sheet: c.sheetNumber }, geometry: c.footprint })),
      });
    };
    if (map.current) draw();
    else {
      const t = setInterval(() => map.current && (draw(), clearInterval(t)), 200);
      return () => clearInterval(t);
    }
  }, [coverage]);

  // Old map panels under the coverage outlines and markers.
  useEffect(() => {
    const wanted = new Set(overlays.map((o) => o.id));
    const sync = () => {
      const m = map.current!;
      for (const id of [...shownPanels.current]) {
        if (wanted.has(id)) continue;
        if (m.getLayer(`old-${id}`)) m.removeLayer(`old-${id}`);
        if (m.getSource(`old-${id}`)) m.removeSource(`old-${id}`);
        shownPanels.current.delete(id);
      }
      for (const o of overlays) {
        if (shownPanels.current.has(o.id)) continue;
        shownPanels.current.add(o.id);
        loadPanel(o)
          .then((canvas) => {
            // Skip if the search or year changed while the image loaded.
            if (!map.current || !shownPanels.current.has(o.id) || m.getSource(`old-${o.id}`)) return;
            m.addSource(`old-${o.id}`, {
              type: "canvas",
              canvas,
              animate: false,
              coordinates: o.corners as [[number, number], [number, number], [number, number], [number, number]],
            });
            m.addLayer(
              {
                id: `old-${o.id}`,
                type: "raster",
                source: `old-${o.id}`,
                paint: { "raster-opacity": opacity.current / 100, "raster-fade-duration": 0 },
              },
              "coverage-fill",
            );
            // Stack in the given order (the panel holding the address last, on top).
            for (const other of overlays) {
              if (m.getLayer(`old-${other.id}`)) m.moveLayer(`old-${other.id}`, "coverage-fill");
            }
          })
          .catch(() => shownPanels.current.delete(o.id));
      }
    };
    if (map.current) sync();
    else {
      const t = setInterval(() => map.current && (sync(), clearInterval(t)), 200);
      return () => clearInterval(t);
    }
  }, [overlays]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    for (const id of shownPanels.current) {
      if (m.getLayer(`old-${id}`)) m.setPaintProperty(`old-${id}`, "raster-opacity", overlayOpacity / 100);
    }
  }, [overlayOpacity]);

  // Search point, radius and numbered finding markers.
  useEffect(() => {
    const draw = () => {
      const m = map.current!;
      markers.current.forEach((mk) => mk.remove());
      markers.current = [];
      elements.current.clear();
      const radius = m.getSource("radius") as maplibregl.GeoJSONSource;
      if (!point) {
        radius.setData({ type: "FeatureCollection", features: [] });
        return;
      }
      radius.setData({ type: "Feature", properties: {}, geometry: circle(point.lat, point.lon, radiusM) });
      const home = document.createElement("div");
      home.className = "marker home";
      home.title = "The address you searched";
      markers.current.push(new maplibregl.Marker({ element: home }).setLngLat([point.lon, point.lat]).addTo(m));
      findings.forEach((f, i) => {
        const el = document.createElement("button");
        el.className = `marker ${f.relevance}`;
        el.textContent = String(i + 1);
        el.setAttribute("aria-label", `${i + 1}: ${f.title}`);
        el.onclick = () => select.current(f.id);
        elements.current.set(f.id, el);
        markers.current.push(new maplibregl.Marker({ element: el }).setLngLat([f.lon, f.lat]).addTo(m));
      });
      const bounds = new maplibregl.LngLatBounds();
      circle(point.lat, point.lon, radiusM).coordinates[0].forEach((c) => bounds.extend(c as [number, number]));
      findings.forEach((f) => bounds.extend([f.lon, f.lat]));
      m.fitBounds(bounds, { padding: 40, maxZoom: 18, duration: 600 });
    };
    if (map.current) draw();
    else {
      const t = setInterval(() => map.current && (draw(), clearInterval(t)), 200);
      return () => clearInterval(t);
    }
  }, [point, radiusM, findings]);

  // Highlight the finding whose card is hovered or whose marker was clicked.
  useEffect(() => {
    elements.current.forEach((el, id) => {
      el.style.outline = id === active ? "3px solid #1f1d1a" : "";
      el.style.zIndex = id === active ? "2" : "";
    });
  }, [active, findings]);

  if (failed) {
    return (
      <p className="small" style={{ padding: 16 }}>
        The map can&apos;t be shown in this browser. The list of past uses still works.
      </p>
    );
  }
  return <div ref={box} style={{ width: "100%", height: "100%" }} role="img" aria-label="Map of the address and nearby past uses" />;
}
