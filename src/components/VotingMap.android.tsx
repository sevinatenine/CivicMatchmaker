import { Colors } from '@/constants/Colors';
import { buildLeafletHtml } from '@/lib/leafletMap';
import { VotingPlace } from '@/lib/votingPlacesApi';
import { ComponentType, RefAttributes, useEffect, useRef } from 'react';
import { Linking, StyleSheet, View } from 'react-native';
import { WebView as RNWebView, WebViewMessageEvent, WebViewProps } from 'react-native-webview';

type Point = { lat: number; lng: number };

// react-native-webview 14 declares `WebView<P = undefined>`, and `WebViewProps & undefined` is
// `never`, so plain <WebView> rejects every prop. Same component, typed with the real props.
type WebViewHandle = RNWebView<object>;
const WebView = RNWebView as unknown as ComponentType<WebViewProps & RefAttributes<WebViewHandle>>;

// Android: Leaflet + OpenStreetMap in a WebView, the same free map as the website.
// (react-native-maps on Android is Google Maps, which needs a key and a billing account.)
const HTML = buildLeafletHtml(Colors);
// Gives OpenStreetMap tile requests a Referer, which its tile policy requires
const BASE_URL = 'https://civicmatchmaker.app/';

/** Pins for each voting place, plus your address. Fits the map to show all of them. */
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
  const web = useRef<WebViewHandle>(null);
  const ready = useRef(false);
  const latest = useRef({ places, origin, selected, onSelect });
  useEffect(() => {
    latest.current = { places, origin, selected, onSelect };
  });

  const send = (js: string) => web.current?.injectJavaScript(`${js}; true;`);
  const sendData = (p: VotingPlace[], o: Point | null) =>
    send(`window.setData(${JSON.stringify({ places: p, origin: o })})`);
  const sendSelected = (i: number | null) => send(`window.select(${i ?? -1})`);

  // After the page is ready, keep it in sync with the props
  useEffect(() => {
    if (ready.current) sendData(places, origin);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- send helpers only use refs
  }, [places, origin]);
  useEffect(() => {
    if (ready.current) sendSelected(selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- send helpers only use refs
  }, [selected]);

  const onMessage = (e: WebViewMessageEvent) => {
    let msg: { type?: string; index?: number };
    try {
      msg = JSON.parse(e.nativeEvent.data);
    } catch {
      return;
    }
    if (msg.type === 'ready') {
      ready.current = true;
      const l = latest.current;
      sendData(l.places, l.origin);
      if (l.selected !== null) sendSelected(l.selected);
    } else if (msg.type === 'select' && typeof msg.index === 'number') {
      latest.current.onSelect(msg.index);
    }
  };

  const hasPoints = !!origin || places.some((p) => p.lat !== null && p.lng !== null);
  if (!hasPoints) return null;

  return (
    <View style={styles.frame}>
      <WebView
        ref={web}
        originWhitelist={['*']}
        source={{ html: HTML, baseUrl: BASE_URL }}
        applicationNameForUserAgent="CivicMatchmaker/1.0"
        onMessage={onMessage}
        // A reload starts a fresh page; wait for its 'ready' again
        onLoadStart={() => {
          ready.current = false;
        }}
        // Links in the map (e.g. the OpenStreetMap credit) open in the browser, not in the map
        onShouldStartLoadWithRequest={(req) => {
          if (req.url === BASE_URL || req.url.startsWith('about:')) return true;
          Linking.openURL(req.url);
          return false;
        }}
        nestedScrollEnabled
        scrollEnabled={false}
        setSupportMultipleWindows={false}
        style={styles.web}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    height: 260,
    borderRadius: 18,
    overflow: 'hidden',
    marginBottom: 16,
    backgroundColor: Colors.card,
  },
  web: { flex: 1, backgroundColor: Colors.card },
});
