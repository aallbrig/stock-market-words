async function main() {
  const main = document.querySelector('main');
  const request = await fetch('/api/all-exchanges.txt');
  const data = await request.text();
  main.innerHTML = data.replaceAll("\n", "<br />")
}

document.addEventListener('DOMContentLoaded', (_) => {
  _ = main();
});
