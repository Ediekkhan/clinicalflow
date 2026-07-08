RATE_LIMITS = {
    "auth:patient:login": {"requests": 5, "window_seconds": 300},
    "auth:patient:signup": {"requests": 3, "window_seconds": 3600},
    "auth:specialist:login": {"requests": 5, "window_seconds": 300},
    "auth:staff:login": {"requests": 5, "window_seconds": 300},
    "auth:refresh": {"requests": 10, "window_seconds": 300},
    "triage:analyze": {"requests": 10, "window_seconds": 3600},
    "appointments:create": {"requests": 5, "window_seconds": 3600},
    "webhook:whatsapp": {"requests": 100, "window_seconds": 60},
    "api:general": {"requests": 200, "window_seconds": 60},
}

