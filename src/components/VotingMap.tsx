import { Colors } from '@/constants/Colors';
import { VotingPlace } from '@/lib/votingPlacesApi';
import { useRef } from 'react';
import { StyleSheet, View } from 'react-native';
import MapView, { Marker } from 'react-native-maps';

type Point = { lat: number; lng: number };

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
  const map = useRef<MapView>(null);
  const pinned = places
    .map((p, i) => ({ p, i }))
    .filter(({ p }) => p.lat !== null && p.lng !== null);

  const coords = [
    ...(origin ? [{ latitude: origin.lat, longitude: origin.lng }] : []),
    ...pinned.map(({ p }) => ({ latitude: p.lat!, longitude: p.lng! })),
  ];
  if (coords.length === 0) return null;

  const fit = () => {
    if (coords.length === 1) return; // initialRegion already centers on it
    map.current?.fitToCoordinates(coords, {
      edgePadding: { top: 40, right: 40, bottom: 40, left: 40 },
      animated: false,
    });
  };

  // Rounded corners go on the wrapper: on Android, borderRadius on MapView itself can blank it
  return (
    <View style={styles.frame}>
      <MapView
        ref={map}
        style={StyleSheet.absoluteFill}
        initialRegion={{
          ...coords[0],
          latitudeDelta: 0.08,
          longitudeDelta: 0.08,
        }}
        onMapReady={fit}
        userInterfaceStyle="dark"
      >
        {origin && (
          <Marker
            coordinate={{ latitude: origin.lat, longitude: origin.lng }}
            title="Your address"
            pinColor={Colors.text}
          />
        )}
        {pinned.map(({ p, i }) => (
          <Marker
            key={`${i}-${p.name}`}
            coordinate={{ latitude: p.lat!, longitude: p.lng! }}
            title={p.name}
            description={p.address}
            pinColor={selected === i ? Colors.red : Colors.blue}
            onPress={() => onSelect(i)}
          />
        ))}
      </MapView>
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
});
