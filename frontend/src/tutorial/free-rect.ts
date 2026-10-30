/** A rectangle in any one coordinate space (screen pixels, for the tutorial). */
export interface Box {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

const overlaps = (a: Box, b: Box) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;

/**
 * The biggest rectangle inside `area` (kept `margin` away from its edges) that touches none of
 * the `obstacles` (each grown by `pad`): where an info card can sit without covering the labels
 * pointing at the board. Null when no rectangle is at least `minWidth` x `minHeight`.
 *
 * Every side of the best rectangle lies on the area's edge or on an obstacle's edge, so trying
 * all pairs of such coordinates finds it; there are a handful of obstacles, so this is instant.
 */
export function largestFreeRect(
  area: Box,
  obstacles: Box[],
  { margin = 12, pad = 10, minWidth = 320, minHeight = 200 } = {},
): Box | null {
  const inner: Box = {
    left: area.left + margin,
    top: area.top + margin,
    right: area.right - margin,
    bottom: area.bottom - margin,
  };
  const blocked = obstacles
    .map((o) => ({ left: o.left - pad, top: o.top - pad, right: o.right + pad, bottom: o.bottom + pad }))
    .filter((o) => overlaps(o, inner));
  const clamp = (value: number, low: number, high: number) => Math.min(Math.max(value, low), high);
  const xs = [...new Set([inner.left, inner.right, ...blocked.flatMap((o) => [o.left, o.right])])]
    .map((x) => clamp(x, inner.left, inner.right))
    .sort((a, b) => a - b);
  const ys = [...new Set([inner.top, inner.bottom, ...blocked.flatMap((o) => [o.top, o.bottom])])]
    .map((y) => clamp(y, inner.top, inner.bottom))
    .sort((a, b) => a - b);

  let best: Box | null = null;
  let bestArea = 0;
  for (let i = 0; i < xs.length; i++) {
    for (let j = i + 1; j < xs.length; j++) {
      const width = xs[j] - xs[i];
      if (width < minWidth) continue;
      for (let k = 0; k < ys.length; k++) {
        for (let l = k + 1; l < ys.length; l++) {
          const height = ys[l] - ys[k];
          if (height < minHeight || width * height <= bestArea) continue;
          const rect: Box = { left: xs[i], top: ys[k], right: xs[j], bottom: ys[l] };
          if (blocked.some((o) => overlaps(o, rect))) continue;
          best = rect;
          bestArea = width * height;
        }
      }
    }
  }
  return best;
}
