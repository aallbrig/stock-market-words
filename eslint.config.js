// ESLint v9 flat config (CommonJS — package.json has "type": "commonjs")
module.exports = [
  // ── Standard browser scripts ────────────────────────────────────────────────
  {
    files: ["hugo/site/static/js/**/*.js"],
    ignores: [
      "hugo/site/static/js/portfolio-worker.js",
      "hugo/site/static/js/nav-schema-validate.js",
    ],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        // Browser built-ins
        window: "readonly",
        document: "readonly",
        console: "readonly",
        fetch: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        Worker: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        location: "readonly",
        history: "readonly",
        navigator: "readonly",
        performance: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        requestAnimationFrame: "readonly",
        CustomEvent: "readonly",
        Event: "readonly",
        MutationObserver: "readonly",
        IntersectionObserver: "readonly",
        alert: "readonly",
        confirm: "readonly",
        // jQuery (used in filtered-data.js, raw-ftp-data.js)
        $: "readonly",
        jQuery: "readonly",
        // Bootstrap JS (used in portfolio-extractor.js)
        bootstrap: "readonly",
        // CJS compat guard pattern: `if (typeof module !== 'undefined' && module.exports)`
        module: "writable",
        // Third-party CDN globals
        Chart: "readonly",
        // Project globals
        TickerEngine: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "error",
      "no-console": "off",
    },
  },

  // ── Web Worker (uses `self` as global scope, not `window`) ──────────────────
  {
    files: ["hugo/site/static/js/portfolio-worker.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        self: "readonly",
        console: "readonly",
        fetch: "readonly",
        URL: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        TickerEngine: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "error",
      "no-console": "off",
    },
  },

  // ── ESM script (nav-schema-validate.js uses `import` from CDN URL) ──────────
  {
    files: ["hugo/site/static/js/nav-schema-validate.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        window: "readonly",
        console: "readonly",
        fetch: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "error",
      "no-console": "off",
    },
  },
];
