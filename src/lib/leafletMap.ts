// Shared Leaflet + OpenStreetMap settings for the voting map: the web version
// (VotingMap.web.tsx) and the Android WebView version (VotingMap.android.tsx).
// No imports, so it can be loaded directly by Node for testing.

/** OpenStreetMap tiles: free, no key, attribution required. Darkened with a CSS filter. */
export const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export const LEAFLET_VERSION = '1.9.4';
// Subresource integrity hashes for the files above (checked against unpkg and node_modules/leaflet)
export const LEAFLET_CSS_SRI = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
const LEAFLET_JS_SRI = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';

export type MapTheme = {
  background: string;
  card: string;
  text: string;
  textMuted: string;
  blue: string;
  red: string;
};

/**
 * A full HTML page with a Leaflet map, for a WebView. The page script is a string because
 * Hermes doesn't keep function source text. Talks to React Native through:
 *   window.setData({ places, origin })  draw pins (places use the VotingPlace shape)
 *   window.select(index)                highlight one place (-1 for none)
 *   postMessage {type: 'ready'}         once the functions above exist
 *   postMessage {type: 'select', index} when a pin is tapped
 */
export function buildLeafletHtml(theme: MapTheme): string {
  const c = JSON.stringify(theme);
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.css"
  integrity="${LEAFLET_CSS_SRI}" crossorigin="" />
<script src="https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.js"
  integrity="${LEAFLET_JS_SRI}" crossorigin=""></script>
<style>
  html, body, #map { margin: 0; height: 100%; background: ${theme.card}; }
  .leaflet-container {
    background: ${theme.background};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }
  .dark-tiles { filter: invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.9) saturate(0.6); }
  .leaflet-popup-content-wrapper, .leaflet-popup-tip {
    background: ${theme.card}; color: ${theme.text}; box-shadow: 0 3px 14px rgba(0, 0, 0, 0.5);
  }
  .leaflet-popup-content { font-size: 14px; line-height: 1.4; }
  .leaflet-container a.leaflet-popup-close-button { color: ${theme.textMuted}; }
</style>
</head>
<body>
<div id="map"></div>
<script>
(function () {
  var C = ${c};
  function post(msg) {
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(JSON.stringify(msg));
  }
  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, function (ch) { return '&#' + ch.charCodeAt(0) + ';'; });
  }

  // keyboard: false, because focusing the map on press scrolls the page and the tap is lost.
  // No zoom buttons: phones pinch to zoom, and the buttons covered popups.
  var map = L.map('map', { keyboard: false, zoomControl: false }).setView([39.8, -98.6], 4);
  L.tileLayer(${JSON.stringify(TILES)}, {
    attribution: ${JSON.stringify(ATTRIBUTION)}, maxZoom: 19, className: 'dark-tiles'
  }).addTo(map);
  var layer = L.layerGroup().addTo(map);
  var pins = [];
  var current = -1;

  window.select = function (i) {
    current = i;
    pins.forEach(function (m, j) {
      if (!m) return;
      var on = j === i;
      m.setStyle({ fillColor: on ? C.red : C.blue });
      m.setRadius(on ? 12 : 9);
      if (on) { m.bringToFront(); map.panTo(m.getLatLng()); m.openPopup(); }
    });
  };

  window.setData = function (data) {
    layer.clearLayers();
    pins = [];
    var bounds = [];
    if (data.origin) {
      L.circleMarker([data.origin.lat, data.origin.lng], {
        radius: 7, color: C.background, weight: 2, fillColor: C.text, fillOpacity: 1
      }).bindTooltip('Your address').addTo(layer);
      bounds.push([data.origin.lat, data.origin.lng]);
    }
    (data.places || []).forEach(function (p, i) {
      if (p.lat == null || p.lng == null) { pins.push(null); return; }
      var m = L.circleMarker([p.lat, p.lng], {
        radius: 9, color: C.background, weight: 2, fillColor: C.blue, fillOpacity: 1
      })
        .bindPopup('<strong>' + esc(p.name) + '</strong><br/>' + esc(p.address))
        .on('click', function () { post({ type: 'select', index: i }); })
        .addTo(layer);
      pins.push(m);
      bounds.push([p.lat, p.lng]);
    });
    map.invalidateSize();
    if (bounds.length === 1) map.setView(bounds[0], 14);
    else if (bounds.length > 1) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
    if (current >= 0) window.select(current);
  };

  post({ type: 'ready' });
})();
</script>
</body>
</html>`;
}
