import { useEffect, useState } from 'react';
import { api } from './api.js';

// The archetype registry (labels/emoji/colours/edges) is static, so fetch it
// once and share the result across every badge, card and the network view.
let cache = null;
let inflight = null;

export function useNeurotypes() {
  const [data, setData] = useState(cache);
  useEffect(() => {
    if (cache) {
      setData(cache);
      return;
    }
    if (!inflight) inflight = api.getNeurotypes();
    let active = true;
    inflight
      .then((d) => {
        cache = d;
        if (active) setData(d);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  return data; // { neurotypes: {id: {...}}, order: [...], edges: [...] } | null
}
