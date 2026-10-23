import { ScrollViewStyleReset } from 'expo-router/html';
import { type PropsWithChildren } from 'react';

// Web only: the root HTML for every page. Runs in Node during static rendering, so no DOM here.
export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="en">
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
        <ScrollViewStyleReset />
        <style>{'body { background-color: #1C1E22; }'}</style>
      </head>
      <body>{children}</body>
    </html>
  );
}
