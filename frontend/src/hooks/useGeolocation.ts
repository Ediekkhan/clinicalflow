'use client';

import { useState } from 'react';

export function useGeolocation() {
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  function requestLocation() {
    if (!navigator.geolocation) {
      setError('Location is not available on this device.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
        setError(null);
      },
      () => setError('Location permission was denied.'),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  return { coords, error, requestLocation };
}

