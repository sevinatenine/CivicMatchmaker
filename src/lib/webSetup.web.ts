// Web-only setup, imported once from the root layout.
// leaflet.css comes from the CDN <link> in src/app/+html.tsx (Metro can't bundle its url(images/...))
import './leafletDark.css';

// Expo Router's navigation calls Array.prototype.findLast and structuredClone, which Safari
// only has from iOS 15.4. Without these, older iPhones go gray on the first screen change.
if (!Array.prototype.findLast) {
  // eslint-disable-next-line no-extend-native -- polyfill, only when missing
  Object.defineProperty(Array.prototype, 'findLast', {
    configurable: true,
    writable: true,
    value: function <T>(this: T[], pred: (v: T, i: number, a: T[]) => unknown, thisArg?: unknown) {
      for (let i = this.length - 1; i >= 0; i--) {
        if (pred.call(thisArg, this[i], i, this)) return this[i];
      }
      return undefined;
    },
  });
}
if (!Array.prototype.findLastIndex) {
  // eslint-disable-next-line no-extend-native -- polyfill, only when missing
  Object.defineProperty(Array.prototype, 'findLastIndex', {
    configurable: true,
    writable: true,
    value: function <T>(this: T[], pred: (v: T, i: number, a: T[]) => unknown, thisArg?: unknown) {
      for (let i = this.length - 1; i >= 0; i--) {
        if (pred.call(thisArg, this[i], i, this)) return i;
      }
      return -1;
    },
  });
}
// Navigation state is plain JSON, so a JSON round trip is enough
if (typeof globalThis.structuredClone !== 'function') {
  globalThis.structuredClone = <T>(value: T): T =>
    value === undefined ? value : JSON.parse(JSON.stringify(value));
}

/**
 * Phone browsers don't always scroll a text box above the on-screen keyboard, especially when
 * it's inside a scrolling area (every Screen is). So after a text box gets focus, and again
 * when the visible area shrinks for the keyboard, scroll it to the middle of the screen.
 * Returns a cleanup function.
 */
export function keepFocusedInputVisible(): () => void {
  const isTextField = (el: Element | null): el is HTMLElement =>
    !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA');

  const reveal = () => {
    const el = document.activeElement;
    if (isTextField(el)) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
  };

  let timer: ReturnType<typeof setTimeout> | undefined;
  const onFocus = (e: FocusEvent) => {
    if (!isTextField(e.target as Element)) return;
    clearTimeout(timer);
    timer = setTimeout(reveal, 300); // wait for the keyboard to finish opening
  };

  document.addEventListener('focusin', onFocus);
  window.visualViewport?.addEventListener('resize', reveal);
  return () => {
    clearTimeout(timer);
    document.removeEventListener('focusin', onFocus);
    window.visualViewport?.removeEventListener('resize', reveal);
  };
}
