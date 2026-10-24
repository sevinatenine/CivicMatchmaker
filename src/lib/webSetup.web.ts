// Web-only setup, imported once from the root layout.
// leaflet.css comes from the CDN <link> in src/app/+html.tsx (Metro can't bundle its url(images/...))
import './leafletDark.css';

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
