/** Tiny hash router — works with the statically-served SPA (no server rewrites). */

import { useEffect, useState } from "react";

function parseHash(): string {
  const raw = window.location.hash.replace(/^#/, "");
  return raw || "/dashboard";
}

export function useHashRoute(): [string, (route: string) => void] {
  const [route, setRoute] = useState<string>(parseHash);

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = (next: string) => {
    if (parseHash() === next) {
      setRoute(next);
      return;
    }
    window.location.hash = next;
    setRoute(next);
  };

  return [route, navigate];
}

/** Split a route into segments, e.g. "/cases/abc" -> ["cases", "abc"]. */
export function routeSegments(route: string): string[] {
  return route.replace(/^\/+/, "").split("/").filter(Boolean);
}
