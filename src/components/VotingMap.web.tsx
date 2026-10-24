import { Colors } from '@/constants/Colors';
import { ATTRIBUTION, TILES } from '@/lib/leafletMap';
import { VotingPlace } from '@/lib/votingPlacesApi';
import type { CircleMarker, Map as LeafletMap } from 'leaflet';
import { useEffect, useRef } from 'react';

type Point = { lat: number; lng: number };

// Tiles are darkened in leafletDark.css (Android uses the same filter, in leafletMap.ts).

const escape = (s: string) =>
  s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

/**
 * Web version of VotingMap, drawn with Leaflet (react-native-maps doesn't run in a browser).
 * Leaflet touches `window` when it loads, so it's imported inside an effect; static
 * rendering runs in Node, where there is no window.
 */
export function VotingMap({
  places,
  origin,
  selected,
  onSelect,
}: {
  places: VotingPlace[];
  origin: Point | null;
  selected: number | null;
  onSelect: (index: number) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<LeafletMap | null>(null);
  const markers = useRef<Map<number, CircleMarker>>(new Map());
  const onSelectRef = useRef(onSelect);
  useEffect(() => {
    onSelectRef.current = onSelect;
  });

  const hasPoints = !!origin || places.some((p) => p.lat !== null && p.lng !== null);

  // Build the map and its pins whenever the list of places changes
  useEffect(() => {
    if (!hasPoints || !container.current) return;
    let cancelled = false;
    const pins = markers.current;

    import('leaflet').then((mod) => {
      const L = mod.default ?? mod;
      if (cancelled || !container.current) return;

      // keyboard: false, because Leaflet focuses the map on press for arrow-key panning, and the
      // browser then scrolls the page to show it, so the pin slides out from under your finger
      // and the tap is lost. The list below the map covers keyboard and screen-reader users.
      // No zoom buttons: phones pinch to zoom, and the buttons covered popups.
      const m = L.map(container.current, { keyboard: false, zoomControl: false });
      L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 19, className: 'dark-tiles' }).addTo(m);

      const bounds: [number, number][] = [];
      if (origin) {
        L.circleMarker([origin.lat, origin.lng], {
          radius: 7,
          color: Colors.background,
          weight: 2,
          fillColor: Colors.text,
          fillOpacity: 1,
        })
          .bindTooltip('Your address')
          .addTo(m);
        bounds.push([origin.lat, origin.lng]);
      }

      pins.clear();
      places.forEach((p, i) => {
        if (p.lat === null || p.lng === null) return;
        const marker = L.circleMarker([p.lat, p.lng], {
          radius: 9,
          color: Colors.background,
          weight: 2,
          fillColor: Colors.blue,
          fillOpacity: 1,
        })
          .bindPopup(`<strong>${escape(p.name)}</strong><br/>${escape(p.address)}`)
          .on('click', () => onSelectRef.current(i))
          .addTo(m);
        pins.set(i, marker);
        bounds.push([p.lat, p.lng]);
      });

      if (bounds.length === 1) m.setView(bounds[0], 14);
      else m.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
      map.current = m;
    });

    return () => {
      cancelled = true;
      map.current?.remove();
      map.current = null;
      pins.clear();
    };
  }, [places, origin, hasPoints]);

  // Highlight the selected place in red and bring it into view
  useEffect(() => {
    markers.current.forEach((marker, i) => {
      const on = i === selected;
      marker.setStyle({ fillColor: on ? Colors.red : Colors.blue });
      marker.setRadius(on ? 12 : 9);
      if (on) {
        marker.bringToFront();
        map.current?.panTo(marker.getLatLng());
      }
    });
  }, [selected]);

  if (!hasPoints) return null;

  return (
    <div
      ref={container}
      style={{
        height: 260,
        borderRadius: 18,
        overflow: 'hidden',
        marginBottom: 16,
        backgroundColor: Colors.card,
        // Leaflet panes use z-indexes up to 1000; keep them under the app's header
        position: 'relative',
        zIndex: 0,
      }}
    />
  );
}
