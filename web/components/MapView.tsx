"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { PublicFinding } from "@/lib/present";

export type Coverage = {
  sheetId: string;
  year: string;
  sheetNumber: number;
  footprint: GeoJSON.Polygon;
};

type Props = {
  coverage: Coverage[];
  point: { lat: number; lon: number } | null;
  radiusM: number;
  findings: PublicFinding[];
  active: number | null;
  onSelect: (id: number) => void;
};

// Free vector tiles, no key (OpenStreetMap data).
const STYLE = "https://tiles.openfreemap.org/styles/positron";
const CARONDELET: [number, number] = [-90.256, 38.552];

function circle(lat: number, lon: number, radiusM: number): GeoJSON.Polygon {
  const kx = 111_320 * Math.cos((lat * Math.PI) / 180);
  const ring = Array.from({ length: 65 }, (_, i) => {
    const a = (i / 64) * 2 * Math.PI;
    return [lon + (radiusM * Math.cos(a)) / kx, lat + (radiusM * Math.sin(a)) / 111_320];
  });
  return { type: "Polygon", coordinates: [ring] };
}

export default function MapView({ coverage, point, radiusM, findings, active, onSelect }: Props) {
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
    try {
      m = new maplibregl.Map({ container: box.current, style: STYLE, center: CARONDELET, zoom: 14 });
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
