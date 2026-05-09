/**
 * nav-schema-validate.js
 *
 * Runs on every page load. Reads the navigation data inlined by Hugo into
 * window.__navigationData__, fetches the JSON Schema from
 * /schemas/models/navigation.json, and validates with Ajv.
 * Results are written to the browser console only — no UI changes.
 *
 * The schema is published at: /schemas/models/navigation.json
 */
import Ajv2020 from 'https://esm.sh/ajv@8/dist/2020';

(async function validateNavigationData() {
  const tag = '[Navigation Schema]';

  const data = window.__navigationData__;
  if (!data) {
    console.warn(tag, 'window.__navigationData__ not found — skipping validation.');
    return;
  }

  let schema;
  try {
    const res = await fetch('/schemas/models/navigation.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    schema = await res.json();
  } catch (err) {
    console.error(tag, 'Failed to fetch navigation schema:', err);
    return;
  }

  const ajv = new Ajv2020({ allErrors: true });
  const validate = ajv.compile(schema);
  const valid = validate(data);

  if (valid) {
    console.info(tag, 'navigation.json validates against schema ✓');
  } else {
    console.warn(tag, `${validate.errors.length} schema violation(s):`, validate.errors);
  }
})();
