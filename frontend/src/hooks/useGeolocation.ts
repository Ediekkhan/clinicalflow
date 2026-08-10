'use client';

import { useState } from 'react';

type Coordinates = { latitude: number; longitude: number };

function validCoordinates(coords: Coordinates) {
  return coords.latitude >= -90 && coords.latitude <= 90 && coords.longitude >= -180 && coords.longitude <= 180;
}

export function useGeolocation() {
  const [coords, setCoords] = useState<Coordinates | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function requestLocation() {
    if (!navigator.geolocation) {
      setCoords(null);
      setError('Location is not available on this device. Entering the queue requires your current location.');
      return;
    }
    setIsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const nextCoords = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        if (!validCoordinates(nextCoords)) {
          setCoords(null);
          setError('Your browser returned invalid coordinates. Please try again.');
        } else {
          setCoords(nextCoords);
          setError(null);
        }
        setIsLoading(false);
      },
      () => {
        setCoords(null);
        setError('Location permission was denied. We need your location to route you to the nearest registered hospital.');
        setIsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  }

  return { coords, error, isLoading, requestLocation };
}
