import { useEffect } from 'react'
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'

// Leaflet's default marker icons break under bundlers; use inline SVG pins instead.
const pin = (color) => L.divIcon({
  className: '',
  html: `<svg width="28" height="38" viewBox="0 0 28 38" xmlns="http://www.w3.org/2000/svg"><path d="M14 0C6.3 0 0 6.2 0 13.8 0 24 14 38 14 38s14-14 14-24.2C28 6.2 21.7 0 14 0z" fill="${color}"/><circle cx="14" cy="14" r="5" fill="white"/></svg>`,
  iconSize: [28, 38], iconAnchor: [14, 38], popupAnchor: [0, -34],
})
// Soft pastel pin colours to match the app theme
const COLORS = { me: '#4a90b8', hospital: '#dc7a80', clinic: '#e5b567', pharmacy: '#4aa98f', blood_bank: '#a58bd0', ambulance: '#64748b' }

function Recenter({ center }) {
  const map = useMap()
  useEffect(() => { map.setView(center, map.getZoom()) }, [center[0], center[1]]) // eslint-disable-line
  return null
}

export default function MapView({ center, places = [] }) {
  return (
    <MapContainer center={center} zoom={14} scrollWheelZoom={false}>
      <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <Recenter center={center} />
      <Marker position={center} icon={pin(COLORS.me)}><Popup>You are here</Popup></Marker>
      <Circle center={center} radius={200} pathOptions={{ color: COLORS.me, weight: 1 }} />
      {places.map((p, i) => (
        <Marker key={i} position={[p.lat, p.lon]} icon={pin(COLORS[p.kind] || '#64748b')}>
          <Popup><b>{p.name}</b><br />{p.distance_km} km away{p.phone ? <><br />{p.phone}</> : null}</Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}