async function main() {
  const body = document.querySelector('body');
  const request = await fetch('./api/all-exchanges.txt');
  const data = await request.text();
  body.innerHTML = data.replaceAll("\n", "<br />")
}

document.addEventListener('DOMContentLoaded', (_) => {
  _ = main();
});
