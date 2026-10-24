import { LEAFLET_CSS_SRI, LEAFLET_VERSION } from '@/lib/leafletMap';
import { ScrollViewStyleReset, useServerDocumentContext } from 'expo-router/html';
import { type PropsWithChildren } from 'react';

const GLOBAL_CSS = `
body { background-color: #1C1E22; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
body, input, textarea, button {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif;
}
::selection { background: rgba(169, 199, 238, 0.35); }
`;

// Web only: the root HTML for every page. Runs in Node during static rendering, so no DOM here.
// Since SDK 58 the JS bundle, react-native-web styles, CSS and fonts arrive as headNodes/bodyNodes;
// leaving them out gives a page that never loads its JavaScript.
export default function Root({ children }: PropsWithChildren) {
  const { htmlAttributes, bodyAttributes, headNodes, bodyNodes } = useServerDocumentContext();
  return (
    <html lang="en" {...htmlAttributes}>
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        {/* interactive-widget: on Android Chrome, the page shrinks when the keyboard opens
            instead of the keyboard sliding over the text box you're typing in */}
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, shrink-to-fit=no, interactive-widget=resizes-content"
        />
        <meta name="theme-color" content="#23262B" />
        {/* Voting map styles; same file the Android WebView map loads (src/lib/leafletMap.ts) */}
        <link
          rel="stylesheet"
          href={`https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.css`}
          integrity={LEAFLET_CSS_SRI}
          crossOrigin=""
        />
        <ScrollViewStyleReset />
        <style>{GLOBAL_CSS}</style>
        {headNodes}
      </head>
      <body {...bodyAttributes}>
        {children}
        {bodyNodes}
      </body>
    </html>
  );
}
